from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.dependencies import get_db_session
from app.repositories.system_repository import SystemRepository

router = APIRouter(prefix="/system", tags=["System"])

@router.delete("/wipe", status_code=status.HTTP_204_NO_CONTENT)
def wipe_entire_database(db: Session = Depends(get_db_session)):
    """
    **Factory Reset**
    
    - Deletes ALL uploaded files and their histories.
    - Deletes ALL configurations and analysis results.
    - Deletes ALL pipelines, including global templates.
    """
    repo = SystemRepository(db)
    repo.factory_reset()
    
    return None