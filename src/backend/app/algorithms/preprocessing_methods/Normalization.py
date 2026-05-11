"""
Normalization Step
Scales EEG data per session using z-score or min-max normalization to make trials comparable
"""

import pandas as pd
from app.schemas.domain_enum import DomainType
from app.algorithms.base import BaseStep, AlgorithmExample
from app.models.eeg_data import EEGData
from app.core.registry import register_algorithm

class NormalizationStep(BaseStep):
    id = "normalization"
    name = "Normalization"
    description = "Scales EEG data per session to have zero mean and unit variance (z-score) for each channel."
    category = "Scaling"
    domainType = DomainType.TIME
    type = "preprocessing"
    howItWorks = (
        "Computes mean/std per channel across all trials in a session, "
        "then applies normalization to each channel."
    )
    useCases = [
        "Make EEG trials comparable across the session",
        "Prepare data for machine learning models",
        "Reduce variability across sessions"
    ]
    relatedAlgorithms = ["remove_bad_channels", "ica_artifact_removal"]
    examples = [
        AlgorithmExample(
            title="Session Normalization",
            description="Normalize all EEG channels per session to have zero mean and unit variance."
        )
    ]
    parameters = []

    def process(self, data: EEGData, **params) -> EEGData:
        df_copy = data.df.copy()
        method = "zscore"
        all_normalized_data = []

        session_grouped = df_copy.groupby(['subject_id', 'session_id'])

        for (subject_id, session_id), session_df in session_grouped:
            session_channels = session_df[data.channel_cols].values

            mean = session_channels.mean(axis=0)
            std = session_channels.std(axis=0)
            std[std == 0] = 1.0

            normalized = (session_channels - mean) / std

            normalized_df = pd.DataFrame(normalized, columns=data.channel_cols, index=session_df.index)

            meta_cols = [c for c in session_df.columns if c not in data.channel_cols]
            combined = pd.concat([session_df[meta_cols], normalized_df], axis=1)
            all_normalized_data.append(combined)

        final_df = pd.concat(all_normalized_data, ignore_index=True)
        data.df = final_df
        data._time_data_cache = None

        data.meta["last_step"] = "zscore_normalization_plain"
        data.meta["normalization_params"] = {"method": method, "level": "session"}

        return data

register_algorithm(NormalizationStep())
