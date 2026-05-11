import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from scipy.signal import welch
from io import BytesIO
import base64
from typing import Dict
from app.core.registry import register_algorithm
from app.algorithms.base import BaseStep, AlgorithmParameter, AlgorithmExample
from app.models.eeg_data import EEGData
from app.schemas.domain_enum import DomainType


class QualityAnalysis(BaseStep):
    # 1. Identity & Metadata
    id = "quality"
    name = "Quality Analysis"
    description = "Analyzes signal quality metrics including SNR, variance, and data quality scores"
    category = "Quality Analysis"
    type = "analysis"
    domainType = DomainType.TIME
    allowedDomainTypes = [DomainType.TIME, DomainType.FREQUENCY, DomainType.TIME_FREQUENCY]

    howItWorks = "Calculates multiple signal quality metrics including SNR, variance, kurtosis, and data quality scores for each channel"
    useCases = [
        "Evaluate signal quality across channels",
        "Identify channels with poor signal quality",
        "Assess data quality before further analysis",
    ]
    relatedAlgorithms = ["differential_entropy"]

    # 2. Parameters (Using AlgorithmParameter)
    parameters = [
        AlgorithmParameter(
            name="quality_threshold",
            type="number",
            value="50.0",
            default="50.0",
            min=0,
            max=100,
            description="Minimum quality score threshold for acceptable signal quality",
        )
    ]

    examples = [
        AlgorithmExample(
            title="Basic Quality Assessment",
            description="Quality analysis for EEG data channels",
            parameters={"quality_threshold": 50.0},
        )
    ]

    # 3. Process Logic
    def process(self, data: EEGData, **params) -> EEGData:
        """
        Run the algorithm and attach results to EEGData.
        """
        # Validate parameters
        validated_params = self.validate_parameters(params)

        df = data.channels_only
        channel_cols = data.channel_cols
        sampling_rate = data.sampling_rate

        print(f"[Info] Quality Analysis: Processing {len(channel_cols)} channels")

        # Calculate quality metrics for each channel
        quality_metrics = {}
        for channel in channel_cols:
            if channel in df.columns:
                channel_data = df[channel].dropna()
                if len(channel_data) > 10:
                    quality_metrics[channel] = self._calculate_channel_metrics(
                        channel_data, sampling_rate
                    )
                    print(
                        f"[Info] Channel {channel}: Quality Score = {quality_metrics[channel]['data_quality_score']:.1f}"
                    )

        # Generate visualizations
        topographic_map = self._generate_quality_topographic_map(quality_metrics)
        distribution_chart = self._generate_quality_distribution(quality_metrics)

        # Construct Payload
        result_payload = {
            "summary": self._generate_summary(quality_metrics, validated_params),
            "analysis_data": {
                "quality_metrics": quality_metrics,
                "channel_count": len(channel_cols),
            },
            "visualization_data": {
                "topographic_map": topographic_map,
                "plots": {
                    "topographic_map": topographic_map,  # <-- إضافة
                    "distribution_chart": distribution_chart,
                },
            },
        }

        # Attach Result to Data Object
        if not hasattr(data, "analysis_results"):
            data.analysis_results = {}

        data.analysis_results[self.id] = result_payload
        return data

    def _calculate_channel_metrics(
        self, channel_data: pd.Series, sampling_rate: float
    ) -> Dict[str, float]:
        """Calculate realistic quality metrics for a single channel"""
        if len(channel_data) < 10:
            return self._get_empty_metrics()

        try:
            # Basic statistics
            variance = np.var(channel_data)
            mean_amp = np.mean(np.abs(channel_data))
            kurtosis = stats.kurtosis(channel_data)
            skewness = stats.skew(channel_data)

            # More realistic SNR calculation
            snr = self._calculate_realistic_snr(channel_data, sampling_rate)

            # Line noise detection (50/60 Hz)
            line_noise_ratio = self._detect_line_noise(channel_data, sampling_rate)

            # Realistic quality score calculation
            quality_score = self._calculate_realistic_quality_score(
                variance, snr, kurtosis, skewness, line_noise_ratio, mean_amp
            )

            return {
                "data_quality_score": float(quality_score),
                "signal_to_noise_ratio": float(snr),
                "variance": float(variance),
                "mean_amplitude": float(mean_amp),
                "kurtosis": float(kurtosis),
                "skewness": float(skewness),
                "line_noise_ratio": float(line_noise_ratio),
            }

        except Exception as e:
            print(f"Error calculating metrics for channel: {e}")
            return self._get_empty_metrics()

    def _get_empty_metrics(self):
        return {
            "data_quality_score": 0.0,
            "signal_to_noise_ratio": 0.0,
            "variance": 0.0,
            "mean_amplitude": 0.0,
            "kurtosis": 0.0,
            "skewness": 0.0,
            "line_noise_ratio": 0.0,
        }

    def _calculate_realistic_snr(self, data: pd.Series, sampling_rate: float) -> float:
        """Calculate more realistic SNR using spectral analysis"""
        try:
            # Use Welch's method for PSD estimation
            freqs, psd = welch(data, fs=sampling_rate, nperseg=min(256, len(data)))

            # Signal power in EEG bands (1-40 Hz)
            eeg_bands = [(1, 4), (4, 8), (8, 13), (13, 30), (30, 40)]
            signal_power = 0
            for low, high in eeg_bands:
                band_mask = (freqs >= low) & (freqs <= high)
                if np.any(band_mask):
                    signal_power += np.trapz(psd[band_mask], freqs[band_mask])

            # Noise power in high frequencies (45-95 Hz, avoiding line noise)
            noise_mask = (freqs >= 45) & (freqs <= 95)
            if np.any(noise_mask):
                noise_power = np.trapz(psd[noise_mask], freqs[noise_mask])
            else:
                # Fallback: use frequencies above 40 Hz
                noise_mask = freqs >= 40
                if np.any(noise_mask):
                    noise_power = np.trapz(psd[noise_mask], freqs[noise_mask])
                else:
                    noise_power = np.median(psd) * (freqs[-1] - freqs[0])

            # Avoid division by zero
            if noise_power <= 0:
                noise_power = 1e-10
            if signal_power <= 0:
                signal_power = 1e-10

            snr = 10 * np.log10(signal_power / noise_power)

            # Cap SNR to realistic EEG range
            return max(min(snr, 30), -10)

        except Exception as e:
            print(f"SNR calculation error: {e}")
            # Simple fallback
            variance = np.var(data)
            if variance <= 0:
                return -10
            return 10 * np.log10(variance + 1e-10)

    def _detect_line_noise(self, data: pd.Series, sampling_rate: float) -> float:
        """Detect line noise (50/60 Hz) contamination"""
        try:
            freqs, psd = welch(data, fs=sampling_rate, nperseg=min(256, len(data)))

            line_freqs = [50, 60]
            line_noise_power = 0
            total_power = np.trapz(psd, freqs)

            for freq in line_freqs:
                # Look for peaks around line frequency
                freq_mask = (freqs >= freq - 1) & (freqs <= freq + 1)
                if np.any(freq_mask):
                    line_noise_power += np.max(psd[freq_mask])

            return line_noise_power / total_power if total_power > 0 else 0

        except Exception:
            return 0

    def _calculate_realistic_quality_score(
        self,
        variance: float,
        snr: float,
        kurtosis: float,
        skewness: float,
        line_noise_ratio: float,
        mean_amplitude: float,
    ) -> float:
        """Calculate realistic quality score (0-100) with more lenient thresholds"""

        # Handle edge cases
        if variance <= 0 or np.isnan(variance):
            return 0

        # 1. Variance score - much more lenient range
        log_variance = np.log10(variance + 1e-12)

        if log_variance < -15:
            var_score = 0
        elif log_variance > -2:
            var_score = 0
        else:
            var_score = 100 * (1 - min(abs(log_variance + 8) / 10, 1))

        # 2. SNR score - more realistic mapping
        if snr < -5:
            snr_score = 0
        elif snr > 20:
            snr_score = 100
        else:
            snr_score = (snr + 5) * 4

        # 3. Kurtosis - much more lenient
        excess_kurtosis = kurtosis
        if abs(excess_kurtosis) < 5:
            kurt_score = 100
        elif abs(excess_kurtosis) > 20:
            kurt_score = 0
        else:
            kurt_score = 100 - (abs(excess_kurtosis) - 5) * 6.67

        # 4. Skewness - much more lenient
        if abs(skewness) < 2:
            skew_score = 100
        elif abs(skewness) > 10:
            skew_score = 0
        else:
            skew_score = 100 - (abs(skewness) - 2) * 12.5

        # 5. Line noise penalty
        if line_noise_ratio < 0.1:
            line_score = 100
        elif line_noise_ratio > 0.5:
            line_score = 0
        else:
            line_score = 100 - (line_noise_ratio - 0.1) * 250

        # 6. Amplitude check
        if mean_amplitude < 1e-6:
            amp_score = 0
        elif mean_amplitude > 1000:
            amp_score = 0
        else:
            log_amp = np.log10(mean_amplitude + 1e-12)
            if -6 < log_amp < -2:
                amp_score = 100
            else:
                amp_score = 50

        # Weighted average - focus more on SNR and line noise
        quality_score = (
            var_score * 0.15
            + snr_score * 0.25
            + kurt_score * 0.10
            + skew_score * 0.10
            + line_score * 0.25
            + amp_score * 0.15
        )

        return max(0, min(100, quality_score))

    def _generate_summary(self, quality_metrics: Dict, parameters: Dict) -> Dict:
        """Generate analysis summary"""
        if not quality_metrics:
            return {}

        quality_scores = [
            metrics["data_quality_score"] for metrics in quality_metrics.values()
        ]
        threshold = float(parameters.get("quality_threshold", 50.0))

        good_channels = [
            chan
            for chan, metrics in quality_metrics.items()
            if metrics["data_quality_score"] >= threshold
        ]

        # Calculate additional statistics
        avg_snr = np.mean(
            [metrics["signal_to_noise_ratio"] for metrics in quality_metrics.values()]
        )
        avg_line_noise = np.mean(
            [metrics["line_noise_ratio"] for metrics in quality_metrics.values()]
        )

        return {
            "total_channels": len(quality_metrics),
            "good_channels": len(good_channels),
            "poor_channels": len(quality_metrics) - len(good_channels),
            "average_quality_score": float(np.mean(quality_scores)),
            "average_snr": float(avg_snr),
            "average_line_noise": float(avg_line_noise),
            "quality_threshold": threshold,
            "best_channel": max(
                quality_metrics.items(), key=lambda x: x[1]["data_quality_score"]
            )[0],
            "worst_channel": min(
                quality_metrics.items(), key=lambda x: x[1]["data_quality_score"]
            )[0],
            # Add standardized keys for Frontend
            "overall_quality_score": float(np.mean(quality_scores)),
            "quality_assessment": "Good" if np.mean(quality_scores) > 60 else "Poor",
        }

    def _generate_quality_topographic_map(self, quality_metrics: Dict) -> str:
        """Generate channel quality bar chart (UI-friendly)."""
        if not quality_metrics:
            return ""

        try:
            channels = list(quality_metrics.keys())
            quality_scores = [
                float(quality_metrics[ch].get("data_quality_score", 0.0))
                for ch in channels
            ]

            fig, ax = plt.subplots(figsize=(10, 4))  # أصغر شوية

            # color coding
            colors = [
                "green" if s >= 70 else "orange" if s >= 40 else "red"
                for s in quality_scores
            ]
            bars = ax.bar(
                channels,
                quality_scores,
                color=colors,
                alpha=0.85,
                edgecolor="black",
                linewidth=0.4,
            )

            ax.set_title("Channel Quality Scores", fontsize=13, fontweight="bold")
            ax.set_xlabel("Channels")
            ax.set_ylabel("Quality Score (0-100)")
            ax.set_ylim(0, 100)
            ax.grid(True, alpha=0.25, axis="y")

            # thresholds
            ax.axhline(y=70, linestyle="--", alpha=0.6, label="Good (≥70)")
            ax.axhline(y=40, linestyle="--", alpha=0.6, label="Acceptable (≥40)")
            ax.legend(fontsize=9)

            # لو القنوات كتير: ما نكتبش كل labels عشان متبقاش الصورة ضخمة
            n = len(channels)
            if n > 20:
                step = max(1, n // 12)  # حوالي 12 label بس
                xticks = np.arange(0, n, step)
                ax.set_xticks(xticks)
                ax.set_xticklabels(
                    [channels[i] for i in xticks], rotation=45, ha="right"
                )
            else:
                ax.tick_params(axis="x", rotation=45)

            # value labels (بس لو عدد القنوات مش كبير)
            if n <= 25:
                for bar, score in zip(bars, quality_scores):
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 1.5,
                        f"{score:.0f}",
                        ha="center",
                        va="bottom",
                        fontsize=8,
                    )

            plt.tight_layout()
            return self._plot_to_base64(fig)

        except Exception as e:
            print(f"Error generating quality bar chart: {e}")
            return ""

    def _generate_quality_distribution(self, quality_metrics: Dict) -> str:
        """Generate quality distribution chart (UI-friendly)."""
        if not quality_metrics:
            return ""

        try:
            quality_scores = [
                float(m.get("data_quality_score", 0.0))
                for m in quality_metrics.values()
            ]

            fig, ax = plt.subplots(figsize=(7, 4))
            ax.hist(
                quality_scores,
                bins=min(15, max(5, len(quality_scores) // 2)),
                alpha=0.75,
                edgecolor="black",
            )
            ax.set_title("Quality Score Distribution", fontsize=13, fontweight="bold")
            ax.set_xlabel("Quality Score")
            ax.set_ylabel("Number of Channels")
            ax.grid(True, alpha=0.25)

            mean_score = float(np.mean(quality_scores)) if quality_scores else 0.0
            ax.axvline(
                mean_score, linestyle="--", linewidth=2, label=f"Mean: {mean_score:.1f}"
            )
            ax.legend(fontsize=9)

            plt.tight_layout()
            return self._plot_to_base64(fig)

        except Exception as e:
            print(f"Error generating quality distribution: {e}")
            return ""

    def _plot_to_base64(self, fig) -> str:
        """Convert matplotlib plot to base64 string (smaller & more UI-friendly)."""
        buffer = BytesIO()
        # DPI أقل عشان حجم الصورة مايبقاش ضخم
        fig.savefig(buffer, format="png", dpi=80, bbox_inches="tight")
        buffer.seek(0)
        img_bytes = buffer.read()
        buffer.close()
        plt.close(fig)

        # base64
        img_str = base64.b64encode(img_bytes).decode("utf-8")
        return f"data:image/png;base64,{img_str}"


# Register
register_algorithm(QualityAnalysis())
