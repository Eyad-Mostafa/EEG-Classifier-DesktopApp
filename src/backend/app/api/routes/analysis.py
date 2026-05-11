from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.services.analysis_service import run_analysis
from app.core.registry import get_algorithm, get_all_algorithms
from app.db.models import AnalysisMethod
from app.db.dependencies import get_db_session
from app.repositories.analysis_repository import AnalysisRepository
from app.schemas.analysis_schema import (
    AnalysisRequest,
    AnalysisResponse,
    ErrorResponse,
    AnalysisHistoryRequest,
    AnalysisHistoryResponse,
    AnalysisHistoryItem,
)

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.post(
    "/run",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    responses={404: {"model": ErrorResponse}, 422: {"description": "Validation error"}},
)
def run_analysis_endpoint(
    request: AnalysisRequest,
    db: Session = Depends(get_db_session),
):
    # 1. Get the method
    method = get_algorithm(request.method_id)

    if not method:
        raise HTTPException(
            status_code=404, detail=f"Analysis method '{request.method_id}' not found"
        )

    # 2. Validate Parameters
    try:
        validated_params = method.validate_parameters(request.parameters or {})
    except ValueError as e:
        raise HTTPException(
            status_code=422, detail=f"Parameter validation failed: {str(e)}"
        )

    repo = AnalysisRepository(db)

    db_method = (
        db.query(AnalysisMethod)
        .filter(AnalysisMethod.method_name == request.method_id)
        .one_or_none()
    )

    if not db_method:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis method '{request.method_id}' not found in database",
        )

    try:
        existing_run = repo.get_existing_run(
            config_id=request.config_id,
            pipeline_id=request.pipeline_id,
            analysis_method_id=db_method.analysis_method_id,
            source_type=request.source_type,
            parameters_json=validated_params,
        )

        if existing_run and existing_run.get("results"):
            latest_result = existing_run["results"][0]
            cached_result = latest_result.get("result_json")

            if cached_result:
                return AnalysisResponse(
                    method_id=request.method_id,
                    success=True,
                    result=cached_result,
                )

        raw_result = run_analysis(
            request.file_id,
            request.method_id,
            request.samplingRate,
            validated_params,
        )

        if not raw_result:
            raise HTTPException(status_code=500, detail="Analysis produced no result")

        analysis_run_id = repo.create_analysis_run(
            config_id=request.config_id,
            pipeline_id=request.pipeline_id,
            analysis_method_id=db_method.analysis_method_id,
            source_type=request.source_type,
            parameters_json=validated_params,
        )

        repo.save_analysis_result(
            analysis_run_id=analysis_run_id,
            result_path=f"analysis://{request.source_type}/{request.config_id}/{request.pipeline_id}/{request.method_id}",
            result_json=raw_result,
        )

        return AnalysisResponse(
            method_id=request.method_id,
            success=True,
            result=raw_result,
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/methods")
def list_analysis_methods(detailed: bool = False):
    """
    Get all available analysis methods.
    """
    all_steps = get_all_algorithms(detailed=detailed)

    analysis_methods = [step for step in all_steps if step.get("type") == "analysis"]

    return analysis_methods


@router.get("/methods/{method_id}")
def get_analysis_method_detail(method_id: str):
    """
    Get detailed information for a specific analysis method.
    """
    method = get_algorithm(method_id)

    if not method:
        raise HTTPException(
            status_code=404, detail=f"Analysis method '{method_id}' not found"
        )

    return method.get_info(detailed=True)


@router.get("/db-methods")
def list_analysis_methods_from_db(db: Session = Depends(get_db_session)):
    rows = db.query(AnalysisMethod).all()
    return [
        {
            "analysis_method_id": row.analysis_method_id,
            "method_name": row.method_name,
            "description": row.description,
        }
        for row in rows
    ]


@router.post("/history", response_model=AnalysisHistoryResponse)
def get_analysis_history(
    request: AnalysisHistoryRequest,
    db: Session = Depends(get_db_session),
):
    repo = AnalysisRepository(db)

    runs = repo.get_runs_by_context(
        config_id=request.config_id,
        pipeline_id=request.pipeline_id,
        source_type=request.source_type,
    )

    if not runs:
        return AnalysisHistoryResponse(items=[])

    method_ids = {
        run["analysis_method_id"]
        for run in runs
        if run.get("analysis_method_id") is not None
    }

    methods = (
        db.query(AnalysisMethod)
        .filter(AnalysisMethod.analysis_method_id.in_(method_ids))
        .all()
        if method_ids
        else []
    )

    method_name_map = {
        method.analysis_method_id: method.method_name for method in methods
    }

    items = []

    for run in runs:
        results = run.get("results") or []
        if not results:
            continue

        latest_result = results[0]
        result_json = latest_result.get("result_json")

        if not result_json:
            continue

        method_id = method_name_map.get(run["analysis_method_id"])
        if not method_id:
            continue

        executed_at = run.get("executed_at")
        executed_at_str = executed_at.isoformat() if executed_at else None

        items.append(
            AnalysisHistoryItem(
                method_id=method_id,
                analysis_run_id=run["analysis_run_id"],
                executed_at=executed_at_str,
                result=result_json,
            )
        )

    return AnalysisHistoryResponse(items=items)
