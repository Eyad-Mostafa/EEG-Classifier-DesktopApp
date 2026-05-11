from typing import Any, Dict

from typing import Any, Dict
def build_analysis_service_response(method_id: str, analysis_result: Any) -> Dict:
    """
    Normalize analysis_result into a dict matching AnalysisResponse fields.
    """
    payload = {}
    if isinstance(analysis_result, dict):
        payload = analysis_result
    else:
        payload = {"analysis_data": analysis_result}  # Updated key

    # Use the keys directly from payload
    summary = payload.get("summary", {})
    analysis_data = payload.get("analysis_data", payload.get("data", None))  # Handle both
    visualization_data = payload.get("visualization_data", payload.get("visualization", None))

    return {
        "method_id": method_id,
        "success": True,
        "result": {
            "summary": summary,
            "analysis_data": analysis_data,  
            "visualization_data": visualization_data
        }
    }