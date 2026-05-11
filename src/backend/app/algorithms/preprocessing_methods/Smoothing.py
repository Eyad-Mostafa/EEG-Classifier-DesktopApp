"""
Smoothing Step
Applies smoothing to EEG signals using moving average filter

"""
from app.schemas.domain_enum import DomainType
from app.algorithms.base import BaseStep , AlgorithmParameter ,AlgorithmExample
from app.models.eeg_data import EEGData
from app.core.registry import register_algorithm

class SmoothingFilter(BaseStep):
    id = "smoothing_filter"
    name = "Smoothing Filter"
    description = "Applies a moving average filter to smooth EEG signals and reduce high-frequency noise"
    category = "Filtering"
    domainType = DomainType.TIME
    type = "preprocessing"
    howItWorks = "Implements a moving average filter that computes the average of data points within a specified window size, effectively reducing high-frequency noise while preserving the underlying signal trends."
    useCases = [
        "Reduce high-frequency noise in EEG signals",
        "Enhance signal quality for visualization",
        "Preprocess data for further analysis"
    ]
    relatedAlgorithms = ["lowpass_filter", "median_filter"]
    examples = [
        AlgorithmExample(
            title="5-Point Moving Average Smoothing",
            description="Apply a moving average filter with a window size of 5 to smooth EEG signals while retaining important features."
        )
    ]
    parameters = [
        AlgorithmParameter(
            name="window_size",
            type="number",
            value="5",
            default="5",
            min=1,
            max=100,
            options=None,
            required=True
        )
    ]

    def process(self, data: EEGData, **params) -> EEGData:
        """
        Applies moving average smoothing to EEG signals.
        Trial/session/subject safe.
        """
        validated_params = self.validate_parameters(params)
        window_size = int(validated_params["window_size"])
        
        if window_size < 1:
            raise ValueError("window_size must be at least 1")

        df_copy = data.df.copy()
        channel_cols = data.channel_cols

        # Define smoothing function for a single trial
        def smooth_trial_data(signal_series):
            return signal_series.rolling(window=window_size, center=True, min_periods=1).mean()

        # Ensure necessary columns exist
        for col in ['subject_id', 'session_id', 'trial_id']:
            if col not in df_copy.columns:
                raise ValueError(f"Smoothing requires '{col}' column in the data.")

        # Apply smoothing to each channel, grouped by subject/session/trial
        for col in channel_cols:
            df_copy[col] = df_copy.groupby(['subject_id', 'session_id', 'trial_id'])[col].transform(smooth_trial_data)

        # Update EEGData
        data.df = df_copy
        data._time_data_cache = None

        # Update metadata
        data.meta["last_step"] = self.name
        data.meta["smoothing_params"] = {"window_size": window_size}

        return data
    
register_algorithm(SmoothingFilter())