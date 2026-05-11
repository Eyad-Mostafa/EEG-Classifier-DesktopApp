import datetime
import json
from fastapi import APIRouter, Depends, HTTPException
from app.services.pipeline_service import build_pipeline_signature
from sqlalchemy.orm import Session
from typing import List, Optional
from sqlalchemy import and_

from app.db import get_session
from app.db.models import (
    Pipeline,
    File,
    FileConfiguration,
    PipelineStep,
    PreprocessingMethod,
)
from app.schemas.pipeline import (
    SavePipelineRequest,
    LoadPipelineResponse,
    PipelineSummaryResponse,
)
from app.models.pipeline_request import StepModel

router = APIRouter(prefix="/pipelines", tags=["Pipelines"])


def get_db():
    db = get_session()
    try:
        yield db
    finally:
        db.close()


@router.post("/save")
def save_pipeline(request: SavePipelineRequest, db: Session = Depends(get_db)):
    """Save a pipeline to database"""

    print("=" * 50)
    print("SAVE PIPELINE REQUEST:")
    print(f"  Name: {request.pipeline_name}")
    print(f"  Is Template: {request.is_template}")
    print(f"  Config ID: {request.config_id}")
    print(f"  Steps: {len(request.pipeline)}")

    # Use config_id directly for file-specific pipelines
    config_id = request.config_id if not request.is_template else None

    prepared_steps = []

    # Prepare steps first
    for idx, step in enumerate(request.pipeline):
        method = db.query(PreprocessingMethod).filter_by(method_name=step.name).first()
        if not method:
            method = PreprocessingMethod(method_name=step.name)
            db.add(method)
            db.flush()

        prepared_steps.append(
            {
                "method_id": method.method_id,
                "step_order": idx,
                "parameters": step.params if step.params else {},
            }
        )

    # Build signature
    signature = build_pipeline_signature(config_id, prepared_steps)

    # Check for duplicates
    existing_pipeline = db.query(Pipeline).filter_by(signature=signature).first()
    if existing_pipeline:
        return {
            "message": "Pipeline already exists",
            "pipeline_id": existing_pipeline.pipeline_id,
            "is_template": existing_pipeline.is_template,
            "steps_saved": len(request.pipeline),
            "duplicate": True,
        }

    # Create Pipeline entry
    pipeline = Pipeline(
        pipeline_name=request.pipeline_name,
        is_template=request.is_template,
        config_id=config_id,
        executed_at=datetime.datetime.now(),
        notes=request.notes or "",
        signature=signature,
    )

    db.add(pipeline)
    db.flush()

    # Create PipelineStep entries
    for step_data in prepared_steps:
        step_entry = PipelineStep(
            pipeline_id=pipeline.pipeline_id,
            step_order=step_data["step_order"],
            method_id=step_data["method_id"],
            parameters_json=json.dumps(step_data["parameters"]),
        )
        db.add(step_entry)

    db.commit()
    db.refresh(pipeline)

    return {
        "message": "Pipeline saved successfully",
        "pipeline_id": pipeline.pipeline_id,
        "is_template": pipeline.is_template,
        "steps_saved": len(request.pipeline),
        "duplicate": False,
    }


@router.get("/global")
def get_global_pipelines(db: Session = Depends(get_db)):
    """Get all global pipelines (templates)"""
    pipelines = (
        db.query(Pipeline)
        .filter(Pipeline.is_template == True)
        .order_by(Pipeline.executed_at.desc())
        .all()
    )

    result = []
    for p in pipelines:
        steps = (
            db.query(PipelineStep)
            .filter(PipelineStep.pipeline_id == p.pipeline_id)
            .order_by(PipelineStep.step_order)
            .all()
        )

        # Convert steps to StepModel format for frontend
        step_models = []
        for step in steps:
            params = json.loads(step.parameters_json) if step.parameters_json else {}
            step_models.append(StepModel(name=step.method.method_name, params=params))

        result.append(
            {
                "pipeline_id": p.pipeline_id,
                "pipeline_name": p.pipeline_name,
                "executed_at": p.executed_at,
                "pipeline": [{"name": s.name, "params": s.params} for s in step_models],
                "notes": p.notes,
                "algorithm_count": len(steps),
            }
        )

    return result


