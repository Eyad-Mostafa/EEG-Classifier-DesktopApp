from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class InferenceRequest(BaseModel):
    model_id: str = Field(..., description="The ID of the model from the JSON registry")
    config_id: str = Field(..., description="The ID of the filtered EEG data to analyze")
    apply_preprocessing: bool = False
    label_mapping: Optional[Dict[str, str]] = None

class PredictionItem(BaseModel):
    subject: str
    session: str
    trial: int
    predictedClass: str
    confidence: float
    trueClass: Optional[str] = None
    correct: Optional[bool] = None

class InferenceSummary(BaseModel):
    total_trials_analyzed: int
    class_distribution: Dict[str, int]
    average_confidence: float
    metrics: Optional[dict] = None

class InferenceResponse(BaseModel):
    status: str
    model_used: str
    result_id: str
    summary: InferenceSummary
    predictions: List[PredictionItem]