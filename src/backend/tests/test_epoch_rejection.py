import sys
import os
import pandas as pd
import numpy as np

# --- 1. SETUP PATHS ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.eeg_data import EEGData
from app.algorithms.preprocessing_methods.epoch_rejection import EpochRejectionStep 

def test_epoch_rejection_logic():
    print("\n--- STARTING TEST: Epoch Rejection (Amplitude & Variance) ---")
    
    # --- 2. CREATE FAKE DATA (4 Channels for better stats) ---
    # We create 3 Trials (10 samples each)
    # Trial 1: Perfect Data (All 0s) -> KEEP
    # Trial 2: High Amplitude Spike -> REJECT (Amplitude Fail)
    # Trial 3: High Variance (Noisy) -> REJECT (Variance Fail)
    
    # Base data: 30 samples (3 trials * 10 samples)
    n_samples = 30
    data = {
        'subject_id': [1] * n_samples,
        'session_id': [1] * n_samples,
        'trial_id':   [1]*10 + [2]*10 + [3]*10,
        'channel_1':  [0.0] * n_samples,
        'channel_2':  [0.0] * n_samples,
        'channel_3':  [0.0] * n_samples,
        'channel_4':  [0.0] * n_samples, # 4th channel helps Z-score math
        'labels':     ['test'] * n_samples,
        'category':   ['test'] * n_samples,
        'time_index': range(n_samples)
    }
    df = pd.DataFrame(data)
    
    # --- INJECT FAULTS ---

    # TRIAL 2: Amplitude Fault
    # Inject a huge spike (500) in Channel 1. 
    # This exceeds amplitude_threshold (100).
    print("-> Injecting Amplitude Spike (500uV) into Trial 2...")
    df.loc[15, 'channel_1'] = 500.0 

    # TRIAL 3: Variance Fault
    # We want high variance but LOW amplitude (to prove it's not the amp filter working).
    # We make Channel 1 "noisy" (-40 to +40) while others are flat (0).
    # The amplitude (40) is < 100, so it PASSES the amplitude check.
    # But Channel 1's variance will be huge compared to Ch2, Ch3, Ch4.
    print("-> Injecting Variance Noise (+/- 40uV) into Trial 3...")
    # Oscillate between -40 and 40
    df.loc[20:29, 'channel_1'] = [40, -40, 35, -35, 40, -40, 30, -30, 40, -40]

    # Load into Data Model
    eeg_data = EEGData(df=df)

    # MANUAL MATH CHECK (What is the code actually calculating?)
    print(f"\n[Manual Calculation for Trial 3]")
    trial_3_data = df[df['trial_id'] == 3][['channel_1', 'channel_2', 'channel_3', 'channel_4']].values
    
    # Step A: Variance per channel
    variances = np.var(trial_3_data, axis=0)
    print(f"-> Variances per channel: {variances}")
    
    # Step B: Mean and Std of those variances
    mean_var = np.mean(variances)
    std_var = np.std(variances)
    print(f"-> Mean Variance: {mean_var:.2f}")
    print(f"-> Std  Variance: {std_var:.2f}")
    
    # Step C: Z-Scores
    z_scores = (variances - mean_var) / (std_var + 1e-8)
    max_z = np.max(np.abs(z_scores))
    print(f"-> Z-Scores: {z_scores}")
    print(f"-> MAX Z-Score: {max_z:.4f}")
    
    # --- 3. RUN ALGORITHM ---
    step = EpochRejectionStep()
    
    # Thresholds: 
    # Amp = 100 (Trial 2 fails this)
    # Var = 2.0 (Trial 3 fails this because Ch1 is wildly different from Ch2,3,4)
    print(f"-> Running Process (Amp Thresh=100, Var Thresh=2.0)...")
    result_data = step.process(
        eeg_data, 
        amplitude_threshold=100.0, 
        variance_threshold=1.5
    )

    # --- 4. VERIFY RESULTS ---
    remaining = result_data.df['trial_id'].unique()
    print(f"-> Original Trials: [1, 2, 3]")
    print(f"-> Remaining Trials: {remaining}")

    # CHECK 1: Good Data
    if 1 in remaining:
        print("✅ PASS: Trial 1 (Clean) was retained.")
    else:
        print("❌ FAIL: Trial 1 (Clean) was wrongly removed.")

    # CHECK 2: Amplitude
    if 2 not in remaining:
        print("✅ PASS: Trial 2 (Amplitude Spike) was rejected.")
    else:
        print("❌ FAIL: Trial 2 (Amplitude Spike) was NOT rejected.")

    # CHECK 3: Variance
    if 3 not in remaining:
        print("✅ PASS: Trial 3 (High Variance/Noise) was rejected.")
    else:
        print("❌ FAIL: Trial 3 (High Variance) was NOT rejected.")

if __name__ == "__main__":
    test_epoch_rejection_logic()