import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import signal
from scipy.signal import hilbert
import seaborn as sns
from io import BytesIO
import base64
import networkx as nx
from typing import Dict, List, Tuple, Any
import traceback
import math

from app.core.registry import register_algorithm
from app.algorithms.base import BaseStep, AlgorithmParameter, AlgorithmExample
from app.models.eeg_data import EEGData
from app.schemas.domain_enum import DomainType

class FunctionalConnectivityAnalysis(BaseStep):
    # 1. Identity & Metadata
    id = "functional_connectivity"
    name = "Functional Connectivity Analysis"
    description = "Analyzes brain network connectivity using Phase Locking Value (PLV) and Coherence"
    category = "Network Analysis"
    type = "analysis"
    domainType = DomainType.TIME
    allowedDomainTypes = [DomainType.TIME, DomainType.FREQUENCY, DomainType.TIME_FREQUENCY]
    
    howItWorks = """
    Computes functional connectivity between EEG channels using:
    - Phase Locking Value (PLV): Measures phase synchronization between signals
    - Coherence: Frequency-domain correlation between channels
    - Network Analysis: Identifies hub channels and network properties
    Works across Time, Frequency, and Time-Frequency domains.
    """
    
    useCases = [
        "Study brain network dynamics during cognitive tasks",
        "Identify hyper/hypo-connectivity in clinical populations",
        "Track changes in functional networks over time",
        "Compare resting-state vs task-based connectivity"
    ]
    
    relatedAlgorithms = ["spectral_analysis", "differential_entropy"]
    
    # 2. Parameters
    parameters = [
        AlgorithmParameter(
            name="frequency_band",
            type="string",
            value="alpha",
            default="alpha",
            options=["delta", "theta", "alpha", "beta", "gamma", "full_spectrum"],
            description="Frequency band for connectivity analysis"
        ),
        AlgorithmParameter(
            name="connectivity_threshold",
            type="number",
            value="0.5",
            default="0.5",
            min=0.1,
            max=0.9,
            description="Threshold for significant connections in network analysis"
        ),
        AlgorithmParameter(
            name="min_connections",
            type="number", 
            value="3",
            default="3",
            min=1,
            max=10,
            description="Minimum number of strong connections to identify hub channels"
        )
    ]
    
    examples = [
        AlgorithmExample(
            title="Alpha Band Connectivity",
            description="Analyze functional connectivity in the alpha frequency band (8-13 Hz)",
            parameters={"frequency_band": "alpha", "connectivity_threshold": 0.6}
        ),
        AlgorithmExample(
            title="Full Spectrum Network Analysis",
            description="Comprehensive connectivity analysis across all frequency bands",
            parameters={"frequency_band": "full_spectrum", "connectivity_threshold": 0.4}
        )
    ]

    def process(self, data: EEGData, **params) -> EEGData:
        """
        Run functional connectivity analysis on EEG data across all domains
        """
        try:
            # Validate parameters
            validated_params = self.validate_parameters(params)
            frequency_band = validated_params.get("frequency_band", "alpha")
            connectivity_threshold = float(validated_params.get("connectivity_threshold", 0.5))
            min_connections = int(validated_params.get("min_connections", 3))
            
            df = data.channels_only
            channel_cols = data.channel_cols
            sampling_rate = data.sampling_rate
            
            print(f"[Info] Starting Functional Connectivity Analysis for {len(channel_cols)} channels")
            
            # 🔧 DOMAIN-SPECIFIC PROCESSING
            current_domain = getattr(data, 'domain', DomainType.TIME)
            
            print(f"[Info] Processing connectivity in {current_domain.value} domain")
            
            if current_domain == DomainType.FREQUENCY:
                # Frequency domain data (after FFT, PSD, etc.)
                plv_matrix, coherence_matrix = self._calculate_connectivity_frequency_domain(
                    df, channel_cols, frequency_band, sampling_rate
                )
                
            elif current_domain == DomainType.TIME_FREQUENCY:
                # Time-Frequency domain data (after STFT, Wavelet, etc.)
                df = self._reduce_time_frequency_data(df, channel_cols, sampling_rate)
                
                plv_matrix, coherence_matrix = self._calculate_connectivity_time_frequency_domain(
                    df, channel_cols, frequency_band, sampling_rate
                )
                
            else:  # DomainType.TIME (default)
                # Time domain data (raw or filtered)
                filtered_data = self._filter_to_frequency_band(df, frequency_band, sampling_rate)
                plv_matrix = self._calculate_plv_matrix(filtered_data, channel_cols, sampling_rate)
                coherence_matrix = self._calculate_coherence_matrix(filtered_data, channel_cols, sampling_rate)
            
            # Perform network analysis
            network_metrics = self._analyze_network_properties(
                plv_matrix, channel_cols, connectivity_threshold, min_connections
            )
            
            # Generate visualizations
            connectivity_plot = self._plot_connectivity_matrices(plv_matrix, coherence_matrix, channel_cols)
            network_plot = self._plot_network_graph(plv_matrix, channel_cols, connectivity_threshold, network_metrics)
            
            # Construct result payload
            result_payload = {
                "summary": self._generate_connectivity_summary(
                    plv_matrix, coherence_matrix, network_metrics, validated_params, current_domain
                ),
                "analysis_data": {
                    "plv_matrix": self._matrix_to_dict(plv_matrix, channel_cols),
                    "coherence_matrix": self._matrix_to_dict(coherence_matrix, channel_cols),
                    "network_metrics": network_metrics,
                    "frequency_band_used": frequency_band,
                    "connectivity_threshold": connectivity_threshold,
                    "processing_domain": current_domain.value  # Track which domain was used
                },
                "visualization_data": {
                    "topographic_map": connectivity_plot,
                    "plots": {"network_plot": network_plot},
                    "visualization_type": "image/png"
                }
            }
            
            # Attach to data object
            if not hasattr(data, 'analysis_results'):
                data.analysis_results = {}
            
            data.analysis_results[self.id] = result_payload
            return data
            
        except Exception as e:
            print(f"[Error] ERROR in Functional Connectivity Analysis: {str(e)}")
            traceback.print_exc()
            
            # Attach error result
            if not hasattr(data, 'analysis_results'):
                data.analysis_results = {}
                
            data.analysis_results[self.id] = {
                "summary": {"processing_error": f"Connectivity analysis failed: {str(e)}"},
                "analysis_data": None,
                "visualization_data": None
            }
            
            return data

    def _calculate_connectivity_frequency_domain(self, df: pd.DataFrame, channels: List[str], 
                                               frequency_band: str, sampling_rate: float) -> Tuple[np.ndarray, np.ndarray]:
        """Calculate connectivity for frequency domain data (after FFT/PSD)"""
        n_channels = len(channels)
        plv_matrix = np.zeros((n_channels, n_channels))
        coherence_matrix = np.zeros((n_channels, n_channels))
        
        for i in range(n_channels):
            for j in range(i, n_channels):
                if i == j:
                    plv_matrix[i, j] = 1.0
                    coherence_matrix[i, j] = 1.0
                else:
                    freq_data_i = df[channels[i]].values
                    freq_data_j = df[channels[j]].values
                    
                    # For complex FFT data: use phase differences
                    if np.iscomplexobj(freq_data_i) and np.iscomplexobj(freq_data_j):
                        phase_i = np.angle(freq_data_i)
                        phase_j = np.angle(freq_data_j)
                        plv = np.abs(np.mean(np.exp(1j * (phase_i - phase_j))))
                    else:
                        # For PSD data: fallback to time-domain PLV calculation
                        plv = self._calculate_fallback_plv(df, channels[i], channels[j], sampling_rate)
                    
                    # Coherence in frequency domain
                    if len(freq_data_i) > 10 and len(freq_data_j) > 10:
                        coherence = np.abs(np.corrcoef(freq_data_i, freq_data_j)[0, 1])
                    else:
                        coherence = 0.0
                    
                    plv_matrix[i, j] = plv_matrix[j, i] = plv
                    coherence_matrix[i, j] = coherence_matrix[j, i] = coherence
        
        return plv_matrix, coherence_matrix

    def _calculate_connectivity_time_frequency_domain(self, df: pd.DataFrame, channels: List[str],
                                                    frequency_band: str, sampling_rate: float) -> Tuple[np.ndarray, np.ndarray]:
        """ULTRA-FAST correlation-only connectivity for time-frequency data"""
        n_channels = len(channels)
        
        print(f"[Info] ULTRA-FAST correlation-based TF processing for {n_channels} channels")
        
        # Extract and drastically reduce data
        reduced_data = []
        for channel in channels:
            data = df[channel].values
            
            # Convert 2D to 1D by aggressive averaging
            if hasattr(data, 'ndim') and data.ndim > 1:
                # Use only mean across time (most aggressive reduction)
                data = data.mean(axis=1)
            
            # Limit to very small sample
            if len(data) > 100:
                data = data[::len(data)//100]  # Keep only ~100 points
            
            reduced_data.append(data)
        
        # Compute correlation matrices (very fast)
        plv_matrix = np.eye(n_channels)
        coherence_matrix = np.eye(n_channels)
        
        for i in range(n_channels):
            for j in range(i + 1, n_channels):
                data_i = reduced_data[i]
                data_j = reduced_data[j]
                
                min_len = min(len(data_i), len(data_j))
                if min_len > 5:
                    try:
                        # Use simple correlation for both PLV and coherence
                        corr = abs(np.corrcoef(data_i[:min_len], data_j[:min_len])[0, 1])
                        if np.isnan(corr):
                            corr = 0.0
                    except:
                        corr = 0.0
                else:
                    corr = 0.0
                
                plv_matrix[i, j] = plv_matrix[j, i] = corr
                coherence_matrix[i, j] = coherence_matrix[j, i] = corr
        
        return plv_matrix, coherence_matrix

    def _calculate_fallback_plv(self, df: pd.DataFrame, channel_i: str, channel_j: str, 
                               sampling_rate: float) -> float:
        """Fallback PLV calculation when frequency domain data structure is unknown"""
        try:
            # Try to reconstruct time series or use available data
            signal_i = df[channel_i].values
            signal_j = df[channel_j].values
            
            if len(signal_i) > 10 and len(signal_j) > 10:
                analytic_i = hilbert(signal_i)
                analytic_j = hilbert(signal_j)
                phase_i = np.angle(analytic_i)
                phase_j = np.angle(analytic_j)
                return np.abs(np.mean(np.exp(1j * (phase_i - phase_j))))
            else:
                return 0.0
        except:
            return 0.0

    # 🔧 ADD THIS NEW METHOD RIGHT HERE:
    def _reduce_time_frequency_data(self, df: pd.DataFrame, channels: List[str], sampling_rate: float) -> pd.DataFrame:
        """Reduce time-frequency data complexity for faster processing"""
        reduced_df = df.copy()
        
        for channel in channels:
            tf_data = df[channel].values
            
            # If data is 2D (time-frequency), reduce it
            if hasattr(tf_data, 'ndim') and tf_data.ndim > 1:
                # Strategy 1: Average across time (keep frequency info)
                reduced_data = np.mean(tf_data, axis=1)
                
                # Strategy 2: Or take specific time windows (e.g., middle section)
                # time_points = tf_data.shape[1]
                # start_idx = time_points // 4
                # end_idx = 3 * time_points // 4
                # reduced_data = np.mean(tf_data[:, start_idx:end_idx], axis=1)
                
                reduced_df[channel] = reduced_data
        
        return reduced_df

    def _filter_to_frequency_band(self, df: pd.DataFrame, frequency_band: str, sampling_rate: float) -> pd.DataFrame:
        """Filter data to specified frequency band"""
        if frequency_band == "full_spectrum":
            return df
            
        band_ranges = {
            "delta": (0.5, 4),
            "theta": (4, 8),
            "alpha": (8, 13),
            "beta": (13, 30),
            "gamma": (30, 45)
        }
        
        low_freq, high_freq = band_ranges.get(frequency_band, (8, 13))
        
        # Apply bandpass filter
        filtered_df = df.copy()
        nyquist = sampling_rate / 2
        low = low_freq / nyquist
        high = high_freq / nyquist
        
        b, a = signal.butter(4, [low, high], btype='band')
        
        for column in df.columns:
            filtered_df[column] = signal.filtfilt(b, a, df[column].values)
            
        return filtered_df

    def _calculate_plv_matrix(self, df: pd.DataFrame, channels: List[str], sampling_rate: float) -> np.ndarray:
        """Calculate Phase Locking Value matrix between all channel pairs"""
        n_channels = len(channels)
        plv_matrix = np.zeros((n_channels, n_channels))
        
        for i in range(n_channels):
            for j in range(i, n_channels):
                if i == j:
                    plv_matrix[i, j] = 1.0
                else:
                    signal_i = df[channels[i]].values
                    signal_j = df[channels[j]].values
                    
                    # Calculate instantaneous phase using Hilbert transform
                    analytic_i = hilbert(signal_i)
                    analytic_j = hilbert(signal_j)
                    
                    phase_i = np.angle(analytic_i)
                    phase_j = np.angle(analytic_j)
                    
                    # Phase Locking Value
                    phase_diff = phase_i - phase_j
                    plv = np.abs(np.mean(np.exp(1j * phase_diff)))
                    
                    plv_matrix[i, j] = plv
                    plv_matrix[j, i] = plv
                    
        return plv_matrix

    def _calculate_coherence_matrix(self, df: pd.DataFrame, channels: List[str], sampling_rate: float) -> np.ndarray:
        """Calculate coherence matrix between all channel pairs"""
        n_channels = len(channels)
        coherence_matrix = np.zeros((n_channels, n_channels))
        
        for i in range(n_channels):
            for j in range(i, n_channels):
                if i == j:
                    coherence_matrix[i, j] = 1.0
                else:
                    signal_i = df[channels[i]].values
                    signal_j = df[channels[j]].values
                    
                    f, Cxy = signal.coherence(signal_i, signal_j, fs=sampling_rate, nperseg=min(256, len(signal_i)))
                    
                    # Average coherence across frequency bands
                    avg_coherence = np.mean(Cxy)
                    coherence_matrix[i, j] = avg_coherence
                    coherence_matrix[j, i] = avg_coherence
                    
        return coherence_matrix

    def _analyze_network_properties(self, connectivity_matrix: np.ndarray, channels: List[str], 
                                  threshold: float, min_connections: int) -> Dict[str, Any]:
        """Analyze network properties and identify hub channels"""
        try:
            # Create binary adjacency matrix
            adjacency_matrix = (connectivity_matrix > threshold).astype(float)
            np.fill_diagonal(adjacency_matrix, 0)  # Remove self-connections
            
            # Create network graph
            G = nx.from_numpy_array(adjacency_matrix)
            
            # Calculate network metrics
            degree_centrality = nx.degree_centrality(G)
            betweenness_centrality = nx.betweenness_centrality(G)
            
            # Identify hub channels (high degree centrality)
            hub_channels = []
            for i, channel in enumerate(channels):
                degree = degree_centrality[i]
                if degree >= (min_connections / len(channels)):
                    hub_channels.append({
                        'channel': channel,
                        'degree_centrality': float(degree),
                        'betweenness_centrality': float(betweenness_centrality[i]),
                        'connection_count': int(np.sum(adjacency_matrix[i]))
                    })
            
            # Sort hubs by degree centrality
            hub_channels.sort(key=lambda x: x['degree_centrality'], reverse=True)
            
            # Network-level metrics
            network_density = nx.density(G)
            avg_clustering = nx.average_clustering(G)
            avg_shortest_path = nx.average_shortest_path_length(G) if nx.is_connected(G) else float('inf')
            
            return {
                'network_density': float(network_density),
                'average_clustering_coefficient': float(avg_clustering),
                'average_shortest_path_length': float(avg_shortest_path) if avg_shortest_path != float('inf') else None,
                'hub_channels': hub_channels[:5],  # Top 5 hubs
                'total_connections': int(np.sum(adjacency_matrix) / 2),  # Undirected, so divide by 2
                'connection_threshold_used': threshold
            }
            
        except Exception as e:
            print(f"Network analysis error: {e}")
            return {
                'network_density': 0.0,
                'average_clustering_coefficient': 0.0,
                'average_shortest_path_length': None,
                'hub_channels': [],
                'total_connections': 0,
                'connection_threshold_used': threshold
            }

    def _plot_connectivity_matrices(self, plv_matrix: np.ndarray, coherence_matrix: np.ndarray, 
                                  channels: List[str]) -> str:
        """Plot connectivity matrices side by side"""
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
            
            # Shorten channel names for display
            short_channels = [self._get_short_channel_name(ch) for ch in channels]
            
            # PLV Matrix
            im1 = ax1.imshow(plv_matrix, cmap='viridis', aspect='auto', vmin=0, vmax=1)
            ax1.set_title('Phase Locking Value (PLV) Matrix', fontsize=16, fontweight='bold')
            ax1.set_xticks(range(len(channels)))
            ax1.set_yticks(range(len(channels)))
            ax1.set_xticklabels(short_channels, rotation=45)
            ax1.set_yticklabels(short_channels)
            plt.colorbar(im1, ax=ax1, shrink=0.8)
            
            # Coherence Matrix
            im2 = ax2.imshow(coherence_matrix, cmap='plasma', aspect='auto', vmin=0, vmax=1)
            ax2.set_title('Coherence Matrix', fontsize=16, fontweight='bold')
            ax2.set_xticks(range(len(channels)))
            ax2.set_yticks(range(len(channels)))
            ax2.set_xticklabels(short_channels, rotation=45)
            ax2.set_yticklabels(short_channels)
            plt.colorbar(im2, ax=ax2, shrink=0.8)
            
            plt.tight_layout()
            return self._plot_to_base64(fig)
            
        except Exception as e:
            print(f"Connectivity matrix plot error: {e}")
            return self._generate_fallback_plot()

    def _plot_network_graph(self, connectivity_matrix: np.ndarray, channels: List[str], 
                          threshold: float, network_metrics: Dict) -> str:
        """Plot network graph with hub identification"""
        try:
            fig, ax = plt.subplots(figsize=(15, 12))
            
            # Create positions for channels (similar to topographic map)
            positions = self._create_channel_positions(channels)
            
            if not positions:
                ax.text(0.5, 0.5, 'Network graph unavailable:\nChannel positions not mapped', 
                       ha='center', va='center', transform=ax.transAxes, fontsize=14)
                ax.set_title('Functional Network Graph', fontsize=16)
            else:
                # Create network graph
                adjacency_matrix = (connectivity_matrix > threshold).astype(float)
                np.fill_diagonal(adjacency_matrix, 0)
                
                G = nx.from_numpy_array(adjacency_matrix)
                pos = {i: positions[channels[i]] for i in range(len(channels))}
                
                # Node sizes based on degree centrality
                degrees = dict(G.degree())
                node_sizes = [300 + 500 * degrees[i] for i in range(len(channels))]
                
                # Node colors based on hub status
                hub_indices = [channels.index(hub['channel']) for hub in network_metrics.get('hub_channels', [])]
                node_colors = ['red' if i in hub_indices else 'skyblue' for i in range(len(channels))]
                
                # Draw network
                nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color=node_colors, 
                                     alpha=0.9, edgecolors='black', linewidths=2, ax=ax)
                nx.draw_networkx_edges(G, pos, alpha=0.3, edge_color='gray', width=1.5, ax=ax)
                nx.draw_networkx_labels(G, pos, labels={i: self._get_short_channel_name(channels[i]) 
                                                       for i in range(len(channels))}, 
                                      font_size=8, ax=ax)
                
                # Draw head outline
                head = plt.Circle((0, 0), 0.95, fill=False, linewidth=3, color='black', alpha=0.8)
                ax.add_patch(head)
                
                ax.set_xlim(-1.2, 1.2)
                ax.set_ylim(-1.2, 1.2)
                ax.set_aspect('equal')
                ax.set_title(f'Functional Network Graph (Threshold: {threshold})\n'
                           f'Hubs: {len(hub_indices)} channels', fontsize=16, fontweight='bold')
                ax.axis('off')
            
            plt.tight_layout()
            return self._plot_to_base64(fig)
            
        except Exception as e:
            print(f"Network graph plot error: {e}")
            return self._generate_fallback_plot()

    def _generate_connectivity_summary(self, plv_matrix: np.ndarray, coherence_matrix: np.ndarray,
                                     network_metrics: Dict, params: Dict, domain: DomainType) -> Dict[str, Any]:
        """Generate comprehensive connectivity summary"""
        # Basic statistics
        avg_plv = np.mean(plv_matrix[np.triu_indices_from(plv_matrix, k=1)])
        avg_coherence = np.mean(coherence_matrix[np.triu_indices_from(coherence_matrix, k=1)])
        
        # Strong connections count
        strong_plv_connections = (np.sum(plv_matrix > 0.7) - len(plv_matrix)) // 2  # Divide by 2: symmetric matrix counts each pair twice
        strong_coherence_connections = (np.sum(coherence_matrix > 0.7) - len(coherence_matrix)) // 2  # Divide by 2: symmetric matrix counts each pair twice
        
        return {
            "frequency_band": params.get("frequency_band", "alpha"),
            "processing_domain": domain.value,
            "average_plv": float(avg_plv),
            "average_coherence": float(avg_coherence),
            "strong_plv_connections": int(strong_plv_connections),
            "strong_coherence_connections": int(strong_coherence_connections),
            "network_density": network_metrics.get("network_density", 0.0),
            "hub_channels_count": len(network_metrics.get("hub_channels", [])),
            "total_network_connections": network_metrics.get("total_connections", 0),
            "connectivity_threshold": params.get("connectivity_threshold", 0.5),
            "top_hub": network_metrics.get("hub_channels", [{}])[0].get("channel", "None") if network_metrics.get("hub_channels") else "None"
        }

    def _matrix_to_dict(self, matrix: np.ndarray, channels: List[str]) -> Dict[str, Dict[str, float]]:
        """Convert numpy matrix to nested dictionary for JSON serialization"""
        result = {}
        for i, chan_i in enumerate(channels):
            result[chan_i] = {}
            for j, chan_j in enumerate(channels):
                result[chan_i][chan_j] = float(matrix[i, j])
        return result

    def _get_short_channel_name(self, channel_name: str) -> str:
        """Get shortened channel name for display"""
        if channel_name.startswith('channel_'):
            return channel_name.replace('channel_', 'Ch')
        elif len(channel_name) <= 4:
            return channel_name
        else:
            return channel_name[:4]

    def _create_channel_positions(self, channel_names: List[str]) -> Dict[str, Tuple[float, float]]:
        """Create channel positions for network plot"""
        positions = {}
        standard_mapping = {
            'Fp1': (-0.3, 0.8), 'Fpz': (0.0, 0.8), 'Fp2': (0.3, 0.8),
            'AF7': (-0.5, 0.7), 'AF3': (-0.25, 0.7), 'AFz': (0.0, 0.7), 'AF4': (0.25, 0.7), 'AF8': (0.5, 0.7),
            'F7': (-0.7, 0.5), 'F5': (-0.5, 0.5), 'F3': (-0.3, 0.5), 'F1': (-0.15, 0.5), 'Fz': (0.0, 0.5),
            'F2': (0.15, 0.5), 'F4': (0.3, 0.5), 'F6': (0.5, 0.5), 'F8': (0.7, 0.5),
            'FT7': (-0.8, 0.3), 'FC5': (-0.6, 0.3), 'FC3': (-0.4, 0.3), 'FC1': (-0.2, 0.3), 'FCz': (0.0, 0.3),
            'FC2': (0.2, 0.3), 'FC4': (0.4, 0.3), 'FC6': (0.6, 0.3), 'FT8': (0.8, 0.3),
            'T7': (-0.9, 0.1), 'C5': (-0.7, 0.1), 'C3': (-0.5, 0.1), 'C1': (-0.25, 0.1), 'Cz': (0.0, 0.1),
            'C2': (0.25, 0.1), 'C4': (0.5, 0.1), 'C6': (0.7, 0.1), 'T8': (0.9, 0.1),
            'TP7': (-0.9, -0.1), 'CP5': (-0.7, -0.1), 'CP3': (-0.5, -0.1), 'CP1': (-0.25, -0.1), 'CPz': (0.0, -0.1),
            'CP2': (0.25, -0.1), 'CP4': (0.5, -0.1), 'CP6': (0.7, -0.1), 'TP8': (0.9, -0.1),
            'P7': (-0.8, -0.3), 'P5': (-0.6, -0.3), 'P3': (-0.4, -0.3), 'P1': (-0.2, -0.3), 'Pz': (0.0, -0.3),
            'P2': (0.2, -0.3), 'P4': (0.4, -0.3), 'P6': (0.6, -0.3), 'P8': (0.8, -0.3),
            'PO7': (-0.6, -0.5), 'PO5': (-0.45, -0.5), 'PO3': (-0.3, -0.5), 'POz': (0.0, -0.5),
            'PO4': (0.3, -0.5), 'PO6': (0.45, -0.5), 'PO8': (0.6, -0.5),
            'O1': (-0.3, -0.7), 'Oz': (0.0, -0.7), 'O2': (0.3, -0.7),
            'A1': (-1.0, 0.0), 'A2': (1.0, 0.0),
        }
        
        for channel in channel_names:
            clean_channel = channel.replace('channel_', '').replace('ch_', '').replace('CH', '')
            
            if clean_channel in standard_mapping:
                positions[channel] = standard_mapping[clean_channel]
            elif clean_channel.upper() in [k.upper() for k in standard_mapping.keys()]:
                matched_key = [k for k in standard_mapping.keys() if k.upper() == clean_channel.upper()][0]
                positions[channel] = standard_mapping[matched_key]
            else:
                if clean_channel.isdigit():
                    channel_num = int(clean_channel)
                    total_channels = len(channel_names)
                    angle = 2 * math.pi * channel_num / total_channels
                    radius = 0.8 - (0.3 * (channel_num / total_channels))
                    x = radius * math.cos(angle)
                    y = radius * math.sin(angle)
                    positions[channel] = (x, y)
        
        if not positions:
            total_channels = len(channel_names)
            for i, channel in enumerate(channel_names):
                angle = 2 * math.pi * i / total_channels
                radius = 0.7
                x = radius * math.cos(angle)
                y = radius * math.sin(angle)
                positions[channel] = (x, y)
        
        return positions

    def _plot_to_base64(self, fig) -> str:
        """Convert matplotlib plot to base64 string"""
        buffer = BytesIO()
        fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        buffer.close()
        plt.close(fig)
        return f"data:image/png;base64,{image_base64}"

    def _generate_fallback_plot(self) -> str:
        """Generate fallback plot when visualization fails"""
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, 'Connectivity Visualization\nNot Available', 
                   ha='center', va='center', transform=ax.transAxes, fontsize=16)
            ax.set_title('Functional Connectivity Analysis')
            ax.axis('off')
            plt.tight_layout()
            return self._plot_to_base64(fig)
        except Exception:
            return ""

# Register the algorithm
register_algorithm(FunctionalConnectivityAnalysis())