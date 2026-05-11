from typing import Any, Dict, List, Literal,Optional
from pydantic import BaseModel, Field

class VisualizationRequest(BaseModel):
    rawDataId: str = Field(..., description="Configured data (raw uploaded EEG file)")
    cleanDataId: Optional[str] = Field(None, description="Preprocessed data (after preprocessing pipeline)")
    rawDataOnly: bool = Field(..., description="if user send preprocessed data or not")
    samplingRate: float = Field(..., description="Sampling rate of the EEG data")

class EEGTrialData(BaseModel):
    trialId: str
    label: Optional[str] = ""
    category: Optional[str]
    time: List[float]
    channels: Dict[str, List[float]]

class EEGSessionData(BaseModel):
    sessionId: str
    trials: List[EEGTrialData]

class EEGSubjectData(BaseModel):
    subjectId: str
    sessions: List[EEGSessionData]

class VisualizationResponse(BaseModel):
    raw: List[EEGSubjectData]
    clean: Optional[List[EEGSubjectData]]

class SummaryResponse(BaseModel):
    rawSummary: Dict[str, Any]
    cleanSummary: Optional[Dict[str, Any]]

class SpectrogramData(BaseModel):
    times: List[float]
    frequencies: List[float]
    values: List[List[float]]  # 2D array: freq x time

class SpectrogramResponse(BaseModel):
    rawSpectrograms: List[SpectrogramData]
    cleanSpectrograms: Optional[List[SpectrogramData]]

class PlotFilterRequest(BaseModel):
    data_type: Literal["raw", "clean"]
    subject_id: str
    session_id: str
    labels: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    channels: List[str] = Field(default_factory=list)

class SavePlotRequest(BaseModel):
    config_id: str
    plot_name: Optional[str] = None
    filters: PlotFilterRequest