import io
import base64
from typing import List
from fastapi import HTTPException
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from scipy.signal import spectrogram
from app.models.eeg_data import EEGData
from app.services.temp_file_store_service import temp_file_store
from app.schemas.visualization_schema import EEGSessionData, EEGSubjectData, EEGTrialData, VisualizationRequest, VisualizationResponse


# Set a clean, professional style at the top of the file
plt.style.use('default')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
plt.rcParams['axes.facecolor'] = '#f5f5f5'
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['grid.color'] = '#dddddd'
plt.rcParams['grid.linestyle'] = '-'
plt.rcParams['grid.alpha'] = 0.3

def generate_eeg_base64(df: pd.DataFrame, max_samples: int = 1000, title: str = "EEG Signals") -> str:
    """
    Generates a clean stacked EEG plot and returns it as a base64 string.
    """
    try:
        channel_cols = [c for c in df.columns if c.startswith("channel_")]
        num_channels = len(channel_cols)
        data_len = min(max_samples, len(df))
        
        # Create time axis
        if 'time' in df.columns:
            time_axis = df['time'].values[:data_len]
        else:
            time_axis = np.arange(data_len)

        # Calculate figure size
        fig_width = max(12, num_channels * 0.5)
        fig_height = max(6, num_channels * 0.3)
        
        fig, ax = plt.subplots(1, 1, figsize=(fig_width, fig_height))

        # Calculate offsets
        offset = 0
        colors = plt.cm.Set1(np.linspace(0, 1, num_channels))

        for i, ch in enumerate(channel_cols):
            data = df[ch].values[:data_len]
            # Center the data
            data = data - np.mean(data)
            rng = np.max(data) - np.min(data)
            
            # Plot with clean lines
            ax.plot(time_axis, data + offset, 
                   color=colors[i], 
                   linewidth=1.2,
                   label=ch.replace('channel_', 'CH '))
            
            # Add channel label
            ax.text(time_axis[-1] + (time_axis[-1]-time_axis[0])*0.01, 
                   offset, 
                   ch.replace('channel_', 'CH '),
                   fontsize=8,
                   verticalalignment='center')
            
            offset += rng * 1.3

        # Clean styling
        ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
        ax.set_xlabel('Time (s)' if 'time' in df.columns else 'Samples', fontsize=11)
        ax.set_ylabel('Amplitude (μV)', fontsize=11)
        ax.grid(True, alpha=0.3)
        ax.set_yticks([])  # Hide y-axis ticks for stacked view
        ax.set_xlim(time_axis[0], time_axis[-1] * 1.05)
        
        plt.tight_layout()

        # Save
        img_buffer = io.BytesIO()
        fig.savefig(img_buffer, format="png", dpi=120, bbox_inches="tight")
        img_buffer.seek(0)
        base64_data = base64.b64encode(img_buffer.getvalue()).decode("utf-8")
        plt.close(fig)
        return base64_data

    except Exception as e:
        print(f"Error generating figure: {e}")
        return None
    
def generate_combined_spectrogram(df: pd.DataFrame, sampling_rate: float) -> str:
    """
    Generates a single spectrogram image combining all EEG channels.
    Returns the base64 string of the image.
    """
    channel_cols = [c for c in df.columns if c.startswith("channel_")]
    fig, axs = plt.subplots(len(channel_cols), 1, figsize=(50, 2*len(channel_cols)), sharex=True)

    if len(channel_cols) == 1:
        axs = [axs]  # ensure axs is iterable

    for i, ch in enumerate(channel_cols):
        f, t, Sxx = spectrogram(df[ch].values, fs=sampling_rate, nperseg=256)
        axs[i].pcolormesh(t, f, 10*np.log10(Sxx+1e-12), shading='gouraud')
        axs[i].set_ylabel(f"{ch} [Hz]")
    
    axs[-1].set_xlabel("Time [s]")
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    plt.close(fig)

    return img_base64

def generate_visualization(request: VisualizationRequest) -> VisualizationResponse:
    raw_info = temp_file_store.get(request.rawDataId)
    if not raw_info:
        raise HTTPException(status_code=404, detail=f"Raw file ID {request.rawDataId} not found")

    clean_info = None
    if not request.rawDataOnly and request.cleanDataId:
        clean_info = temp_file_store.get(request.cleanDataId)
        if not clean_info:
            raise HTTPException(status_code=404, detail=f"Clean file ID {request.cleanDataId} not found")

    try:
        raw_data = EEGData.from_storage(raw_info)
        raw_data.sampling_rate = request.samplingRate
        clean_data = EEGData.from_storage(clean_info) if clean_info else None
        if clean_data:
            clean_data.sampling_rate = request.samplingRate
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading CSV files: {e}")

    def build_subjects_map(eeg_data: EEGData) -> List[EEGSubjectData]:
        fs = eeg_data.sampling_rate
        df = eeg_data.df

        has_labels   = 'labels'   in df.columns
        has_category = 'category' in df.columns

        # Build groupby key dynamically — avoids KeyError if a column is missing
        GROUP_COLS = ["subject_id", "session_id", "trial_id"]
        if has_labels:
            GROUP_COLS.append("labels")
        if has_category:
            GROUP_COLS.append("category")

        subjects_map = {}

        for keys, trial_df in df.groupby(GROUP_COLS):
            # Unpack keys positionally to match GROUP_COLS order
            keys = keys if isinstance(keys, tuple) else (keys,)
            key_dict = dict(zip(GROUP_COLS, keys))

            subject_id = key_dict["subject_id"]
            session_id = key_dict["session_id"]
            trial_id   = key_dict["trial_id"]
            label      = str(key_dict["labels"])   if has_labels   else ""
            category   = key_dict["category"]      if has_category else ""

            N    = len(trial_df)
            time = [i / fs for i in range(N)]
            channels = {col: trial_df[col].tolist() for col in eeg_data.channel_cols}

            trial_obj = EEGTrialData(
                trialId=str(trial_id),
                category=category,
                label=label,
                time=time,
                channels=channels
            )

            subjects_map.setdefault(subject_id, {})
            subjects_map[subject_id].setdefault(session_id, [])
            subjects_map[subject_id][session_id].append(trial_obj)

        result: List[EEGSubjectData] = []
        for subject_id, sessions_dict in subjects_map.items():
            sessions = [
                EEGSessionData(sessionId=str(sid), trials=trials)
                for sid, trials in sessions_dict.items()
            ]
            result.append(EEGSubjectData(subjectId=str(subject_id), sessions=sessions))

        return result

    raw_subjects   = build_subjects_map(raw_data)
    clean_subjects = build_subjects_map(clean_data) if clean_data else None

    return VisualizationResponse(raw=raw_subjects, clean=clean_subjects)