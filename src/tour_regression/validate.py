
"""Held-out evaluation for DT-CARGO tour regression.

Run from the project root:

    python -m src.tour_regression.validate

Default split: 80% training / 20% testing.
All preprocessing, clustering and regression are fitted on training data only.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    median_absolute_error,
    r2_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeRegressor

from .config import (
    CLUSTER_FEATURES,
    DECISION_TREE_PARAMS,
    DEFAULT_DATA_PATH,
    KMEANS_PARAMS,
    MODEL_VERSION,
    REGRESSION_FEATURES,
    TARGET_COLUMN,
)
from .train import _load_training_data


def calculate_metrics(
    actual: np.ndarray,
    predicted: np.ndarray,
) -> dict[str, Any]:
    """Calculate regression metrics."""

    nonzero = actual != 0

    mape = None
    if nonzero.any():
        mape = float(
            np.mean(
                np.abs(
                    (actual[nonzero] - predicted[nonzero])
                    / actual[nonzero]
                )
            ) * 100
        )

    return {
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
        "mape_sample_count": int(nonzero.sum()),
        "mean_actual_hours": float(np.mean(actual)),
        "mean_predicted_hours": float(np.mean(predicted)),
    }


def assign_cluster_names(
    profiles: dict[int, dict[str, float]],
) -> dict[int, str]:
    """Generate descriptive cluster names from training profiles."""

    ordered = sorted(
        profiles,
        key=lambda cid: profiles[cid]["median_distance_km"],
        reverse=True,
    )

    if len(ordered) == 2:
        return {
            ordered[0]: "Longer-distance / higher-speed pattern",
            ordered[1]: "Shorter-distance / lower-speed pattern",
        }

    return {
        cid: f"Operational pattern {cid}"
        for cid in profiles
    }


def build_cluster_profiles(
    data: pd.DataFrame,
    labels: np.ndarray,
) -> dict[int, dict[str, float]]:
    """Build cluster profiles using training data only."""

    frame = data.copy()
    frame["cluster"] = labels

    profiles = {}

    for cluster_id, group in frame.groupby("cluster"):
        profiles[int(cluster_id)] = {
            "tour_count": int(len(group)),
            "median_distance_km": float(
                group["total_distance_km"].median()
            ),
            "median_speed_kmh": float(
                group["distance_based_avg_speed_kmh_clean"].median()
            ),
            "median_track_count": float(
                group["track_count"].median()
            ),
            "median_elapsed_span_hours": float(
                group[TARGET_COLUMN].median()
            ),
        }

    return profiles


def evaluate_split(
    actual: np.ndarray,
    predicted: np.ndarray,
) -> dict[str, Any]:
    """Calculate metrics and residual statistics."""

    metrics = calculate_metrics(actual, predicted)

    residuals = predicted - actual

    metrics["mean_error_hours"] = float(np.mean(residuals))
    metrics["maximum_absolute_error_hours"] = float(
        np.max(np.abs(residuals))
    )

    return metrics


def run_validation(
    data_path: Path,
    output_dir: Path,
    test_size: float = 0.20,
    random_state: int = 42,
) -> dict[str, Any]:

    print("\nDT-CARGO TOUR REGRESSION")
    print("HELD-OUT VALIDATION")
    print("=" * 60)

    # --------------------------------------------------
    # 1. Load and validate data
    # --------------------------------------------------

    print("\n[1/7] Loading dataset...")

    data = _load_training_data(data_path)

    print(f"Usable tours: {len(data):,}")

    # --------------------------------------------------
    # 2. Split before fitting any transformations
    # --------------------------------------------------

    print("\n[2/7] Creating train/test split...")

    train_data, test_data = train_test_split(
        data,
        test_size=test_size,
        random_state=random_state,
        shuffle=True,
    )

    train_data = train_data.copy()
    test_data = test_data.copy()

    print(f"Training tours: {len(train_data):,}")
    print(f"Testing tours : {len(test_data):,}")

    # --------------------------------------------------
    # 3. Fit clustering preprocessing on training data
    # --------------------------------------------------

    print("\n[3/7] Fitting clustering on training data only...")

    X_cluster_train = train_data[CLUSTER_FEATURES].astype(float)
    X_cluster_test = test_data[CLUSTER_FEATURES].astype(float)

    imputer = SimpleImputer(strategy="median")

    train_imputed = imputer.fit_transform(X_cluster_train)
    test_imputed = imputer.transform(X_cluster_test)

    train_logged = np.log1p(
        np.clip(train_imputed, 0, None)
    )
    test_logged = np.log1p(
        np.clip(test_imputed, 0, None)
    )

    scaler = StandardScaler()

    train_scaled = scaler.fit_transform(train_logged)
    test_scaled = scaler.transform(test_logged)

    kmeans = KMeans(**KMEANS_PARAMS)

    train_clusters = kmeans.fit_predict(train_scaled).astype(int)

    # Test clusters are assigned using the already-fitted K-Means.
    test_clusters = kmeans.predict(test_scaled).astype(int)

    print("K-Means fitted on training data.")
    print("Test tours assigned to existing training clusters.")

    # --------------------------------------------------
    # 4. Fit regression model on training data only
    # --------------------------------------------------

    print("\n[4/7] Training Decision Tree regressor...")

    X_train = train_data[REGRESSION_FEATURES].astype(float).copy()
    X_test = test_data[REGRESSION_FEATURES].astype(float).copy()

    X_train["cluster"] = train_clusters
    X_test["cluster"] = test_clusters

    y_train = train_data[TARGET_COLUMN].to_numpy(dtype=float)
    y_test = test_data[TARGET_COLUMN].to_numpy(dtype=float)

    y_train_log = np.log1p(y_train)

    regressor = DecisionTreeRegressor(**DECISION_TREE_PARAMS)

    regressor.fit(X_train, y_train_log)

    # --------------------------------------------------
    # 5. Generate predictions
    # --------------------------------------------------

    print("\n[5/7] Generating predictions...")

    train_predictions = np.expm1(
        regressor.predict(X_train)
    )
    test_predictions = np.expm1(
        regressor.predict(X_test)
    )

    train_predictions = np.maximum(train_predictions, 0)
    test_predictions = np.maximum(test_predictions, 0)

    # --------------------------------------------------
    # 6. Calculate train and test metrics
    # --------------------------------------------------

    print("\n[6/7] Calculating metrics...")

    train_metrics = evaluate_split(
        y_train,
        train_predictions,
    )

    test_metrics = evaluate_split(
        y_test,
        test_predictions,
    )

    profiles = build_cluster_profiles(
        train_data,
        train_clusters,
    )

    cluster_names = assign_cluster_names(profiles)

    # --------------------------------------------------
    # 7. Save outputs
    # --------------------------------------------------

    print("\n[7/7] Saving validation outputs...")

    output_dir.mkdir(parents=True, exist_ok=True)

    identifier_columns = [
        column
        for column in ["tour_id", "vehicle_id", "fleet_test_id"]
        if column in test_data.columns
    ]

    results = test_data[identifier_columns].copy()

    results["actual_elapsed_span_hours"] = y_test
    results["predicted_elapsed_span_hours"] = test_predictions
    results["predicted_elapsed_span_minutes"] = (
        test_predictions * 60
    )
    results["predicted_cluster_id"] = test_clusters
    results["predicted_cluster_name"] = [
        cluster_names[int(cid)] for cid in test_clusters
    ]

    results["prediction_error_hours"] = (
        test_predictions - y_test
    )

    results["absolute_error_hours"] = np.abs(
        results["prediction_error_hours"]
    )

    results["absolute_error_minutes"] = (
        results["absolute_error_hours"] * 60
    )

    results["absolute_percentage_error_pct"] = np.where(
        y_test != 0,
        np.abs((y_test - test_predictions) / y_test) * 100,
        np.nan,
    )

    # Save test predictions.
    predictions_path = output_dir / "holdout_predictions.csv"
    results.to_csv(predictions_path, index=False)

    # Save metrics.
    report = {
        "evaluation_type": "held_out_test_evaluation",
        "model_version": MODEL_VERSION,
        "evaluated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "dataset_path": str(data_path),
        "total_usable_tours": int(len(data)),
        "train_test_split": {
            "train_percentage": round((1 - test_size) * 100, 2),
            "test_percentage": round(test_size * 100, 2),
            "train_count": int(len(train_data)),
            "test_count": int(len(test_data)),
            "random_state": random_state,
        },
        "preprocessing": (
            "Median imputation, log1p and StandardScaler "
            "fitted on training data only."
        ),
        "clustering": (
            "K-Means fitted on training data only; "
            "test tours assigned using fitted K-Means."
        ),
        "regression": (
            "Decision Tree fitted on training data only "
            "using log1p-transformed elapsed span."
        ),
        "training_metrics": train_metrics,
        "test_metrics": test_metrics,
        "training_cluster_profiles": {
            str(cid): profile
            for cid, profile in profiles.items()
        },
        "training_cluster_names": {
            str(cid): name
            for cid, name in cluster_names.items()
        },
    }

    metrics_path = output_dir / "holdout_metrics.json"

    with open(metrics_path, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    # Test cluster-wise evaluation.
    results["cluster"] = test_clusters

    cluster_rows = []

    for cluster_id, group in results.groupby("cluster"):
        actual = group[
            "actual_elapsed_span_hours"
        ].to_numpy(dtype=float)

        predicted = group[
            "predicted_elapsed_span_hours"
        ].to_numpy(dtype=float)

        cluster_rows.append({
            "cluster_id": int(cluster_id),
            "cluster_name": cluster_names[int(cluster_id)],
            **evaluate_split(actual, predicted),
        })

    cluster_evaluation = pd.DataFrame(cluster_rows)

    cluster_path = output_dir / "holdout_cluster_evaluation.csv"
    cluster_evaluation.to_csv(cluster_path, index=False)

    # --------------------------------------------------
    # Display report
    # --------------------------------------------------

    print("\n" + "=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)

    print("\nTRAINING SET")
    for key in [
        "mae_hours",
        "rmse_hours",
        "r2_score",
    ]:
        print(f"{key:35s}: {train_metrics[key]:.4f}")

    print("\nHELD-OUT TEST SET")
    for key in [
        "mae_hours",
        "rmse_hours",
        "median_absolute_error_hours",
        "r2_score",
        "mape_percentage",
    ]:
        value = test_metrics[key]
        if value is not None:
            print(f"{key:35s}: {value:.4f}")
        else:
            print(f"{key:35s}: Not available")

    print("\nTEST CLUSTER PERFORMANCE")
    print(cluster_evaluation.to_string(index=False))

    print("\nOUTPUT FILES")
    print(f"Predictions : {predictions_path}")
    print(f"Metrics     : {metrics_path}")
    print(f"Clusters    : {cluster_path}")

    print("\nValidation completed successfully.")

    return report


def main() -> None:

    parser = argparse.ArgumentParser(
        description="Held-out validation of DT-CARGO tour regression."
    )

    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help="Tour-level dataset CSV path.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            Path(__file__).resolve().parent
            / "artifacts"
            / "holdout_validation"
        ),
        help="Directory for validation outputs.",
    )

    parser.add_argument(
        "--test-size",
        type=float,
        default=0.20,
        help="Fraction reserved for testing. Default: 0.20.",
    )

    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed for reproducible splitting.",
    )

    args = parser.parse_args()

    if not 0 < args.test_size < 1:
        parser.error("--test-size must be between 0 and 1.")

    run_validation(
        data_path=args.data,
        output_dir=args.output_dir,
        test_size=args.test_size,
        random_state=args.random_state,
    )


if __name__ == "__main__":
    main()
