import os
import sys
import json
from glob import glob
from app.core.registry import get_algorithm

def get_base_path():
    """
    Dynamically finds the correct root path.
    Works in standard Python AND inside the PyInstaller compiled .exe
    """
    if getattr(sys, 'frozen', False):
        # We are running as a compiled PyInstaller executable
        return sys._MEIPASS
    
    # We are running from normal Python source code
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(current_dir, "..", ".."))

def get_models_dir():
    """Universally resolves to the pretrained_models folder."""
    return os.path.join(get_base_path(), "app", "pretrained_models")

def get_available_models():
    models = []
    models_dir = get_models_dir()
    
    # Prevent crashing if the folder doesn't exist yet
    if not os.path.exists(models_dir):
        return models

    for json_path in glob(os.path.join(models_dir, "*.json")):
        with open(json_path, 'r', encoding='utf-8') as f:
            model_data = json.load(f)
            
            pipeline = model_data.get("preprocessing_pipeline", [])
            names = []
            
            for step in pipeline:
                algo = get_algorithm(step.get("id"))
                if algo:
                    names.append(algo.name)
                else:
                    names.append(step.get("id")) 
                    
            model_data["preprocessing_names"] = names
            models.append(model_data)
            
    return models

def get_model_pth_path(model_id: str) -> str:
    """Used by inference endpoint to find the .pth file."""
    models_dir = get_models_dir()
    
    if not os.path.exists(models_dir):
        return None

    for filename in os.listdir(models_dir):
        if filename.endswith(".json"):
            with open(os.path.join(models_dir, filename), 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get("id") == model_id:
                    pth_filename = data.get("files", {}).get("pth")
                    if pth_filename:
                        return os.path.join(models_dir, pth_filename)
    return None

def get_model_metadata(model_id: str) -> dict:
    """Fetches the full JSON metadata dictionary for a specific model."""
    models_dir = get_models_dir()
    
    if not os.path.exists(models_dir):
        return None

    for filename in os.listdir(models_dir):
        if filename.endswith(".json"):
            with open(os.path.join(models_dir, filename), 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get("id") == model_id:
                    return data
    return None