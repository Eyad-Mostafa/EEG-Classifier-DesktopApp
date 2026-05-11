import sys
import os
import pandas as pd
import numpy as np

# --- 1. SETUP PATHS ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.eeg_data import EEGData
# Ensure this path matches your actual file structure
from app.algorithms.preprocessing_methods.remove_bad_channels import RemoveBadChannelsStep

def test_remove_bad_channels_logic():
    print("\n--- STARTING TEST: Remove Bad Channels (Global Average vs MNE Spline) ---")

    # --- 2. CREATE FAKE DATA ---
    fs = 250
    duration = 2
    t = np.linspace(0, duration, duration * fs)
    n_samples = len(t)

    s1 = np.sin(2 * np.pi * 10 * t) 
    s2 = np.sin(2 * np.pi * 10 * t) * 0.9 + 0.1 
    s3 = np.sin(2 * np.pi * 10 * t) * 0.8 - 0.1
    # Channel 4 is the BAD CHANNEL
    s4 = np.random.normal(0, 10, size=n_samples) 

    data_matrix = np.vstack([s1, s2, s3, s4]).T
    channels = ["channel_1", "channel_2", "channel_3", "channel_4"]
    
    df = pd.DataFrame(data_matrix, columns=channels)
    
    # Add metadata columns
    df["subject_id"] = "sub01"
    df["session_id"] = "ses01"
    df["trial_id"] = 1
    
    print(f"-> Created Data with 4 channels.")
    print(f"-> Channel 4 is NOISY (Std Dev: {np.std(s4):.2f})")

    # ---------------------------------------------------------
    # TEST A: SEMESTER 1 MODE (Generic Names)
    # ---------------------------------------------------------
    print("\n[TEST A] Semester 1 Mode: Generic Names (Global Average)")
    
    # --- FIX: Initialize with ONLY DataFrame ---
    eeg_data_A = EEGData(df=df.copy())
    
    # --- FIX: Manually inject sampling rate if needed by properties ---
    # Usually stored in meta or inferred. We set it here to be safe.
    if not hasattr(eeg_data_A, 'sampling_rate') or eeg_data_A.sampling_rate is None:
         eeg_data_A.meta = {"sampling_rate": 250.0}
    
    step = RemoveBadChannelsStep()
    result_A = step.process(eeg_data_A, zscore_threshold=3.0)
    
    cleaned_A = result_A.df["channel_4"].values
    std_A = np.std(cleaned_A)
    print(f"-> Post-Processing Ch4 Std Dev: {std_A:.2f}")

    if std_A < 2.0:
        print("✅ PASS: Noise removed from Channel 4.")
    else:
        print("❌ FAIL: Channel 4 is still noisy.")

    # ---------------------------------------------------------
    # TEST B: SEMESTER 2 MODE (Mapped Names)
    # ---------------------------------------------------------
    print("\n[TEST B] Semester 2 Mode: Mapped Names (MNE Spline Interpolation)")
    
    # --- FIX: Initialize with ONLY DataFrame ---
    eeg_data_B = EEGData(df=df.copy())
    if not hasattr(eeg_data_B, 'sampling_rate') or eeg_data_B.sampling_rate is None:
         eeg_data_B.meta = {"sampling_rate": 250.0}

    mapping = {
        "channel_1": "Fp1",
        "channel_2": "Fp2",
        "channel_3": "Fz",
        "channel_4": "Pz" # Bad Channel
    }

    result_B = step.process(
        eeg_data_B, 
        zscore_threshold=3.0, 
        channel_mapping=mapping
    )

    cleaned_B = result_B.df["channel_4"].values
    
    if np.std(cleaned_B) < 2.0:
        print("✅ PASS: Noise removed using MNE Spline.")
    else:
        print("❌ FAIL: Channel 4 is still noisy.")

if __name__ == "__main__":
    test_remove_bad_channels_logic()