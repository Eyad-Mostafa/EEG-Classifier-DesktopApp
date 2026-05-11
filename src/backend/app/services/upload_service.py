import hashlib
import logging
import os
from datetime import datetime
from sqlite3 import IntegrityError
import uuid
from app.repositories.file_repository import FileRepository
from app.services.eeg_services.eeg_file_service import eeg_file_service
from fastapi import UploadFile, HTTPException
from app.models.eeg_data import EEGData
from app.services.file_store_service import file_store

logger = logging.getLogger(__name__)

class UploadService:

    def __init__(self, db_session):
        self.repo = FileRepository(db_session)

    def _compute_hash(self, path: str) -> str | None:
        try:
            h = hashlib.sha256()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return None

    def process_upload(self, file_path: str, sampling_rate: float) -> str:
        """
        Validate the path, parse file, and insert a DB record with the path.
        Returns file_id.
        """

        # 1) Canonicalize and basic checks
        real_path = os.path.realpath(file_path)
        if not os.path.isabs(real_path):
            raise HTTPException(status_code=400, detail="Expected absolute file path")

        if not os.path.exists(real_path):
            raise HTTPException(status_code=404, detail="File not found")

        if not real_path.lower().endswith(".csv"):
            raise HTTPException(status_code=400, detail="Only .csv files supported")

        # 2) Ensure the process can read the file (permission check)
        if not os.access(real_path, os.R_OK):
            raise HTTPException(status_code=403, detail="File is not readable by server process")

        # 3) Parse the EEG CSV into your domain object (uses your existing parser)
        try:
            with open(real_path, "rb") as fh:
                eeg_data = eeg_file_service.create_eeg_data(fh, sampling_rate=sampling_rate)

            # ========== NEW VALIDATION ==========
            is_valid, error_msg = eeg_data.validate_structure()
            if not is_valid:
                raise HTTPException(status_code=422, detail=error_msg)
            # ===================================

            clean_name = os.path.basename(real_path)
            
            if not eeg_data.meta:
                eeg_data.meta = {}
            
            eeg_data.meta["original_name"] = clean_name

            file_id = self.handle_open_file(real_path, sampling_rate, eeg_data)

        except ValueError as ve:
            raise HTTPException(status_code=422, detail=str(ve))
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Error processing upload")
            raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
        
        logger.info(f"File stored successfully. ID: {file_id}, Name: {clean_name}")
        return str(file_id)
    

    def handle_open_file(self, real_path: str, sampling_rate: float, eeg_data: EEGData):
        # 1) Compute hash first
        file_hash = self._compute_hash(real_path)  # your existing _compute_hash

        # 2) Check DB for existing file by hash
        existing = self.repo.get_by_hash(file_hash)  # should return dict or None
        if existing:
            file_id = existing["file_id"]
            self.repo.update_file(file_id, {
                "last_opened_at": datetime.now(),
                "sampling_rate": sampling_rate  # ← ADD THIS
            })
            # ensure same file present in memory — add or skip
            if file_id not in file_store.list_files():
                file_store.add_file(eeg_data, file_id=file_id)
        else:
            # not exist in DB -> create id and persist to DB first
            file_id = str(uuid.uuid4())
            payload = {
                "file_id": file_id,
                "file_name": os.path.basename(real_path),
                "file_path": real_path,
                "file_hash": file_hash,
                "sampling_rate": sampling_rate,
                "first_opened_at": datetime.now(),
                "last_opened_at": datetime.now(),
            }
            try:
                self.repo.add_file(payload)   # will insert using payload["file_id"]
            except IntegrityError:
                # race: somebody else inserted the same hash concurrently
                self.repo.session.rollback()
                existing = self.repo.get_by_hash(file_hash)
                if existing:
                    file_id = existing["file_id"]
                else:
                    # re-raise if unexpected
                    raise

            # add to in-memory store using same file_id
            file_store.add_file(eeg_data, file_id=file_id)

        # now file_id is the canonical id used by both DB and memory
        files = file_store.list_files()
        print("file_id:", file_id)
        print("in-memory keys:", list(files.keys()))
        return file_id