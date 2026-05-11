import numpy as np
import pandas as pd
import base64
import io
import math
import traceback
from matplotlib import pyplot as plt
import matplotlib
import matplotlib.gridspec as gridspec
from matplotlib.patches import Circle, Ellipse
from scipy.interpolate import griddata
from typing import Any, Dict, List, Optional, Tuple

matplotlib.use('Agg')

from app.core.registry import register_algorithm
from app.algorithms.base import BaseStep, AlgorithmParameter, AlgorithmExample
from app.models.eeg_data import EEGData
from app.schemas.domain_enum import DomainType


class DifferentialEntropyMethod(BaseStep):
    # 1. Identity & Metadata
    id = "differential_entropy"
    name = "Differential Entropy"
    description = "Compute differential entropy per trial for each EEG channel and generate topographic maps per condition"
    category = "Entropy Analysis"
    type = "analysis"
    domainType = DomainType.TIME
    allowedDomainTypes = [DomainType.TIME, DomainType.FREQUENCY, DomainType.TIME_FREQUENCY]

    howItWorks = """
    Differential entropy measures the uncertainty or randomness in continuous EEG signals.
    For normally distributed signals, it is calculated as: 0.5 * log(2πeσ²) where σ² is the variance.
    Computed per trial so that label/condition differences are preserved and visualized.
    Higher entropy indicates more complex, less predictable brain activity.
    """

    useCases = [
        "Assessing brain complexity and information processing",
        "Detecting neurological conditions affecting signal regularity",
        "Comparing cognitive states (resting vs. task) per label",
        "Monitoring anesthesia depth or sleep stages"
    ]

    relatedAlgorithms = [
        "sample_entropy",
        "approximate_entropy",
        "spectral_entropy"
    ]

    parameters = [
        AlgorithmParameter(
            name="normalize_output",
            type="boolean",
            value="true",
            default="true",
            description="Normalize entropy values to 0-1 range per label for better visualization"
        ),
        AlgorithmParameter(
            name="exclude_extreme_channels",
            type="boolean",
            value="true",
            default="true",
            description="Exclude channels with extremely low variance from analysis"
        ),
        AlgorithmParameter(
            name="variance_threshold",
            type="number",
            value="0.001",
            default="0.001",
            min=0.0001,
            max=1.0,
            description="Relative variance threshold (fraction of median) for valid channel analysis"
        )
    ]

    examples = [
        AlgorithmExample(
            title="Basic Entropy Analysis",
            description="Standard differential entropy calculation with default parameters",
            parameters={}
        ),
        AlgorithmExample(
            title="Comparative Study",
            description="Analyze entropy differences between conditions with normalization",
            parameters={
                "normalize_output": True,
                "exclude_extreme_channels": True
            }
        )
    ]

    # ──────────────────────────────────────────────────────────────────────────
    # MAIN PROCESS
    # ──────────────────────────────────────────────────────────────────────────
    def process(self, data: EEGData, **params) -> EEGData:
        """
        Trial-by-trial differential entropy computation.

        Flow:
        ──────────────────────────────────────────────────────────────────────
        1. Validate parameters.
        1b. [NEW] Resolve which channels to analyse:
              - If data.meta contains 'selected_channels' (set by the filter
                step when the user picked specific channels), restrict
                channel_cols to only those channels.
              - Fall back to all channel_cols if none of the user's selections
                exist in the dataframe.
        2. Compute a relative variance threshold across all channel data.
        3. Group data by (subject_id, session_id, trial_id).
        4. For each trial:
              For each channel:
                  a. Extract signal, drop NaNs.
                  b. Check variance against threshold.
                  c. Compute DE = 0.5 * log(2πe * σ²).
                  d. Store (trial_key, channel, label, de_value).
        5. Aggregate per channel per label:
              mean_de[label][channel] = mean of all trial DE values.
        6. Optionally normalize mean_de per label to [0, 1].
        7. Compute overall mean DE per channel (across all labels/trials).
        8. Build multi-panel visualization.
        9. Attach result payload to data.analysis_results[self.id].
        ──────────────────────────────────────────────────────────────────────
        """

        # ── Step 1: Parameters ────────────────────────────────────────────────
        validated_params   = self.validate_parameters(params)
        normalize_output   = validated_params.get("normalize_output", True)
        exclude_extreme    = validated_params.get("exclude_extreme_channels", True)
        variance_threshold = float(validated_params.get("variance_threshold", 0.001))

        # ── Step 1b [CHANGED]: Resolve channel list from user selection ────────
        #
        # WHY: The filter step saves the user's channel selection in
        #      data.meta["selected_channels"] as { channel_name: True/False }.
        #      We honour that selection here so the plots only show the
        #      channels the user cares about.
        #
        # HOW:
        #   1. Read data.meta["selected_channels"] if it exists.
        #   2. Keep only channels marked True AND present in the dataframe.
        #   3. If the intersection is empty (e.g. names don't match), fall back
        #      to the full data.channel_cols and log a warning.
        #
        all_channel_cols = data.channel_cols  # full list from EEGData

        selected_channels_meta: Dict[str, bool] = (
            (data.meta or {}).get("selected_channels", {})
        )

        if selected_channels_meta:
            # Channels the user explicitly turned ON
            user_selected = [
                ch for ch, is_on in selected_channels_meta.items()
                if is_on
            ]
            # Intersect with what actually exists in the dataframe
            channel_cols = [ch for ch in user_selected if ch in data.df.columns]

            if not channel_cols:
                # Selection doesn't match any real column — fall back gracefully
                print(
                    "[DifferentialEntropy] WARNING: selected_channels from meta "
                    "did not match any dataframe columns. "
                    f"Requested: {user_selected[:10]}... "
                    "Falling back to all available channels."
                )
                channel_cols = all_channel_cols
            else:
                print(
                    f"[DifferentialEntropy] Using {len(channel_cols)} user-selected "
                    f"channel(s): {channel_cols[:10]}{'...' if len(channel_cols) > 10 else ''}"
                )
        else:
            # No selection stored → use everything
            channel_cols = all_channel_cols
        # ── END OF CHANGE ─────────────────────────────────────────────────────

        has_labels = 'labels' in data.df.columns

        if not channel_cols:
            return self._error_result(data, "No channel columns found in dataframe.")

        # ── Step 2: Relative variance threshold ───────────────────────────────
        all_variances = {
            ch: float(np.var(data.df[ch].dropna().values))
            for ch in channel_cols
            if len(data.df[ch].dropna()) > 0
        }

        if not all_variances:
            return self._error_result(data, "All channels are empty or fully NaN.")

        median_variance    = float(np.median(list(all_variances.values())))
        relative_threshold = max(median_variance * variance_threshold, 1e-12)

        # ── Step 3 & 4: Trial-by-trial computation ────────────────────────────
        per_trial_records: List[Dict] = []
        skipped_channels_global = set()

        grouped = data.df.groupby(['subject_id', 'session_id', 'trial_id'])

        for (sub_id, sess_id, trial_id), trial_df in grouped:

            label = None
            if has_labels:
                raw = trial_df['labels'].iloc[0]
                try:
                    label = int(raw)
                except (ValueError, TypeError):
                    label = str(raw)

            for channel in channel_cols:          # ← now uses filtered list
                signal = trial_df[channel].dropna().values

                if len(signal) == 0:
                    continue

                variance = float(np.var(signal))

                if exclude_extreme and variance < relative_threshold:
                    skipped_channels_global.add(channel)
                    continue

                if variance <= 0:
                    continue

                de = 0.5 * np.log(2 * np.pi * np.e * variance)

                per_trial_records.append({
                    "subject": str(sub_id),
                    "session": str(sess_id),
                    "trial":   str(trial_id),
                    "label":   label,
                    "channel": channel,
                    "de":      float(de),
                })

        if not per_trial_records:
            return self._error_result(
                data,
                f"All channels excluded after variance filtering. "
                f"Median variance: {median_variance:.6f}. "
                "Try setting exclude_extreme_channels=false or lowering variance_threshold."
            )

        # ── Step 5: Aggregate per (label, channel) ───────────────────────────
        records_df = pd.DataFrame(per_trial_records)

        valid_channels = [ch for ch in channel_cols if ch in records_df['channel'].values]

        if has_labels:
            agg = (
                records_df
                .groupby(['label', 'channel'])['de']
                .agg(['mean', 'std', 'count'])
                .reset_index()
            )
            unique_labels = sorted(records_df['label'].dropna().unique().tolist())
        else:
            agg = (
                records_df
                .groupby(['channel'])['de']
                .agg(['mean', 'std', 'count'])
                .reset_index()
            )
            agg['label'] = 'all'
            unique_labels = ['all']

        mean_de_by_label: Dict[Any, Dict[str, float]] = {}
        std_de_by_label:  Dict[Any, Dict[str, float]] = {}

        for _, row in agg.iterrows():
            lbl = row['label']
            ch  = row['channel']
            mean_de_by_label.setdefault(lbl, {})[ch] = float(row['mean'])
            std_de_by_label.setdefault(lbl, {})[ch]  = float(row.get('std', 0.0) or 0.0)

        overall_mean_de: Dict[str, float] = (
            records_df.groupby('channel')['de'].mean().to_dict()
        )

        # ── Step 6: Normalize per label (optional) ────────────────────────────
        raw_mean_de_by_label = {
            lbl: dict(ch_map) for lbl, ch_map in mean_de_by_label.items()
        }

        if normalize_output:
            for lbl, ch_map in mean_de_by_label.items():
                vals = list(ch_map.values())
                if len(vals) > 1:
                    mn, mx = min(vals), max(vals)
                    if mx > mn:
                        mean_de_by_label[lbl] = {
                            ch: (v - mn) / (mx - mn) for ch, v in ch_map.items()
                        }

            vals = list(overall_mean_de.values())
            if len(vals) > 1:
                mn, mx = min(vals), max(vals)
                if mx > mn:
                    overall_mean_de = {
                        ch: (v - mn) / (mx - mn) for ch, v in overall_mean_de.items()
                    }

        # ── Step 6b [CHANGED]: Remap column names → real EEG channel names ──────
        #
        # WHY: The dataframe stores channels as generic column names like
        #      'channel_1', 'channel_2', etc. The filter step saves the user's
        #      human-readable mapping (e.g. channel_1 → "Fp1") inside
        #      data.meta["channel_mapping"].
        #      Without this remap, _create_channel_positions receives "channel_1"
        #      and strips it to "1" (a digit), so it falls back to placing the
        #      dot in an arbitrary circle instead of the correct scalp position.
        #
        # HOW: Build a rename dict  { "channel_1": "Fp1", ... }  from meta and
        #      apply it to every structure that carries channel keys:
        #        - valid_channels   (list)
        #        - overall_mean_de  (dict)
        #        - mean_de_by_label (nested dict)
        #        - raw_mean_de_by_label (nested dict)
        #        - std_de_by_label  (nested dict)
        #        - records_df       (the 'channel' column, needed for box plots)
        #      If no mapping is stored in meta, rename_map is empty and nothing
        #      changes — fully backward-compatible.
        #
        channel_mapping: Dict[str, str] = (data.meta or {}).get("channel_mapping", {})

        # channel_mapping may be  { "channel_1": "Fp1", "channel_2": "Fpz", … }
        # Build the lookup only for columns that are actually in our working set.
        rename_map: Dict[str, str] = {
            col: eeg_name
            for col, eeg_name in channel_mapping.items()
            if col in valid_channels          # only remap channels we computed
        }

        def _remap_key(key: str) -> str:
            return rename_map.get(key, key)

        if rename_map:
            print(
                f"[DifferentialEntropy] Remapping {len(rename_map)} column name(s) "
                f"to EEG names: {rename_map}"
            )

            # Remap valid_channels list
            valid_channels = [_remap_key(ch) for ch in valid_channels]

            # Remap overall_mean_de
            overall_mean_de = {_remap_key(ch): v for ch, v in overall_mean_de.items()}

            # Remap mean_de_by_label, raw_mean_de_by_label, std_de_by_label
            mean_de_by_label = {
                lbl: {_remap_key(ch): v for ch, v in ch_map.items()}
                for lbl, ch_map in mean_de_by_label.items()
            }
            raw_mean_de_by_label = {
                lbl: {_remap_key(ch): v for ch, v in ch_map.items()}
                for lbl, ch_map in raw_mean_de_by_label.items()
            }
            std_de_by_label = {
                lbl: {_remap_key(ch): v for ch, v in ch_map.items()}
                for lbl, ch_map in std_de_by_label.items()
            }

            # Remap the 'channel' column in records_df (used by box plots)
            records_df['channel'] = records_df['channel'].map(
                lambda c: rename_map.get(c, c)
            )

            # Also remap per_trial_records so the payload reflects real names
            for rec in per_trial_records:
                rec['channel'] = rename_map.get(rec['channel'], rec['channel'])
        # ── END OF CHANGE ─────────────────────────────────────────────────────

        # ── Step 7: Build visualization ───────────────────────────────────────
        visualization = self._generate_visualization(
            mean_de_by_label=mean_de_by_label,
            raw_mean_de_by_label=raw_mean_de_by_label,
            std_de_by_label=std_de_by_label,
            overall_mean_de=overall_mean_de,
            valid_channels=valid_channels,
            unique_labels=unique_labels,
            records_df=records_df,
            has_labels=has_labels,
        )

        # ── Step 8: Build result payload ──────────────────────────────────────
        all_raw_vals = [r['de'] for r in per_trial_records]

        result_payload = {
            "summary": {
                "total_channels":         len(valid_channels),
                "channels_analyzed":      valid_channels,
                "channels_skipped":       list(skipped_channels_global),
                "sampling_rate":          data.sampling_rate,
                "total_trials_processed": len(grouped),
                "labels_found":           unique_labels if has_labels else [],
                "parameters_used":        validated_params,
                "normalization_applied":  normalize_output,
                # ── [CHANGED] expose selection and remapping info ─────────────
                "user_selected_channels": list(selected_channels_meta.keys()) if selected_channels_meta else "all",
                "channel_name_mapping":   rename_map if rename_map else "none (columns already use EEG names)",
                "channels_skipped_eeg":   [_remap_key(ch) for ch in skipped_channels_global],
            },
            "analysis_data": {
                "entropy_values":   overall_mean_de,
                "entropy_by_label": {
                    str(lbl): ch_map
                    for lbl, ch_map in mean_de_by_label.items()
                },
                "per_trial": per_trial_records,
                "statistical_summary": {
                    "mean_entropy":  float(np.mean(all_raw_vals)),
                    "max_entropy":   float(np.max(all_raw_vals)),
                    "min_entropy":   float(np.min(all_raw_vals)),
                    "std_entropy":   float(np.std(all_raw_vals)),
                    "entropy_range": float(np.max(all_raw_vals) - np.min(all_raw_vals)),
                },
                "channel_information": {
                    "total_channels":     len(channel_cols),
                    "analyzed_channels":  len(valid_channels),
                    "available_channels": channel_cols,
                }
            },
            "visualization_data": {
                "topographic_map":    visualization,
                "visualization_type": "image/png",
            }
        }

        if not hasattr(data, 'analysis_results'):
            data.analysis_results = {}

        data.analysis_results[self.id] = result_payload
        return data

    # ──────────────────────────────────────────────────────────────────────────
    # VISUALIZATION
    # ──────────────────────────────────────────────────────────────────────────
    def _generate_visualization(
        self,
        mean_de_by_label:     Dict[Any, Dict[str, float]],
        raw_mean_de_by_label: Dict[Any, Dict[str, float]],
        std_de_by_label:      Dict[Any, Dict[str, float]],
        overall_mean_de:      Dict[str, float],
        valid_channels:       List[str],
        unique_labels:        List[Any],
        records_df:           pd.DataFrame,
        has_labels:           bool,
    ) -> Optional[str]:
        try:
            n_labels = len(unique_labels)

            if has_labels and n_labels >= 2:
                return self._figure_multi_label(
                    mean_de_by_label, raw_mean_de_by_label, std_de_by_label,
                    overall_mean_de, valid_channels, unique_labels, records_df
                )
            else:
                return self._figure_single(overall_mean_de, valid_channels)

        except Exception as e:
            print(f"[Error] Visualization failed: {e}")
            print(traceback.format_exc())
            return self._generate_fallback_plot(overall_mean_de, str(e))

    # ── Multi-label figure ────────────────────────────────────────────────────
    def _figure_multi_label(
        self,
        mean_de_by_label:     Dict,
        raw_mean_de_by_label: Dict,
        std_de_by_label:      Dict,
        overall_mean_de:      Dict,
        valid_channels:       List[str],
        unique_labels:        List,
        records_df:           pd.DataFrame,
    ) -> str:

        lbl_a, lbl_b = unique_labels[0], unique_labels[1]
        de_a = mean_de_by_label[lbl_a]
        de_b = mean_de_by_label[lbl_b]

        shared_channels = [ch for ch in valid_channels if ch in de_a and ch in de_b]
        diff_de = {ch: de_b[ch] - de_a[ch] for ch in shared_channels}

        fig = plt.figure(figsize=(28, 18))
        fig.patch.set_facecolor('#f8f9fa')

        gs = gridspec.GridSpec(
            2, 3,
            figure=fig,
            hspace=0.45,
            wspace=0.35,
            left=0.05, right=0.97,
            top=0.93, bottom=0.06,
        )

        ax_topo_a  = fig.add_subplot(gs[0, 0])
        ax_topo_b  = fig.add_subplot(gs[0, 1])
        ax_topo_d  = fig.add_subplot(gs[0, 2])
        ax_heatmap = fig.add_subplot(gs[1, 0])
        ax_box     = fig.add_subplot(gs[1, 1])
        ax_stats   = fig.add_subplot(gs[1, 2])

        all_vals = list(de_a.values()) + list(de_b.values())
        vmin_shared, vmax_shared = min(all_vals), max(all_vals)

        self._draw_topomap(
            ax_topo_a, de_a, valid_channels,
            title=f'Label {lbl_a}  —  Mean DE',
            cmap='viridis',
            vmin=vmin_shared, vmax=vmax_shared,
            show_colorbar=True,
        )
        self._draw_topomap(
            ax_topo_b, de_b, valid_channels,
            title=f'Label {lbl_b}  —  Mean DE',
            cmap='viridis',
            vmin=vmin_shared, vmax=vmax_shared,
            show_colorbar=True,
        )

        if diff_de:
            abs_max = max(abs(v) for v in diff_de.values()) or 1.0
            self._draw_topomap(
                ax_topo_d, diff_de, shared_channels,
                title=f'Difference  (Label {lbl_b} − Label {lbl_a})',
                cmap='RdBu_r',
                vmin=-abs_max, vmax=abs_max,
                show_colorbar=True,
            )
        else:
            ax_topo_d.text(0.5, 0.5, 'No shared channels\nfor difference map',
                           ha='center', va='center', transform=ax_topo_d.transAxes)
            ax_topo_d.axis('off')

        sorted_channels = sorted(
            shared_channels,
            key=lambda ch: diff_de.get(ch, 0),
            reverse=True
        )[:20]

        heatmap_data = np.array([
            [mean_de_by_label[lbl].get(ch, np.nan) for lbl in unique_labels]
            for ch in sorted_channels
        ])

        im = ax_heatmap.imshow(
            heatmap_data,
            aspect='auto',
            cmap='viridis',
            interpolation='nearest',
        )
        plt.colorbar(im, ax=ax_heatmap, shrink=0.8, label='Mean DE')
        ax_heatmap.set_xticks(range(len(unique_labels)))
        ax_heatmap.set_xticklabels([f'Label {l}' for l in unique_labels], fontsize=10)
        ax_heatmap.set_yticks(range(len(sorted_channels)))
        ax_heatmap.set_yticklabels(
            [self._get_short_channel_name(ch) for ch in sorted_channels], fontsize=8
        )
        ax_heatmap.set_title('Channel × Label Heatmap\n(top 20 most discriminating channels)', fontsize=13, fontweight='bold')
        ax_heatmap.set_xlabel('Label', fontsize=11)
        ax_heatmap.set_ylabel('Channel  (sorted by |diff|)', fontsize=11)

        top_disc_channels = sorted(
            shared_channels,
            key=lambda ch: abs(diff_de.get(ch, 0)),
            reverse=True
        )[:8]

        box_positions  = []
        box_data       = []
        box_colors     = []
        box_labels_txt = []
        color_map      = plt.cm.Set2(np.linspace(0, 1, len(unique_labels)))

        for i, ch in enumerate(top_disc_channels):
            short = self._get_short_channel_name(ch)
            for j, lbl in enumerate(unique_labels[:4]):
                subset = records_df[
                    (records_df['channel'] == ch) & (records_df['label'] == lbl)
                ]['de'].dropna().values
                if len(subset) > 0:
                    pos = i * (len(unique_labels[:4]) + 1) + j
                    box_positions.append(pos)
                    box_data.append(subset)
                    box_colors.append(color_map[j])
                    box_labels_txt.append(f'{short}\nL{lbl}')

        if box_data:
            bp = ax_box.boxplot(
                box_data,
                positions=box_positions,
                widths=0.6,
                patch_artist=True,
                notch=False,
                showfliers=True,
                flierprops=dict(marker='o', markersize=3, alpha=0.4),
                medianprops=dict(color='black', linewidth=2),
            )
            for patch, color in zip(bp['boxes'], box_colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)

            ax_box.set_xticks(box_positions)
            ax_box.set_xticklabels(box_labels_txt, fontsize=7, rotation=45, ha='right')

        ax_box.set_title('DE Distribution per Trial\n(top 8 discriminating channels)', fontsize=13, fontweight='bold')
        ax_box.set_ylabel('Differential Entropy', fontsize=11)
        ax_box.grid(True, alpha=0.3, axis='y')
        ax_box.set_facecolor('#fdfdfd')

        ax_stats.axis('off')
        stats_lines = ["Statistical Summary\n" + "─" * 28]
        for lbl in unique_labels[:6]:
            ch_map = raw_mean_de_by_label.get(lbl, {})
            vals   = list(ch_map.values())
            if vals:
                stats_lines.append(
                    f"Label {lbl}\n"
                    f"  Mean : {np.mean(vals):.4f}\n"
                    f"  Std  : {np.std(vals):.4f}\n"
                    f"  Max  : {np.max(vals):.4f}\n"
                    f"  Min  : {np.min(vals):.4f}\n"
                )

        if diff_de:
            diff_vals = list(diff_de.values())
            stats_lines.append(
                f"Difference (B−A)\n"
                f"  Max  : {np.max(diff_vals):.4f}\n"
                f"  Min  : {np.min(diff_vals):.4f}\n"
                f"  Mean : {np.mean(diff_vals):.4f}"
            )

        ax_stats.text(
            0.05, 0.95, '\n'.join(stats_lines),
            transform=ax_stats.transAxes,
            fontsize=10, fontfamily='monospace',
            verticalalignment='top',
            bbox=dict(boxstyle="round,pad=0.6", facecolor="#e8f4f8", alpha=0.85, lw=0.5)
        )
        ax_stats.set_title('Summary', fontsize=13, fontweight='bold')

        fig.suptitle('Differential Entropy Analysis  —  Trial-by-Trial', fontsize=20, fontweight='bold', y=0.98)

        return self._fig_to_base64(fig)

    # ── Single-label / no-label figure ───────────────────────────────────────
    def _figure_single(
        self,
        overall_mean_de: Dict[str, float],
        valid_channels:  List[str],
    ) -> str:
        fig = plt.figure(figsize=(24, 10))
        fig.patch.set_facecolor('#f8f9fa')

        gs = gridspec.GridSpec(1, 3, figure=fig, wspace=0.35, left=0.05, right=0.97)
        ax_topo = fig.add_subplot(gs[0, 0:2])
        ax_bar  = fig.add_subplot(gs[0, 2])

        self._draw_topomap(ax_topo, overall_mean_de, valid_channels,
                           title='Differential Entropy  —  Overall Mean', cmap='viridis',
                           show_colorbar=True)

        channels_sorted = sorted(overall_mean_de.items(), key=lambda x: x[1], reverse=True)[:12]
        names  = [self._get_short_channel_name(ch) for ch, _ in channels_sorted]
        values = [v for _, v in channels_sorted]

        bars = ax_bar.barh(names, values, color='steelblue', alpha=0.75)
        ax_bar.set_title('Top Channels by Mean DE', fontsize=14, fontweight='bold')
        ax_bar.set_xlabel('Differential Entropy', fontsize=12)
        ax_bar.grid(True, alpha=0.3, axis='x')
        for bar, val in zip(bars, values):
            ax_bar.text(bar.get_width() + 0.005, bar.get_y() + bar.get_height() / 2,
                        f'{val:.3f}', va='center', fontsize=9)

        fig.suptitle('Differential Entropy Analysis', fontsize=18, fontweight='bold')
        return self._fig_to_base64(fig)

    # ──────────────────────────────────────────────────────────────────────────
    # TOPOMAP HELPER
    # ──────────────────────────────────────────────────────────────────────────
    def _draw_topomap(
        self,
        ax,
        entropy_values: Dict[str, float],
        channel_names:  List[str],
        title:          str,
        cmap:           str = 'viridis',
        vmin:           float = None,
        vmax:           float = None,
        show_colorbar:  bool  = True,
    ):
        positions = self._create_channel_positions(channel_names)

        if not positions:
            ax.text(0.5, 0.5, 'Cannot map channels\nto standard positions',
                    ha='center', va='center', transform=ax.transAxes, fontsize=12)
            ax.set_title(title, fontsize=13, fontweight='bold')
            return

        plot_channels = [ch for ch in positions if ch in entropy_values]
        if not plot_channels:
            ax.text(0.5, 0.5, 'No data to display', ha='center', va='center',
                    transform=ax.transAxes)
            ax.set_title(title, fontsize=13, fontweight='bold')
            return

        x_coords = [positions[ch][0] for ch in plot_channels]
        y_coords = [positions[ch][1] for ch in plot_channels]
        de_vals  = [entropy_values[ch] for ch in plot_channels]

        grid_x, grid_y = np.mgrid[-1:1:100j, -1:1:100j]
        grid_z = griddata(
            list(zip(x_coords, y_coords)), de_vals,
            (grid_x, grid_y),
            method='cubic',
            fill_value=np.mean(de_vals)
        )

        kwargs = dict(cmap=cmap, alpha=0.75)
        if vmin is not None:
            kwargs['vmin'] = vmin
        if vmax is not None:
            kwargs['vmax'] = vmax

        contour = ax.contourf(grid_x, grid_y, grid_z, levels=50, **kwargs)
        ax.scatter(x_coords, y_coords, c=de_vals, cmap=cmap,
                   s=120, edgecolors='white', linewidth=1.5, alpha=0.95,
                   vmin=kwargs.get('vmin'), vmax=kwargs.get('vmax'), zorder=3)

        if show_colorbar:
            plt.colorbar(contour, ax=ax, shrink=0.75, pad=0.02)

        for ch in plot_channels:
            x, y  = positions[ch]
            short = self._get_short_channel_name(ch)
            ax.annotate(
                f'{short}', (x, y),
                xytext=(0, 8), textcoords='offset points',
                fontsize=7, ha='center', va='bottom',
                bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.8, lw=0.3),
                zorder=4,
            )

        head = Circle((0, 0), 0.95, fill=False, linewidth=2.5, color='#333', zorder=5)
        ax.add_patch(head)
        ax.plot([-0.08, 0, 0.08], [0.95, 1.08, 0.95], color='#333', linewidth=2, zorder=5)
        for sign in (-1, 1):
            ear = Ellipse((sign * 0.95, 0), 0.18, 0.36,
                          fill=False, linewidth=2, color='#333', zorder=5)
            ax.add_patch(ear)

        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-1.2, 1.2)
        ax.set_aspect('equal')
        ax.set_title(title, fontsize=13, fontweight='bold', pad=10)
        ax.axis('off')

    # ──────────────────────────────────────────────────────────────────────────
    # UTILITIES
    # ──────────────────────────────────────────────────────────────────────────
    def _fig_to_base64(self, fig) -> str:
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                    facecolor=fig.get_facecolor(), edgecolor='none')
        buffer.seek(0)
        encoded = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close(fig)
        return f"data:image/png;base64,{encoded}"

    def _error_result(self, data: EEGData, message: str) -> EEGData:
        if not hasattr(data, 'analysis_results'):
            data.analysis_results = {}
        data.analysis_results[self.id] = {
            "summary":            {"processing_error": message},
            "analysis_data":      None,
            "visualization_data": None,
        }
        return data

    def _create_channel_positions(self, channel_names: List[str]) -> Dict[str, Tuple[float, float]]:
        positions = {}
        standard_mapping = {
            'Fp1': (-0.3, 0.8),   'Fpz': (0.0, 0.8),   'Fp2': (0.3, 0.8),
            'AF7': (-0.5, 0.7),   'AF3': (-0.25, 0.7),  'AFz': (0.0, 0.7),
            'AF4': (0.25, 0.7),   'AF8': (0.5, 0.7),
            'F7':  (-0.7, 0.5),   'F5':  (-0.5, 0.5),   'F3':  (-0.3, 0.5),
            'F1':  (-0.15, 0.5),  'Fz':  (0.0, 0.5),    'F2':  (0.15, 0.5),
            'F4':  (0.3, 0.5),    'F6':  (0.5, 0.5),    'F8':  (0.7, 0.5),
            'FT7': (-0.8, 0.3),   'FC5': (-0.6, 0.3),   'FC3': (-0.4, 0.3),
            'FC1': (-0.2, 0.3),   'FCz': (0.0, 0.3),    'FC2': (0.2, 0.3),
            'FC4': (0.4, 0.3),    'FC6': (0.6, 0.3),    'FT8': (0.8, 0.3),
            'T7':  (-0.9, 0.1),   'C5':  (-0.7, 0.1),   'C3':  (-0.5, 0.1),
            'C1':  (-0.25, 0.1),  'Cz':  (0.0, 0.1),    'C2':  (0.25, 0.1),
            'C4':  (0.5, 0.1),    'C6':  (0.7, 0.1),    'T8':  (0.9, 0.1),
            'TP7': (-0.9, -0.1),  'CP5': (-0.7, -0.1),  'CP3': (-0.5, -0.1),
            'CP1': (-0.25, -0.1), 'CPz': (0.0, -0.1),   'CP2': (0.25, -0.1),
            'CP4': (0.5, -0.1),   'CP6': (0.7, -0.1),   'TP8': (0.9, -0.1),
            'P7':  (-0.8, -0.3),  'P5':  (-0.6, -0.3),  'P3':  (-0.4, -0.3),
            'P1':  (-0.2, -0.3),  'Pz':  (0.0, -0.3),   'P2':  (0.2, -0.3),
            'P4':  (0.4, -0.3),   'P6':  (0.6, -0.3),   'P8':  (0.8, -0.3),
            'PO7': (-0.6, -0.5),  'PO5': (-0.45, -0.5), 'PO3': (-0.3, -0.5),
            'POz': (0.0, -0.5),   'PO4': (0.3, -0.5),   'PO6': (0.45, -0.5),
            'PO8': (0.6, -0.5),
            'O1':  (-0.3, -0.7),  'Oz':  (0.0, -0.7),   'O2':  (0.3, -0.7),
            'A1':  (-1.0, 0.0),   'A2':  (1.0, 0.0),
        }

        for channel in channel_names:
            clean = channel.replace('channel_', '').replace('ch_', '').replace('CH', '')

            if clean in standard_mapping:
                positions[channel] = standard_mapping[clean]
            else:
                upper_match = [k for k in standard_mapping if k.upper() == clean.upper()]
                if upper_match:
                    positions[channel] = standard_mapping[upper_match[0]]
                elif clean.isdigit():
                    ch_num = int(clean)
                    total  = len(channel_names)
                    angle  = 2 * math.pi * ch_num / total
                    r      = 0.8 - (0.3 * ch_num / total)
                    positions[channel] = (r * math.cos(angle), r * math.sin(angle))

        if not positions:
            total = len(channel_names)
            for i, ch in enumerate(channel_names):
                angle = 2 * math.pi * i / total
                positions[ch] = (0.7 * math.cos(angle), 0.7 * math.sin(angle))

        return positions

    def _get_short_channel_name(self, channel_name: str) -> str:
        if channel_name.startswith('channel_'):
            return channel_name.replace('channel_', 'Ch')
        return channel_name if len(channel_name) <= 6 else channel_name[:6] + '..'

    def _generate_fallback_plot(self, entropy_values: Dict[str, float], error_message: str) -> Optional[str]:
        try:
            fig, ax = plt.subplots(figsize=(16, 6))
            channels = list(entropy_values.keys())
            values   = list(entropy_values.values())
            short    = [self._get_short_channel_name(ch) for ch in channels]

            bars = ax.bar(short, values, color='steelblue', alpha=0.7)
            ax.set_title(f'Differential Entropy  (fallback — topomap error)\n{error_message[:80]}',
                         fontsize=12, fontweight='bold')
            ax.set_xlabel('Channel')
            ax.set_ylabel('Differential Entropy')
            ax.tick_params(axis='x', rotation=45)
            ax.grid(True, alpha=0.3, axis='y')

            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                        f'{val:.3f}', ha='center', va='bottom', fontsize=8)

            plt.tight_layout()
            return self._fig_to_base64(fig)
        except Exception:
            return None


# Register
register_algorithm(DifferentialEntropyMethod())