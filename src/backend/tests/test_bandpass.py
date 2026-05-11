import sys
import os
import pandas as pd
import numpy as np
from scipy.fft import fft, fftfreq

# --- 1. SETUP PATHS ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.eeg_data import EEGData
# Adjust import path if needed
from app.algorithms.preprocessing_methods.Bandpass import BandpassFilter 

def test_bandpass_logic():
    print("\n--- STARTING TEST: Bandpass Filter (MNE Implementation) ---")

    # --- 2. CREATE FAKE DATA ---
    # Setup: 4 seconds at 250 Hz
    sfreq = 250 
    duration = 4 
    t = np.linspace(0, duration, duration * sfreq, endpoint=False)
    
    # A. Target Signal (Keep): 10 Hz Sine Wave
    freq_target = 10 
    sig_target = np.sin(2 * np.pi * freq_target * t)
    
    # B. High Noise (Remove): 60 Hz (Mains Hum)
    freq_noise_high = 60 
    sig_noise_high = 0.5 * np.sin(2 * np.pi * freq_noise_high * t)
    
    # C. Low Drift (Remove): 0.1 Hz (Sweat/Movement)
    freq_noise_low = 0.1
    sig_noise_low = 2.0 * np.sin(2 * np.pi * freq_noise_low * t)

    # Combine them: Signal + Noise + Drift
    combined_signal = sig_target + sig_noise_high + sig_noise_low

    # Create DataFrame
    df = pd.DataFrame({
        "time_index": np.arange(len(t)),
        "channel_1": combined_signal,
        "channel_2": combined_signal, # Duplicate to test multi-channel
        "subject_id": ["sub01"] * len(t),
        "session_id": ["ses01"] * len(t),
        "trial_id": [1] * len(t)
    })

    # Initialize Data Object
    eeg_data = EEGData(df=df)
    # Ensure sampling rate is set (MNE needs this!)
    if not hasattr(eeg_data, 'sampling_rate') or eeg_data.sampling_rate is None:
         eeg_data.meta = {"sampling_rate": sfreq}
    
    print(f"-> Created Data ({duration}s @ {sfreq}Hz)")
    print(f"-> Components: {freq_target}Hz (Target), {freq_noise_high}Hz (High Noise), {freq_noise_low}Hz (Low Drift)")

    # --- 3. RUN ALGORITHM ---
    # Filter Settings: Pass frequencies between 1.0 and 40.0 Hz
    step = BandpassFilter()
    print("-> Applying Filter: Low=1.0Hz, High=40.0Hz")
    
    result = step.process(eeg_data, low=1.0, high=40.0)
    
    # --- 4. VERIFY RESULTS (FFT Analysis) ---
    cleaned_signal = result.df["channel_1"].values
    
    # Calculate Power Spectrum using FFT
    N = len(cleaned_signal)
    yf = fft(cleaned_signal)
    xf = fftfreq(N, 1 / sfreq)
    
    # Find indices for our frequencies of interest
    idx_target = np.argmin(np.abs(xf - freq_target))
    idx_high = np.argmin(np.abs(xf - freq_noise_high))
    
    power_target = np.abs(yf[idx_target])
    power_high = np.abs(yf[idx_high])
    
    print(f"\n[FFT Analysis]")
    print(f"-> Power at {freq_target}Hz (Should be High): {power_target:.2f}")
    print(f"-> Power at {freq_noise_high}Hz (Should be Low):  {power_high:.2f}")

    # --- CHECKS ---
    
    # CHECK 1: High Frequency Noise Removal
    # The noise power should be tiny (< 5%) compared to the target signal
    if power_high < (power_target * 0.05):
        print("✅ PASS: High frequency noise (60Hz) successfully removed.")
    else:
        print(f"❌ FAIL: 60Hz noise still present (Power: {power_high:.2f})")

    # CHECK 2: Low Frequency Drift Removal
    # The original drift was huge (Amplitude 2.0). 
    # If removed, the signal should be centered around 0.
    mean_val = np.mean(cleaned_signal)
    if np.abs(mean_val) < 0.1:
        print(f"✅ PASS: Low frequency drift removed (Mean is centered: {mean_val:.4f}).")
    else:
        print(f"❌ FAIL: Low frequency drift remains (Mean: {mean_val:.4f})")

    # CHECK 3: Signal Quality (Correlation)
    # Does the cleaned signal look like the original pure sine wave?
    correlation = np.corrcoef(cleaned_signal, sig_target)[0, 1]
    print(f"-> Correlation with pure target signal: {correlation:.4f}")
    
    if correlation > 0.9:
        print("✅ PASS: Signal shape preserved (High Fidelity).")
    else:
        print("❌ FAIL: Signal distorted or phase shifted too much.")

if __name__ == "__main__":
    test_bandpass_logic()