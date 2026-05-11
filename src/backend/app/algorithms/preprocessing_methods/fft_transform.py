"""
FFT Transform Step
Converts EEG signal from time domain to frequency domain
"""

import numpy as np
import pandas as pd
import mne

from app.schemas.domain_enum import DomainType
from app.algorithms.base import BaseStep, AlgorithmExample
from app.models.eeg_data import EEGData
from app.core.registry import register_algorithm


class FFTTransform(BaseStep):
    id = "fft_transform"
    name = "FFT Transform"
    description = "Transforms EEG from time domain to frequency domain by estimating PSD using Welch's method."
    category = "Frequency Analysis"
    domainType = DomainType.FREQUENCY
    type = "preprocessing"
    parameters = []

    howItWorks = (
        "Computes a frequency-domain representation by estimating the Power Spectral Density (PSD) "
        "using Welch's method. Welch splits the signal into overlapping segments, applies FFT to each "
        "segment, and averages the results to produce a stable spectrum."
    )

    useCases = [
        "Analyze frequency content of EEG signals",
        "Identify dominant frequency bands",
        "Power spectral density analysis",
    ]

    relatedAlgorithms = ["wavelet_transform", "stft_analysis"]

    examples = [
        AlgorithmExample(
            title="Alpha Rhythm Analysis",
            description="Compute PSD to quantify alpha band (8–12 Hz) power.",
        )
    ]

    def process(self, data: EEGData, **params) -> EEGData:
        df = data.df
        sfreq = float(data.sampling_rate)
        channel_cols = data.channel_cols

        # Collect metadata columns (everything except channels and index columns)
        meta_cols = [
            c
            for c in df.columns
            if c not in channel_cols and c not in ["time_index", "frequency_hz"]
        ]

        # Ensure trial-safe grouping keys exist
        for col in ["subject_id", "session_id", "trial_id"]:
            if col not in df.columns:
                raise ValueError(f"FFTTransform requires '{col}' column in the data.")

        # PSD configuration (can be turned into parameters later)
        fmin = float(params.get("fmin", 0.5))
        fmax = float(params.get("fmax", min(45.0, sfreq / 2.0)))
        n_per_seg = int(
            params.get("n_per_seg", int(sfreq))
        )  # 1-second segments by default
        average = params.get("average", "mean")  # "mean" or "median"
        window = params.get("window", "hann")
        remove_dc = bool(params.get("remove_dc", True))
        log10 = bool(params.get("log10", False))

        all_rows = []

        # Group by subject/session/trial to avoid mixing trials
        grouped = df.groupby(["subject_id", "session_id", "trial_id"], sort=False)

        for (_, _, _), trial_df in grouped:
            n_times = len(trial_df)
            if n_times < 8:
                continue

            # Use first row metadata for this trial
            meta = trial_df.iloc[0][meta_cols].to_dict()

            # Build array shape: (n_channels, n_times)
            X = trial_df[channel_cols].to_numpy(dtype=float).T

            # Remove DC offset to avoid an artificial spike at 0 Hz
            if remove_dc:
                X = X - X.mean(axis=1, keepdims=True)

            # Compute Welch PSD for each channel
            psd, freqs = mne.time_frequency.psd_array_welch(
                X,
                sfreq=sfreq,
                fmin=fmin,
                fmax=fmax,
                n_per_seg=min(n_per_seg, n_times),
                average=average,
                window=window,
                verbose=False,
            )

            # Optional log scaling (useful for visualization)
            if log10:
                psd = np.log10(np.maximum(psd, 1e-20))

            # Convert to long-form DataFrame: one row per frequency bin
            for i, f in enumerate(freqs):
                row = meta.copy()
                row["frequency_hz"] = float(f)
                for ci, ch in enumerate(channel_cols):
                    row[ch] = float(psd[ci, i])
                all_rows.append(row)

        out_cols = meta_cols + ["frequency_hz"] + channel_cols
        out_df = pd.DataFrame(all_rows, columns=out_cols)

        # Update EEGData object
        data.df = out_df
        data._time_data_cache = None
        data.meta["last_step"] = self.name
        data.meta["domain"] = "frequency"
        data.meta["index_column_name"] = "frequency_hz"
        data.meta["frequency_representation"] = "psd_welch"
        data.meta["units"] = "V^2/Hz" if not log10 else "log10(V^2/Hz)"

        return data


register_algorithm(FFTTransform())
