import logging
import os
from fastapi import APIRouter, Form, Depends, status, HTTPException
from app.repositories.file_repository import FileRepository
from app.schemas.upload_schema import UploadHistoryItem, UploadResponse
from app.services.upload_service import UploadService
from app.db.dependencies import get_db_session
from sqlalchemy.orm import Session

router = APIRouter(prefix="/upload", tags=["Upload"])
logger = logging.getLogger(__name__)

@router.post("/", status_code=status.HTTP_200_OK, response_model=UploadResponse)
def upload_file(
    file_path: str = Form(...),
    sample_rate: int = Form(...),
    db: Session = Depends(get_db_session),
):
    """
    **Upload an EEG CSV file.**
    
    - Validates the .csv extension.
    - Parses the EEG data structure.
    - Stores it in memory/temp storage for processing.
    """
    service = UploadService(db)

    file_id = service.process_upload(file_path=file_path, sampling_rate=sample_rate)

    return UploadResponse(
        status="uploaded",
        filename=os.path.basename(file_path),
        file_id=file_id
    )


@router.get("/history", status_code=status.HTTP_200_OK, response_model=list[UploadHistoryItem])
def upload_history(db: Session = Depends(get_db_session)):
    """
    **Get upload history.**
    
    - Returns a list of previously uploaded files with metadata.
    - Useful for tracking and debugging uploads.
    """
    repo = FileRepository(db)
    files = repo.list_files()
    return files


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_single_file(file_id: str, db: Session = Depends(get_db_session)):
    """
    **Delete a specific file.**
    
    - Deletes the file record from the database.
    - Automatically cascades to delete all configurations, pipelines, 
      analysis runs, and results linked to this file.
    """
    repo = FileRepository(db)
    success = repo.delete_file(file_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"File with ID {file_id} not found."
        )
    
    return None


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def delete_all_files(db: Session = Depends(get_db_session)):
    """
    **Delete ALL files and everything associated with them.**
    
    - Completely wipes the files table.
    - Automatically cascades to clear all configurations, pipelines, 
      plots, and analysis results from the database.
    - DANGER: This action cannot be undone.
    """
    repo = FileRepository(db)
    repo.delete_all_files()
    
    return None