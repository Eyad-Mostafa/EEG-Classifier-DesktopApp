import numpy as np
import pandas as pd
from scipy.stats import zscore
from app.schemas.domain_enum import DomainType
from app.algorithms.base import BaseStep
from app.models.eeg_data import EEGData
from app.core.registry import register_algorithm

class EEGNetNormalization(BaseStep):
    id = "eegnet_normalization"
    name = "Normalization"
    description = "Applies z-score normalization per trial exactly as used in EEGNet training."
    is_hidden = True
    category = "Scaling"
    domainType = DomainType.TIME
    type = "preprocessing"
    
    def process(self, data: EEGData, **params) -> EEGData:
        df = data.df.copy()
        channel_cols = data.channel_cols
        
        processed_chunks = []
        for (subj, sess, trial), group in df.groupby(["subject_id", "session_id", "trial_id"]):
            group_copy = group.copy()
            for ch in channel_cols:
                signal = group_copy[ch].values
                normalized = zscore(signal)
                if np.isnan(normalized).any():
                    normalized = np.zeros_like(normalized)
                group_copy[ch] = normalized
            processed_chunks.append(group_copy)
            
        data.df = pd.concat(processed_chunks, ignore_index=True)
        data.meta["last_step"] = "Normalization (EEGNet)"
        return data

register_algorithm(EEGNetNormalization())
