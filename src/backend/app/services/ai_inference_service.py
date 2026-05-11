import os
import torch
import numpy as np
from typing import Dict, Any, Optional

from app.services.temp_file_store_service import temp_file_store
from app.core.model_registry import get_model_pth_path, get_model_metadata
from app.models.eeg_data import EEGData
from app.pretrained_models.model_factory import get_model_class

from app.core.registry import get_algorithm
from app.services.csv_export_service import generate_csv_from_predictions


def run_ai_inference(
    config_id: str,
    model_id: str,
    apply_preprocessing: bool = False,
    label_mapping: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    # 1. Fetch Model Metadata & Path
    metadata = get_model_metadata(model_id)
    pth_path = get_model_pth_path(model_id)

    if not metadata or not pth_path or not os.path.exists(pth_path):
        raise ValueError(f"Model '{model_id}' is missing its JSON or .pth file.")

    # Extract dynamic requirements from the JSON contract
    reqs = metadata.get("requirements", {})
    req_channels = reqs.get("num_channels")
    req_time_points = reqs.get("time_points")
    classes_map = metadata.get("classes", [])
    architecture = metadata.get("architecture")
    pipeline_steps = metadata.get("preprocessing_pipeline", [])

    # 2. Fetch the Data
    file_info = temp_file_store.get(config_id)
    if not file_info:
        raise ValueError(f"Data configuration '{config_id}' not found.")

    eeg_data = EEGData.from_storage(file_info)

    # 3. PREPROCESSING PIPELINE
    if apply_preprocessing and pipeline_steps:
        print(f"Applying {len(pipeline_steps)} preprocessing steps for {model_id}...")
        for step in pipeline_steps:
            algo_id = step.get("id")
            algo_params = step.get("params", {})

            # Fetch it using your registry's helper function!
            algorithm = get_algorithm(algo_id)

            if algorithm:
                eeg_data = algorithm.process(eeg_data, **algo_params)
                print(f" -> Applied: {algorithm.name}")
            else:
                print(
                    f" [Warning] Algorithm '{algo_id}' required by model is not registered!"
                )

    # 4. Dynamic Validation
    actual_channels = eeg_data.get_num_channels()
    if actual_channels != req_channels:
        raise ValueError(
            f"Model requires {req_channels} channels, but data has {actual_channels}."
        )

    # 5. Shape the Data (Completely ignoring labels)
    has_labels_col = "labels" in eeg_data.df.columns
    grouped = eeg_data.df.groupby(["subject_id", "session_id", "trial_id"])

    tensor_list = []
    trial_info = []  # Track the composite keys for the UI

    for (sub_id, sess_id, trial_id), trial_df in grouped:
        actual_len = len(trial_df)

        # If too long -> Truncate
        if actual_len > req_time_points:
            channel_data = trial_df.iloc[:req_time_points][eeg_data.channel_cols].values

        # If too short -> Pad with Zeros
        elif actual_len < req_time_points:
            raw_data = trial_df[eeg_data.channel_cols].values
            padding_needed = req_time_points - actual_len
            zeros = np.zeros((padding_needed, actual_channels))
            channel_data = np.vstack((raw_data, zeros))  # Stack zeros to the end

        # If exactly right
        else:
            channel_data = trial_df[eeg_data.channel_cols].values

        # Transpose to match PyTorch (Channels, Time)
        channel_data = channel_data.T

        tensor_list.append(channel_data)

        true_label = None
        if has_labels_col:
            raw = trial_df["labels"].iloc[0]
            try:
                true_label = int(raw)
            except (ValueError, TypeError):
                true_label = None

        # Record the full tracking info
        trial_info.append(
            {
                "subject": sub_id,
                "session": sess_id,
                "trial": trial_id,
                "true_label": true_label,
            }
        )

    if not tensor_list:
        raise ValueError(
            "No valid trials found matching the model's required time points."
        )

    # Stack into a single batch: Shape becomes (Num_Trials, Channels, Time)
    input_tensor = torch.FloatTensor(np.array(tensor_list))

    # 6. Dynamically Instantiate the PyTorch Model
    ModelClass = get_model_class(architecture)
    model = ModelClass(num_channels=req_channels, num_classes=len(classes_map))

    # Load weights and set to eval mode (turns off dropout)
    model.load_state_dict(torch.load(pth_path, map_location=torch.device("cpu")))
    model.eval()

    # 7. Run the actual Prediction!
    with torch.no_grad():
        outputs = model(input_tensor)
        # Convert raw logits to percentages
        probabilities = torch.nn.functional.softmax(outputs, dim=1)
        # Get the highest percentage and its class index
        confidences, predicted_indices = torch.max(probabilities, dim=1)

    # 8. Map back using the dynamic JSON class array and the composite keys
    predictions_list = []
    for i, info in enumerate(trial_info):
        pred_idx = predicted_indices[i].item()
        predicted_class = (
            classes_map[pred_idx]
            if pred_idx < len(classes_map)
            else f"Class {pred_idx}"
        )
        conf_val = round(confidences[i].item() * 100, 2)

        item = {
            "subject": str(info["subject"]),
            "session": str(info["session"]),
            "trial": int(info["trial"]),
            "predictedClass": predicted_class,
            "confidence": conf_val,
        }

        # Attach true class if mapping is available
        if label_mapping and info["true_label"] is not None:
            true_class = label_mapping.get(str(info["true_label"]))
            if true_class:
                item["trueClass"] = true_class
                item["correct"] = true_class == predicted_class

        predictions_list.append(item)

    class_counts = {}
    total_conf = 0.0

    for pred in predictions_list:
        cls_name = pred["predictedClass"]
        class_counts[cls_name] = class_counts.get(cls_name, 0) + 1
        total_conf += pred["confidence"]

    avg_conf = round(total_conf / len(predictions_list), 2) if predictions_list else 0.0

    metrics = None
    if label_mapping and has_labels_col:
        try:
            from sklearn.metrics import (
                accuracy_score,
                f1_score,
                precision_score,
                recall_score,
                classification_report,
            )

            y_true = []
            y_pred = []
            for pred in predictions_list:
                if "trueClass" in pred:
                    y_true.append(pred["trueClass"])
                    y_pred.append(pred["predictedClass"])

            if y_true:
                all_classes = sorted(set(y_true + y_pred))
                report = classification_report(
                    y_true,
                    y_pred,
                    labels=all_classes,
                    output_dict=True,
                    zero_division=0,
                )
                metrics = {
                    "accuracy": round(accuracy_score(y_true, y_pred) * 100, 2),
                    "f1_score": round(
                        f1_score(y_true, y_pred, average="weighted", zero_division=0)
                        * 100,
                        2,
                    ),
                    "precision": round(
                        precision_score(
                            y_true, y_pred, average="weighted", zero_division=0
                        )
                        * 100,
                        2,
                    ),
                    "recall": round(
                        recall_score(
                            y_true, y_pred, average="weighted", zero_division=0
                        )
                        * 100,
                        2,
                    ),
                    "per_class": {
                        cls: {
                            "precision": round(vals["precision"] * 100, 2),
                            "recall": round(vals["recall"] * 100, 2),
                            "f1": round(vals["f1-score"] * 100, 2),
                            "support": int(vals["support"]),
                        }
                        for cls, vals in report.items()
                        if cls not in ("accuracy", "macro avg", "weighted avg")
                    },
                }
        except ImportError:
            print("[Warning] scikit-learn not installed — metrics skipped.")

    summary = {
        "total_trials_analyzed": len(predictions_list),
        "class_distribution": class_counts,
        "average_confidence": avg_conf,
    }
    print(metrics)
    if metrics:
        summary["metrics"] = metrics
    # Generate CSV and get result_id
    result_id = generate_csv_from_predictions(predictions_list, model_id=model_id)

    return {
        "status": "success",
        "model_used": model_id,
        "summary": summary,
        "predictions": predictions_list,
        "result_id": result_id,
    }
