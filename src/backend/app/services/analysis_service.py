from app.core.registry import get_algorithm 
from app.core.executor import execute_pipeline_step
from app.services.temp_file_store_service import temp_file_store
from app.models.eeg_data import EEGData

def run_analysis(file_id: str, method_id: str, samplingRate: int, params: dict):
    # 1. Check Algorithm
    method = get_algorithm(method_id)
    if not method:
        raise ValueError(f"Method '{method_id}' not found.")
    
    if method.type != "analysis":
        # Optional: warn if trying to run a preprocessing step as analysis
        pass 

    # 2. Load Data from Disk
    file_info = temp_file_store.get(file_id)
    if not file_info:
        raise ValueError(f"File {file_id} not found in storage.")

    eeg_data = EEGData.from_storage(file_info)
    eeg_data.sampling_rate = samplingRate
    
    # 3. Execute
    result_data = execute_pipeline_step(method_id, eeg_data, params)
    
    # 4. Save Updated Data to Disk
    # We update the file so the analysis results are persisted
    temp_file_store.update(file_id, result_data.df)
    
    # 5. Return the specific result for this analysis
    # Note: We return a DICT here, not the Schema Object.
    return result_data.analysis_results.get(method_id)