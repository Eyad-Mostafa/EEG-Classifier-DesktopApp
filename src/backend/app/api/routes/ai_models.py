from fastapi import APIRouter, HTTPException
from app.models.eeg_data import EEGData
from app.services.temp_file_store_service import temp_file_store
from app.schemas.ai_model_schema import InferenceRequest, InferenceResponse
from app.core.model_registry import get_available_models
from app.services.ai_inference_service import run_ai_inference
from fastapi.responses import FileResponse
import os

router = APIRouter(prefix="/ai-models", tags=["AI Models"])


@router.get("/")
def get_models():
    """
    Get all available pre-trained AI models.
    Scans the models directory and returns metadata for the UI.
    """
    return get_available_models()


@router.post("/predict", response_model=InferenceResponse)
def predict(request: InferenceRequest):
    """
    Run AI Classification on EEG Data.
    Delegates logic to ai_inference_service.
    """
    try:
        response_data = run_ai_inference(
            request.config_id,
            request.model_id,
            request.apply_preprocessing,
            request.label_mapping,
        )
        return InferenceResponse(**response_data)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")


@router.get("/file-labels/{config_id}")
def get_file_labels(config_id: str):
    """
    Returns the label numbers and detailed label names from a temp config.
    Used by the frontend to build the label→class mapping modal.
    """
    file_info = temp_file_store.get(config_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="Data configuration not found.")

    eeg_data = EEGData.from_storage(file_info)
    return {
        "labels": eeg_data.all_labels,
        "detailed_labels": eeg_data.detailed_labels,
    }


@router.get("/download/{result_id}")
def download_predictions_csv(result_id: str):
    """
    Downloads the predictions CSV associated with the result_id.
    """
    from app.services.csv_export_service import get_csv_info

    csv_info = get_csv_info(result_id)
    if not csv_info:
        raise HTTPException(
            status_code=404, detail="CSV file not found or has expired."
        )

    return FileResponse(
        path=csv_info["file_path"], filename=csv_info["filename"], media_type="text/csv"
    )
