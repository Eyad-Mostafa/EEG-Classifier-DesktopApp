from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List

class UploadResponse(BaseModel):
    status: str
    filename: str
    file_id: str

class UploadHistoryItem(BaseModel):
    file_id: str
    filename: str
    sampling_rate: float
    file_path: str
    first_opened_time: datetime
    last_opened_at: Optional[datetime] = None

class UploadErrorResponse(BaseModel):
    status: str
    message: str
    details: Optional[str] = None    