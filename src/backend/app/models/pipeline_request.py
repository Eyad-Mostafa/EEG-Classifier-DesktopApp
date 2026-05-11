"""
Pydantic models for request validation.

StepModel: Represents one step in the pipeline
PipelineRequest: Represents the full pipeline
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class StepModel(BaseModel):
    """
    Represents a single processing step.
    
    Example:
        {"name": "bandpass_filter", "params": {"low": 1.0, "high": 40.0}}
    """
    name: str = Field(..., description="Step name (must exist in registry)")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Step parameters")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "normalize",
                "params": {"method": "zscore"},
                "domainType": "time"
            }
        }

class PipelineRequest(BaseModel):
    """
    Represents a complete processing pipeline.
    
    Example:
        {"pipeline": [
            {"name": "bandpass_filter", "params": {"low": 1.0}},
            {"name": "normalize"}
        ]}
    """
    pipeline: List[StepModel] = Field(..., description="List of processing steps")
    
    def validate_pipeline_not_empty(cls, v):
        if len(v) == 0:
            raise ValueError("Pipeline must contain at least one step")
        if len(v) > 20:
            raise ValueError("Pipeline cannot exceed 20 steps")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "pipeline": [
                    {"name": "bandpass_filter", "params": {"low": 1.0, "high": 40.0}},
                    {"name": "normalize", "params": {"method": "zscore"}}
                ]
            }
        }