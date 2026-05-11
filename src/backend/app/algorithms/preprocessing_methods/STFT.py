"""
STFT Step
Computes the Short-Time Fourier Transform (STFT) magnitude of EEG signals using existing EEGData methods.
"""

import numpy as np
import pandas as pd
from scipy.signal import stft
from app.schemas.domain_enum import DomainType
from app.algorithms.base import BaseStep, AlgorithmParameter, AlgorithmExample
from app.models.eeg_data import EEGData
from app.core.registry import register_algorithm

class STFT(BaseStep):
    id = "stft"
    name = "Short-Time Fourier Transform"
    category = "Time-Frequency Analysis"
    domainType = DomainType.TIME_FREQUENCY
    type = "preprocessing"
    description = (
        "Computes the Short-Time Fourier Transform (STFT) magnitude of EEG signals "
        "to extract time-frequency representation."
    )
    howItWorks = (
        "Uses EEGData methods to access each channel and applies STFT "
        "to get the frequency content over time. Only magnitude is stored for easy use."
    )
    useCases = [
        "Time-frequency analysis of EEG signals",
        "Feature extraction for ML/DL models",
        "Visualize spectrograms for each channel"
    ]
    relatedAlgorithms = ["fft_transform", "bandpass_filter"]
    examples = [
        AlgorithmExample(
            title="Compute STFT Magnitude",
            description="Apply STFT on EEG channels with 1-second windows and 50% overlap, storing magnitude only."
        )
    ]
    parameters = [
        AlgorithmParameter(
            name="window_size",
            type="number",
            value="256",
            default="256",
            min=16,
            max=2048,
            options=None,
            required=True
        ),
        AlgorithmParameter(
            name="overlap",
            type="number",
            value="128",
            default="128",
            min=0,
            max=2048,
            options=None,
            required=True
        )
    ]

    # -------------------- Process Step --------------------
    def process(self, data: EEGData, **params) -> EEGData:
        """
        Applies STFT to each channel per trial, per session, per subject.
        Stores magnitude in a DataFrame suitable for visualization.
        """
        validated_params = self.validate_parameters(params)
        window_size = validated_params["window_size"]
        overlap = validated_params["overlap"]

        df = data.df
        sampling_rate = data.sampling_rate
        channel_cols = data.channel_cols

        # Metadata columns (everything except channels and time_index)
        meta_cols = [col for col in df.columns if col not in channel_cols and col != 'time_index']

        # Ensure required columns
        for col in ['subject_id', 'session_id', 'trial_id']:
            if col not in df.columns:
                raise ValueError(f"STFT requires '{col}' column in the data.")

        all_trials = []

        grouped = df.groupby(['subject_id', 'session_id', 'trial_id'])

        for (subject_id, session_id, trial_id), trial_df in grouped:
            meta_data = trial_df.iloc[0][meta_cols].to_dict()

            trial_channels_data = []

            for ch in channel_cols:
                signal = trial_df[ch].values
                f, t, Zxx = stft(signal, fs=sampling_rate, nperseg=window_size, noverlap=overlap)
                magnitude = np.abs(Zxx)

                # Convert to DataFrame efficiently using stack
                temp_df = pd.DataFrame(magnitude, index=f, columns=t)
                temp_df = temp_df.stack().reset_index()
                temp_df.columns = ["frequency", "time_index", ch]

                # Add metadata columns
                for k, v in meta_data.items():
                    temp_df[k] = v

                trial_channels_data.append(temp_df)

            # Merge all channels on frequency + time_index + meta columns
            merged_df = trial_channels_data[0]
            for temp_df in trial_channels_data[1:]:
                merged_df = pd.merge(
                    merged_df,
                    temp_df,
                    on=["frequency", "time_index"] + list(meta_data.keys()),
                    how="outer"
                )

            all_trials.append(merged_df)

        # Concatenate all trials
        stft_df = pd.concat(all_trials, ignore_index=True)

        data.df = stft_df
        data._time_data_cache = None  # Clear old cache
        data.meta["last_step"] = self.name
        data.meta["domain"] = "time-frequency"
        data.meta["stft_params"] = {"window_size": window_size, "overlap": overlap}
        data.meta["index_column_name"] = "time_index"

        return data

register_algorithm(STFT())
