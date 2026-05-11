import pandas as pd
from typing import Dict, Any, List, Union

class EEGData:
    """
    Pure Data Container for EEG datasets.
    """

    def __init__(self, df: pd.DataFrame, sampling_rate: float = 250.0):
        if not isinstance(df, pd.DataFrame):
            raise TypeError("EEGData expects a pandas.DataFrame for `df`")

        self.df: pd.DataFrame = df.copy()
        self.sampling_rate: float = float(sampling_rate)

        self.meta: Dict[str, Any] = {}
        self.detailed_labels: Dict[str, int] = {}

        self.channel_cols: List[str] = [c for c in self.df.columns if c.startswith("channel_")]

    # -------------------- Factory Methods --------------------
    @classmethod
    def from_storage(cls, file_data: Union[Dict, 'EEGData']) -> 'EEGData':
        """
        Factory method to create an instance from a TempFileStore dictionary.
        """
        # 1. If it's already an object, return it
        if isinstance(file_data, cls):
            return file_data

        # 2. If it's a dict (from temp_file_store.get())
        if isinstance(file_data, dict) and 'file_path' in file_data:
            
            # A. Load the Data
            # Use 'c' engine for speed
            df = pd.read_csv(file_data['file_path'], engine='c', low_memory=False)
            
            # B. Get Sampling Rate (default 250)
            sampling_rate = file_data.get('sampling_rate', 250)
            
            # C. Create Instance
            instance = cls(df, sampling_rate=sampling_rate)

            # D. RESTORE METADATA
            # The TempFileStore injects 'meta' and 'detailed_labels' from the JSON file.
            # We must explicitly assign them to the new instance.
            
            if 'meta' in file_data:
                instance.meta = file_data['meta']  # <--- Restores channel_mapping & montage
            
            if 'detailed_labels' in file_data:
                instance.detailed_labels = file_data['detailed_labels']

            return instance
        
        raise ValueError(f"Invalid data format for EEGData factory: {type(file_data)}")

    def set_detailed_labels(self, labels_map: Dict[str, int]) -> None:
        """Set/replace the detailed_labels mapping."""
        if not isinstance(labels_map, dict):
            raise TypeError("labels_map must be a dict[str, int]")
        self.detailed_labels = labels_map.copy()

    # -------------------- Properties --------------------
    @property
    def entire_dataset(self) -> pd.DataFrame:
        return self.df

    @property
    def channels_only(self) -> pd.DataFrame:
        return self.df[self.channel_cols]

    @property
    def metadata_only(self) -> pd.DataFrame:
        return self.df.drop(columns=self.channel_cols)

    @property
    def all_subjects(self) -> List[str]:
        return self.df["subject_id"].unique().tolist()

    @property
    def all_labels(self) -> List[Any]:
        if 'labels' in self.df.columns:
            return self.df["labels"].unique().tolist()
        return []  # Return empty list if no labels column


    @property
    def get_detailed_labels(self) -> Dict[str, str]:
        return self.detailed_labels.copy()

    # -------------------- Data Access --------------------
    def get_data_by_category(self, category: str) -> pd.DataFrame:
        return self.df[self.df["category"] == category]

    def get_data_by_subject(self, subject_id: str) -> pd.DataFrame:
        return self.df[self.df["subject_id"] == str(subject_id)]

    def get_time_data(self, time_index: int) -> Dict[str, Any]:
        """
        Retrieves all data for a specific time index efficiently.
        Returns a dictionary structure mimicking the original cache format.
        """
        subset = self.df[self.df["time_index"] == time_index]
        
        if subset.empty:
            return {}

        return {
            "subjects": subset["subject_id"].tolist(),
            "sessions": subset["session_id"].tolist(),
            "trials": subset["trial_id"].tolist(),
            "labels": subset["labels"].tolist() if "labels" in subset.columns else [],
            "category": subset["category"].tolist(),
            "channels": {ch: subset[ch].tolist() for ch in self.channel_cols},
        }

    def get_subject_data_at_time(self, time_index: int, subject_id: str) -> Dict[str, Any]:
        """
        Get specific record for a subject at a specific time.
        """
        mask = (self.df["time_index"] == time_index) & (self.df["subject_id"] == str(subject_id))
        subset = self.df[mask]
        
        result = {}
        for i, row in enumerate(subset.to_dict('records')):
            result[f"record_{i}"] = {
                "subject": row["subject_id"],
                "session": row["session_id"],
                "trial": row["trial_id"],
                "label": row.get("labels", None),
                "category": row["category"],
                "channels": {ch: row[ch] for ch in self.channel_cols},
            }
        return result

    # -------------------- Column Utilities --------------------
    def list_all_columns(self) -> Dict[str, str]:
        return {col: str(dtype) for col, dtype in self.df.dtypes.items()}

    def get_column(self, column_name: str) -> pd.Series:
        if column_name not in self.df.columns:
            raise ValueError(f"Column '{column_name}' not found.")
        return self.df[column_name]

    def get_column_info(self, column_name: str) -> Dict[str, Any]:
        col = self.get_column(column_name)
        return {
            "name": column_name,
            "dtype": str(col.dtype),
            "total_values": len(col),
            "unique_values": col.nunique(),
            "missing_values": int(col.isnull().sum()),
            "sample_values": col.head(5).tolist(),
        }

    # -------------------- Update EEG Data --------------------
    def update_channels(self, new_channels_df: pd.DataFrame):
        """
        Updates channel data with processed values (e.g., after filtering).
        Ensures row counts match.
        """
        if len(new_channels_df) != len(self.df):
            raise ValueError(f"Length mismatch: Original {len(self.df)}, New {len(new_channels_df)}")

        missing_channels = [c for c in self.channel_cols if c not in new_channels_df.columns]
        if missing_channels:
            raise ValueError(f"New DataFrame missing channel columns: {missing_channels}")

        self.df[self.channel_cols] = new_channels_df[self.channel_cols]

    def get_num_channels(self) -> int:
        return len(self.channel_cols)

    def summary(self) -> Dict[str, Any]:
        return {
            "n_rows": len(self.df),
            "n_channels": self.get_num_channels(),
            "n_subjects": len(self.all_subjects),
            "columns": list(self.df.columns),
            "sampling_rate": self.sampling_rate
        }
    
    # -------------------- Utility Methods --------------------
    def get_column_by_condition(self, target_column: str, condition_column: str, condition_value: Any) -> List[Any]:
        """
        Returns values from 'target_column' where 'condition_column' matches 'condition_value'.
        Used by: eeg_file_service.py
        """
        if target_column not in self.df.columns:
            raise ValueError(f"Target column '{target_column}' not found.")
        if condition_column not in self.df.columns:
            raise ValueError(f"Condition column '{condition_column}' not found.")

        subset = self.df.loc[self.df[condition_column] == condition_value, target_column]
        
        return subset.tolist()
    
        # -------------------- Validation Methods --------------------
    def validate_structure(self) -> tuple[bool, str]:
        """
        Validates the EEG data structure.
        Returns: (is_valid, error_message)
        """
        df = self.df
        
        # Check 1: Required columns (labels is now optional)
        required_cols = ['subject_id', 'session_id', 'trial_id', 'category', 'time_index']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return False, f"Missing required columns: {missing_cols}"
        
        # Check 2: trial_id must be integers (no decimals like 1.0, 1.1, 2.0)
        if df['trial_id'].dtype == float:
            decimal_trials = df[df['trial_id'] % 1 != 0]['trial_id'].unique()
            if len(decimal_trials) > 0:
                return False, f"trial_id contains decimal values: {list(decimal_trials)[:5]}. All trial_id must be integers."
        
        # Check 3: No duplicate time_index within the same trial
        duplicate_time_check = df.groupby(['subject_id', 'session_id', 'trial_id', 'time_index']).size()
        duplicate_times = duplicate_time_check[duplicate_time_check > 1]
        if len(duplicate_times) > 0:
            return False, f"Duplicate time_index found within same trial. Each time_index must appear once per trial."
        
        # Check 4: Consistent rows per trial (ALL trials must have SAME number of rows)
        rows_per_trial = df.groupby(['subject_id', 'session_id', 'trial_id']).size()
        if rows_per_trial.nunique() > 1:
            return False, f"Inconsistent rows per trial. Some trials have {rows_per_trial.min()} rows, others have {rows_per_trial.max()} rows. All trials must have same length."
        
        # Check 5: Each trial must have ONE category (labels check is optional)
        category_check = df.groupby(['subject_id', 'session_id', 'trial_id'])['category'].nunique()
        category_conflicts = category_check[category_check > 1]
        if len(category_conflicts) > 0:
            conflict_details = []
            for (subj, sess, trial), count in category_conflicts.items():
                conflict_details.append(f"  subject={subj}, session={sess}, trial_id={trial}: {count} different categories found (Motor AND Imagery)")
            return False, f"Trial ID appears with multiple categories:\n" + "\n".join(conflict_details[:5])
        
        # Check 5b: If labels column exists, check each trial has ONE label
        if 'labels' in df.columns:
            label_check = df.groupby(['subject_id', 'session_id', 'trial_id'])['labels'].nunique()
            label_conflicts = label_check[label_check > 1]
            if len(label_conflicts) > 0:
                conflict_details = []
                for (subj, sess, trial), count in label_conflicts.items():
                    conflict_details.append(f"  subject={subj}, session={sess}, trial_id={trial}: {count} different labels found")
                return False, f"Trial ID appears with multiple labels:\n" + "\n".join(conflict_details[:5])
        
        # Check 6: At least one channel column exists
        channel_cols = [col for col in df.columns if col.startswith('channel_')]
        if len(channel_cols) == 0:
            return False, "No channel columns found. Expected columns like 'channel_1', 'channel_2', etc."
        
        return True, None