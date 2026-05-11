from typing import Any, List
from pydantic import BaseModel


class SubjectFilter(BaseModel):
    subjectId: str
    sessions: List[str]
class SessionTrialsFilter(BaseModel):
    sessionId: str
    trials: List[str]
class SubjectTrialsFilter(BaseModel):
    subjectId: str
    sessions: List[SessionTrialsFilter]
class FilterRequest(BaseModel):
    subjects: List[SubjectTrialsFilter]
    labels: dict[str, int] = {}
    channels: dict[str, str] = {}
    selected_channels: dict[str, bool] = {}
    montage: str = "standard_1020"

class FilterResponse(BaseModel):
    status: str
    tempFileId: str
    n_rows: int
    n_subjects: int