"""
Bandpass Filter Step
Applies a bandpass filter to all EEG channels
"""
import mne
import pandas as pd
from app.schemas.domain_enum import DomainType
from app.algorithms.base import BaseStep , AlgorithmParameter ,AlgorithmExample
from app.models.eeg_data import EEGData
from app.core.registry import register_algorithm


class BandpassFilter(BaseStep):
    id = "bandpass_filter"
    name = "Bandpass Filter"
    category = "Filtering"
    domainType = DomainType.TIME
    type = "preprocessing"
    description  = "Applies a bandpass filter to remove frequencies outside the specified range from EEG signals"
    howItWorks = "Uses a Butterworth filter design to create a bandpass filter with specified cutoff frequencies. The filter is applied in both forward and reverse directions using filtfilt to eliminate phase distortion."
    useCases = [
        "Remove low-frequency drift and high-frequency noise",
        "Isolate specific frequency bands (e.g., alpha, beta, gamma)",
        "Preprocess data for time-frequency analysis"
        ]
    relatedAlgorithms = ["notch_filter", "highpass_filter", "lowpass_filter"]
    examples = [
        AlgorithmExample(
            title="Remove Muscle Artifacts",
            description="Apply 1-40 Hz bandpass to remove slow drifts and high-frequency muscle noise while preserving neural signals."
        )
    ]
    parameters = [
        AlgorithmParameter(
            name="low",
            type="number",
            value="1.0", 
            default="1.0",
            min=0.1,
            max=100.0,
            options=None,
            required=True
        ),
        AlgorithmParameter(
            name="high", 
            type="number",
            value="40.0",
            default="40.0",
            min=1.0,
            max=500.0,
            options=None,
            required=True
        )
    ]



    def process(self, data: EEGData, **params) -> EEGData:
            validated = self.validate_parameters(params)
            low = validated["low"]
            high = validated["high"]

            sfreq = data.sampling_rate
            nyq = sfreq / 2
            if not (0 < low < high < nyq):
                raise ValueError(f"Invalid bandpass frequencies: low={low}, high={high}, nyquist={nyq}")

            channel_cols = data.channel_cols
            df = data.df.copy()

            filtered_chunks = []

            for (subj, sess, trial), group in df.groupby(
                ["subject_id", "session_id", "trial_id"]
            ):
                # ---- build RawArray ----
                signal = group[channel_cols].to_numpy().T

                ch_names = channel_cols
                ch_types = ["eeg"] * len(ch_names)

                info = mne.create_info(
                    ch_names=ch_names,
                    sfreq=sfreq,
                    ch_types=ch_types
                )

                raw = mne.io.RawArray(signal, info, verbose=False)

                # ---- MNE bandpass ----
                raw.filter(l_freq=low, h_freq=high, verbose=False)

                # ---- back to DataFrame ----
                filtered = raw.get_data().T
                filtered_df = group.copy()
                filtered_df[channel_cols] = filtered

                filtered_chunks.append(filtered_df)

            # ---- recombine ----
            data.df = pd.concat(filtered_chunks, ignore_index=True)

            data.meta["last_step"] = "Bandpass Filter (MNE)"
            data.meta["bandpass_params"] = {"low": low, "high": high}

            return data

register_algorithm(BandpassFilter())