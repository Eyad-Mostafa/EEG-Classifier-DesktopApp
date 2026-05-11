import uuid
from typing import Dict
from app.models.eeg_data import EEGData
import copy

class FileStore:
    """
    Central store for uploaded EEGData files, accessible across routers.
    """
    def __init__(self):
        self._files: Dict[str, EEGData] = {}

    def add_file(self, eeg_data: EEGData, file_id: str = None) -> str:
        if file_id is None:
            file_id = str(uuid.uuid4())
        self._files[file_id] = eeg_data
        return file_id

    def get_file(self, file_id: str, deepcopy_file: bool = False) -> EEGData:
        eeg_data = self._files.get(file_id)
        if not eeg_data:
            raise ValueError(f"File not found: {file_id}")
        return copy.deepcopy(eeg_data) if deepcopy_file else eeg_data

    def list_files(self) -> Dict[str, EEGData]:
        return self._files

    def remove_file(self, file_id: str):
        self._files.pop(file_id, None)


# Global instance
file_store = FileStore()
