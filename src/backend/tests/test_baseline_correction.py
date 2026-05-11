import sys
import os
import pandas as pd
import numpy as np

# --- SETUP PATHS ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.eeg_data import EEGData
from app.algorithms.preprocessing_methods.BaselineCorrection import BaselineCorrectionStep

def test_baseline_correction_logic():
    print("\n" + "="*60)
    print("TEST: Baseline Correction (Mean Subtraction)")
    print("="*60)
    
    # --- CREATE TEST DATA ---
    fs = 250  # Sampling rate
    duration = 1.0  # 1 second trial
    n_samples = int(fs * duration)
    t = np.linspace(0, duration, n_samples)  # Time vector from 0 to 1 second
    
    # Create 3 channels with different patterns
    # Channel 1: Sine wave with DC offset
    channel_1 = 50 + 10 * np.sin(2 * np.pi * 5 * t)  # 50µV offset + 5Hz sine
    
    # Channel 2: Ramp function (linear drift)
    channel_2 = 30 + 20 * t  # Starting at 30µV, ramping up to 50µV
    
    # Channel 3: Flat line with different offset
    channel_3 = 25 + np.zeros_like(t)  # Constant 25µV
    
    # Add some noise
    np.random.seed(42)
    noise = np.random.normal(0, 2, n_samples)
    channel_1 += noise
    channel_2 += noise
    channel_3 += noise
    
    # Create DataFrame with 2 trials
    data_list = []
    
    for trial_id in [1, 2]:
        for i, time_val in enumerate(t):
            data_list.append({
                'subject_id': 'sub01',
                'session_id': 'ses01',
                'trial_id': trial_id,
                'time_index': i,
                'channel_1': channel_1[i] + (trial_id-1)*5,  # Different offset per trial
                'channel_2': channel_2[i] + (trial_id-1)*3,
                'channel_3': channel_3[i] + (trial_id-1)*2,
                'labels': 'test',
                'category': 'test'
            })
    
    df = pd.DataFrame(data_list)
    print(f"Created test data: {len(df)} samples, {df['trial_id'].nunique()} trials")
    
    # --- CREATE EEGData OBJECT ---
    eeg_data = EEGData(df=df, sampling_rate=fs)
    
    # --- ANALYZE BASELINE PERIOD ---
    print("\n[ANALYSIS] Baseline period statistics (first 200ms):")
    baseline_samples = int(0.2 * fs)  # First 200ms
    
    for trial_id in [1, 2]:
        trial_data = df[df['trial_id'] == trial_id]
        baseline_data = trial_data.head(baseline_samples)
        
        print(f"\nTrial {trial_id} Baseline (0-200ms):")
        for ch in ['channel_1', 'channel_2', 'channel_3']:
            mean_val = baseline_data[ch].mean()
            std_val = baseline_data[ch].std()
            print(f"  {ch}: mean = {mean_val:.2f}µV, std = {std_val:.2f}µV")
    
    # --- RUN BASELINE CORRECTION ---
    print("\n" + "-"*40)
    print("Running baseline correction (baseline: 0.0-0.2s)...")
    
    step = BaselineCorrectionStep()
    corrected_data = step.process(
        eeg_data,
        baseline_start=0.0,
        baseline_end=0.2
    )
    
    # --- VERIFY RESULTS ---
    print("\n[VERIFICATION] Checking baseline correction results:")
    
    corrected_df = corrected_data.df
    all_passed = True
    
    for trial_id in [1, 2]:
        trial_corrected = corrected_df[corrected_df['trial_id'] == trial_id]
        baseline_corrected = trial_corrected.head(baseline_samples)
        
        print(f"\nTrial {trial_id} AFTER correction (0-200ms):")
        for ch in ['channel_1', 'channel_2', 'channel_3']:
            mean_val = baseline_corrected[ch].mean()
            std_val = baseline_corrected[ch].std()
            
            # Baseline should be near zero after correction
            if abs(mean_val) < 0.1:  # Allow small tolerance
                print(f"  ✅ {ch}: mean = {mean_val:.3f}µV (≈0)")
            else:
                print(f"  ❌ {ch}: mean = {mean_val:.3f}µV (NOT ≈0)")
                all_passed = False
    
    # --- CHECK METADATA ---
    print("\n[METADATA]")
    if "baseline_params" in corrected_data.meta:
        params = corrected_data.meta["baseline_params"]
        print(f"Method: {params.get('method', 'N/A')}")
        print(f"Baseline window: {params.get('baseline_start')} to {params.get('baseline_end')}s")
        print(f"Sample indices: {params.get('baseline_samples', 'N/A')}")
    else:
        print("No baseline parameters found in metadata")
    
    # --- VISUAL CHECK (Optional) ---
    print("\n[VISUAL CHECK] Mean values over time (first trial):")
    trial1_original = df[df['trial_id'] == 1]
    trial1_corrected = corrected_df[corrected_df['trial_id'] == 1]
    
    print("\nOriginal data (first 10 time points):")
    print(trial1_original[['time_index', 'channel_1', 'channel_2', 'channel_3']].head(10).to_string())
    
    print("\nCorrected data (first 10 time points):")
    print(trial1_corrected[['time_index', 'channel_1', 'channel_2', 'channel_3']].head(10).to_string())
    
    # --- FINAL VERDICT ---
    print("\n" + "="*60)
    if all_passed:
        print("✅ BASELINE CORRECTION TEST PASSED!")
        print("All baseline periods are near zero after correction.")
    else:
        print("❌ BASELINE CORRECTION TEST FAILED!")
        print("Some baseline periods still have significant mean values.")
    print("="*60)
    
    return all_passed

if __name__ == "__main__":
    test_baseline_correction_logic()