# app/services/temp_file_store_service.py

import glob
import shutil
import uuid
import tempfile
import os
import json
from typing import Dict, Optional, Any


class TempFileStore:

    def __init__(self):
        self._temp_files: Dict[str, Dict] = {}
        self._temp_dir_obj = tempfile.TemporaryDirectory(
            prefix="eegclassifier_"
        )
        self.temp_dir = self._temp_dir_obj.name
        print(f"Temp storage initialized at: {self.temp_dir}")

        self._cleanup_old_crash_folders()

    def _cleanup_old_crash_folders(self):
        temp_base = tempfile.gettempdir()
        # Find folders starting with temp prefix
        old_folders = glob.glob(os.path.join(temp_base, "eegclassifier_*"))
        for folder in old_folders:
            try:
                if folder != self.temp_dir:
                    shutil.rmtree(folder)
                    print(f"Cleaned up old orphaned folder: {folder}")
            except Exception:
                pass

    def update(self, result_id: str, data: Any) -> None:
        """Overwrites the file on disk for an existing ID."""
        if result_id not in self._temp_files:
            raise ValueError(f"Cannot update. File ID {result_id} not found.")
        
        # Reuse the existing filename base
        old_info = self._temp_files[result_id]
        # Robustly get base name (handle cases where file_name might not exist or be weird)
        base_name = old_info.get("file_name", f"temp_{result_id}").split('_')[0]
        
        # This will rewrite both the CSV and the JSON sidecar
        self._save_to_disk(result_id, data, base_name)

    def save(
        self,
        data: Any,
        base_name: str = "temp",
        download_filename: str = None,
        config_id: str = None,
    ) -> str:
        if config_id is None:
            config_id = str(uuid.uuid4())
        self._save_to_disk(config_id, data, base_name, download_filename)
        return config_id


    def _save_to_disk(
        self,
        result_id: str,
        data: Any,
        base_name: str,
        download_filename: str = None
    ):

        if hasattr(data, "df"):
            df = data.df
            meta_payload = {
                "sampling_rate": getattr(data, "sampling_rate", 250),
                "meta": getattr(data, "meta", {}),
                "detailed_labels": getattr(data, "detailed_labels", {})
            }
        else:
            df = data
            meta_payload = {
                "sampling_rate": 250,
                "meta": {},
                "detailed_labels": {}
            }

        # If custom name provided → use it EXACTLY
        if download_filename:
            final_name = download_filename
        else:
            final_name = f"{base_name}_{result_id}.csv"

        csv_path = os.path.join(self.temp_dir, final_name)

        meta_name = os.path.splitext(final_name)[0] + "_meta.json"
        json_path = os.path.join(self.temp_dir, meta_name)

        df.to_csv(csv_path, index=False)

        with open(json_path, "w") as f:
            json.dump(meta_payload, f)

        file_size_bytes = os.path.getsize(csv_path)

        self._temp_files[result_id] = {
            "file_path": csv_path,
            "meta_path": json_path,
            "file_size_bytes": file_size_bytes,
            "file_size_mb": round(file_size_bytes / (1024 * 1024), 2),
            "file_name": final_name
        }

    def get(self, result_id: str) -> Optional[Dict]:

        info = self._temp_files.get(result_id)
        if not info:
            return None

        result = info.copy()

        if os.path.exists(info["meta_path"]):
            with open(info["meta_path"], "r") as f:
                meta_data = json.load(f)
                result.update(meta_data)

        return result

    def remove(self, result_id: str):

        temp_info = self._temp_files.pop(result_id, None)
        if not temp_info:
            return

        if os.path.exists(temp_info["file_path"]):
            os.remove(temp_info["file_path"])

        if os.path.exists(temp_info["meta_path"]):
            os.remove(temp_info["meta_path"])


# Global instance
temp_file_store = TempFileStore()
