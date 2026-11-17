
"""Evaluate the DT-CARGO hybrid tour regression model.

Run from the repository root:

    python -m src.tour_regression.evaluate

Optional:

    python -m src.tour_regression.evaluate --data path/to/dataset.csv
    python -m src.tour_regression.evaluate --model path/to/model.joblib
    python -m src.tour_regression.evaluate --output-dir path/to/output
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    median_absolute_error,
    r2_score,
)

from .config import (
    ARTIFACT_DIR,
    DEFAULT_DATA_PATH,
    DEFAULT_MODEL_PATH,
    TARGET_COLUMN,
    REGRESSION_FEATURES,
)

from .inference import TourRegressionPredictor
from .train import _load_training_data


def calculate_metrics(
    actual: np.ndarray,
    predicted: np.ndarray,
) -> dict[str, Any]:
    """Calculate regression evaluation metrics."""

    residuals = predicted - actual
    absolute_errors = np.abs(residuals)

    # MAPE is undefined when actual values are zero.
    nonzero_mask = actual != 0

    if nonzero_mask.any():
        mape = float(
            np.mean(
                np.abs(
                    (actual[nonzero_mask] - predicted[nonzero_mask])
                    / actual[nonzero_mask]
                )
            ) * 100
        )
    else:
        mape = None

    return {
        "evaluation_type": "training_set_evaluation",
        "evaluation_note": (
            "These are training-set metrics because the model "
            "was evaluated on the same dataset used for fitting."
        ),
        "sample_count": int(len(actual)),
        "mae_hours": float(mean_absolute_error(actual, predicted)),
        "rmse_hours": float(
            np.sqrt(mean_squared_error(actual, predicted))
        ),
        "median_absolute_error_hours": float(
            median_absolute_error(actual, predicted)
        ),
        "r2_score": float(r2_score(actual, predicted)),
        "mape_percentage": mape,
        "mape_sample_count": int(nonzero_mask.sum()),
        "mean_actual_hours": float(np.mean(actual)),
        "mean_predicted_hours": float(np.mean(predicted)),
        "mean_absolute_error_minutes": float(
            mean_absolute_error(actual, predicted) * 60
        ),
    }


def evaluate_model(
    data_path: Path,
    model_path: Path,
    output_dir: Path,
) -> dict[str, Any]:

    print("\nDT-CARGO TOUR REGRESSION EVALUATION")
    print("=" * 55)

    # --------------------------------------------------
    # 1. Load and validate dataset
    # --------------------------------------------------

    print("\n[1/5] Loading dataset...")

    data = _load_training_data(data_path)

    print(f"Usable tours: {len(data):,}")

    # Verify that all inference features exist.
    missing_features = [
        feature
        for feature in REGRESSION_FEATURES
        if feature not in data.columns
    ]

    if missing_features:
        raise ValueError(
            f"Missing regression features: {missing_features}"
        )

    # --------------------------------------------------
    # 2. Load trained model
    # --------------------------------------------------

    print("\n[2/5] Loading trained model...")

    predictor = TourRegressionPredictor(model_path)

    print(f"Model version: {predictor.model_version}")

    # --------------------------------------------------
    # 3. Generate predictions
    # --------------------------------------------------

    print("\n[3/5] Generating tour predictions...")

    model_inputs = data[REGRESSION_FEATURES].copy()

    predictions = predictor.predict_many(model_inputs)

    # Preserve original identifiers and actual target.
    identifier_columns = [
        column
        for column in ["tour_id", "vehicle_id", "fleet_test_id"]
        if column in data.columns
    ]

    results = data[
        identifier_columns + [TARGET_COLUMN]
    ].copy()

    results = results.rename(
        columns={
            TARGET_COLUMN: "actual_elapsed_span_hours"
        }
    )

    # Join predictions using the original row index.
    results = results.join(predictions)

    results = results.rename(
        columns={
            "predicted_elapsed_span_hours":
                "predicted_elapsed_span_hours",
            "predicted_elapsed_span_minutes":
                "predicted_elapsed_span_minutes",
            "cluster_id": "predicted_cluster_id",
            "cluster_name": "predicted_cluster_name",
        }
    )

    # --------------------------------------------------
    # 4. Calculate prediction errors and metrics
    # --------------------------------------------------

    print("\n[4/5] Calculating evaluation metrics...")

    actual = results[
        "actual_elapsed_span_hours"
    ].to_numpy(dtype=float)

    predicted = results[
        "predicted_elapsed_span_hours"
    ].to_numpy(dtype=float)

    results["prediction_error_hours"] = predicted - actual

    results["absolute_error_hours"] = np.abs(
        results["prediction_error_hours"]
    )

    results["absolute_error_minutes"] = (
        results["absolute_error_hours"] * 60
    )

    # Percentage error is undefined for zero actual values.
    results["absolute_percentage_error_pct"] = np.where(
        actual != 0,
        np.abs((actual - predicted) / actual) * 100,
        np.nan,
    )

    metrics = calculate_metrics(actual, predicted)

    metrics["model_version"] = predictor.model_version
    metrics["evaluated_at_utc"] = datetime.now(
        timezone.utc
    ).isoformat()

    # --------------------------------------------------
    # 5. Save evaluation outputs
    # --------------------------------------------------

    print("\n[5/5] Saving evaluation outputs...")

    output_dir.mkdir(parents=True, exist_ok=True)

    predictions_path = output_dir / "tour_predictions.csv"
    metrics_path = output_dir / "evaluation_metrics.json"
    cluster_path = output_dir / "cluster_evaluation.csv"

    # Main prediction dataset.
    results.to_csv(predictions_path, index=False)

    # Evaluation metrics.
    with open(metrics_path, "w", encoding="utf-8") as file:
        json.dump(metrics, file, indent=4)

    # Cluster-wise descriptive evaluation.
    cluster_metrics = (
        results.groupby(
            ["predicted_cluster_id", "predicted_cluster_name"],
            dropna=False,
        )
        .agg(
            tour_count=("actual_elapsed_span_hours", "size"),
            mean_actual_hours=(
                "actual_elapsed_span_hours", "mean"
            ),
            median_actual_hours=(
                "actual_elapsed_span_hours", "median"
            ),
            mean_predicted_hours=(
                "predicted_elapsed_span_hours", "mean"
            ),
            mae_hours=("absolute_error_hours", "mean"),
            median_absolute_error_hours=(
                "absolute_error_hours", "median"
            ),
        )
        .reset_index()
    )

    cluster_metrics.to_csv(cluster_path, index=False)

    # --------------------------------------------------
    # Display summary
    # --------------------------------------------------

    print("\n" + "=" * 55)
    print("EVALUATION RESULTS")
    print("=" * 55)

    print(f"Evaluated tours : {metrics['sample_count']:,}")
    print(f"MAE             : {metrics['mae_hours']:.4f} hours")
    print(f"RMSE            : {metrics['rmse_hours']:.4f} hours")
    print(
        "Median AE      : "
        f"{metrics['median_absolute_error_hours']:.4f} hours"
    )
    print(f"R2 Score        : {metrics['r2_score']:.4f}")

    if metrics["mape_percentage"] is not None:
        print(
            f"MAPE            : "
            f"{metrics['mape_percentage']:.2f}%"
        )
    else:
        print("MAPE            : Not available")

    print("\nCluster-wise evaluation:")
    print(cluster_metrics.to_string(index=False))

    print("\nSaved files:")
    print(f"Predictions : {predictions_path}")
    print(f"Metrics     : {metrics_path}")
    print(f"Clusters    : {cluster_path}")

    print("\nIMPORTANT:")
    print(
        "These are training-set evaluation metrics, "
        "not independent test-set performance."
    )

    print("\nEvaluation completed successfully.")

    return metrics


def main() -> None:

    parser = argparse.ArgumentParser(
        description="Evaluate DT-CARGO tour regression model."
    )

    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help="Tour-level dataset CSV path.",
    )

    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help="Trained model artifact path.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ARTIFACT_DIR,
        help="Directory for evaluation outputs.",
    )

    args = parser.parse_args()

    evaluate_model(
        data_path=args.data,
        model_path=args.model,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
