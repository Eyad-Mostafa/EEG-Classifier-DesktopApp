import numpy as np
import pandas as pd
import mne
from app.schemas.domain_enum import DomainType
from app.algorithms.base import BaseStep, AlgorithmParameter, AlgorithmExample
from app.models.eeg_data import EEGData
from app.core.registry import register_algorithm

class RemoveBadChannelsStep(BaseStep):
    id = "remove_bad_channels"
    name = "Remove Bad Channels"
    description = "Detects bad channels via statistics. Uses Global Average or Spherical Spline based on montage selection."
    category = "Cleaning"
    domainType = DomainType.TIME
    type = "preprocessing"

    howItWorks = (
        "Computes variance and channel-to-channel correlation. "
        "If a montage is selected and channels are mapped correctly, it uses Spherical Spline Interpolation (MNE). "
        "Otherwise, it falls back to Global Mean Interpolation."
    )

    useCases = [
        "Remove channels with hardware failure or bad scalp contact",
        "Enhance signal consistency across trials"
    ]

    relatedAlgorithms = ["ica_artifact_removal", "common_average_reference"]

    examples = [
        AlgorithmExample(
            title="Removing broken channels",
            description="Detects noisy channels and interpolates them."
        )
    ]

    parameters = [
        AlgorithmParameter(
            name="zscore_threshold",
            type="number",
            value="3.0",
            default="3.0",
            min=1.0,
            max=10.0,
            required=True
        ),
        AlgorithmParameter(
            name="corr_threshold",
            type="number",
            value="0.4",
            default="0.4",
            min=0.0,
            max=1.0,
            required=True
        ),
        AlgorithmParameter(
            name="montage_system",
            type="string",
            value="standard_1020",
            default="standard_1020",
            options=["standard_1020", "standard_1005", "biosemi128", "None"],
            required=True,
            description="The standard electrode layout system to use for interpolation."
        ),
        # --- Mapping Parameter (For next semester) ---
        AlgorithmParameter(
            name="channel_mapping", 
            type="object", 
            value="{}", 
            default="{}", 
            required=False,
            description="Map generic names to the selected montage. E.g. {'channel_1': 'Fp1'}"
        )
    ]

    def process(self, data: EEGData, **params) -> EEGData:
        # --- 1. Parameter Extraction ---
        validated = self.validate_parameters(params)
        z_th = float(validated["zscore_threshold"])
        corr_th = float(validated["corr_threshold"])
        montage_name = validated["montage_system"]
        sfreq = data.sampling_rate

        # Safely parse the mapping
        channel_map = validated.get("channel_mapping", {})
        if not isinstance(channel_map, dict):
            channel_map = {}

        df = data.df
        channel_cols = data.channel_cols

        # --- 2. Load Montage (If selected) ---
        has_geometry = False
        montage = None
        
        # Only attempt to load if user didn't pick "None"
        if montage_name and montage_name != "None":
            try:
                montage = mne.channels.make_standard_montage(montage_name)
                # We assume geometry is possible until proven otherwise (e.g. mapping mismatch)
                has_geometry = True
            except Exception as e:
                print(f"Warning: Could not load montage '{montage_name}'. Reverting to No-Geometry mode.")
                has_geometry = False
        
        # Check if we have a mapping to bridge the gap between Generic Names and Montage
        # If we have generic names (channel_1) but NO mapping, we can't use the montage.
        valid_map = {k: v for k, v in channel_map.items() if k in channel_cols}
        
        if has_geometry and not valid_map:
            # Special Check: Do the columns ALREADY match the montage? (e.g. user uploaded file with 'Fp1', 'C3')
            # If columns are 'Fp1', 'C3' and montage is 1020, we don't need a map!
            common_channels = set(channel_cols).intersection(set(montage.ch_names))
            if len(common_channels) < 3: # Threshold: at least 3 channels must match to attempt spline
                has_geometry = False
                # If we are in "Semester 1 mode" (Generic names, no map), this effectively disables MNE spline silently.

        processed_sessions = []
        session_grouped = df.groupby(["subject_id", "session_id"], sort=False)

        for (subject_id, session_id), session_df in session_grouped:
            
            # --- 3. Create MNE Object ---
            eeg_data = session_df[channel_cols].values.T
            info = mne.create_info(ch_names=channel_cols, sfreq=sfreq, ch_types='eeg')
            raw = mne.io.RawArray(eeg_data, info, verbose=False)
            
            # --- 4. Apply Geometry (If available) ---
            if has_geometry:
                try:
                    # A. Apply mapping if provided
                    if valid_map:
                        raw.rename_channels(valid_map)
                    
                    # B. Apply Montage
                    raw.set_montage(montage, on_missing='ignore', verbose=False)
                except Exception:
                    has_geometry = False 
            
            # --- 5. Detect Bad Channels ---
            data_np = raw.get_data()
            
            # Variance
            variances = np.var(data_np, axis=1)
            z_scores = (variances - np.mean(variances)) / (np.std(variances) + 1e-6)
            
            # Correlation
            corr_matrix = np.corrcoef(data_np)
            corr_scores = np.nanmean(corr_matrix, axis=1)
            
            bad_indices = np.where((np.abs(z_scores) > z_th) | (corr_scores < corr_th))[0]
            bad_names = [raw.ch_names[i] for i in bad_indices]
            raw.info['bads'] = bad_names

            # --- 6. Interpolate (The Logic Switch) ---
            if bad_names:
                interpolated = False
                
                if has_geometry:
                    # MODE A: Spline Interpolation (Best Practice)
                    try:
                        raw.interpolate_bads(reset_bads=True, method=dict(eeg='spline'), verbose=False)
                        interpolated = True
                    except Exception:
                        pass # Fail silently and fall to manual mean

                if not interpolated:
                    # MODE B: Manual Global Average (Fallback)
                    self._manual_mean_interpolation(raw, bad_names)

            # --- 7. Restore Names (Consistency) ---
            if has_geometry and valid_map:
                reverse_map = {v: k for k, v in valid_map.items()}
                try:
                    raw.rename_channels(reverse_map)
                except:
                    pass

            # --- 8. Reconstruct DataFrame ---
            cleaned_data = raw.get_data().T
            cleaned_session_df = pd.DataFrame(cleaned_data, columns=channel_cols, index=session_df.index)
            
            meta_cols = [c for c in session_df.columns if c not in channel_cols]
            combined = pd.concat([session_df[meta_cols], cleaned_session_df], axis=1)
            processed_sessions.append(combined)

        final_df = pd.concat(processed_sessions)
        data.df = final_df
        data.meta["last_step"] = self.name
        
        return data

    def _manual_mean_interpolation(self, raw, bad_names):
        """Helper for manual mean interpolation when no geometry is available."""
        data = raw.get_data()
        all_names = raw.ch_names
        try:
            bad_indices = [all_names.index(ch) for ch in bad_names]
        except ValueError:
            return 

        good_indices = [i for i in range(len(all_names)) if i not in bad_indices]
        
        if good_indices:
            mean_signal = np.mean(data[good_indices, :], axis=0)
            for bad_idx in bad_indices:
                data[bad_idx, :] = mean_signal
            
            raw._data = data
            raw.info['bads'] = []

register_algorithm(RemoveBadChannelsStep())