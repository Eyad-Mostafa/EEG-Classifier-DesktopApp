"""
Baseline Correction Step
Removes baseline drift from EEG signals by subtracting pre-stimulus mean
"""

import pandas as pd
import numpy as np
from app.schemas.domain_enum import DomainType
from app.algorithms.base import BaseStep, AlgorithmParameter, AlgorithmExample
from app.models.eeg_data import EEGData
from app.core.registry import register_algorithm


class BaselineCorrectionStep(BaseStep):
    id = "baseline_correction"
    name = "Baseline Correction"
    description = (
        "Removes baseline drift by subtracting the mean of a pre-stimulus interval."
    )
    category = "Preprocessing"
    domainType = DomainType.TIME
    type = "preprocessing"
    howItWorks = (
        "Subtracts the mean of a specified baseline period from each trial. "
        "This removes DC offset and slow drifts while preserving signal shape."
    )
    useCases = [
        "Remove DC offset and slow drifts",
        "Prepare data for ERP analysis",
        "Standardize signals across trials and subjects"
    ]
    relatedAlgorithms = ["bandpass_filter", "notch_filter", "asr", "rereference"]
    examples = [
        AlgorithmExample(
            title="Remove Pre-Stimulus Drift",
            description="Subtract mean of first 200 ms of each trial from all time points to remove slow baseline drift."
        )
    ]
    parameters = [
        AlgorithmParameter(
            name="baseline_start",
            type="number",
            value="0.0",
            default="0.0",
            min=-1.0,
            max=2.0,
            required=True
        ),
        AlgorithmParameter(
            name="baseline_end",
            type="number",
            value="0.2",
            default="0.2",
            min=0.0,
            max=2.0,
            required=True
        )
    ]

    def process(self, data: EEGData, **params) -> EEGData:
        """
        Applies baseline correction per trial using simple mean subtraction.
        """
        baseline_start = float(params.get("baseline_start", 0.0))
        baseline_end = float(params.get("baseline_end", 0.2))
        fs = data.sampling_rate
        
        # Validate baseline window
        if baseline_end <= baseline_start:
            raise ValueError(f"baseline_end ({baseline_end}) must be greater than baseline_start ({baseline_start})")
        
        channel_cols = data.channel_cols
        df_copy = data.df.copy()
        
        # Convert baseline times to sample indices
        start_idx = int(baseline_start * fs)
        end_idx = int(baseline_end * fs)
        
        all_corrected_data = []

        grouped = df_copy.groupby(['subject_id', 'session_id', 'trial_id'])
        for (subject_id, session_id, trial_id), trial_df in grouped:
            trial_channels = trial_df[channel_cols].values
            
            # Check if baseline indices are valid for this trial
            trial_length = trial_channels.shape[0]
            
            if start_idx >= trial_length or end_idx > trial_length or start_idx < 0:
                all_corrected_data.append(trial_df)
                continue
            
            if start_idx >= end_idx:
                # If invalid indices, skip baseline correction for this trial
                all_corrected_data.append(trial_df)
                continue
            
            # Calculate baseline mean
            baseline_data = trial_channels[start_idx:end_idx, :]
            if len(baseline_data) == 0:
                # No baseline data, skip correction
                all_corrected_data.append(trial_df)
                continue
            
            baseline_mean = baseline_data.mean(axis=0, keepdims=True)
            
            # Subtract baseline mean
            corrected_channels = trial_channels - baseline_mean
            
            corrected_trial_df = pd.DataFrame(corrected_channels, columns=channel_cols, index=trial_df.index)

            # Preserve metadata
            meta_cols = [c for c in trial_df.columns if c not in channel_cols]
            combined = pd.concat([trial_df[meta_cols], corrected_trial_df], axis=1)
            all_corrected_data.append(combined)

        final_df = pd.concat(all_corrected_data, ignore_index=True)
        data.df = final_df
        data._time_data_cache = None

        data.meta["last_step"] = self.name
        data.meta["baseline_params"] = {
            "baseline_start": baseline_start,
            "baseline_end": baseline_end,
            "baseline_samples": f"{start_idx}-{end_idx}",
            "method": "absolute_baseline_correction",
            "level": "trial"
        }

        return data


register_algorithm(BaselineCorrectionStep())