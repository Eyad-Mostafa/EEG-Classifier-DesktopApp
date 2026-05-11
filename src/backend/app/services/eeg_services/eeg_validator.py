import pandas as pd
from typing import List


class EEGDataValidator:
    """
    Responsible for validating EEG data loaded into a DataFrame.
    Checks:
        - Required metadata columns exist
        - At least one channel column exists (starting with 'channel_')
    """
    REQUIRED_COLUMNS: List[str] = [
        'subject_id', 'session_id', 'trial_id',
         'category', 'time_index'
    ]

    @staticmethod
    def validate(df: pd.DataFrame) -> bool:
        """
        Validate the DataFrame for required structure.
        Raises ValueError if validation fails.
        """

        # 1. Check required metadata columns
        missing_cols = set(EEGDataValidator.REQUIRED_COLUMNS) - set(df.columns)
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        # 2. Check channel columns exist
        channel_cols = [col for col in df.columns if col.startswith("channel_")]
        if not channel_cols:
            raise ValueError("No channel columns found (must start with 'channel_')")

        return True