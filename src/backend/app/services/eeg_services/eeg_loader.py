import pandas as pd
import io
from typing import Union
from app.models.eeg_data import EEGData


class EEGDataLoader:
    """
    Responsible for loading EEG data from various sources into a pandas DataFrame.
    Sources supported:
        - bytes / bytearray (CSV content)
        - file-like objects (UploadFile, SpooledTemporaryFile)
        - file path (str)
        - pandas DataFrame
        - EEGData instance
    """

    @staticmethod
    def load_data(source: Union[str, bytes, bytearray, pd.DataFrame, EEGData, io.IOBase]) -> pd.DataFrame:
        """Internal helper to parse different input types into a DataFrame."""
        
        dtype_options = {
            'subject_id': str, 
            'session_id': str, 
            'trial_id': str
        }

        # 1. Binary Data (bytes)
        if isinstance(source, (bytes, bytearray)):
            return pd.read_csv(io.BytesIO(source), dtype=dtype_options)
        
        # 2. File Path (string)
        elif isinstance(source, str):
            return pd.read_csv(source, engine='c', low_memory=False, dtype=dtype_options)
        
        # 3. Existing DataFrame
        elif isinstance(source, pd.DataFrame):
            return source.copy()
        
        # 4. Existing EEGData Object
        elif isinstance(source, EEGData):
            return source.df.copy()
            
        # 5. File-like Objects (FastAPI UploadFile.file)
        # We check if it has a 'read' method. This covers SpooledTemporaryFile.
        elif hasattr(source, "read"):
            # Ensure we are at the start of the file
            if hasattr(source, "seek"):
                source.seek(0)
            return pd.read_csv(source, engine='c', low_memory=False, dtype=dtype_options)
        
        else:
            raise ValueError(f"Unsupported file_source type: {type(source)}")
