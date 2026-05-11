import importlib
import os
from typing import Dict, List, Optional
from app.algorithms.base import BaseStep

_ALGORITHMS: Dict[str, BaseStep] = {}

def register_algorithm(step_instance: BaseStep):
    if not isinstance(step_instance, BaseStep):
        raise TypeError(f"Cannot register {type(step_instance)}. Must inherit from BaseStep.")
    
    if step_instance.id in _ALGORITHMS:
        print(f"Warning: Overwriting algorithm '{step_instance.id}'")
        
    _ALGORITHMS[step_instance.id] = step_instance
    print(f"Registered algorithm: {step_instance.id} ({step_instance.type})")

def get_algorithm(method_id: str) -> Optional[BaseStep]:
    return _ALGORITHMS.get(method_id)

def get_all_algorithms(detailed: bool = False) -> List[Dict]:
    return [step.get_info(detailed=detailed) for step in _ALGORITHMS.values() if not step.is_hidden]

def auto_import_algorithms():
    """
    Recursively imports all python files in 'app/algorithms' 
    to trigger the register_algorithm() calls.
    """
    current_dir = os.path.dirname(__file__) # app/core
    
    # ▼▼▼ FIX 1: Point to 'algorithms' folder ▼▼▼
    steps_dir = os.path.abspath(os.path.join(current_dir, "..", "algorithms")) 
    base_package = "app.algorithms"
    # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

    if not os.path.exists(steps_dir):
        print(f"[ERROR] Algorithms directory not found: {steps_dir}")
        return

    for root, _, files in os.walk(steps_dir):
        for filename in files:
            if filename.endswith(".py") and filename not in ["__init__.py", "base.py"]:
                relative_path = os.path.relpath(root, steps_dir)
                
                if relative_path == ".":
                    module_name = f"{base_package}.{filename[:-3]}"
                else:
                    package_path = relative_path.replace(os.path.sep, ".")
                    module_name = f"{base_package}.{package_path}.{filename[:-3]}"

                try:
                    importlib.import_module(module_name)
                except Exception as e:
                    print(f"[ERROR] Failed to import {module_name}: {e}")

# Run on startup
auto_import_algorithms()