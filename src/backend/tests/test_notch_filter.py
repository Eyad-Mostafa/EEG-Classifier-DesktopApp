import sys
import os
import pandas as pd
import numpy as np

# --- SETUP PATHS ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.eeg_data import EEGData
from app.algorithms.preprocessing_methods.NotchFilter import NotchFilterStep

def test_notch_filter_logic():
    print("\n" + "="*60)
    print("TEST: Notch Filter (50Hz Powerline Noise Removal)")
    print("="*60)
    
    # --- CREATE TEST DATA WITH 50Hz NOISE ---
    fs = 250  # Sampling rate
    duration = 2.0  # 2 second trial
    n_samples = int(fs * duration)
    t = np.linspace(0, duration, n_samples)
    
    # Create clean signals
    np.random.seed(42)
    
    # Signal 1: 10Hz alpha wave
    alpha_wave = 20 * np.sin(2 * np.pi * 10 * t)
    
    # Signal 2: 20Hz beta wave
    beta_wave = 15 * np.sin(2 * np.pi * 20 * t)
    
    # Signal 3: Mixed frequencies
    mixed_wave = 10 * np.sin(2 * np.pi * 5 * t) + 8 * np.sin(2 * np.pi * 15 * t)
    
    # Add 50Hz powerline noise
    powerline_noise = 30 * np.sin(2 * np.pi * 50 * t)
    
    # Create channels with different signal + noise combinations
    channel_1 = alpha_wave + 0.5 * powerline_noise  # Mild 50Hz contamination
    channel_2 = beta_wave + powerline_noise  # Strong 50Hz contamination
    channel_3 = mixed_wave + 0.3 * powerline_noise  # Weak 50Hz contamination
    
    # Add some random noise
    noise_level = 2
    channel_1 += np.random.normal(0, noise_level, n_samples)
    channel_2 += np.random.normal(0, noise_level, n_samples)
    channel_3 += np.random.normal(0, noise_level, n_samples)
    
    # Create DataFrame
    data_list = []
    for trial_id in [1, 2]:
        for i, time_val in enumerate(t):
            data_list.append({
                'subject_id': 'sub01',
                'session_id': 'ses01',
                'trial_id': trial_id,
                'time_index': i,
                'channel_1': channel_1[i],
                'channel_2': channel_2[i],
                'channel_3': channel_3[i],
                'labels': 'test',
                'category': 'test'
            })
    
    df = pd.DataFrame(data_list)
    print(f"Created test data: {len(df)} samples, {df['trial_id'].nunique()} trials")
    
    # --- CREATE EEGData OBJECT ---
    eeg_data = EEGData(df=df, sampling_rate=fs)
    
    # --- ANALYZE FREQUENCY CONTENT BEFORE FILTERING ---
    print("\n[ANALYSIS] Frequency analysis (Trial 1, Channel 2):")
    from scipy import signal
    from scipy.fft import fft, fftfreq
    
    trial1_ch2 = df[df['trial_id'] == 1]['channel_2'].values
    
    # Compute FFT
    n = len(trial1_ch2)
    yf = fft(trial1_ch2)
    xf = fftfreq(n, 1/fs)
    
    # Find peaks at 50Hz
    freq_idx = np.where((xf >= 45) & (xf <= 55))[0]
    if len(freq_idx) > 0:
        power_50hz = np.max(np.abs(yf[freq_idx]))
        print(f"Power at 50Hz: {power_50hz:.2f}")
    
    # --- RUN NOTCH FILTER ---
    print("\n" + "-"*40)
    print("Running notch filter (freq=50Hz, Q=30)...")
    
    step = NotchFilterStep()
    filtered_data = step.process(
        eeg_data,
        freq=50.0,
        quality_factor=30.0
    )
    
    # --- ANALYZE FREQUENCY CONTENT AFTER FILTERING ---
    print("\n[ANALYSIS] Frequency analysis AFTER filtering (Trial 1, Channel 2):")
    
    filtered_df = filtered_data.df
    trial1_ch2_filtered = filtered_df[filtered_df['trial_id'] == 1]['channel_2'].values
    
    # Compute FFT of filtered signal
    yf_filtered = fft(trial1_ch2_filtered)
    
    # Check 50Hz power reduction
    if len(freq_idx) > 0:
        power_50hz_filtered = np.max(np.abs(yf_filtered[freq_idx]))
        reduction = (power_50hz - power_50hz_filtered) / power_50hz * 100
        print(f"Power at 50Hz after filtering: {power_50hz_filtered:.2f}")
        print(f"Reduction: {reduction:.1f}%")
    
    # --- VERIFY SIGNAL PRESERVATION ---
    print("\n[VERIFICATION] Signal preservation check:")
    
    # Check that lower frequencies are preserved
    low_freq_idx = np.where((xf >= 5) & (xf <= 30))[0]
    if len(low_freq_idx) > 0:
        low_freq_power_before = np.mean(np.abs(yf[low_freq_idx]))
        low_freq_power_after = np.mean(np.abs(yf_filtered[low_freq_idx]))
        preservation = low_freq_power_after / low_freq_power_before * 100
        
        print(f"Low-frequency power (5-30Hz):")
        print(f"  Before: {low_freq_power_before:.2f}")
        print(f"  After:  {low_freq_power_after:.2f}")
        print(f"  Preservation: {preservation:.1f}%")
        
        if preservation > 80:  # Should preserve >80% of signal power
            print("  ✅ Good signal preservation")
        else:
            print("  ❌ Poor signal preservation")
    
    # --- CHECK TIME DOMAIN CHANGES ---
    print("\n[VERIFICATION] Time domain comparison:")
    
    # Check amplitude range
    for ch in ['channel_1', 'channel_2', 'channel_3']:
        trial1_original = df[df['trial_id'] == 1][ch].values
        trial1_filtered = filtered_df[filtered_df['trial_id'] == 1][ch].values
        
        range_original = np.ptp(trial1_original)  # Peak-to-peak
        range_filtered = np.ptp(trial1_filtered)
        
        change = abs(range_filtered - range_original) / range_original * 100
        
        print(f"{ch}:")
        print(f"  Original range: {range_original:.2f}µV")
        print(f"  Filtered range: {range_filtered:.2f}µV")
        print(f"  Change: {change:.1f}%")
    
    # --- CHECK METADATA ---
    print("\n[METADATA]")
    if "notch_params" in filtered_data.meta:
        params = filtered_data.meta["notch_params"]
        print(f"Frequency: {params.get('freq')}Hz")
        print(f"Q factor: {params.get('quality_factor')}")
        print(f"Notch width: {params.get('notch_width', 'N/A'):.2f}Hz")
        print(f"Implementation: {params.get('implementation', 'N/A')}")
    else:
        print("No notch filter parameters found in metadata")
    
    # --- VISUAL CHECK ---
    print("\n[VISUAL CHECK] Sample values (first 20 time points):")
    print("\nOriginal data - Channel 2:")
    print(df[df['trial_id'] == 1][['time_index', 'channel_2']].head(20).to_string())
    
    print("\nFiltered data - Channel 2:")
    print(filtered_df[filtered_df['trial_id'] == 1][['time_index', 'channel_2']].head(20).to_string())
    
    # --- FINAL VERDICT ---
    print("\n" + "="*60)
    print("✅ NOTCH FILTER TEST COMPLETE!")
    print("Check that:")
    print("1. 50Hz power was significantly reduced")
    print("2. Lower frequencies (5-30Hz) were preserved")
    print("3. Signal shape maintained in time domain")
    print("="*60)
    
    return True

if __name__ == "__main__":
    test_notch_filter_logic()