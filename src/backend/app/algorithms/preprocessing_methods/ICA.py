"""
ICA Artifact Removal Step (MNE Implementation)
Removes artifacts from EEG channels using MNE-Python's ICA with 10-20 Montage Support.
"""
import pandas as pd
import mne
from app.schemas.domain_enum import DomainType
from app.algorithms.base import BaseStep, AlgorithmParameter
import warnings
from sklearn.exceptions import ConvergenceWarning
from app.models.eeg_data import EEGData
from app.core.registry import register_algorithm

class ICAArtifactRemovalMNE(BaseStep):
    id = "ica_artifact_removal"
    name = "ICA Artifact Removal"
    description = "Decomposes EEG signals using MNE's FastICA to separate and automatically remove artifacts."
    category = "Artifact Removal"
    domainType = DomainType.TIME
    type = "preprocessing"
    
    howItWorks = "Maps channels to standard montage, fits FastICA spatially, automatically identifies eye blink components using a proxy channel, and reconstructs cleaned signals."
    useCases = [
        "Robust, automated removal of eye blinks using MNE infrastructure",
        "Spatial filtering using 10-20 system coordinates"
    ]
    
    parameters = [
        AlgorithmParameter(name="n_components", type="number", value="0.99", default="0.99", min=0.0, max=1.0, 
                          description="Number of components to keep (int) or variance to explain (float)"),
        AlgorithmParameter(name="method", type="string", value="fastica", default="fastica", 
                          description="ICA method: 'fastica', 'infomax', or 'picard'"),
        AlgorithmParameter(name="max_iter", type="number", value="500", default="500", 
                          description="Maximum iterations for convergence (prevent infinite loops)"),
        AlgorithmParameter(name="random_state", type="number", value="42", default="42"),
        AlgorithmParameter(name="eog_channel", type="string", value="Fp1", default="Fp1", 
                          description="Channel to use as a proxy for eye blinks (e.g., Fp1, Fp2, or an EOG channel)"),
        AlgorithmParameter(name="eog_threshold", type="number", value="2.5", default="3.0", 
                          description="Z-score threshold to identify blinks. Lower values (e.g., 2.0 or 1.5) are more aggressive.")
    ]

    def process(self, data: EEGData, **params) -> EEGData:
        # 1. Parse Parameters
        validated_params = self.validate_parameters(params)
        
        n_comp_param = float(validated_params.get("n_components", 0.99))
        n_components = int(n_comp_param) if n_comp_param >= 1 else n_comp_param
        
        method = validated_params.get("method", "fastica")
        # Increase default iterations to ensure convergence
        max_iter = int(validated_params.get("max_iter", 1000))
        
        sfreq = data.sampling_rate
        random_state = int(validated_params.get("random_state", 42))
        
        # Extract the new EOG parameters
        eog_channel = validated_params.get("eog_channel", "Fp1")
        eog_threshold = float(validated_params.get("eog_threshold", 3.0))

        # --- A. RETRIEVE CONFIGURATION ---
        channel_mapping = data.meta.get("channel_mapping", {})
        montage_name = data.meta.get("montage", "standard_1020")

        df = data.df
        channel_cols = data.channel_cols 
        
        meta_cols = [col for col in df.columns if col not in channel_cols]
        processed_chunks = []

        # 2. Group by Subject and Session
        session_grouped = df.groupby(['subject_id', 'session_id'], sort=False)

        for (subject_id, session_id), session_df in session_grouped:
            
            # --- B. PREPARE MNE DATA ---
            data_values = session_df[channel_cols].values.T
            
            mne_ch_names = []
            for col in channel_cols:
                if col in channel_mapping and channel_mapping[col].strip():
                    mne_ch_names.append(channel_mapping[col].strip())
                else:
                    mne_ch_names.append(col)

            info = mne.create_info(ch_names=mne_ch_names, sfreq=sfreq, ch_types='eeg')
            raw = mne.io.RawArray(data_values, info, verbose=False)

            # --- C. APPLY MONTAGE ---
            try:
                montage = mne.channels.make_standard_montage(montage_name)
                raw.set_montage(montage, on_missing='ignore')
            except Exception as e:
                print(f"[Warning] Could not set montage '{montage_name}': {e}")

            # --- D. FIT ICA ---
            try:
                ica = mne.preprocessing.ICA(
                    n_components=n_components,
                    method=method,
                    max_iter=max_iter, 
                    random_state=random_state,
                    verbose=False
                )
                
                # Force the ConvergenceWarning to act as a strict Exception
                with warnings.catch_warnings():
                    warnings.simplefilter("error", category=ConvergenceWarning)
                    ica.fit(raw)

                # --- E. AUTOMATIC ARTIFACT DETECTION (With Smart Fallback & Threshold) ---
                actual_eog_channel = None
                
                # 1. Check if the user's requested channel exists
                if eog_channel in raw.ch_names:
                    actual_eog_channel = eog_channel
                else:
                    # 2. Smart Fallback: Hunt for common frontal/eye channels
                    # Ordered from best (closest to eyes) to acceptable
                    fallback_list = ['Fp2', 'Fp1', 'Fpz', 'AF7', 'AF8', 'EOG', 'eog', 'Fz', 'F7', 'F8']
                    for fallback in fallback_list:
                        if fallback in raw.ch_names:
                            actual_eog_channel = fallback
                            print(f"[Info] Requested EOG channel '{eog_channel}' not found. Auto-falling back to '{fallback}'.")
                            break

                # 3. Execute Detection using the threshold
                if actual_eog_channel:
                    # MNE calculates scores to find the bad components based on our aggressive threshold
                    eog_indices, eog_scores = ica.find_bads_eog(raw, ch_name=actual_eog_channel, threshold=eog_threshold, verbose=False)
                    # Tell ICA to exclude these specific components
                    ica.exclude = eog_indices
                    print(f"[Info] Found and excluded {len(eog_indices)} blink components using {actual_eog_channel} (threshold: {eog_threshold}).")
                else:
                    # 4. Total Failure State
                    print(f"[Warning] No frontal or EOG proxy channels found in {raw.ch_names}. "
                          "ICA cannot automatically detect blinks. Zero components removed.")
                    
                # --- F. APPLY & RECONSTRUCT ---
                # This apply function will now drop the components listed in ica.exclude
                raw_cleaned = ica.apply(raw.copy())

                cleaned_data = raw_cleaned.get_data().T
                
                # --- G. RESTORE ORIGINAL NAMES ---
                cleaned_session_df = pd.DataFrame(
                    cleaned_data,
                    columns=channel_cols, 
                    index=session_df.index
                )
                
                meta_data_df = session_df[meta_cols]
                combined_chunk = pd.concat([meta_data_df, cleaned_session_df], axis=1)
                processed_chunks.append(combined_chunk)

            except ConvergenceWarning:
                # Halt immediately if ICA spins its wheels
                raise ValueError(
                    f"ICA failed to converge for Subject {subject_id} Session {session_id}. "
                    "The data is too noisy. Ensure you apply a High-Pass Filter (e.g., 1 Hz) before running ICA."
                )
            except Exception as e:
                # Halt the pipeline instead of just printing and continuing
                raise ValueError(f"MNE ICA Failed for Subject {subject_id} Session {session_id}: {str(e)}")

        # 3. Reassemble
        if processed_chunks:
            final_df = pd.concat(processed_chunks)
        else:
            final_df = df.copy()

        data.df = final_df
        data.meta["last_step"] = self.name
        data.meta["mne_ica_params"] = {
            "method": method, 
            "n_components": n_components, 
            "montage_used": montage_name,
            "max_iter": max_iter,
            "eog_channel_used": eog_channel,
            "eog_threshold_used": eog_threshold
        }

        return data
    
register_algorithm(ICAArtifactRemovalMNE())