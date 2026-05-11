"""
Epoch Rejection Step
Rejects bad trials/epochs based on amplitude thresholds or statistical criteria
"""

import numpy as np
import pandas as pd
from app.schemas.domain_enum import DomainType
from app.algorithms.base import BaseStep , AlgorithmParameter ,AlgorithmExample
from app.models.eeg_data import EEGData
from app.core.registry import register_algorithm

class EpochRejectionStep(BaseStep):
    id = "epoch_rejection"
    name = "Epoch Rejection"
    description = (
        "Rejects bad trials based on amplitude thresholds or statistical measures."
        "Operates trial by trial to remove noisy or artifact-contaminated epochs."
    )
    category = "Artifact Removal"
    domainType = DomainType.TIME
    type = "preprocessing"
    howItWorks = (
        "Detects trials where the amplitude exceeds a specified threshold or "
        "where the signal variance is abnormal, and removes them from the dataset."
    )
    useCases = [
        "Remove artifact-contaminated trials",
        "Improve quality of downstream processing",
    ]
    relatedAlgorithms = ["asr", "ica_artifact_removal", "remove_bad_channels"]
    examples = [
        AlgorithmExample(
            title="Reject High-Amplitude Epochs",
            description="Remove trials where the signal exceeds the set amplitude threshold."
        )
    ]
    parameters = [
        AlgorithmParameter(
            name="amplitude_threshold",
            type="number",
            value="100.0",
            default="100.0",
            min=1.0,
            max=1000.0,
            required=True
        ),
        AlgorithmParameter(
            name="variance_threshold",
            type="number",
            value="3.0",
            default="3.0",
            min=0.1,
            max=10.0,
            required=False
        )
    ]

    def process(self, data: EEGData, **params) -> EEGData:
        """
        Rejects bad trials based on amplitude and/or variance thresholds
        """
        amp_th = float(params.get("amplitude_threshold", 100.0))
        var_th = float(params.get("variance_threshold", 3.0))
        channel_cols = data.channel_cols
        df_copy = data.df.copy()

        if amp_th <= 0 or var_th <= 0:
            raise ValueError("Thresholds must be positive numbers")

        retained_trials = []

        grouped = df_copy.groupby(['subject_id', 'session_id', 'trial_id'])
        for (subject_id, session_id, trial_id), trial_df in grouped:
            trial_channels = trial_df[channel_cols].values

            # Check amplitude
            max_amp = np.max(np.abs(trial_channels))
            # Check variance (z-score)
            trial_var = np.var(trial_channels, axis=0)
            z_scores = (trial_var - trial_var.mean()) / (trial_var.std() + 1e-8)
            max_z = np.max(np.abs(z_scores))

            if max_amp <= amp_th and max_z <= var_th:
                retained_trials.append(trial_df)
            else:
                # Trial rejected
                continue

        if retained_trials:
            final_df = pd.concat(retained_trials, ignore_index=True)
        else:
            # No trial left, return empty dataframe
            final_df = pd.DataFrame(columns=df_copy.columns)

        data.df = final_df
        data._time_data_cache = None

        data.meta["last_step"] = self.name
        data.meta["epoch_rejection_params"] = {
            "amplitude_threshold": amp_th,
            "variance_threshold": var_th,
            "level": "trial"
        }

        return data
    
register_algorithm(EpochRejectionStep())