from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query
import numpy as np
from requests import Session
from app.db.dependencies import get_db_session
from app.models.eeg_data import EEGData
from app.repositories.visualization_repository import VisualizationPlotRepository
from app.schemas.visualization_schema import EEGSessionData, EEGSubjectData, EEGTrialData, SavePlotRequest, SpectrogramData, SpectrogramResponse, SummaryResponse, VisualizationRequest, VisualizationResponse
from app.services.temp_file_store_service import temp_file_store
from scipy.signal import spectrogram
from app.services.visualization import generate_visualization

router = APIRouter(prefix="/visualization", tags=["Visualization"])

@router.post("/", response_model=VisualizationResponse)
def get_visualization(request: VisualizationRequest):
    results = generate_visualization(request)
    return results

@router.post("/spectrogram", response_model=SpectrogramResponse)
def get_spectrograms(request: VisualizationRequest):
    raw_info = temp_file_store.get(request.rawDataId)
    if not raw_info:
        raise HTTPException(
            status_code=404,
            detail=f"Raw file ID {request.rawDataId} not found"
        )

    clean_info = None
    if not request.rawDataOnly and request.cleanDataId:
        clean_info = temp_file_store.get(request.cleanDataId)
        if not clean_info:
            raise HTTPException(
                status_code=404,
                detail=f"Clean file ID {request.cleanDataId} not found"
            )

    try:
        raw_eeg = EEGData.from_storage(raw_info)
        clean_eeg = EEGData.from_storage(clean_info) if clean_info else None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading EEG: {e}")

    raw_data = []
    for idx, col in enumerate(raw_eeg.channels_only.columns):
        ch_array = raw_eeg.channels_only[col].to_numpy()
        if ch_array.size == 0:
            raise HTTPException(status_code=500, detail=f"Empty RAW channel {idx}")
        try:
            f, t, Sxx = spectrogram(ch_array, fs=raw_eeg.sampling_rate)
            raw_data.append(SpectrogramData(times=t.tolist(), frequencies=f.tolist(), values=Sxx.tolist()))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error computing RAW spectrogram channel {idx}: {e}")

    clean_data = []
    if clean_eeg:
        for idx, col in enumerate(clean_eeg.channels_only.columns):
            ch_array = clean_eeg.channels_only[col].to_numpy()
            if ch_array.size == 0:
                raise HTTPException(status_code=500, detail=f"Empty CLEAN channel {idx}")
            try:
                f, t, Sxx = spectrogram(ch_array, fs=clean_eeg.sampling_rate)
                clean_data.append(SpectrogramData(times=t.tolist(), frequencies=f.tolist(), values=Sxx.tolist()))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error computing CLEAN spectrogram channel {idx}: {e}")

    return SpectrogramResponse(
        rawSpectrograms=raw_data,
        cleanSpectrograms=clean_data if clean_data else None
    )


@router.post("/summary", response_model=SummaryResponse)
def get_visualization_summary(request: VisualizationRequest):

    raw_info = temp_file_store.get(request.rawDataId)
    clean_info = temp_file_store.get(request.cleanDataId)

    if not raw_info or not clean_info:
        raise HTTPException(status_code=404, detail="One or both file IDs not found")

    try:
        raw_eeg = EEGData.from_storage(raw_info)
        clean_eeg = EEGData.from_storage(clean_info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading EEG: {e}")

    return SummaryResponse(
        rawSummary=raw_eeg.summary(),
        cleanSummary=clean_eeg.summary()
    )

@router.post("/add-plot")
def create_plot(payload: SavePlotRequest, db: Session = Depends(get_db_session)):
    repo = VisualizationPlotRepository(db)
    try:
        result = repo.save_or_update_plot(payload)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/plot/{plot_id}")
def get_plot(plot_id: int, db: Session = Depends(get_db_session)):
    repo = VisualizationPlotRepository(db)
    row = repo.get_by_id(plot_id)
    if not row:
        raise HTTPException(status_code=404, detail="Plot not found")
    return row


@router.get("/get-plots")
def list_plots(
    config_id: str = Query(...),
    db: Session = Depends(get_db_session),
):
    repo = VisualizationPlotRepository(db)
    return repo.get_by_config_id(config_id)


@router.put("/plot/{plot_id}")
def update_plot(
    plot_id: int,
    patch: Dict[str, Any],
    db: Session = Depends(get_db_session),
):
    repo = VisualizationPlotRepository(db)
    repo.update_plot(plot_id, patch)
    return {"success": True}


@router.delete("/plot/{plot_id}")
def delete_plot(plot_id: int, db: Session = Depends(get_db_session)):
    repo = VisualizationPlotRepository(db)
    repo.delete_plot(plot_id)
    return {"success": True}

@router.delete("/plots/all/{config_id}", status_code=204)
def delete_all_plots(config_id: str, db: Session = Depends(get_db_session)):
    repo = VisualizationPlotRepository(db)
    repo.delete_all_plots(config_id)