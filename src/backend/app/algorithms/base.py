"""
Abstract base class for all processing steps.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Literal
from app.schemas.domain_enum import DomainType
from app.models.eeg_data import EEGData

class ParameterValidationError(ValueError):
    """Custom exception for parameter validation errors"""
    def __init__(self, parameter_name: str, value: any, constraints: dict, message: str = None):
        self.parameter_name = parameter_name
        self.value = value
        self.constraints = constraints
        self.message = message or self._generate_message()
        super().__init__(self.message)
    
    def _generate_message(self) -> str:
        return f"Invalid value '{self.value}' for parameter '{self.parameter_name}'."

class AlgorithmParameter:
    # Updated to include description
    def __init__(
            self, 
            name: str,
            type: Literal['string', 'number', 'boolean', 'array'],
            value: str = None,
            default: Optional[str] = None,
            min: Optional[float] = None,
            max: Optional[float] = None,
            options: Optional[List[str]] = None,
            required: bool = False,
            description: str = "" 
    ):
        self.name = name
        self.type = type
        self.value = value
        self.default = default
        self.min = min 
        self.max = max
        self.options = options
        self.required = required
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "value": self.value,
            "default": self.default,
            "min": self.min,
            "max": self.max,
            "options": self.options,
            "required": self.required,
            "description": self.description # <--- ADDED THIS
        }

class AlgorithmExample:
    def __init__(self, title: str, description: str, parameters: Dict[str, Any] = None):
        self.title = title
        self.description = description
        self.parameters = parameters or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "parameters": self.parameters
        }

class BaseStep(ABC):
    id: str
    name: str
    category: str
    domainType: DomainType
    allowedDomainTypes: List[DomainType] = []
    description: str
    type: str = "preprocessing"
    howItWorks: str = ""
    useCases: List[str] = []
    relatedAlgorithms: List[str] = []
    examples: List[AlgorithmExample] = []
    parameters: List[AlgorithmParameter] = []
    is_hidden: bool = False

    def validate_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        validated_params = {}
        
        for param_def in self.parameters:
            param_name = param_def.name
            param_type = param_def.type
            # Use default if param missing
            param_value = params.get(param_name, param_def.default)
            
            # Handle the '0' string vs 0 integer issue automatically
            if param_type == 'string' and param_def.options:
                if str(param_value) not in param_def.options:
                    # Try mapping index to value (0 -> 'select')
                    if str(param_value).isdigit():
                        idx = int(param_value)
                        if 0 <= idx < len(param_def.options):
                            param_value = param_def.options[idx]

            # Type Casting Logic
            if param_type == 'number':
                try:
                    param_value = float(param_value)
                except:
                    pass # Let validation logic handle it later
            elif param_type == 'boolean':
                if isinstance(param_value, str):
                    param_value = param_value.lower() in ['true', '1', 'yes']

            validated_params[param_name] = param_value
        
        return validated_params    

    @abstractmethod
    def process(self, data: EEGData, **params) -> EEGData:
        raise NotImplementedError("Subclass must implement process()")

    def get_info(self, detailed: bool = False) -> Dict[str, Any]:
        info = {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "domainType": self.domainType.value if hasattr(self.domainType, 'value') else str(self.domainType),
            "allowedDomainTypes": [dt.value if hasattr(dt, 'value') else str(dt) for dt in self.allowedDomainTypes],
            "description": self.description,
            "type": self.type,
            "parameters": [p.to_dict() for p in self.parameters]
        }
        if detailed:
            info.update({
                "howItWorks": self.howItWorks,
                "useCases": self.useCases,
                "relatedAlgorithms": self.relatedAlgorithms,
                "examples": [ex.to_dict() for ex in self.examples],
            })
        return info