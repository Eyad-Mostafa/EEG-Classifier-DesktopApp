"""
Notch Filter Step
Removes powerline noise (50/60 Hz) from EEG signals
"""

import pandas as pd
import numpy as np
import mne
from app.schemas.domain_enum import DomainType
from app.algorithms.base import BaseStep , AlgorithmParameter ,AlgorithmExample
from app.models.eeg_data import EEGData
from app.core.registry import register_algorithm


class NotchFilterStep(BaseStep):
    id = "notch_filter"
    name = "Notch Filter"
    description = "Removes powerline noise (50/60 Hz) from EEG channels using a notch filter."
    category = "Filtering"
    domainType = DomainType.TIME
    type = "preprocessing"
    howItWorks = (
        "Applies a narrow-band stop (notch) filter at the specified frequency "
        "to remove line noise while preserving other frequency components."
    )
    useCases = [
        "Remove 50/60 Hz electrical interference",
        "Clean EEG data for downstream analysis"
    ]
    relatedAlgorithms = ["bandpass_filter", "ica_artifact_removal", "asr"]
    examples = [
        AlgorithmExample(
            title="50 Hz Line Noise Removal",
            description="Apply a notch filter centered at 50 Hz to remove electrical noise from EEG recordings."
        )
    ]
    parameters = [
        AlgorithmParameter(
            name="freq",
            type="number",
            value="50.0",
            default="50.0",
            min=40.0,
            max=70.0,
            required=True
        ),
        AlgorithmParameter(
            name="quality_factor",
            type="number",
            value="30.0",
            default="30.0",
            min=1.0,
            max=100.0,
            required=False
        )
    ]

    def process(self, data: EEGData, **params) -> EEGData:
        """
        Applies a notch filter per trial to remove powerline interference.
        """
        freq = float(params.get("freq", 50.0))
        q = float(params.get("quality_factor", 30.0))
        fs = data.sampling_rate

        nyq = fs / 2
        if not (0 < freq < nyq):
            raise ValueError(f"Notch frequency must be between 0 and Nyquist ({nyq} Hz)")

        channel_cols = data.channel_cols
        n_channels = len(channel_cols)

        info = mne.create_info(
            ch_names=channel_cols,
            sfreq=fs,
            ch_types=['eeg'] * n_channels
        )

        df_copy = data.df.copy()
        
        for (subject_id, session_id, trial_id), trial_df in df_copy.groupby(['subject_id', 'session_id', 'trial_id']):
            # Extract EEG data for this trial
            eeg_data = trial_df[channel_cols].values.T  # Shape: (n_channels, n_samples)
            
            # Create MNE RawArray for this trial
            raw = mne.io.RawArray(eeg_data, info)
            
            # Apply notch filter - USE THE Q PARAMETER!
            raw.notch_filter(
                freqs=freq,
                picks='all',
                filter_length='auto',
                method='fir',
                phase='zero-double',
                fir_window='hamming',
                notch_widths=freq/q,
                verbose=False  
            )
            
            filtered_data = raw.get_data().T  
            df_copy.loc[trial_df.index, channel_cols] = filtered_data

        data.df = df_copy
        data._time_data_cache = None

        data.meta["last_step"] = self.name
        data.meta["notch_params"] = {
            "freq": freq,
            "quality_factor": q,
            "notch_width": freq/q,  # Add this for clarity
            "level": "trial",
            "implementation": "mne"
        }

        return data


register_algorithm(NotchFilterStep())