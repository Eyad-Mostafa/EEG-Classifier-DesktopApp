import asyncio

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from app.schemas.preprocess_schema import PreprocessRequest, PreprocessResponse
from app.services.temp_file_store_service import temp_file_store
from app.services.generator_service import EEGGeneratorService
from app.core.registry import get_algorithm, get_all_algorithms
from app.services.pipeline_service import run_preprocessing_pipeline

router = APIRouter(prefix="/preprocess", tags=["Preprocess"])

@router.post("/", response_model=PreprocessResponse)
def preprocess_csv(request: PreprocessRequest):
    """
    Run a Preprocessing Pipeline on an EEG File.
    Delegates logic to pipeline_service.
    """
    try:
        response_data = run_preprocessing_pipeline(request.file_id, request.samplingRate, request.pipeline)
        return PreprocessResponse(**response_data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.get("/download/{result_id}")
async def download_result(result_id: str):
    try:
        info = temp_file_store.get(result_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Result not found")

    return FileResponse(
        path=info["file_path"],
        media_type="text/csv",
        filename=info["file_name"],
    )


@router.get("/sample-csv")
async def download_sample_csv():
    """
    Generate and stream a synthetic sample CSV.
    Generation runs in a thread pool so it never blocks the async event loop.
    """
    try:
        # Run the blocking CPU call in a thread — keeps the event loop free
        loop = asyncio.get_event_loop()
        stream = await loop.run_in_executor(
            None, EEGGeneratorService.generate_synthetic_csv
        )
        return StreamingResponse(
            iter([stream.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=sample_eeg_file.csv"},
        )
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")


@router.get("/steps")
def get_available_steps():
    """Get ONLY Preprocessing steps."""
    all_steps = get_all_algorithms(detailed=False)
    
    preprocess_steps = [
        s for s in all_steps 
        if s.get('type') == 'preprocessing'
    ]
    return preprocess_steps


@router.get("/steps/{step_id}")
def get_step_detail(step_id: str):
    """Get details for a specific step."""
    step_instance = get_algorithm(step_id)
    
    if not step_instance:
        raise HTTPException(status_code=404, detail="Step not found")
    
    if step_instance.type != 'preprocessing':
        raise HTTPException(status_code=404, detail=f"Step '{step_id}' is not a preprocessing step")

    return step_instance.get_info(detailed=True)
