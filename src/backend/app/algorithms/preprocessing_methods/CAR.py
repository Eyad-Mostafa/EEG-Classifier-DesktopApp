"""
CAR Step
Applies Common Average Reference (CAR) to EEG signals using existing EEGData methods.
"""

from app.schemas.domain_enum import DomainType
from app.algorithms.base import BaseStep, AlgorithmExample
from app.models.eeg_data import EEGData
from app.core.registry import register_algorithm


class CARFilter(BaseStep):
    id = "car_filter"
    name = "Common Average Reference (CAR)"
    category = "Referencing"
    domainType = DomainType.TIME
    type = "preprocessing"
    description = "Applies Common Average Reference (CAR) to EEG signals to reduce common noise across channels."
    howItWorks = (
        "Uses EEGData methods to access channel data, computes the average across all channels, "
        "and subtracts it from each channel to reduce common noise."
    )
    useCases = [
        "Reduce common noise across EEG channels",
        "Improve signal-to-noise ratio",
        "Preprocess data for feature extraction (FFT, STFT, etc.)",
    ]
    relatedAlgorithms = ["bandpass_filter", "ica_artifact_removal"]
    examples = [
        AlgorithmExample(
            title="Apply CAR",
            description="Subtract the average of all EEG channels from each channel to remove common noise.",
        )
    ]
    parameters = []  # CAR does not require any user-defined parameters

    # -------------------- Processing Step --------------------
    def process(self, data: EEGData, **params) -> EEGData:
        """
        Applies Common Average Reference (CAR) per trial, per session, per subject.
        Each channel is referenced to the average of all channels at each time point.
        """
        # Get the number of EEG channels in the dataset
        num_channels = data.get_num_channels()
        if num_channels == 0:
            raise ValueError("No EEG channels found in EEGData")

        # Select channel names to use for CAR
        channel_cols = data.channel_cols[:num_channels]

        # Create a copy of the data to avoid modifying the original DataFrame
        df_copy = data.df.copy()

        # Function to apply CAR on a single group (trial/session/subject)
        def apply_car(group):
            # Compute the mean across all channels for each time point
            avg_signal = group[channel_cols].mean(axis=1)
            # Subtract the mean from each channel to remove common noise
            car_group = group[channel_cols].subtract(avg_signal, axis=0)
            return car_group

        # Apply CAR to each trial for each session for each subject
        df_car = df_copy.groupby(["subject_id", "session_id", "trial_id"])[
            channel_cols
        ].apply(apply_car)

        # Reset index to match the original DataFrame structure
        df_car.index = df_copy.index

        # Update the EEGData object with the CAR-referenced channels
        data.update_channels(df_car)

        # Update metadata to indicate the last preprocessing step
        data.meta["last_step"] = self.name

        return data


register_algorithm(CARFilter())
