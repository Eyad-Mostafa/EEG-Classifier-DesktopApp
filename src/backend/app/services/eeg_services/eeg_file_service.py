from datetime import datetime
import io
from typing import Dict, List, Any, Optional, Union
import pandas as pd
from requests import Session

from app.models.eeg_data import EEGData
from app.repositories.configuration_repository import FileConfigurationRepository
from app.services.eeg_services.eeg_loader import EEGDataLoader
from app.services.eeg_services.eeg_validator import EEGDataValidator
from app.services.file_store_service import file_store
from app.services.temp_file_store_service import temp_file_store
from app.schemas.config_schema import FilterRequest, FilterResponse


class EEGFileService:

    def __init__(self, db_session: Optional[Session] = None):
        self.repo = FileConfigurationRepository(db_session) if db_session else None

    def create_eeg_data(
        self,
        source: Union[str, bytes, bytearray, EEGData, "io.IOBase"],
        sampling_rate: float = 250,
    ) -> EEGData:
        """
        Loads, validates, and returns a new EEGData instance from the source.
        """
        df = EEGDataLoader.load_data(source)
        EEGDataValidator.validate(df)
        return EEGData(df=df, sampling_rate=sampling_rate)

    def get_metadata(self, file_id: str) -> Dict:
        eeg_data = file_store.get_file(file_id)
        if not eeg_data:
            raise ValueError("File not found")

        def natural_key(val):
            s = str(val)
            return int(s) if s.isdigit() else s

        # Get unique combinations of subject, session, trial
        unique_trials = eeg_data.df[
            ["subject_id", "session_id", "trial_id"]
        ].drop_duplicates()

        # Build nested structure: subject -> session -> trials
        subjects_map = {}
        for _, row in unique_trials.iterrows():
            subject_id = str(row["subject_id"])
            session_id = str(row["session_id"])
            trial_id = str(row["trial_id"])

            if subject_id not in subjects_map:
                subjects_map[subject_id] = {}

            if session_id not in subjects_map[subject_id]:
                subjects_map[subject_id][session_id] = []

            subjects_map[subject_id][session_id].append(trial_id)

        subjects_info = []
        sorted_subjects = sorted(subjects_map.keys(), key=natural_key)

        for subject_id in sorted_subjects:
            sessions_info = []
            sorted_sessions = sorted(subjects_map[subject_id].keys(), key=natural_key)

            for session_id in sorted_sessions:
                trials_list = sorted(
                    set(subjects_map[subject_id][session_id]), key=natural_key
                )
                sessions_info.append(
                    {
                        "sessionId": str(session_id),
                        "trials": [str(t) for t in trials_list],
                    }
                )

            subjects_info.append(
                {"subjectId": str(subject_id), "sessions": sessions_info}
            )

        labels = (
            sorted(eeg_data.all_labels, key=natural_key) if eeg_data.all_labels else []
        )
        channels = [c for c in eeg_data.df.columns if c.startswith("channel_")]

        return {
            "fileId": file_id,
            "samplingRate": eeg_data.sampling_rate,
            "subjects": subjects_info,
            "labels": labels,
            "channels": channels,
        }

    def get_detailed_labels(self, file_id: str):
        eeg_data = file_store.get_file(file_id)
        if not eeg_data:
            raise ValueError("File not found")
        return eeg_data.get_detailed_labels

    def set_labels(self, labels: Dict[str, int], file_id: str):
        eeg_data = file_store.get_file(file_id)
        if not eeg_data:
            raise ValueError("File not found")
        eeg_data.set_detailed_labels(labels)

    def process_filter(
        self, eeg_data: EEGData, sessions_map: Dict[str, List[Dict[str, List[str]]]]
    ) -> pd.DataFrame:
        """Filters the DataFrame by subject, session, and trial."""
        # Build list of (subject_id, session_id, trial_id) tuples to keep
        keep_tuples = []
        for subject_data in sessions_map:
            subject_id = str(subject_data["subjectId"])
            for session_data in subject_data["sessions"]:
                session_id = str(session_data["sessionId"])
                for trial_id in session_data["trials"]:
                    keep_tuples.append((subject_id, session_id, str(trial_id)))

        if not keep_tuples:
            raise ValueError("No subjects, sessions, or trials selected.")

        # Create DataFrame of combinations to keep
        keep_df = pd.DataFrame(
            keep_tuples, columns=["subject_id", "session_id", "trial_id"]
        )

        # Merge to filter
        filtered_df = eeg_data.df.merge(
            keep_df, on=["subject_id", "session_id", "trial_id"], how="inner"
        )

        if filtered_df.empty:
            raise ValueError("Filtering resulted in empty dataset.")

        return filtered_df

    def apply_filter(self, file_id: str, filter_req: FilterRequest) -> Dict[str, Any]:
        """
        Orchestrates the filtering workflow.
        """
        # A. Get Original Data
        original_eeg = file_store.get_file(file_id)
        if not original_eeg:
            raise ValueError("File not found")

        has_labels_column = 'labels' in original_eeg.df.columns
        if not has_labels_column:
            filter_req.labels = {}
            
        # B. Get Filtered DataFrame
        filtered_df = self.process_filter(
            original_eeg, [s.dict() for s in filter_req.subjects]
        )
        
        # ✅ FORCE REMOVE 'labels' column if original didn't have it
        if not has_labels_column and 'labels' in filtered_df.columns:
            filtered_df = filtered_df.drop(columns=['labels'])

        # C. Apply label filter
        if filter_req.labels and len(filter_req.labels) > 0 and has_labels_column:
            print("filter_req.labels : ", list(filter_req.labels.keys()))
            if 'labels' in filtered_df.columns:
                selected_label_numbers = list(filter_req.labels.values())
                filtered_df = filtered_df[filtered_df['labels'].isin(selected_label_numbers)]
            
                if filtered_df.empty:
                    raise ValueError(f"No data found for selected labels: {selected_label_numbers}")

        # D. Apply channel filter (NEW)
        if filter_req.selected_channels:
            selected_channel_names = [ch for ch, selected in filter_req.selected_channels.items() if selected]

            if selected_channel_names:
                existing_channels = [ch for ch in selected_channel_names if ch in filtered_df.columns]
                if existing_channels:
                    metadata_cols = ['subject_id', 'session_id', 'trial_id', 'category']

                    if 'labels' in filtered_df.columns:
                        metadata_cols.append('labels')

                    keep_cols = [col for col in metadata_cols if col in filtered_df.columns] + existing_channels
                    filtered_df = filtered_df[keep_cols]

                    if filtered_df.empty:
                        raise ValueError("No data found after channel filtering")

        # 3. Create NEW Object
        filtered_eeg = EEGData(df=filtered_df, sampling_rate=original_eeg.sampling_rate)

        # Instead of starting empty, we copy the original metadata.
        if original_eeg.meta:
            filtered_eeg.meta = original_eeg.meta.copy()
        else:
            filtered_eeg.meta = {}

        # 4. Update Metadata with User Selections
        if filter_req.labels and has_labels_column:
            filtered_eeg.set_detailed_labels(filter_req.labels)
        else:
            filtered_eeg.detailed_labels = original_eeg.detailed_labels.copy()

        if filter_req.channels:
            filtered_eeg.meta["channel_mapping"] = filter_req.channels
        
        if filter_req.selected_channels:
            filtered_eeg.meta["selected_channels"] = filter_req.selected_channels

        if filter_req.montage:
            filtered_eeg.meta["montage"] = filter_req.montage

        config_payload = {
            # ensure you pass numeric DB PK for file_id. Resolve if necessary.
            "file_id": file_id,
            "configuration_json": filter_req.dict(),  # serializable structure
            "created_at": datetime.now(),
            "last_opened_at": datetime.now(),
        }
        config_id = self.repo.add_configuration(config_payload)

        # 5. Save the OBJECT
        # The 'original_name' is now safely inside filtered_eeg.meta
        result_id = temp_file_store.save(
            filtered_eeg, base_name=f"filtered_", config_id=config_id
        )
        print(",config_id : ", config_id, "results_id :", result_id)

        return FilterResponse(
            status="success",
            tempFileId=result_id,
            n_rows=len(filtered_df),
            n_subjects=filtered_df["subject_id"].nunique(),
        )

    def delete_config_history(self, file_id: str) -> int:
        """
        Delete all saved configurations for a specific file.
        """
        if self.repo is None:
            raise ValueError("Database session is required")

        deleted_count = self.repo.delete_by_file_id(file_id)

        if deleted_count == 0:
            raise ValueError("No configuration history found for this file")

        return deleted_count

    def delete_single_config(self, file_id: str, config_id: str) -> None:
        """
        Delete one saved configuration for a specific file.
        """
        if self.repo is None:
            raise ValueError("Database session is required")

        deleted = self.repo.delete_by_id_and_file_id(
            file_id=file_id,
            config_id=config_id,
        )

        if not deleted:
            raise ValueError("Configuration not found")


eeg_file_service = EEGFileService()
