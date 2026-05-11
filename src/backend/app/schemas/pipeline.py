import datetime
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.models.pipeline_request import StepModel

class SavePipelineRequest(BaseModel):
    pipeline_name: str
    is_template: bool = True
    config_id: Optional[str] = None
    file_name: Optional[str] = None  # Add this field
    executed_at: Optional[datetime.datetime] = None
    pipeline: List[StepModel]
    notes: Optional[str] = None

class LoadPipelineResponse(BaseModel):
    pipeline_id: int
    pipeline_name: str
    is_template: bool
    file_id: Optional[str] = None
    file_name: Optional[str] = None
    executed_at: datetime.datetime
    notes: Optional[str] = None
    steps: List[StepModel]
    algorithm_count: int

class PipelineSummaryResponse(BaseModel):
    pipeline_id: int
    pipeline_name: str
    is_template: bool
    file_id: Optional[str] = None
    file_name: Optional[str] = None
    executed_at: datetime.datetime
    notes: Optional[str] = None
    algorithm_count: int