import sys
import os
import pandas as pd
import numpy as np

# --- 1. SETUP PATHS ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.eeg_data import EEGData
# Adjust the import path to match where your spectral_analysis.py actually lives
from app.algorithms.analysis_methods.spectral_analysis import SpectralAnalysis

def test_spectral_logic():
    print("\n--- STARTING TEST: Spectral Analysis (Welch's Method) ---")

    # --- 2. CREATE FAKE DATA (Pure Alpha Waves) ---
    # We create a signal that is 100% Alpha (10 Hz)
    sfreq = 250 
    duration = 4 
    t = np.linspace(0, duration, duration * sfreq, endpoint=False)
    
    # Generate 10Hz Sine Wave (Alpha is 8-13Hz)
    freq_target = 10 
    sig_target = np.sin(2 * np.pi * freq_target * t)
    
    # Add tiny noise so it's not perfect (makes math more realistic)
    noise = np.random.normal(0, 0.1, len(t))
    combined_signal = sig_target + noise

    df = pd.DataFrame({
        "time_index": np.arange(len(t)),
        "channel_1": combined_signal, # This channel has the Alpha wave
        "channel_2": noise,           # This channel is just silence/noise
        "subject_id": ["sub01"] * len(t),
        "session_id": ["ses01"] * len(t),
        "trial_id": [1] * len(t)
    })

    eeg_data = EEGData(df=df)
    # Inject sampling rate if not auto-detected
    if not hasattr(eeg_data, 'sampling_rate') or eeg_data.sampling_rate is None:
         eeg_data.meta = {"sampling_rate": sfreq}
    
    print(f"-> Created Data: Channel 1 has strong {freq_target}Hz (Alpha) signal.")

    # --- 3. RUN ALGORITHM ---
    step = SpectralAnalysis()
    # Using window_size=2 seconds for good frequency resolution
    result = step.process(eeg_data, window_size=2)
    
    # --- 4. VERIFY RESULTS ---
    # Retrieve the results dictionary
    results_payload = result.analysis_results[step.id]
    analysis_data = results_payload["analysis_data"]
    
    # Get results specifically for Channel 1 (The Alpha Channel)
    ch1_res = analysis_data["spectral_results"]["channel_1"]
    
    print("\n[Results for Channel 1]")
    print(f"-> Dominant Band Detected: {ch1_res['dominant_band'].upper()}")
    
    # Print power distribution
    print("-> Power Distribution:")
    for band, data in ch1_res["band_powers"].items():
        print(f"   - {band}: {data['relative_power']:.4f}")

    # --- ASSERTIONS ---
    
    # CHECK 1: Dominant Band Logic
    if ch1_res["dominant_band"] == "alpha":
        print("✅ PASS: Correctly identified 'Alpha' as the dominant band.")
    else:
        print(f"❌ FAIL: Expected 'alpha', but got '{ch1_res['dominant_band']}'.")

    # CHECK 2: Relative Power Accuracy
    # Since the signal is almost pure 10Hz, Alpha power should be > 50% (0.5)
    alpha_power = ch1_res["band_powers"]["alpha"]["relative_power"]
    if alpha_power > 0.5:
        print(f"✅ PASS: Alpha power is high ({alpha_power:.2f}), confirming accurate PSD calculation.")
    else:
        print(f"❌ FAIL: Alpha power is too low ({alpha_power:.2f}). Calculation error likely.")

    # CHECK 3: Visualization Generation
    vis_data = results_payload["visualization_data"]["topographic_map"]
    if vis_data and vis_data.startswith("data:image/png;base64"):
        print("✅ PASS: Base64 Plot string generated successfully.")
    else:
        print("❌ FAIL: Plot generation failed.")

if __name__ == "__main__":
    test_spectral_logic()