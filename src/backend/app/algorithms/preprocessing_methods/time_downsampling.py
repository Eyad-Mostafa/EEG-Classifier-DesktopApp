import numpy as np
import pandas as pd
import mne
from app.schemas.domain_enum import DomainType
from app.algorithms.base import BaseStep, AlgorithmParameter
from app.models.eeg_data import EEGData
from app.core.registry import register_algorithm

class TimeDownsampling(BaseStep):
    id = "time_downsampling"
    name = "Time Domain Down Sampling"
    description = "Reduces the temporal sampling rate by selecting every nth time point."
    category = "Resampling"
    domainType = DomainType.TIME
    type = "preprocessing"
    parameters = [
        AlgorithmParameter(
            name="factor",
            type="number",
            value="2",
            default="2",
            min=2,
            max=20,
            required=True,
        )
    ]

    def process(self, data: EEGData, **params) -> EEGData:
        """
        Time downsampling using MNE (trial-by-trial).
        """

        factor = int(params.get("factor", 2))
        if factor <= 1:
            return data

        sfreq = data.sampling_rate
        new_sfreq = sfreq / factor

        df = data.df
        channel_cols = data.channel_cols

        meta_cols = [c for c in df.columns if c not in channel_cols]

        downsampled_trials = []

        group_cols = [
            "subject_id",
            "session_id",
            "trial_id",
        ]

        for keys, trial_df in df.groupby(group_cols):
            eeg = trial_df[channel_cols].to_numpy().T

            info = mne.create_info(
                ch_names=channel_cols,
                sfreq=sfreq,
                ch_types=["eeg"] * len(channel_cols),
            )

            raw = mne.io.RawArray(eeg, info, verbose=False)

            raw.resample(new_sfreq, npad="auto", verbose=False)

            new_eeg = raw.get_data().T

            new_df = pd.DataFrame(new_eeg, columns=channel_cols)

            for col in meta_cols:
                new_df[col] = trial_df.iloc[0][col]

            new_df["time_index"] = np.arange(len(new_df))

            downsampled_trials.append(new_df)

        result_df = pd.concat(downsampled_trials, ignore_index=True)

        data.df = result_df
        data.sampling_rate = new_sfreq
        data._time_data_cache = None

        data.meta["last_step"] = self.name
        data.meta["downsampling_params"] = {
            "factor": factor,
            "old_rate": sfreq,
            "new_rate": new_sfreq,
            "method": "mne.resample (anti-alias)",
        }

        return data

register_algorithm(TimeDownsampling())
