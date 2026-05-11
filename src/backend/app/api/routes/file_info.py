from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.db.dependencies import get_db_session
from app.schemas.eeg_metadata_schema import EEGMetadataSchema
from app.schemas.config_schema import FilterRequest, FilterResponse
from app.services.eeg_services.eeg_file_service import EEGFileService, eeg_file_service
from app.repositories.configuration_repository import FileConfigurationRepository

router = APIRouter(prefix="/file-info", tags=["File Info"])


@router.get("/{file_id}/metadata", response_model=EEGMetadataSchema)
def get_file_metadata(file_id: str):
    try:
        metadata = eeg_file_service.get_metadata(file_id)
        return metadata
    except ValueError:
        raise HTTPException(status_code=404, detail="File not found")


@router.get("/{file_id}/config-history")
def get_file_config_history(file_id: str, db: Session = Depends(get_db_session)):
    """
    Get all saved configurations for a specific file.
    Returns the newest configurations first.
    """
    repo = FileConfigurationRepository(db)

    try:
        configurations = repo.get_by_file_id(file_id)
        return configurations
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to load configuration history: {str(e)}"
        )


@router.post("/filter/{file_id}", response_model=FilterResponse)
def filter_file(
    file_id: str,
    filter_req: FilterRequest = Body(...),
    db: Session = Depends(get_db_session),
):
    """
    Applies subject and session filtering to the loaded EEG dataset.
    Delegates complex orchestration to the Service layer.
    """
    service = EEGFileService(db)
    try:
        result = service.apply_filter(file_id, filter_req)
        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Filtering failed: {str(e)}")


@router.delete("/{file_id}/config-history")
def delete_file_config_history(file_id: str, db: Session = Depends(get_db_session)):
    """
    Delete all saved configurations for a specific file.
    """
    service = EEGFileService(db)

    try:
        deleted_count = service.delete_config_history(file_id)

        return {
            "message": "Configuration history deleted successfully",
            "file_id": file_id,
            "deleted_count": deleted_count,
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete configuration history: {str(e)}",
        )


@router.delete("/{file_id}/config-history/{config_id}")
def delete_single_file_config(
    file_id: str,
    config_id: str,
    db: Session = Depends(get_db_session),
):
    """
    Delete one saved configuration for a specific file.
    """
    service = EEGFileService(db)

    try:
        service.delete_single_config(file_id=file_id, config_id=config_id)

        return {
            "message": "Configuration deleted successfully",
            "file_id": file_id,
            "config_id": config_id,
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete configuration: {str(e)}",
        )
