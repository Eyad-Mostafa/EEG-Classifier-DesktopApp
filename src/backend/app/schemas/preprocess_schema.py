from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.models.pipeline_request import StepModel
from app.schemas.domain_enum import DomainType

class PreprocessRequest(BaseModel):
    file_id: str = Field(..., description="The UUID of the file in temp storage")
    samplingRate: int = Field(..., description="The sampling rate of the EEG data")
    pipeline: List[StepModel]
class PreprocessResponse(BaseModel):
    status: str
    result_id: str
    file_name: str
    sampling_rate: float
    file_size_mb: float
    processing_time: str
    figure_data_original: Optional[str] = None
    figure_data_processed: Optional[str] = None
    summary: Dict[str, Any]
    meta: Dict[str, Any]
    domainType: DomainType
    data_preview: List[Dict[str, Any]]