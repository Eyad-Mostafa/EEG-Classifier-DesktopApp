import numpy as np
import pandas as pd
import mne
from app.schemas.domain_enum import DomainType
from app.algorithms.base import BaseStep, AlgorithmParameter
from app.models.eeg_data import EEGData
from app.core.registry import register_algorithm


def robust_mad(x, axis=None, eps=1e-12):
    """Median Absolute Deviation (robust std proxy)."""
    med = np.median(x, axis=axis, keepdims=True)
    mad = np.median(np.abs(x - med), axis=axis, keepdims=True)
    # 1.4826*MAD ~ std for normal distribution
    return med, 1.4826 * mad + eps


class ASRStepMNE(BaseStep):
    id = "asr_mne"
    name = "Artifact Subspace Reconstruction (ASR)"
    category = "Artifact Removal"
    domainType = DomainType.TIME
    type = "preprocessing"

    description = (
        "ASR-like cleaning: detects artifact windows using robust statistics, then "
        "reduces high-variance PCA components to reconstruct the signal."
    )

    parameters = [
        AlgorithmParameter(
            name="threshold",
            type="number",
            value="3.0",
            default="3.0",
            min=1.0,
            max=10.0,
            required=True,
            description="Robust z-score threshold on window RMS (artifact detection).",
        ),
        AlgorithmParameter(
            name="window_size",
            type="number",
            value="0.5",
            default="0.5",
            min=0.1,
            max=5.0,
            required=True,
            description="Window size in seconds.",
        ),
        AlgorithmParameter(
            name="max_bad_channels_ratio",
            type="number",
            value="0.25",
            default="0.25",
            min=0.0,
            max=1.0,
            required=True,
            description="If more than this ratio of channels are 'bad' in a window, treat it as artifact window.",
        ),
        AlgorithmParameter(
            name="pca_var_cap",
            type="number",
            value="3.0",
            default="3.0",
            min=1.0,
            max=10.0,
            required=True,
            description="Caps PCA component variance relative to median component variance.",
        ),
    ]

    def process(self, data: EEGData, **params) -> EEGData:
        threshold = float(params.get("threshold", 3.0))
        window_size = float(params.get("window_size", 0.5))
        max_bad_ratio = float(params.get("max_bad_channels_ratio", 0.25))
        pca_var_cap = float(params.get("pca_var_cap", 3.0))

        df_copy = data.df.copy()
        channel_cols = data.channel_cols
        sfreq = data.sampling_rate

        all_cleaned = []

        grouped = df_copy.groupby(["subject_id", "session_id", "trial_id"], sort=False)
        for _, trial_df in grouped:
            X = trial_df[channel_cols].values.T  # shape: (n_channels, n_samples)

            info = mne.create_info(ch_names=channel_cols, sfreq=sfreq, ch_types="eeg")
            raw = mne.io.RawArray(X, info, verbose=False)

            n_samples = raw.n_times
            win = max(2, int(window_size * sfreq))

            # -------- 1) Build robust baseline from the whole trial (median/MAD) --------
            # We measure RMS per channel over windows, then compute robust z-score.
            # baseline_rms_med/std are computed robustly across time windows.
            rms_list = []
            for start in range(0, n_samples, win):
                stop = min(start + win, n_samples)
                W = raw._data[:, start:stop]
                rms = np.sqrt(np.mean(W**2, axis=1))  # per-channel RMS
                rms_list.append(rms)
            rms_mat = np.stack(rms_list, axis=1)  # (n_channels, n_windows)

            rms_med, rms_robust_std = robust_mad(rms_mat, axis=1)  # per channel
            rms_med = rms_med.squeeze()
            rms_robust_std = rms_robust_std.squeeze()

            # -------- 2) Process window-by-window --------
            for start in range(0, n_samples, win):
                stop = min(start + win, n_samples)
                W = raw._data[:, start:stop]  # (ch, t)

                # ---- 2A) Detect artifact window using robust z on RMS ----
                rms = np.sqrt(np.mean(W**2, axis=1))
                z = np.abs((rms - rms_med) / rms_robust_std)

                bad_ch = z > threshold
                if np.mean(bad_ch) <= max_bad_ratio:
                    # window seems clean enough -> keep it unchanged
                    continue

                # ---- 2B) Reconstruct artifact window using PCA variance capping ----
                # Center
                Wc = W - W.mean(axis=1, keepdims=True)

                # PCA via SVD
                # Wc = U * S * Vt  (U: channels x channels, S: channels, Vt: channels x time)
                U, S, Vt = np.linalg.svd(Wc, full_matrices=False)

                # Component variances proportional to S^2
                comp_var = (S**2) / (Wc.shape[1] + 1e-12)
                med_var = np.median(comp_var)

                # Cap overly-large components
                cap = pca_var_cap * med_var
                comp_var_capped = np.minimum(comp_var, cap)

                # Convert back to capped singular values
                S_capped = np.sqrt(comp_var_capped * (Wc.shape[1] + 1e-12))

                # Reconstruct
                Wrec = (U * S_capped) @ Vt
                Wrec = Wrec + W.mean(axis=1, keepdims=True)

                raw._data[:, start:stop] = Wrec

            # -------- 3) Rebuild dataframe --------
            cleaned_trial = pd.DataFrame(
                raw.get_data().T, columns=channel_cols, index=trial_df.index
            )
            meta_cols = [c for c in trial_df.columns if c not in channel_cols]
            combined = pd.concat([trial_df[meta_cols], cleaned_trial], axis=1)
            all_cleaned.append(combined)

        final_df = pd.concat(all_cleaned, ignore_index=True)
        data.df = final_df
        data._time_data_cache = None
        data.meta["last_step"] = self.name
        data.meta["asr_params"] = {
            "threshold": threshold,
            "window_size": window_size,
            "max_bad_channels_ratio": max_bad_ratio,
            "pca_var_cap": pca_var_cap,
        }
        return data


register_algorithm(ASRStepMNE())
