import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import signal
from io import BytesIO
import base64
from typing import Dict
import traceback
from app.core.registry import register_algorithm
from app.algorithms.base import BaseStep, AlgorithmParameter, AlgorithmExample
from app.models.eeg_data import EEGData
from app.schemas.domain_enum import DomainType

class SpectralAnalysis(BaseStep):
    id = "spectral_analysis"
    name = "Spectral Analysis"
    description = "Analyzes EEG frequency bands and power spectral density"
    category = "Frequency Analysis"
    type = "analysis"
    domainType = DomainType.TIME
    allowedDomainTypes = [ DomainType.TIME, DomainType.FREQUENCY, DomainType.TIME_FREQUENCY ]

    howItWorks = "Computes power spectral density using FFT and Welch's method to analyze brain wave frequencies"
    useCases = [
        "Identify dominant frequency bands",
        "Compare power across different frequency ranges", 
        "Detect abnormal brain wave patterns"
    ]
    relatedAlgorithms = ["differential_entropy", "fft_transform"]
    
    parameters = [
        AlgorithmParameter(
            name="window_size",
            type="number",
            default="2",
            min=1,
            max=10,
            description="Window size for spectral analysis in seconds"
        )
    ]
    
    examples = [
        AlgorithmExample(
            title="Standard Frequency Band Analysis",
            description="Analyze delta, theta, alpha, beta, and gamma bands",
            parameters={"window_size": 2}
        )
    ]
    
    def process(self, data: EEGData, **params) -> EEGData:
        """
        Run spectral analysis and attach results - with 3-domain support.
        """
        try:
            print(f"[Info] Starting Spectral Analysis with {len(data.channel_cols)} channels")
            
            # Validate parameters
            validated_params = self.validate_parameters(params)
            
            df = data.channels_only
            channel_cols = data.channel_cols
            sampling_rate = data.sampling_rate
            
            # DOMAIN-SPECIFIC PROCESSING
            current_domain = getattr(data, 'domain', DomainType.TIME)
            
            print(f"[Info] Processing spectral analysis in {current_domain.value} domain")
            
            # Define frequency bands
            freq_bands = self._get_frequency_bands()
            
            # Analyze each channel with domain adaptation
            spectral_results = {}
            for channel in channel_cols:
                channel_data = df[channel].dropna().values
                if len(channel_data) > 10:
                    if current_domain == DomainType.FREQUENCY:
                        # Data is already in frequency domain
                        spectral_results[channel] = self._analyze_channel_spectrum_frequency_domain(
                            channel_data, sampling_rate, freq_bands
                        )
                    elif current_domain == DomainType.TIME_FREQUENCY:
                        # Data is in time-frequency domain
                        spectral_results[channel] = self._analyze_channel_spectrum_time_frequency_domain(
                            channel_data, sampling_rate, freq_bands
                        )
                    else:
                        # Time domain data (default)
                        spectral_results[channel] = self._analyze_channel_spectrum(
                            channel_data, sampling_rate, freq_bands
                        )
                else:
                    print(f"[Warning] Skipping channel {channel}: insufficient data")
            
            if not spectral_results:
                result_payload = {
                    "summary": {"error": "No channels with sufficient data for spectral analysis"},
                    "analysis_data": None,
                    "visualization_data": None
                }
            else:
                # Generate visualization
                topographic_map = self._plot_power_spectrum_comparison(spectral_results)
                
                # Construct payload with domain information
                result_payload = {
                    "summary": self._generate_spectral_summary(spectral_results, freq_bands, current_domain),
                    "analysis_data": {
                        "spectral_results": spectral_results,
                        "frequency_bands": freq_bands,
                        "processing_domain": current_domain.value  # 🔧 NEW: Track which domain was used
                    },
                    "visualization_data": {
                        "topographic_map": topographic_map,
                        "visualization_type": "image/png"
                    }
                }
            
            # Attach result to data object
            if not hasattr(data, 'analysis_results'):
                data.analysis_results = {}
            
            data.analysis_results[self.id] = result_payload
            
            return data
            
        except Exception as e:
            print(f"[Error] ERROR in Spectral Analysis: {str(e)}")
            traceback.print_exc()
            
            # Attach error result to data object
            if not hasattr(data, 'analysis_results'):
                data.analysis_results = {}
                
            data.analysis_results[self.id] = {
                "summary": {"processing_error": f"Spectral analysis failed: {str(e)}"},
                "analysis_data": None,
                "visualization_data": None
            }
            
            return data

    # 🔧 NEW: Frequency Domain Spectral Analysis
    def _analyze_channel_spectrum_frequency_domain(self, data: np.ndarray, sampling_rate: float, freq_bands: Dict) -> Dict:
        """Analyze spectral content for frequency domain data"""
        try:
            # Data is already in frequency domain (complex FFT results or PSD values)
            if np.iscomplexobj(data):
                # Complex FFT data - compute power spectrum
                freqs = np.fft.fftfreq(len(data), 1/sampling_rate)
                psd = np.abs(data) ** 2
                # Keep only positive frequencies
                positive_freq_mask = freqs >= 0
                freqs = freqs[positive_freq_mask]
                psd = psd[positive_freq_mask]
            else:
                # Assume data is already PSD values
                freqs = np.linspace(0, sampling_rate/2, len(data))
                psd = data
            
            # Calculate power in each frequency band
            band_powers = {}
            total_power = np.trapz(psd, freqs)
            
            for band_name, (low_freq, high_freq) in freq_bands.items():
                band_mask = (freqs >= low_freq) & (freqs <= high_freq)
                if np.any(band_mask):
                    band_power = np.trapz(psd[band_mask], freqs[band_mask])
                    relative_power = band_power / total_power if total_power > 0 else 0
                    
                    band_powers[band_name] = {
                        "relative_power": float(relative_power)
                    }
                else:
                    band_powers[band_name] = {
                        "relative_power": 0.0
                    }
            
            # Find dominant band
            dominant_band = max(band_powers.items(), key=lambda x: x[1]["relative_power"])[0] if band_powers else "unknown"
            
            return {
                "band_powers": band_powers,
                "dominant_band": dominant_band,
                "processing_note": "frequency_domain_input"
            }
            
        except Exception as e:
            print(f"Error in frequency domain spectrum analysis: {e}")
            return {
                "band_powers": {},
                "dominant_band": "error"
            }

    # 🔧 NEW: Time-Frequency Domain Spectral Analysis
    def _analyze_channel_spectrum_time_frequency_domain(self, data: np.ndarray, sampling_rate: float, freq_bands: Dict) -> Dict:
        """Analyze spectral content for time-frequency domain data"""
        try:
            # Handle 2D time-frequency data (e.g., from STFT)
            if hasattr(data, 'ndim') and data.ndim > 1:
                # Average across time to get frequency profile
                freq_profile = np.mean(data, axis=1)
                # Create frequency axis (approximate)
                freqs = np.linspace(0, sampling_rate/2, len(freq_profile))
                psd = freq_profile
            else:
                # Fallback to standard analysis
                return self._analyze_channel_spectrum(data, sampling_rate, freq_bands)
            
            # Calculate power in each frequency band
            band_powers = {}
            total_power = np.trapz(psd, freqs)
            
            for band_name, (low_freq, high_freq) in freq_bands.items():
                band_mask = (freqs >= low_freq) & (freqs <= high_freq)
                if np.any(band_mask):
                    band_power = np.trapz(psd[band_mask], freqs[band_mask])
                    relative_power = band_power / total_power if total_power > 0 else 0
                    
                    band_powers[band_name] = {
                        "relative_power": float(relative_power)
                    }
                else:
                    band_powers[band_name] = {
                        "relative_power": 0.0
                    }
            
            # Find dominant band
            dominant_band = max(band_powers.items(), key=lambda x: x[1]["relative_power"])[0] if band_powers else "unknown"
            
            return {
                "band_powers": band_powers,
                "dominant_band": dominant_band,
                "processing_note": "time_frequency_domain_input"
            }
            
        except Exception as e:
            print(f"Error in time-frequency domain spectrum analysis: {e}")
            return {
                "band_powers": {},
                "dominant_band": "error"
            }

    # 🔧 UPDATED: Summary with domain information
    def _generate_spectral_summary(self, spectral_results: Dict, freq_bands: Dict, domain: DomainType) -> Dict:
        """Generate simplified summary statistics for spectral analysis"""
        try:
            channel_dominant_bands = [result["dominant_band"] for result in spectral_results.values() if result["dominant_band"] != "error"]
            
            # Calculate average relative powers across channels
            avg_relative_powers = {}
            for band in freq_bands.keys():
                band_powers = [result["band_powers"][band]["relative_power"] for result in spectral_results.values() 
                            if band in result["band_powers"]]
                avg_relative_powers[band] = float(np.mean(band_powers)) if band_powers else 0.0
            
            return {
                "total_channels_analyzed": len(spectral_results),
                "highest_power_band": max(avg_relative_powers.items(), key=lambda x: x[1])[0] if avg_relative_powers else "unknown",
                "average_relative_powers": avg_relative_powers,
                "processing_domain": domain.value,  # 🔧 NEW: Include domain info
                "domain_adaptation": "applied" if domain != DomainType.TIME else "standard"
            }
        except Exception as e:
            print(f"Error generating spectral summary: {e}")
            return {"error": "Failed to generate summary"}
        
    def _get_frequency_bands(self) -> Dict[str, tuple]:
            """Define frequency bands for analysis"""
            return {
                "delta": (0.5, 4),
                "theta": (4, 8),
                "alpha": (8, 13),
                "beta": (13, 30),
                "gamma": (30, 45)
            }
    
    def _analyze_channel_spectrum(self, data: np.ndarray, sampling_rate: float, freq_bands: Dict) -> Dict:
        """Analyze spectral content for a single channel"""
        try:
            # Compute power spectral density using Welch's method
            nperseg = min(256, len(data))
            freqs, psd = signal.welch(data, fs=sampling_rate, nperseg=nperseg)
            
            # Calculate power in each frequency band
            band_powers = {}
            total_power = np.trapz(psd, freqs)
            
            for band_name, (low_freq, high_freq) in freq_bands.items():
                band_mask = (freqs >= low_freq) & (freqs <= high_freq)
                if np.any(band_mask):
                    band_power = np.trapz(psd[band_mask], freqs[band_mask])
                    relative_power = band_power / total_power if total_power > 0 else 0
                    
                    band_powers[band_name] = {
                        "relative_power": float(relative_power)
                    }
                else:
                    band_powers[band_name] = {
                        "relative_power": 0.0
                    }
            
            # Find dominant band
            dominant_band = max(band_powers.items(), key=lambda x: x[1]["relative_power"])[0] if band_powers else "unknown"
            
            return {
                "band_powers": band_powers,
                "dominant_band": dominant_band
            }
            
        except Exception as e:
            print(f"Error in channel spectrum analysis: {e}")
            return {
                "band_powers": {},
                "dominant_band": "error"
            }
    
    def _plot_power_spectrum_comparison(self, spectral_results: Dict) -> str:
        """Plot simplified power spectrum comparison"""
        try:
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Prepare data for bar chart
            bands = ['delta', 'theta', 'alpha', 'beta', 'gamma']
            avg_powers = []
            
            for band in bands:
                band_powers = [result["band_powers"][band]["relative_power"] for result in spectral_results.values() 
                             if band in result["band_powers"]]
                avg_powers.append(np.mean(band_powers) if band_powers else 0)
            
            colors = ['blue', 'green', 'red', 'orange', 'purple']
            bars = ax.bar(bands, avg_powers, color=colors, alpha=0.7)
            
            ax.set_xlabel('Frequency Bands')
            ax.set_ylabel('Average Relative Power')
            ax.set_title('Average Power Distribution Across Frequency Bands')
            ax.grid(True, alpha=0.3)
            
            # Add value labels on bars
            for bar, value in zip(bars, avg_powers):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{value:.3f}', ha='center', va='bottom', fontweight='bold')
            
            plt.tight_layout()
            return self._plot_to_base64(fig)
            
        except Exception as e:
            print(f"Error generating power spectrum plot: {e}")
            return self._generate_fallback_plot()
    
    def _generate_fallback_plot(self) -> str:
        """Generate a simple fallback plot"""
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, 'Spectral Analysis Visualization\nNot Available', 
                   ha='center', va='center', transform=ax.transAxes, fontsize=16)
            ax.set_title('Spectral Analysis')
            ax.axis('off')
            
            plt.tight_layout()
            return self._plot_to_base64(fig)
        except Exception:
            return ""
    
    def _plot_to_base64(self, fig) -> str:
        """Convert matplotlib plot to base64 string"""
        buffer = BytesIO()
        fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        buffer.close()
        plt.close(fig)
        return f"data:image/png;base64,{image_base64}"

register_algorithm(SpectralAnalysis())