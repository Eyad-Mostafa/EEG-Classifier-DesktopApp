import logging
import traceback
from typing import List
from app.models.pipeline_request import StepModel
from app.models.eeg_data import EEGData
from app.core.registry import get_algorithm

logger = logging.getLogger(__name__)

class AlgorithmExecutionError(Exception):
    pass

def execute_pipeline_step(method_id: str, data: EEGData, params: dict) -> EEGData:
    """Runs a single algorithm step."""
    step_instance = get_algorithm(method_id)
    
    if not step_instance:
        raise ValueError(f"Algorithm '{method_id}' not found in registry.")

    logger.info(f"Executing Step: {step_instance.name} ({step_instance.type})")

    try:
        result_data = step_instance.process(data, **params)
        return result_data
    except Exception as e:
        error_msg = f"Error executing '{method_id}': {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise AlgorithmExecutionError(error_msg)

class PipelineExecutor:
    """Runs a chain of steps (Preprocessing)."""
    def __init__(self, pipeline_steps: List[StepModel]):
        self.pipeline_steps = pipeline_steps
    
    def run(self, data: EEGData) -> EEGData:
        current_data = data
        total_steps = len(self.pipeline_steps)
        
        for i, step_model in enumerate(self.pipeline_steps):
            step_id = step_model.name
            params = step_model.params or {}
            logger.info(f"Pipeline [{i+1}/{total_steps}]: Running {step_id}...")
            try:
                current_data = execute_pipeline_step(step_id, current_data, params)
            except Exception as e:
                raise RuntimeError(f"Pipeline failed at step {i+1}/{total_steps} ('{step_id}'): {str(e)}") from e
        
        return current_data