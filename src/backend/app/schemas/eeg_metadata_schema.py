from pydantic import BaseModel
from typing import List, Optional

from pydantic import BaseModel
from typing import List, Optional

class SessionTrialsSchema(BaseModel):
    sessionId: str
    trials: List[str] 

class SubjectSessionTrialsSchema(BaseModel):
    subjectId: str
    sessions: List[SessionTrialsSchema]

class EEGMetadataSchema(BaseModel):
    fileId: str
    samplingRate: float
    subjects: List[SubjectSessionTrialsSchema] 
    labels: Optional[List[int]] = []
    channels: List[str]