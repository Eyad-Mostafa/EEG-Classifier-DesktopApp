# app/services/pipeline_service.py

import os
import re
import time
import hashlib
import json
from typing import Dict, Any

from app.core.executor import PipelineExecutor
from app.services.temp_file_store_service import temp_file_store
from app.models.eeg_data import EEGData
from app.services.visualization import generate_eeg_base64
from app.schemas.domain_enum import DomainType
from app.core.registry import get_algorithm


def sanitize_filename(name: str) -> str:
    """
    Remove illegal characters for Windows/Linux filenames.
    """
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = name.replace(" ", "_")
    return name


def run_preprocessing_pipeline(
    file_id: str, samplingRate: int, pipeline_steps: list
) -> Dict[str, Any]:

    # 1 Load original file
    file_info = temp_file_store.get(file_id)
    if not file_info:
        raise ValueError(f"File {file_id} not found in temp storage")

    # Extract ORIGINAL uploaded name safely
    original_filename = file_info["file_name"]
    original_name = os.path.splitext(original_filename)[0]

    original_name = sanitize_filename(original_name)

    eeg_data = EEGData.from_storage(file_info)
    eeg_data.sampling_rate = samplingRate

    # 2 Visualize BEFORE
    fig_original_b64 = generate_eeg_base64(eeg_data.df, title="Raw EEG Data")

    start_time = time.time()

    # 3 Execute Pipeline
    executor = PipelineExecutor(pipeline_steps)
    result_eeg = executor.run(eeg_data)

    duration = time.time() - start_time

    # 4 Visualize AFTER
    fig_processed_b64 = generate_eeg_base64(result_eeg.df, title="Processed EEG Data")

    # 5 Build clean step suffix
    step_names = []
    for step in pipeline_steps:
        name = getattr(step, "name", "step")
        step_names.append(sanitize_filename(name))

    if not step_names:
        steps_suffix = "raw"
    else:
        steps_suffix = ",".join(step_names)

    # FINAL NAME FORMAT
    custom_name = f"preprocessed_{steps_suffix}.csv"

    # 6 Save with custom name
    result_id = temp_file_store.save(result_eeg, download_filename=custom_name)

    temp_info = temp_file_store.get(result_id)

    # 7 Determine domain
    final_domain = DomainType.TIME.value

    new_sampling_rate = result_eeg.sampling_rate

    if pipeline_steps:
        last_step_name = pipeline_steps[-1].name
        algorithm_instance = get_algorithm(last_step_name)

        if algorithm_instance:
            domain_enum = getattr(algorithm_instance, "domainType", DomainType.TIME)
            final_domain = (
                domain_enum.value if hasattr(domain_enum, "value") else str(domain_enum)
            )

    return {
        "status": "success",
        "result_id": result_id,
        "file_name": temp_info["file_name"],
        "sampling_rate": new_sampling_rate,
        "file_size_mb": temp_info["file_size_mb"],
        "processing_time": f"{duration:.2f}s",
        "figure_data_original": fig_original_b64,
        "figure_data_processed": fig_processed_b64,
        "summary": result_eeg.summary(),
        "meta": result_eeg.meta,
        "domainType": final_domain,
        "data_preview": result_eeg.df.head(50).to_dict(orient="records"),
    }


def build_pipeline_signature(config_id, steps):
    payload = {
        "config_id": config_id,
        "steps": steps,
    }

    canonical_string = json.dumps(payload, sort_keys=True, separators=(",", ":"))

    return hashlib.sha256(canonical_string.encode("utf-8")).hexdigest()
