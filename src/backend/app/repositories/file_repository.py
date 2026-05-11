from typing import Optional, List, Dict, Any
from sqlalchemy import desc, nullslast
from sqlalchemy.orm import Session
from app.db.models import File
from datetime import datetime

from app.schemas.upload_schema import UploadHistoryItem

class FileRepository:
    """
    Simple repository for files. Methods commit by default for simplicity.
    If you prefer to control transactions at a higher level, remove commits here.
    """
    def __init__(self, session: Session):
        self.session = session

    def get_by_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        if not file_hash:
            return None
        dbf = self.session.query(File).filter(File.file_hash == file_hash).one_or_none()
        return self._to_dict(dbf) if dbf else None

    def add_file(self, payload: Dict[str, Any]) -> str:
        db_file = File(
            file_id=payload["file_id"],
            file_name=payload["file_name"],
            file_path=payload["file_path"],
            file_hash=payload.get("file_hash"),
            sampling_rate=payload.get("sampling_rate"),
            first_opened_at=payload.get("first_opened_at") or datetime.now(),
            last_opened_at=payload.get("last_opened_at") or datetime.now(),
        )
        self.session.add(db_file)
        self.session.commit()         # simple behavior: commit immediately
        self.session.refresh(db_file)

        return db_file.file_id


    def get_by_id(self, file_id: int) -> Optional[Dict[str, Any]]:
        dbf = self.session.get(File, file_id)
        return self._to_dict(dbf) if dbf else None


    def get_by_path(self, path: str) -> Optional[Dict[str, Any]]:
        dbf = self.session.query(File).filter(File.file_path == path).one_or_none()
        return self._to_dict(dbf) if dbf else None


    def list_files(self, limit: int = 100, offset: int = 0) -> List[UploadHistoryItem]:
        rows = self.session.query(File).order_by(nullslast(desc(File.last_opened_at))).limit(limit).offset(offset).all()

        return [
            UploadHistoryItem(
                file_id=r.file_id,
                filename=r.file_name,
                sampling_rate=r.sampling_rate,
                file_path=r.file_path,
                first_opened_time=r.first_opened_at,
                last_opened_at=r.last_opened_at,
            )
            for r in rows
        ]


    def update_file(self, file_id: int, patch: Dict[str, Any]) -> None:
        dbf = self.session.get(File, file_id)
        if not dbf:
            return
        for k, v in patch.items():
            if hasattr(dbf, k):
                setattr(dbf, k, v)
        self.session.commit()


    def delete_file(self, file_id: str) -> bool:
        """Deletes a single file and cascades to all related data."""
        dbf = self.session.get(File, file_id)
        if not dbf:
            return False
            
        self.session.delete(dbf)
        self.session.commit()
        return True

    def delete_all_files(self) -> None:
        """Deletes all files and cascades to all related data."""
        files = self.session.query(File).all()
        for f in files:
            self.session.delete(f)
            
        self.session.commit()


    def _to_dict(self, dbf: File) -> Dict[str, Any]:
        return {
            "file_id": dbf.file_id,
            "file_name": dbf.file_name,
            "file_path": dbf.file_path,
            "file_hash": dbf.file_hash,
            "sampling_rate": dbf.sampling_rate,
            "first_opened_at": dbf.first_opened_at,
        }