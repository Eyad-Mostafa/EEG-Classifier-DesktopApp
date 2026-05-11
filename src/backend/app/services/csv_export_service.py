import os
import csv
import uuid
from typing import List, Dict, Optional
from datetime import datetime

# Reuse the same temp directory as the main temp_file_store
from app.services.temp_file_store_service import temp_file_store

# In-memory store: maps result_id to a dict with file path and filename
_csv_store: Dict[str, Dict[str, str]] = {}


def generate_csv_from_predictions(
    predictions: List[Dict], model_id: str = "Unknown"
) -> str:
    """
    Takes the list of prediction dictionaries, generates a CSV file inside
    the same temp directory used by the rest of the app, and returns a unique result_id.
    """
    temp_dir = temp_file_store.temp_dir

    result_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_model_id = "".join(c if c.isalnum() else "_" for c in model_id)
    filename = f"predictions_{safe_model_id}_{timestamp}.csv"
    file_path = os.path.join(temp_dir, filename)

    base_fields = ["subject", "session", "trial", "predictedClass", "confidence"]
    optional_fields = ["trueClass", "correct"]

    # add optional fields only if at least one row has a real value for them
    fieldnames = base_fields.copy()
    for field in optional_fields:
        if any(pred.get(field) not in (None, "", []) for pred in predictions):
            fieldnames.append(field)

    with open(file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for pred in predictions:
            row = {k: pred.get(k, "") for k in fieldnames}
            writer.writerow(row)

    _csv_store[result_id] = {"file_path": file_path, "filename": filename}
    return result_id


def get_csv_info(result_id: str) -> Optional[Dict[str, str]]:
    """
    Returns the dict containing file_path and filename if it exists, else None.
    """
    info = _csv_store.get(result_id)
    if info and os.path.exists(info["file_path"]):
        return info
    return None
