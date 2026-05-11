from pydantic import BaseModel
from typing import Any, Dict, List, Union, Optional


class AnalysisResult(BaseModel):
    summary: Dict[str, Any] = {}
    analysis_data: Union[List[Any], Dict[str, Any], None] = None
    visualization_data: Optional[Dict[str, Any]] = None


class AnalysisResponse(BaseModel):
    method_id: str
    success: bool
    result: AnalysisResult


class ErrorResponse(BaseModel):
    detail: str


class AnalysisRequest(BaseModel):
    method_id: str
    file_id: str
    config_id: str
    pipeline_id: Optional[int] = None
    source_type: str
    samplingRate: float
    parameters: Optional[Dict[str, Any]] = None


class AnalysisHistoryRequest(BaseModel):
    config_id: str
    pipeline_id: Optional[int] = None
    source_type: str


class AnalysisHistoryItem(BaseModel):
    method_id: str
    analysis_run_id: int
    executed_at: Optional[str] = None
    result: AnalysisResult


class AnalysisHistoryResponse(BaseModel):
    items: List[AnalysisHistoryItem]
