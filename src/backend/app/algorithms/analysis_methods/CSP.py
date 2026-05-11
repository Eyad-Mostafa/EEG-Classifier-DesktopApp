import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import linalg
from io import BytesIO
import base64
from typing import Dict, List, Tuple, Any, Optional
import traceback

from app.core.registry import register_algorithm
from app.algorithms.base import BaseStep, AlgorithmParameter, AlgorithmExample
from app.models.eeg_data import EEGData
from app.schemas.domain_enum import DomainType

class CommonSpatialPatterns(BaseStep):
    # 1. Identity & Metadata
    id = "common_spatial_patterns"
    name = "Common Spatial Patterns (CSP)"
    description = "Spatial filtering technique for multi-class EEG signal classification"
    category = "Spatial Analysis"
    type = "analysis"
    domainType = DomainType.TIME
    allowedDomainTypes = [DomainType.TIME, DomainType.FREQUENCY, DomainType.TIME_FREQUENCY]
    
    howItWorks = """
    Common Spatial Patterns (CSP) is a powerful spatial filtering technique that:
    - Maximizes variance for one class while minimizing for another
    - Finds optimal spatial filters for discriminating between mental states
    - Widely used in motor imagery and BCI applications
    - Works by diagonalizing the covariance matrices of two classes
    """
    
    useCases = [
        "Motor imagery classification (left vs right hand movement)",
        "Brain-Computer Interface (BCI) applications",
        "Mental state discrimination (rest vs task)",
        "Clinical EEG analysis for condition discrimination"
    ]
    
    relatedAlgorithms = ["spectral_analysis", "functional_connectivity"]
    
    # 2. Parameters
    parameters = [
        AlgorithmParameter(
            name="frequency_band",
            type="string",
            value="alpha",
            default="alpha",
            options=["delta", "theta", "alpha", "beta", "gamma", "custom"],
            description="Frequency band for CSP analysis"
        ),
        AlgorithmParameter(
            name="n_components",
            type="number",
            value="4",
            default="4",
            min=2,
            max=20,
            description="Number of CSP components to extract"
        ),
        AlgorithmParameter(
            name="class_definition",
            type="string",
            value="first_half_vs_second_half",
            default="first_half_vs_second_half",
            options=["first_half_vs_second_half", "odd_vs_even", "manual_markers"],
            description="How to define classes for CSP (for demonstration purposes)"
        )
    ]
    
    examples = [
        AlgorithmExample(
            title="Motor Imagery Simulation",
            description="CSP analysis simulating left vs right hand motor imagery",
            parameters={
                "frequency_band": "beta",
                "n_components": 4,
                "class_definition": "first_half_vs_second_half"
            }
        ),
        AlgorithmExample(
            title="Rest vs Task Analysis",
            description="Spatial patterns discriminating resting state from cognitive task",
            parameters={
                "frequency_band": "alpha",
                "n_components": 6,
                "class_definition": "odd_vs_even"
            }
        )
    ]

    def process(self, data: EEGData, **params) -> EEGData:
        """
        Run Common Spatial Patterns analysis on EEG data
        """
        try:
            # Validate parameters
            validated_params = self.validate_parameters(params)
            frequency_band = validated_params.get("frequency_band", "alpha")
            n_components = int(validated_params.get("n_components", 4))
            class_definition = validated_params.get("class_definition", "first_half_vs_second_half")
            
            # Get ALL channels from the data
            df = data.channels_only
            channel_cols = data.channel_cols
            sampling_rate = data.sampling_rate
            
            print(f"[Info] Starting CSP Analysis for {len(channel_cols)} channels: {channel_cols}")
            
            # Check if we have enough channels
            if len(channel_cols) < 2:
                raise ValueError(f"Need at least 2 channels for CSP analysis. Found {len(channel_cols)} channels.")
            
            # 🔧 DOMAIN-SPECIFIC PROCESSING
            current_domain = getattr(data, 'domain', DomainType.TIME)
            print(f"[Info] Processing CSP in {current_domain.value} domain")
            
            # Prepare data for CSP - using ALL channels
            if current_domain == DomainType.FREQUENCY:
                # Frequency domain processing
                X_class1, X_class2 = self._prepare_classes_frequency_domain(
                    df, channel_cols, class_definition, frequency_band, sampling_rate
                )
            elif current_domain == DomainType.TIME_FREQUENCY:
                # Time-frequency domain processing
                X_class1, X_class2 = self._prepare_classes_time_frequency_domain(
                    df, channel_cols, class_definition, frequency_band, sampling_rate
                )
            else:
                # Time domain processing (default)
                X_class1, X_class2 = self._prepare_classes_time_domain(
                    df, channel_cols, class_definition, frequency_band, sampling_rate
                )
            
            # Check if we have enough data for both classes
            if X_class1.shape[0] < 2 or X_class2.shape[0] < 2:
                raise ValueError("Insufficient data for both classes. Need at least 2 samples per class.")
            
            print(f"[Info] Class 1 shape: {X_class1.shape}, Class 2 shape: {X_class2.shape}")
            print(f"[Info] Analyzing {X_class1.shape[1]} channels with {n_components} components")
            
            # Perform CSP analysis on ALL channels
            csp_results = self._compute_csp(X_class1, X_class2, n_components, channel_cols)
            
            # Generate visualization
            component_plot = self._plot_csp_analysis(csp_results, channel_cols)
            
            # Construct result payload with user-friendly data
            result_payload = {
                "summary": self._generate_csp_summary(csp_results, validated_params, current_domain, channel_cols),
                "analysis_data": self._generate_user_friendly_analysis_data(csp_results, validated_params, current_domain, channel_cols),
                "visualization_data": {
                    "topographic_map": component_plot,
                    "plots": {"component_plot": component_plot},
                    "visualization_type": "image/png"
                }
            }
            
            # Attach to data object
            if not hasattr(data, 'analysis_results'):
                data.analysis_results = {}
            
            data.analysis_results[self.id] = result_payload
            return data
            
        except Exception as e:
            print(f"[Error] ERROR in CSP Analysis: {str(e)}")
            traceback.print_exc()
            
            if not hasattr(data, 'analysis_results'):
                data.analysis_results = {}
                
            data.analysis_results[self.id] = {
                "summary": {"processing_error": f"CSP analysis failed: {str(e)}"},
                "analysis_data": None,
                "visualization_data": None
            }
            
            return data

    def _generate_user_friendly_analysis_data(self, csp_results: Dict, params: Dict, domain: DomainType, channel_cols: List[str]) -> Dict:
        """Generate user-friendly analysis data without overwhelming numerical details"""
        discrimination_power = np.array(csp_results["discrimination_power"])
        explained_variance = np.array(csp_results["explained_variance"])
        
        # Find best components
        best_disc_idx = np.argmax(discrimination_power)
        best_var_idx = np.argmax(explained_variance)
        
        # Calculate meaningful metrics
        n_effective_components = np.sum(discrimination_power > 0.3)  # More realistic threshold
        avg_discrimination = np.mean(discrimination_power)
        
        return {
            "key_metrics": {
                "total_channels_analyzed": len(channel_cols),
                "channels_used": channel_cols,
                "best_discriminating_component": csp_results["component_names"][best_disc_idx],
                "best_variance_component": csp_results["component_names"][best_var_idx],
                "max_discrimination_power": round(float(np.max(discrimination_power)), 3),
                "average_discrimination_power": round(float(avg_discrimination), 3),
                "effective_components_count": int(n_effective_components),
                "total_variance_explained": round(float(np.sum(explained_variance)), 3),
                "analysis_quality": self._assess_quality(discrimination_power)
            },
            "component_performance": [
                {
                    "component": name,
                    "discrimination_power": round(power, 3),
                    "variance_explained": round(var, 3),
                    "performance_level": self._get_performance_level(power)
                }
                for name, power, var in zip(
                    csp_results["component_names"], 
                    discrimination_power, 
                    explained_variance
                )
            ],
            "processing_info": {
                "frequency_band": params.get("frequency_band", "alpha"),
                "n_components": csp_results["n_components"],
                "processing_domain": domain.value,
                "total_components_generated": len(csp_results["component_names"])
            }
        }

    def _assess_quality(self, discrimination_power: np.ndarray) -> str:
        """Realistic quality assessment based on discrimination power"""
        max_power = np.max(discrimination_power)
        avg_power = np.mean(discrimination_power)
        n_strong_components = np.sum(discrimination_power > 0.7)
        n_moderate_components = np.sum(discrimination_power > 0.4)
        
        if max_power > 0.8 and n_strong_components >= 2:
            return "Excellent"
        elif max_power > 0.6 and n_strong_components >= 1:
            return "Good"
        elif max_power > 0.4 and n_moderate_components >= 2:
            return "Moderate"
        elif max_power > 0.2:
            return "Weak"
        else:
            return "Poor"

    def _get_performance_level(self, power: float) -> str:
        """Get performance level for individual components"""
        if power > 0.7:
            return "Strong"
        elif power > 0.5:
            return "Good"
        elif power > 0.3:
            return "Moderate"
        elif power > 0.1:
            return "Weak"
        else:
            return "Poor"

    def _prepare_classes_time_domain(self, df: pd.DataFrame, channels: List[str], 
                                   class_definition: str, frequency_band: str, 
                                   sampling_rate: float) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare class data for CSP in time domain using ALL channels"""
        print(f"[Info] Preparing time domain data for {len(channels)} channels")
        
        # Filter data to specified frequency band - using ALL channels
        filtered_data = self._filter_to_frequency_band(df[channels], frequency_band, sampling_rate)
        
        # Split data into two classes based on definition
        n_samples = len(filtered_data)
        
        if class_definition == "first_half_vs_second_half":
            split_point = n_samples // 2
            X_class1 = filtered_data.iloc[:split_point].values
            X_class2 = filtered_data.iloc[split_point:].values
            
        elif class_definition == "odd_vs_even":
            X_class1 = filtered_data.iloc[::2].values  # Odd indices
            X_class2 = filtered_data.iloc[1::2].values  # Even indices
            
        else:  # manual_markers (simulated)
            # For demonstration, split by amplitude characteristics
            mean_amplitude = np.mean(np.abs(filtered_data.values), axis=1)
            median_amp = np.median(mean_amplitude)
            X_class1 = filtered_data[mean_amplitude > median_amp].values
            X_class2 = filtered_data[mean_amplitude <= median_amp].values
        
        print(f"[Info] Class 1: {X_class1.shape[0]} samples × {X_class1.shape[1]} channels")
        print(f"[Info] Class 2: {X_class2.shape[0]} samples × {X_class2.shape[1]} channels")
        return X_class1, X_class2

    def _prepare_classes_frequency_domain(self, df: pd.DataFrame, channels: List[str],
                                        class_definition: str, frequency_band: str,
                                        sampling_rate: float) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare class data for CSP in frequency domain using ALL channels"""
        print(f"[Info] Preparing frequency domain data for {len(channels)} channels")
        
        # For frequency domain, use band power features for ALL channels
        band_powers = []
        
        for channel in channels:
            channel_data = df[channel].values
            if np.iscomplexobj(channel_data):
                # Complex FFT data - compute band power
                freqs = np.fft.fftfreq(len(channel_data), 1/sampling_rate)
                psd = np.abs(channel_data) ** 2
                positive_mask = freqs >= 0
                freqs = freqs[positive_mask]
                psd = psd[positive_mask]
            else:
                # Assume PSD data
                freqs = np.linspace(0, sampling_rate/2, len(channel_data))
                psd = channel_data
            
            # Extract power in specified band
            band_power = self._extract_band_power(freqs, psd, frequency_band)
            band_powers.append(band_power)
        
        band_powers = np.array(band_powers).T  # [samples × channels]
        
        # Split into classes
        n_samples = len(band_powers)
        if class_definition == "first_half_vs_second_half":
            split_point = n_samples // 2
            X_class1 = band_powers[:split_point]
            X_class2 = band_powers[split_point:]
        else:  # odd_vs_even
            X_class1 = band_powers[::2]
            X_class2 = band_powers[1::2]
        
        print(f"[Info] Frequency domain - Class 1: {X_class1.shape}, Class 2: {X_class2.shape}")
        return X_class1, X_class2

    def _prepare_classes_time_frequency_domain(self, df: pd.DataFrame, channels: List[str],
                                             class_definition: str, frequency_band: str,
                                             sampling_rate: float) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare class data for CSP in time-frequency domain using ALL channels"""
        print(f"[Info] Preparing time-frequency domain data for {len(channels)} channels")
        
        # Reduce time-frequency data and extract features for ALL channels
        reduced_data = []
        
        for channel in channels:
            tf_data = df[channel].values
            
            # Handle 2D time-frequency data
            if hasattr(tf_data, 'ndim') and tf_data.ndim > 1:
                # Average across time to get frequency profile
                freq_profile = np.mean(tf_data, axis=1)
                reduced_data.append(freq_profile)
            else:
                # Use as is
                reduced_data.append(tf_data)
        
        # Create feature matrix
        feature_matrix = np.column_stack(reduced_data)
        
        # Split into classes
        n_samples = len(feature_matrix)
        if class_definition == "first_half_vs_second_half":
            split_point = n_samples // 2
            X_class1 = feature_matrix[:split_point]
            X_class2 = feature_matrix[split_point:]
        else:  # odd_vs_even
            X_class1 = feature_matrix[::2]
            X_class2 = feature_matrix[1::2]
        
        print(f"[Info] Time-Freq domain - Class 1: {X_class1.shape}, Class 2: {X_class2.shape}")
        return X_class1, X_class2

    def _filter_to_frequency_band(self, data: pd.DataFrame, frequency_band: str, 
                                sampling_rate: float) -> pd.DataFrame:
        """Filter data to specified frequency band for ALL channels"""
        if frequency_band == "custom":
            return data
            
        band_ranges = {
            "delta": (0.5, 4),
            "theta": (4, 8),
            "alpha": (8, 13),
            "beta": (13, 30),
            "gamma": (30, 45)
        }
        
        low_freq, high_freq = band_ranges.get(frequency_band, (8, 13))
        
        print(f"[Info] Filtering {len(data.columns)} channels to {frequency_band} band ({low_freq}-{high_freq} Hz)")
        
        # Apply bandpass filter to ALL channels
        filtered_data = data.copy()
        nyquist = sampling_rate / 2
        low = low_freq / nyquist
        high = high_freq / nyquist
        
        from scipy.signal import butter, filtfilt
        b, a = butter(4, [low, high], btype='band')
        
        for column in data.columns:
            filtered_data[column] = filtfilt(b, a, data[column].values)
            
        return filtered_data

    def _extract_band_power(self, freqs: np.ndarray, psd: np.ndarray, 
                           frequency_band: str) -> float:
        """Extract power in specified frequency band"""
        band_ranges = {
            "delta": (0.5, 4),
            "theta": (4, 8),
            "alpha": (8, 13),
            "beta": (13, 30),
            "gamma": (30, 45)
        }
        
        low_freq, high_freq = band_ranges.get(frequency_band, (8, 13))
        band_mask = (freqs >= low_freq) & (freqs <= high_freq)
        
        if np.any(band_mask):
            return np.trapz(psd[band_mask], freqs[band_mask])
        else:
            return 0.0

    def _compute_csp(self, X1: np.ndarray, X2: np.ndarray, n_components: int,
                    channel_names: List[str]) -> Dict[str, Any]:
        """Compute Common Spatial Patterns for ALL channels"""
        # Ensure data has correct shape [samples × channels]
        if X1.shape[1] != len(channel_names) or X2.shape[1] != len(channel_names):
            raise ValueError(f"Data shape doesn't match number of channels. Expected {len(channel_names)} channels, got {X1.shape[1]} and {X2.shape[1]}")
        
        print(f"[Info] Computing CSP for {len(channel_names)} channels: {channel_names}")
        
        # Calculate covariance matrices for each class
        cov1 = np.cov(X1.T)
        cov2 = np.cov(X2.T)
        
        # Regularize covariance matrices
        reg_coef = 0.01
        cov1 += reg_coef * np.eye(cov1.shape[0])
        cov2 += reg_coef * np.eye(cov2.shape[0])
        
        # Solve generalized eigenvalue problem: cov1 * W = lambda * cov2 * W
        eigenvalues, eigenvectors = linalg.eigh(cov1, cov1 + cov2)
        
        # Sort eigenvectors by descending eigenvalues
        sorted_indices = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[sorted_indices]
        eigenvectors = eigenvectors[:, sorted_indices]
        
        # Select top and bottom components
        n_components = min(n_components, len(channel_names))
        component_indices = list(range(n_components)) + list(range(-n_components, 0))
        selected_components = eigenvectors[:, component_indices]
        
        # Calculate spatial patterns (pseudo-inverse of filters)
        spatial_patterns = linalg.pinv(selected_components).T
        
        # Normalize patterns
        spatial_patterns = spatial_patterns / np.linalg.norm(spatial_patterns, axis=0)
        
        # Calculate explained variance
        total_variance = np.sum(eigenvalues)
        explained_variance = eigenvalues[component_indices] / total_variance
        
        # Calculate discrimination power
        var_class1 = np.var(X1 @ selected_components, axis=0)
        var_class2 = np.var(X2 @ selected_components, axis=0)
        discrimination_power = np.abs(var_class1 - var_class2) / (var_class1 + var_class2 + 1e-10)
        
        # Create component names
        component_names = [f"CSP{i+1}" for i in range(n_components)] + \
                         [f"CSP-{i+1}" for i in range(n_components)]
        
        print(f"[Info] CSP computed: {len(component_names)} components from {len(channel_names)} channels")
        
        return {
            "spatial_filters": selected_components,
            "spatial_patterns": spatial_patterns,
            "eigenvalues": eigenvalues[component_indices],
            "explained_variance": explained_variance,
            "component_names": component_names,
            "discrimination_power": discrimination_power.tolist(),
            "n_components": n_components
        }

    def _plot_csp_analysis(self, csp_results: Dict, channel_names: List[str]) -> str:
        """Plot simplified CSP analysis visualization"""
        try:
            # Create a clean, single figure
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
            
            # Plot 1: Component Performance (Left)
            self._plot_component_performance(ax1, csp_results)
            
            # Plot 2: Spatial Patterns (Right)
            self._plot_spatial_patterns(ax2, csp_results, channel_names)
            
            plt.suptitle(f'Common Spatial Patterns (CSP) Analysis - {len(channel_names)} Channels', 
                        fontsize=16, fontweight='bold', y=0.98)
            plt.tight_layout()
            
            return self._plot_to_base64(fig)
            
        except Exception as e:
            print(f"[Error] CSP analysis plot error: {e}")
            traceback.print_exc()
            return self._generate_fallback_plot()

    def _plot_component_performance(self, ax, csp_results: Dict):
        """Plot component discrimination power with realistic quality assessment"""
        component_names = csp_results["component_names"]
        discrimination_power = csp_results["discrimination_power"]
        
        # Color coding: blue for CSP+, red for CSP-
        colors = ['#2E86AB' if 'CSP-' not in name else '#A23B72' for name in component_names]
        
        bars = ax.bar(component_names, discrimination_power, color=colors, alpha=0.8, edgecolor='black', linewidth=0.5)
        
        ax.set_title('Component Discrimination Power', fontweight='bold', fontsize=14)
        ax.set_ylabel('Discrimination Power', fontweight='bold')
        ax.set_xlabel('CSP Components', fontweight='bold')
        ax.set_ylim(0, 1.1)
        ax.grid(True, alpha=0.3, axis='y')
        ax.tick_params(axis='x', rotation=45)
        
        # Add value labels on bars
        for bar, value in zip(bars, discrimination_power):
            height = bar.get_height()
            if height > 0.1:  # Only label significant values
                ax.text(bar.get_x() + bar.get_width()/2, height + 0.02,
                       f'{value:.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        # Add realistic quality thresholds
        ax.axhline(y=0.7, color='green', linestyle='--', alpha=0.7, label='Strong')
        ax.axhline(y=0.5, color='orange', linestyle='--', alpha=0.7, label='Good')
        ax.axhline(y=0.3, color='red', linestyle='--', alpha=0.7, label='Moderate')
        
        # Add legend
        ax.legend(loc='upper right', framealpha=0.9)
        
        # Add realistic quality assessment
        quality = self._assess_quality(np.array(discrimination_power))
        color_map = {"Excellent": "green", "Good": "orange", "Moderate": "red", "Weak": "purple", "Poor": "gray"}
        color = color_map.get(quality, "black")
        
        ax.text(0.02, 0.98, f'Quality: {quality}', transform=ax.transAxes,
               fontsize=12, fontweight='bold', color=color,
               bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.9))

    def _plot_spatial_patterns(self, ax, csp_results: Dict, channel_names: List[str]):
        """Plot spatial patterns as a clean heatmap"""
        spatial_patterns = csp_results["spatial_patterns"]
        component_names = csp_results["component_names"]
        
        # Shorten names for better display
        short_channels = [ch.replace('channel_', '').replace('ch_', '')[:8] for ch in channel_names]
        short_components = [comp.replace('CSP', 'C') for comp in component_names]
        
        # Create heatmap
        vmax = np.max(np.abs(spatial_patterns))
        im = ax.imshow(spatial_patterns, cmap='RdBu_r', aspect='auto', 
                      vmin=-vmax, vmax=vmax)
        
        ax.set_title(f'Spatial Patterns ({len(channel_names)} Channels)', fontweight='bold', fontsize=14)
        ax.set_xlabel('Components', fontweight='bold')
        ax.set_ylabel('Channels', fontweight='bold')
        
        # Set ticks and labels
        ax.set_xticks(range(len(short_components)))
        ax.set_xticklabels(short_components, rotation=0, fontweight='bold')
        ax.set_yticks(range(len(short_channels)))
        ax.set_yticklabels(short_channels, fontsize=8)
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
        cbar.set_label('Weight Value', rotation=270, labelpad=15, fontweight='bold')
        
        # Add grid
        ax.set_xticks([x - 0.5 for x in range(1, len(short_components))], minor=True)
        ax.set_yticks([y - 0.5 for y in range(1, len(short_channels))], minor=True)
        ax.grid(which="minor", color="gray", linestyle='-', linewidth=0.2)
        ax.tick_params(which="minor", size=0)

    def _generate_csp_summary(self, csp_results: Dict, params: Dict, domain: DomainType, channel_cols: List[str]) -> Dict:
        """Generate CSP analysis summary"""
        try:
            discrimination_power = np.array(csp_results["discrimination_power"])
            explained_variance = np.array(csp_results["explained_variance"])
            
            best_component_idx = np.argmax(discrimination_power)
            best_component = csp_results["component_names"][best_component_idx]
            max_power = float(np.max(discrimination_power))
            
            quality = self._assess_quality(discrimination_power)
            
            return {
                "analysis_quality": quality,
                "best_component": best_component,
                "max_discrimination": round(max_power, 3),
                "effective_components": int(np.sum(discrimination_power > 0.3)),
                "total_variance_explained": round(float(np.sum(explained_variance)), 3),
                "frequency_band": params.get("frequency_band", "alpha"),
                "processing_domain": domain.value,
                "component_count": csp_results["n_components"],
                "channels_analyzed": len(channel_cols),
                "interpretation": self._get_interpretation(quality, max_power)
            }
            
        except Exception as e:
            return {
                "analysis_success": False,
                "error": "Summary generation failed"
            }

    def _get_interpretation(self, quality: str, max_power: float) -> str:
        """Provide meaningful interpretation for users"""
        interpretations = {
            "Excellent": "Strong spatial patterns detected. The CSP components effectively discriminate between the two classes.",
            "Good": "Good discrimination performance. The spatial patterns show meaningful separation between classes.",
            "Moderate": "Moderate discrimination. Some components show useful patterns but overall separation is limited.",
            "Weak": "Weak discrimination. The spatial patterns show minimal separation between classes.",
            "Poor": "Poor discrimination. The analysis did not find meaningful spatial patterns for class separation."
        }
        return interpretations.get(quality, "Analysis completed successfully.")

    def _plot_to_base64(self, fig) -> str:
        """Convert plot to base64 string"""
        buffer = BytesIO()
        fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight', facecolor='white')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        buffer.close()
        plt.close(fig)
        return f"data:image/png;base64,{image_base64}"

    def _generate_fallback_plot(self) -> str:
        """Generate fallback plot"""
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, 'CSP Analysis Results\nVisualization Available', 
                   ha='center', va='center', transform=ax.transAxes, fontsize=14)
            ax.set_title('Common Spatial Patterns (CSP) Analysis', fontweight='bold')
            ax.axis('off')
            plt.tight_layout()
            return self._plot_to_base64(fig)
        except:
            return ""

    def validate_parameters(self, params: Dict) -> Dict:
        """Validate and sanitize algorithm parameters"""
        validated = {}
        
        # Validate frequency_band
        valid_bands = ["delta", "theta", "alpha", "beta", "gamma", "custom"]
        validated["frequency_band"] = params.get("frequency_band", "alpha")
        if validated["frequency_band"] not in valid_bands:
            validated["frequency_band"] = "alpha"
        
        # Validate n_components - increased max to handle more channels
        try:
            n_comp = int(params.get("n_components", 4))
            validated["n_components"] = str(max(2, min(20, n_comp)))
        except (ValueError, TypeError):
            validated["n_components"] = "4"
        
        # Validate class_definition
        valid_definitions = ["first_half_vs_second_half", "odd_vs_even", "manual_markers"]
        validated["class_definition"] = params.get("class_definition", "first_half_vs_second_half")
        if validated["class_definition"] not in valid_definitions:
            validated["class_definition"] = "first_half_vs_second_half"
        
        return validated

# Register the algorithm
register_algorithm(CommonSpatialPatterns())