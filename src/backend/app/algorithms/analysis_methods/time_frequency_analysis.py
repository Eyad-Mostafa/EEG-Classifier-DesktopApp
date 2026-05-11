import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import signal
from io import BytesIO
import base64
from typing import Dict, List, Tuple, Any
import traceback
import math

from app.core.registry import register_algorithm
from app.algorithms.base import BaseStep, AlgorithmParameter, AlgorithmExample
from app.models.eeg_data import EEGData
from app.schemas.domain_enum import DomainType


class TimeFrequencyAnalysis(BaseStep):
    id = "time_frequency_analysis"
    name = "Time-Frequency Analysis (ERSP)"
    description = "Analyzes frequency power changes over time across all channels"
    category = "Time-Frequency Analysis"
    type = "analysis"
    domainType = DomainType.TIME
    allowedDomainTypes = [ DomainType.TIME ]

    howItWorks = """
    Computes Event-Related Spectral Perturbation (ERSP) to show frequency power changes.
    Positive values indicate synchronization (ERS), negative values indicate desynchronization (ERD).
    """

    parameters = [
        AlgorithmParameter(
            name="frequency_range",
            type="string",
            value="4-45",
            default="4-45",
            options=["1-30", "4-30", "4-45", "8-30", "8-45"],
            description="Frequency range for analysis (Hz)"
        ),
        AlgorithmParameter(
            name="baseline_period",
            type="string",
            value="-0.3-0",
            default="-0.3-0",
            description="Baseline period relative to event onset (seconds)"
        ),
        AlgorithmParameter(
            name="time_window",
            type="string",
            value="-1-2",
            default="-1-2",
            description="Time window around event (seconds)"
        ),
        AlgorithmParameter(
            name="create_synthetic_events",
            type="boolean",
            value="true",
            default="true",
            description="Create synthetic events if no real events exist"
        ),
        AlgorithmParameter(
            name="channels_per_row",
            type="integer",
            value="4",
            default="4",
            min="1",
            max="8",
            description="Number of channels to display per row in multi-channel plot"
        ),
        AlgorithmParameter(
            name="plot_type",
            type="string",
            value="all_channels",
            default="all_channels",
            options=["all_channels", "selected_channels", "topographical"],
            description="Type of visualization to generate"
        ),
        AlgorithmParameter(
            name="selected_channels",
            type="string",
            value="",
            default="",
            description="Comma-separated list of channels to plot (if plot_type is 'selected_channels')"
        )
    ]

    examples = [
        AlgorithmExample(
            title="Multi-channel ERSP Analysis",
            description="Compute ERSP on all available channels with grid layout",
            parameters={
                "frequency_range": "4-45",
                "baseline_period": "-0.3-0",
                "time_window": "-1-2",
                "create_synthetic_events": True,
                "channels_per_row": 4,
                "plot_type": "all_channels"
            }
        )
    ]
    
    def process(self, data: EEGData, **params) -> EEGData:
        try:
            # Parse parameters
            freq_range = params.get("frequency_range", "4-45")
            baseline_str = params.get("baseline_period", "-0.3-0")
            time_window_str = params.get("time_window", "-1-2")
            create_synthetic_events = params.get("create_synthetic_events", True) in [True, "true", "True", 1, "1"]
            channels_per_row = int(params.get("channels_per_row", 4))
            plot_type = params.get("plot_type", "all_channels")
            selected_channels_str = params.get("selected_channels", "")
            
            f_low, f_high = self._parse_range(freq_range)
            b_start, b_end = self._parse_range(baseline_str)
            t_start, t_end = self._parse_range(time_window_str)

            df = data.df
            channel_cols = data.channel_cols
            fs = data.sampling_rate
            
            if len(channel_cols) == 0:
                raise ValueError("No EEG channels found in data.")

            print(f"[Info] Found {len(channel_cols)} channels: {channel_cols}")
            
            # Filter channels if selected_channels is specified
            if plot_type == "selected_channels" and selected_channels_str:
                selected_channels = [ch.strip() for ch in selected_channels_str.split(',') if ch.strip()]
                # Keep only channels that exist in the data
                selected_channels = [ch for ch in selected_channels if ch in channel_cols]
                if selected_channels:
                    channel_cols = selected_channels
                    print(f"[Info] Using selected channels: {channel_cols}")
            
            # Handle events - create synthetic if needed
            if not hasattr(data, 'events') or not data.events:
                if create_synthetic_events:
                    print("[Info] Creating synthetic events for ERSP analysis")
                    data.events = self._create_synthetic_events(df, fs)
                    print(f"[Info] Created {len(data.events)} synthetic events")
                else:
                    raise ValueError("ERSP requires event markers. No events found in data.")
            
            print(f"[Info] Using {len(data.events)} events")
            
            # Compute ERSP for each channel
            all_ersp_data = {}
            all_freqs = None
            all_times = None
            
            for channel in channel_cols:
                print(f"[Info] Processing channel: {channel}")
                
                # Get epoch data for this channel
                epochs = self._extract_epochs(df[channel].values, data.events, fs, t_start, t_end)
                
                if epochs.size == 0:
                    print(f"[Warning] No valid epochs for channel {channel}")
                    continue
                
                # Compute ERSP for this channel
                ersp_data, freqs, times = self._compute_ersp(epochs, fs, f_low, f_high, b_start, b_end, t_start, t_end)
                
                if ersp_data is not None:
                    all_ersp_data[channel] = ersp_data
                    if all_freqs is None:
                        all_freqs = freqs
                    if all_times is None:
                        all_times = times
            
            if not all_ersp_data:
                raise ValueError("ERSP computation failed for all channels.")
            
            # Generate appropriate visualization based on plot_type
            if plot_type == "topographical" and len(channel_cols) > 1:
                topographic_map = self._generate_topographical_plot(all_ersp_data, all_freqs, all_times, channel_cols, params)
            else:
                # Generate multi-channel ERSP grid plot
                topographic_map = self._generate_multi_channel_ersp_plot(all_ersp_data, all_freqs, all_times, channel_cols, params)
            
            # Generate summary with statistics for all channels
            summary = self._generate_multi_channel_summary(all_ersp_data, all_freqs, all_times, params)

            result_payload = {
                "summary": summary,
                "analysis_data": {
                    "channels_analyzed": list(all_ersp_data.keys()),
                    "total_channels": len(channel_cols),
                    "events_used": len(data.events),
                    "events_type": "synthetic" if create_synthetic_events else "real",
                    "parameters": params,
                    "frequency_range": [float(f_low), float(f_high)],
                    "time_window": [float(t_start), float(t_end)]
                },
                "visualization_data": {
                    "topographic_map": topographic_map,
                    "visualization_type": "image/png"
                },
                "full_results": {
                    "ersp_data": {ch: data.tolist() for ch, data in all_ersp_data.items()},
                    "frequencies": all_freqs.tolist(),
                    "times": all_times.tolist()
                }
            }

            if not hasattr(data, 'analysis_results'):
                data.analysis_results = {}
            data.analysis_results[self.id] = result_payload

            data.meta["last_step"] = self.name
            return data

        except Exception as e:
            traceback.print_exc()
            return self._error_result(data, str(e))

    def _generate_multi_channel_ersp_plot(self, all_ersp_data: Dict[str, np.ndarray], 
                                         freqs: np.ndarray, times: np.ndarray, 
                                         channels: List[str], params: Dict) -> str:
        """Generate ERSP plots for all channels in a grid layout"""
        try:
            n_channels = len(channels)
            channels_per_row = int(params.get("channels_per_row", 4))
            n_rows = math.ceil(n_channels / channels_per_row)
            
            # Adjust figure size based on number of rows
            fig_height = max(4, 3 * n_rows)
            fig, axes = plt.subplots(n_rows, channels_per_row, 
                                    figsize=(channels_per_row * 4, fig_height),
                                    squeeze=False)
            
            # Flatten axes for easy iteration
            axes_flat = axes.flatten()
            
            # Get global color limits for consistent scaling
            all_data = np.concatenate([data for data in all_ersp_data.values()])
            vmax = max(3.0, np.max(np.abs(all_data)) * 0.8)
            vmin = -vmax
            
            # Check if synthetic events were used
            events_type = "Synthetic" if params.get("create_synthetic_events", True) in [True, "true", "True", 1, "1"] else "Real"
            
            for idx, channel in enumerate(channels):
                ax = axes_flat[idx]
                ersp_data = all_ersp_data[channel]
                
                # Plot ERSP for this channel
                im = ax.imshow(ersp_data, 
                              aspect='auto',
                              origin='lower',
                              extent=[times[0], times[-1], freqs[0], freqs[-1]],
                              cmap='RdBu_r',
                              vmin=vmin, vmax=vmax,
                              interpolation='bilinear')
                
                # Add event onset line
                ax.axvline(x=0, color='black', linestyle='--', linewidth=1.5, alpha=0.7)
                
                # Add baseline shading
                baseline_str = params.get("baseline_period", "-0.3-0")
                baseline_parts = baseline_str.split('-')
                if len(baseline_parts) >= 2:
                    try:
                        if len(baseline_parts) == 3 and baseline_parts[0] == '':
                            baseline_start = float('-' + baseline_parts[1])
                            baseline_end = float(baseline_parts[2])
                        else:
                            baseline_start = float(baseline_parts[0])
                            baseline_end = float(baseline_parts[1])
                        ax.axvspan(baseline_start, baseline_end, alpha=0.2, color='gray')
                    except:
                        pass
                
                # Set title as channel name
                ax.set_title(channel, fontsize=11, fontweight='bold', pad=3)
                
                # Set frequency scale (log)
                ax.set_yscale('log')
                
                # Set appropriate frequency ticks
                freq_ticks = []
                freq_labels = []
                for freq in [1, 2, 4, 8, 13, 20, 30, 45]:
                    if freq >= freqs[0] and freq <= freqs[-1]:
                        freq_ticks.append(freq)
                        freq_labels.append(str(freq))
                
                ax.set_yticks(freq_ticks)
                ax.set_yticklabels(freq_labels, fontsize=8)
                
                # Only show x labels on bottom row
                if idx >= n_channels - channels_per_row or n_rows == 1:
                    ax.set_xlabel('Time (s)', fontsize=9)
                else:
                    ax.set_xticklabels([])
                
                # Only show y labels on first column
                if idx % channels_per_row == 0:
                    ax.set_ylabel('Freq (Hz)', fontsize=9)
                else:
                    ax.set_yticklabels([])
                
                ax.grid(True, alpha=0.2, linestyle='--', which='both')
            
            # Hide unused subplots
            for idx in range(n_channels, len(axes_flat)):
                axes_flat[idx].axis('off')
            
            # Add a single colorbar for all subplots
            cbar_ax = fig.add_axes([0.92, 0.15, 0.02, 0.7])
            cbar = fig.colorbar(im, cax=cbar_ax)
            cbar.set_label('Power Change (dB)', fontsize=10)
            
            # Add overall title
            freq_range = params.get("frequency_range", "4-45")
            baseline = params.get("baseline_period", "-0.3-0")
            time_window = params.get("time_window", "-1-2")
            
            plt.suptitle(f'Multi-Channel ERSP Analysis ({events_type} Events)\n'
                        f'Frequency: {freq_range} Hz | Baseline: {baseline} s | Window: {time_window} s',
                        fontsize=14, fontweight='bold', y=0.98)
            
            plt.tight_layout(rect=[0, 0, 0.9, 0.96])  # Adjust layout for colorbar and title
            return self._fig_to_base64(fig)
            
        except Exception as e:
            print(f"Multi-channel plot error: {e}")
            traceback.print_exc()
            return self._fallback_plot()

    def _generate_topographical_plot(self, all_ersp_data: Dict[str, np.ndarray],
                                   freqs: np.ndarray, times: np.ndarray,
                                   channels: List[str], params: Dict) -> str:
        """Generate a summary topographical plot showing maximum power changes"""
        try:
            # Calculate time-frequency points of interest
            n_time_points = len(times)
            post_event_idx = np.where(times >= 0)[0][0] if np.any(times >= 0) else 0
            
            # Create subplots for different frequency bands
            bands = {
                'Theta (4-8 Hz)': (4, 8),
                'Alpha (8-13 Hz)': (8, 13),
                'Beta (13-30 Hz)': (13, 30),
                'Gamma (30-45 Hz)': (30, 45)
            }
            
            fig, axes = plt.subplots(2, 2, figsize=(12, 10))
            axes = axes.flatten()
            
            for idx, (band_name, (f_low, f_high)) in enumerate(bands.items()):
                if idx >= len(axes):
                    break
                    
                ax = axes[idx]
                
                # Get frequency indices for this band
                freq_mask = (freqs >= f_low) & (freqs <= f_high)
                if not np.any(freq_mask):
                    continue
                
                # Calculate average power in post-event period for each channel
                channel_powers = []
                channel_names = []
                
                for channel in channels:
                    if channel in all_ersp_data:
                        ersp_data = all_ersp_data[channel]
                        # Average across frequencies and post-event time
                        band_data = ersp_data[freq_mask, post_event_idx:]
                        if band_data.size > 0:
                            avg_power = np.mean(band_data)
                            channel_powers.append(avg_power)
                            channel_names.append(channel)
                
                if channel_powers:
                    # Create a simple topographic representation
                    # For now, just show a bar chart with channel powers
                    y_pos = np.arange(len(channel_names))
                    
                    # Color bars based on power value
                    colors = ['red' if p < 0 else 'blue' for p in channel_powers]
                    
                    bars = ax.barh(y_pos, channel_powers, color=colors, alpha=0.7)
                    ax.set_yticks(y_pos)
                    ax.set_yticklabels(channel_names, fontsize=9)
                    ax.set_xlabel('Avg Power Change (dB)', fontsize=10)
                    ax.set_title(f'{band_name} Band', fontsize=11, fontweight='bold')
                    
                    # Add zero line
                    ax.axvline(x=0, color='black', linestyle='-', linewidth=0.5, alpha=0.5)
                    
                    # Add value labels on bars
                    for bar in bars:
                        width = bar.get_width()
                        ha = 'left' if width >= 0 else 'right'
                        offset = 0.01 if width >= 0 else -0.01
                        ax.text(width + offset, bar.get_y() + bar.get_height()/2,
                               f'{width:.2f}', va='center', ha=ha, fontsize=8)
                
                ax.grid(True, alpha=0.2, axis='x')
            
            # Hide unused subplots
            for idx in range(len(bands), len(axes)):
                axes[idx].axis('off')
            
            # Add overall title
            events_type = "Synthetic" if params.get("create_synthetic_events", True) in [True, "true", "True", 1, "1"] else "Real"
            plt.suptitle(f'Topographical ERSP Summary - Post-Event Average Power\n'
                        f'{events_type} Events | {len(channels)} Channels',
                        fontsize=14, fontweight='bold', y=0.98)
            
            plt.tight_layout(rect=[0, 0, 1, 0.96])
            return self._fig_to_base64(fig)
            
        except Exception as e:
            print(f"Topographical plot error: {e}")
            # Fall back to multi-channel plot
            return self._generate_multi_channel_ersp_plot(all_ersp_data, freqs, times, channels, params)

    def _generate_multi_channel_summary(self, all_ersp_data: Dict[str, np.ndarray],
                                       freqs: np.ndarray, times: np.ndarray,
                                       params: Dict) -> Dict:
        """Generate summary statistics for all channels"""
        try:
            channel_summaries = {}
            
            for channel, ersp_data in all_ersp_data.items():
                # Calculate statistics for this channel
                max_power = np.max(ersp_data)
                min_power = np.min(ersp_data)
                mean_power = np.mean(ersp_data)
                
                # Find time and frequency of maximum absolute power change
                max_idx = np.unravel_index(np.argmax(np.abs(ersp_data)), ersp_data.shape)
                max_time = times[max_idx[1]]
                max_freq = freqs[max_idx[0]]
                max_power_value = ersp_data[max_idx]
                
                # Calculate band-specific statistics
                bands = {
                    "theta": (4, 8),
                    "alpha": (8, 13),
                    "beta": (13, 30),
                    "gamma": (30, 45)
                }
                
                band_stats = {}
                for band_name, (f_low, f_high) in bands.items():
                    freq_mask = (freqs >= f_low) & (freqs <= f_high)
                    if np.any(freq_mask):
                        band_data = ersp_data[freq_mask, :]
                        band_stats[band_name] = {
                            "mean_power": float(np.mean(band_data)),
                            "max_power": float(np.max(band_data)),
                            "min_power": float(np.min(band_data)),
                            "ers_percentage": float(np.mean(band_data > 1.0) * 100),
                            "erd_percentage": float(np.mean(band_data < -1.0) * 100)
                        }
                
                channel_summaries[channel] = {
                    "max_power_change": float(max_power),
                    "min_power_change": float(min_power),
                    "mean_power_change": float(mean_power),
                    "peak_time": float(max_time),
                    "peak_frequency": float(max_freq),
                    "peak_power": float(max_power_value),
                    "band_statistics": band_stats
                }
            
            # Calculate overall statistics across all channels
            all_data = np.concatenate([data for data in all_ersp_data.values()])
            overall_max = np.max(all_data)
            overall_min = np.min(all_data)
            overall_mean = np.mean(all_data)
            
            # Find channel with strongest response
            channel_max_values = {ch: np.max(np.abs(data)) for ch, data in all_ersp_data.items()}
            strongest_channel = max(channel_max_values, key=channel_max_values.get)
            strongest_value = channel_max_values[strongest_channel]
            
            # Check if synthetic events were used
            events_type = "synthetic" if params.get("create_synthetic_events", True) in [True, "true", "True", 1, "1"] else "real"
            
            return {
                "executive_summary": {
                    "total_channels_analyzed": len(all_ersp_data),
                    "overall_max_power_change": float(overall_max),
                    "overall_min_power_change": float(overall_min),
                    "overall_mean_power_change": float(overall_mean),
                    "strongest_response_channel": strongest_channel,
                    "strongest_response_value": float(strongest_value),
                    "frequency_range": params.get("frequency_range"),
                    "baseline": params.get("baseline_period"),
                    "time_window": params.get("time_window"),
                    "events_type": events_type,
                    "analysis_type": "Multi-Channel Event-Related Spectral Perturbation (ERSP)"
                },
                "channel_summaries": channel_summaries,
                "interpretation": {
                    "ers": "Event-Related Synchronization (> 1 dB) - Increased cortical synchronization",
                    "erd": "Event-Related Desynchronization (< -1 dB) - Decreased cortical synchronization",
                    "neutral": "No significant change (-1 dB to 1 dB) - Baseline-like activity"
                }
            }
        except Exception as e:
            print(f"Multi-channel summary generation error: {e}")
            return {
                "executive_summary": {
                    "error": f"Could not generate summary: {str(e)}",
                    "analysis_type": "Multi-Channel Event-Related Spectral Perturbation (ERSP)"
                }
            }

    # Existing helper methods remain the same (slightly modified for multi-channel support)
    def _create_synthetic_events(self, df: pd.DataFrame, fs: float) -> List[int]:
        """Create synthetic events for ERSP analysis if no real events exist"""
        try:
            # Create events every 2 seconds
            event_interval = int(2 * fs)  # 2 seconds between events
            total_samples = len(df)
            
            # Start after 1 second to avoid beginning artifacts
            start_sample = int(1 * fs)
            # End 1 second before the end
            end_sample = total_samples - int(1 * fs)
            
            events = list(range(start_sample, end_sample, event_interval))
            
            # Ensure we have at least 3 events
            if len(events) < 3:
                # If data is too short, create 3 evenly spaced events
                events = np.linspace(start_sample, end_sample, 3, dtype=int).tolist()
            
            print(f"[Info] Created {len(events)} synthetic events at samples: {events[:5]}...")
            return events
        except Exception as e:
            print(f"[Warning] Failed to create synthetic events: {e}")
            # Fallback: create 5 evenly spaced events
            total_samples = len(df)
            return np.linspace(int(0.5 * fs), total_samples - int(0.5 * fs), 5, dtype=int).tolist()

    def _extract_epochs(self, data: np.ndarray, events: List[int], 
                       fs: float, t_start: float, t_end: float) -> np.ndarray:
        """Extract epochs around event markers"""
        try:
            n_samples_pre = int(abs(t_start) * fs)  # Pre-stimulus samples
            n_samples_post = int(abs(t_end) * fs)   # Post-stimulus samples
            
            # Total epoch length
            epoch_len = n_samples_pre + n_samples_post
            
            epochs = []
            for event_sample in events:
                start_idx = event_sample - n_samples_pre
                end_idx = event_sample + n_samples_post
                
                if start_idx >= 0 and end_idx <= len(data):
                    epoch = data[start_idx:end_idx]
                    if len(epoch) == epoch_len:
                        epochs.append(epoch)
            
            if epochs:
                print(f"[Info] Extracted {len(epochs)} epochs of length {epoch_len} samples")
                return np.array(epochs)
            else:
                print("[Warning] No valid epochs extracted")
                return np.array([])
        except Exception as e:
            print(f"Epoch extraction error: {e}")
            traceback.print_exc()
            return np.array([])

    def _compute_ersp(self, epochs: np.ndarray, fs: float, 
                     f_low: float, f_high: float,
                     b_start: float, b_end: float,
                     t_start: float, t_end: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Compute proper ERSP using Morlet wavelet convolution"""
        try:
            n_epochs, n_samples = epochs.shape
            
            # Create time array for the full epoch
            times = np.linspace(t_start, t_end, n_samples)
            
            # Define frequencies for analysis (logarithmic spacing for better visualization)
            n_freqs = 40
            freqs = np.logspace(np.log10(max(1, f_low)), np.log10(f_high), n_freqs)
            
            # Initialize ERSP array
            ersp_all = np.zeros((len(freqs), n_samples))
            
            for freq_idx, freq in enumerate(freqs):
                # Morlet wavelet with 6 cycles
                n_cycles = 6
                sigma = n_cycles / (2 * np.pi * freq)
                
                # Time vector for wavelet
                wavelet_length = int(6 * sigma * fs)
                t_wavelet = np.arange(-wavelet_length, wavelet_length + 1) / fs
                
                # Create complex Morlet wavelet
                wavelet = np.exp(2j * np.pi * freq * t_wavelet)
                wavelet *= np.exp(-t_wavelet**2 / (2 * sigma**2))
                wavelet = wavelet / np.sqrt(np.sum(np.abs(wavelet)**2))  # Normalize
                
                epoch_power_sum = np.zeros(n_samples)
                
                for epoch_idx in range(n_epochs):
                    # Convolve each epoch with wavelet
                    conv = np.convolve(epochs[epoch_idx], wavelet, mode='same')
                    power = np.abs(conv) ** 2
                    epoch_power_sum += power
                
                # Average across epochs
                ersp_all[freq_idx, :] = epoch_power_sum / n_epochs
            
            # Baseline normalization using ONLY baseline period
            baseline_mask = (times >= b_start) & (times <= b_end)
            if np.any(baseline_mask) and np.sum(baseline_mask) > 1:
                # Get baseline mean for each frequency
                baseline_mean = np.mean(ersp_all[:, baseline_mask], axis=1, keepdims=True)
                # Avoid division by zero
                baseline_mean = np.where(baseline_mean <= 0, 1e-10, baseline_mean)
                # Convert to dB relative to baseline
                ersp_db = 10 * np.log10(ersp_all / baseline_mean)
                print(f"[Info] Baseline normalization complete: {ersp_db.shape}")
            else:
                print(f"[Warning] Invalid baseline mask: {np.sum(baseline_mask)} points")
                ersp_db = np.zeros_like(ersp_all)
            
            return ersp_db, freqs, times
            
        except Exception as e:
            print(f"ERSP computation error: {e}")
            traceback.print_exc()
            return None, None, None

    def _parse_range(self, range_str: str) -> Tuple[float, float]:
        try:
            parts = range_str.split('-')
            if len(parts) == 2:
                return float(parts[0]), float(parts[1])
            elif len(parts) == 3 and parts[0] == '':
                return float('-' + parts[1]), float(parts[2])
            else:
                # Default fallbacks based on parameter type
                if 'time' in range_str or 'window' in range_str:
                    return -1.0, 2.0
                elif 'baseline' in range_str:
                    return -0.3, 0.0
                else:
                    return 4.0, 45.0
        except:
            # Default fallbacks based on parameter type
            if 'time' in range_str or 'window' in range_str:
                return -1.0, 2.0
            elif 'baseline' in range_str:
                return -0.3, 0.0
            else:
                return 4.0, 45.0

    def _fig_to_base64(self, fig) -> str:
        buffer = BytesIO()
        fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        buffer.seek(0)
        img_str = base64.b64encode(buffer.read()).decode('utf-8')
        buffer.close()
        plt.close(fig)
        return f"data:image/png;base64,{img_str}"

    def _fallback_plot(self) -> str:
        fig, ax = plt.subplots(figsize=(8, 6), facecolor='white')
        ax.text(0.5, 0.5, 'ERSP Analysis\nNo valid data for visualization',
                ha='center', va='center', fontsize=14, transform=ax.transAxes,
                bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.7))
        ax.axis('off')
        return self._fig_to_base64(fig)

    def _error_result(self, data: EEGData, error_msg: str) -> EEGData:
        if not hasattr(data, 'analysis_results'):
            data.analysis_results = {}
        data.analysis_results[self.id] = {
            "summary": {"error": f"ERSP analysis failed: {error_msg}"},
            "analysis_data": None,
            "visualization_data": {
                "topographic_map": self._fallback_plot(),
                "visualization_type": "image/png"
            },
            "full_results": None
        }
        return data


# Register the algorithm
register_algorithm(TimeFrequencyAnalysis())