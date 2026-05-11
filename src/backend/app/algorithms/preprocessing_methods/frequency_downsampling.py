import pandas as pd
import numpy as np
from scipy import signal
from scipy.interpolate import interp1d
from app.schemas.domain_enum import DomainType
from app.algorithms.base import BaseStep, AlgorithmParameter, AlgorithmExample
from app.models.eeg_data import EEGData
from app.core.registry import register_algorithm


class FrequencyDownsampling(BaseStep):
    id = "frequency_downsampling"
    name = "Frequency Domain Down Sampling"
    description = (
        "Reduces frequency resolution by binning or decimating frequency bins, "
        "while preserving spectral characteristics. Different from time-domain downsampling."
    )
    category = "Resampling"
    domainType = DomainType.FREQUENCY
    type = "preprocessing"
    
    parameters = [
        AlgorithmParameter(
            name="target_resolution",
            type="number",
            value="1.0",
            default="1.0",
            min=0.1,
            max=10.0,
            required=True,
            description="Target frequency resolution in Hz"
        )
    ]

    def process(self, data: EEGData, **params) -> EEGData:
        """
        Downsample frequency domain data (PSD from FFTTransform).
        
        IMPORTANT: This is NOT time-domain downsampling. It reduces the 
        number of frequency points in PSD data.
        """
        # Get parameters
        target_resolution = float(params.get("target_resolution", 1.0))
        
        # Set defaults internally
        method = "interpolate"  
        preserve_bandwidth = True  
        
        if target_resolution <= 0:
            raise ValueError("Target resolution must be positive")
        
        df = data.df.copy()
        
        # Verify we're in frequency domain
        if "frequency_hz" not in df.columns:
            raise ValueError("Data must be in frequency domain (contain 'frequency_hz' column)")
        
        # Group by trial
        grouped = df.groupby(['subject_id', 'session_id', 'trial_id'], sort=False)
        all_downsampled = []
        
        for (subj, sess, trial), trial_df in grouped:
            if trial_df.empty:
                continue
            
            # Sort by frequency (critical!)
            trial_df = trial_df.sort_values('frequency_hz').reset_index(drop=True)
            
            # Get current frequency resolution
            current_freqs = trial_df['frequency_hz'].values
            if len(current_freqs) < 2:
                all_downsampled.append(trial_df)
                continue
            
            current_resolution = np.mean(np.diff(current_freqs))
            
            # If target resolution is coarser than current, downsample
            if target_resolution >= current_resolution * 1.01:  # 1% tolerance
                downsampled_trial = self._downsample_frequency_data(
                    trial_df, 
                    target_resolution, 
                    method,
                    preserve_bandwidth,
                    data.channel_cols
                )
                all_downsampled.append(downsampled_trial)
            else:
                # Resolution already finer than target, keep as is
                all_downsampled.append(trial_df)
        
        # Combine all trials
        if all_downsampled:
            result_df = pd.concat(all_downsampled, ignore_index=True)
        else:
            result_df = df.copy()
        
        # Update EEGData
        data.df = result_df
        data._time_data_cache = None
        data.meta["last_step"] = self.name
        data.meta["frequency_downsampling"] = {
            "original_resolution": f"{current_resolution:.3f} Hz",
            "target_resolution": f"{target_resolution:.3f} Hz",
            "method": method,  
            "preserve_bandwidth": preserve_bandwidth 
        }
        
        return data
    
    def _downsample_frequency_data(self, trial_df: pd.DataFrame, target_resolution: float, 
                                   method: str, preserve_bandwidth: bool, channel_cols: list) -> pd.DataFrame:
        """
        Downsample frequency-domain PSD data.
        """
        freqs = trial_df['frequency_hz'].values
        metadata = trial_df.iloc[0][['subject_id', 'session_id', 'trial_id']].to_dict()
        
        # Create new frequency grid
        f_min, f_max = freqs[0], freqs[-1]
        
        if preserve_bandwidth:
            # Preserve exact frequency range
            n_new = max(2, int(np.ceil((f_max - f_min) / target_resolution)))
            new_freqs = np.linspace(f_min, f_max, n_new)
        else:
            # Simple decimation-like approach
            step = max(1, int(np.round(target_resolution / np.mean(np.diff(freqs)))))
            new_freqs = freqs[::step]
        
        # Prepare result DataFrame
        result_rows = []
        
        for f_new in new_freqs:
            row = metadata.copy()
            row['frequency_hz'] = f_new
            
            # Handle each channel based on method
            for channel in channel_cols:
                if channel not in trial_df.columns:
                    continue
                    
                psd_values = trial_df[channel].values
                
                if method == "interpolate":
                    # Linear interpolation instead of cubic (more stable for PSD)
                    # Never extrapolate - clamp to frequency bounds
                    f_clamped = np.clip(f_new, f_min, f_max)
                    interp_func = interp1d(freqs, psd_values, kind='linear', 
                                          bounds_error=False, fill_value="extrapolate")
                    interpolated_value = float(interp_func(f_clamped))
                    
                    # Ensure PSD values stay within reasonable bounds
                    # PSD values should be non-negative and not explode
                    min_val = np.min(psd_values)
                    max_val = np.max(psd_values)
                    
                    # If interpolation gives extreme values, use nearest
                    if interpolated_value < min_val * 0.1 or interpolated_value > max_val * 10:
                        idx = np.argmin(np.abs(freqs - f_clamped))
                        row[channel] = float(psd_values[idx])
                    else:
                        # Clip to reasonable range and ensure non-negative
                        row[channel] = max(0, min(interpolated_value, max_val * 5))
                    
                elif method == "bin_average":
                    # Find nearest frequency bins and average
                    idx = np.searchsorted(freqs, f_new)
                    if idx == 0:
                        row[channel] = float(psd_values[0])
                    elif idx == len(freqs):
                        row[channel] = float(psd_values[-1])
                    else:
                        # Weighted average of neighboring bins
                        f_prev, f_next = freqs[idx-1], freqs[idx]
                        weight_prev = (f_next - f_new) / (f_next - f_prev)
                        weight_next = (f_new - f_prev) / (f_next - f_prev)
                        averaged = float(psd_values[idx-1] * weight_prev + 
                                       psd_values[idx] * weight_next)
                        # Ensure non-negative for PSD
                        row[channel] = max(0, averaged)
                            
                elif method == "decimate":
                    # Simple nearest neighbor
                    idx = np.argmin(np.abs(freqs - f_new))
                    row[channel] = float(psd_values[idx])
            
            # Copy other metadata columns - convert to simple types
            for col in trial_df.columns:
                if col not in ['frequency_hz', 'subject_id', 'session_id', 'trial_id'] + channel_cols:
                    if col in trial_df.columns:
                        val = trial_df.iloc[0][col]
                        # Convert complex types to simple strings to avoid memory issues
                        if isinstance(val, (list, dict, np.ndarray)):
                            row[col] = str(val)[:100]  # Truncate very long strings
                        else:
                            row[col] = val
            
            result_rows.append(row)
        
        return pd.DataFrame(result_rows)


register_algorithm(FrequencyDownsampling())