@router.get("/file/{file_id}")
def get_file_pipelines(file_id: str, db: Session = Depends(get_db)):
    """Get all pipelines saved for a specific config_id"""
    print(f"Getting pipelines for config_id: {file_id}")

    # Direct query by config_id
    pipelines = (
        db.query(Pipeline)
        .filter(and_(Pipeline.config_id == file_id, Pipeline.is_template == False))
        .order_by(Pipeline.executed_at.desc())
        .all()
    )

    print(f"  Found {len(pipelines)} pipelines")

    result = []
    for p in pipelines:
        steps = (
            db.query(PipelineStep)
            .filter(PipelineStep.pipeline_id == p.pipeline_id)
            .order_by(PipelineStep.step_order)
            .all()
        )

        step_models = []
        for step in steps:
            params = json.loads(step.parameters_json) if step.parameters_json else {}
            step_models.append(StepModel(name=step.method.method_name, params=params))

        result.append(
            {
                "pipeline_id": p.pipeline_id,
                "pipeline_name": p.pipeline_name,
                "executed_at": p.executed_at,
                "pipeline": [{"name": s.name, "params": s.params} for s in step_models],
                "notes": p.notes,
                "algorithm_count": len(steps),
                "config_id": file_id,
            }
        )

    return result


@router.get("/load/{pipeline_id}")
def load_pipeline(pipeline_id: int, db: Session = Depends(get_db)):
    """Load a complete pipeline by ID"""

    pipeline = db.query(Pipeline).filter(Pipeline.pipeline_id == pipeline_id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    # Get steps in order
    steps = (
        db.query(PipelineStep)
        .filter(PipelineStep.pipeline_id == pipeline_id)
        .order_by(PipelineStep.step_order)
        .all()
    )

    # Get file info if applicable
    file_id = None
    file_name = None
    if pipeline.config_id:
        config = (
            db.query(FileConfiguration)
            .filter(FileConfiguration.config_id == pipeline.config_id)
            .first()
        )
        if config:
            db_file = db.query(File).filter(File.file_id == config.file_id).first()
            if db_file:
                file_id = db_file.file_hash
                file_name = db_file.file_name

    # Convert steps to StepModel list
    step_models = []
    for step in steps:
        params = json.loads(step.parameters_json) if step.parameters_json else {}
        step_models.append(StepModel(name=step.method.method_name, params=params))

    return {
        "pipeline_id": pipeline.pipeline_id,
        "pipeline_name": pipeline.pipeline_name,
        "is_template": pipeline.is_template,
        "file_id": file_id,
        "file_name": file_name,
        "executed_at": pipeline.executed_at,
        "notes": pipeline.notes,
        "steps": [{"name": s.name, "params": s.params} for s in step_models],
        "algorithm_count": len(step_models),
    }


@router.delete("/delete/{pipeline_id}")
def delete_pipeline(pipeline_id: int, db: Session = Depends(get_db)):
    """Delete a pipeline"""

    pipeline = db.query(Pipeline).filter(Pipeline.pipeline_id == pipeline_id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    db.delete(pipeline)
    db.commit()

    return {"message": "Pipeline deleted successfully"}


@router.post("/auto-save")
def auto_save_pipeline(request: SavePipelineRequest, db: Session = Depends(get_db)):
    """Auto-save pipeline when applied without explicit save - always file-specific"""

    # Force file-specific and add auto-save marker
    request.is_template = False
    if not request.pipeline_name.startswith("[AUTO]"):
        request.pipeline_name = f"[AUTO] {request.pipeline_name}"

    return save_pipeline(request, db)
