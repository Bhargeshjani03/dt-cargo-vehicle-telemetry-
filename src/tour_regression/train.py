"""Train and persist the DT-CARGO hybrid KMeans + Decision Tree model.

Run from the repository root:
    python -m src.tour_regression.train

Optional:
    python -m src.tour_regression.train --data path/to/dataset.csv
    python -m src.tour_regression.train --output path/to/model.joblib

The model uses Dataset B (75% unrecorded-time-ratio filter, without the
extreme-distance tail) by default. The target is log1p-transformed during
training and predictions are converted back with expm1 during inference.
"""

from __future__ import annotations

import argparse
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeRegressor

from .config import (
    CLUSTER_FEATURES,
    DECISION_TREE_PARAMS,
    DEFAULT_DATA_PATH,
    DEFAULT_MODEL_PATH,
    KMEANS_PARAMS,
    MODEL_VERSION,
    REGRESSION_FEATURES,
    TARGET_COLUMN,
)


def _load_training_data(data_path: Path) -> pd.DataFrame:
    if not data_path.is_file():
        raise FileNotFoundError(
            f"Training CSV not found: {data_path}\n"
            "Expected Dataset B at data/processed/tour_level/"
            "pca_experiments/input/experiment_B_75pct_without_extreme.csv."
        )

    data = pd.read_csv(data_path, low_memory=False)

    required = list(dict.fromkeys(
        [*REGRESSION_FEATURES, TARGET_COLUMN]
    ))
    missing = [column for column in required if column not in data.columns]
    if missing:
        raise ValueError(f"Training CSV is missing required columns: {missing}")

    # Only modeling columns are converted. IDs and diagnostic columns are
    # retained in the source CSV and are not used as model features.
    for column in required:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    data[required] = data[required].replace([np.inf, -np.inf], np.nan)

    before = len(data)
    data = data.dropna(subset=required).copy()

    # All features used by log1p-based clustering and the target must be
    # non-negative. Do not silently clip training rows into validity.
    nonnegative_columns = [*CLUSTER_FEATURES, "track_count", TARGET_COLUMN]
    invalid_mask = (data[nonnegative_columns] < 0).any(axis=1)
    invalid_count = int(invalid_mask.sum())
    if invalid_count:
        data = data.loc[~invalid_mask].copy()

    if len(data) < 100:
        raise ValueError(
            f"Only {len(data)} usable training rows remain; at least 100 are required."
        )

    if data["track_count"].le(0).any():
        raise ValueError("track_count must be greater than zero.")

    print(f"Loaded rows: {before:,}")
    print(f"Rows removed for missing/non-finite modeling values: {before - len(data) - invalid_count:,}")
    print(f"Rows removed for negative modeling values: {invalid_count:,}")
    print(f"Rows used for final fit: {len(data):,}")

    return data.reset_index(drop=True)


def _fit_clustering(data: pd.DataFrame) -> tuple[
    SimpleImputer, StandardScaler, KMeans, np.ndarray
]:
    """Fit the experiment's impute -> log1p -> scale -> KMeans flow."""
    raw = data[CLUSTER_FEATURES].astype(float)

    # Match the cross-validation cells: median imputation is fitted on the
    # raw distance/speed values, followed by log1p and StandardScaler.
    imputer = SimpleImputer(strategy="median")
    imputed = imputer.fit_transform(raw)
    logged = np.log1p(np.clip(imputed, 0, None))

    scaler = StandardScaler()
    scaled = scaler.fit_transform(logged)

    kmeans = KMeans(**KMEANS_PARAMS)
    labels = kmeans.fit_predict(scaled)

    return imputer, scaler, kmeans, labels


def train_model(data_path: Path, output_path: Path) -> dict[str, Any]:
    data = _load_training_data(data_path)

    imputer, scaler, kmeans, cluster_labels = _fit_clustering(data)

    # Cluster is an additional feature; it is not the regression target.
    X = data[REGRESSION_FEATURES].astype(float).copy()
    X["cluster"] = cluster_labels.astype(int)
    y_log = np.log1p(data[TARGET_COLUMN].to_numpy(dtype=float))

    regressor = DecisionTreeRegressor(**DECISION_TREE_PARAMS)
    regressor.fit(X, y_log)

    profiles = {}
    profile_frame = data.copy()
    profile_frame["cluster"] = cluster_labels

    for cluster_id, group in profile_frame.groupby("cluster", sort=True):
        profiles[int(cluster_id)] = {
            "tour_count": int(len(group)),
            "median_distance_km": float(group["total_distance_km"].median()),
            "median_speed_kmh": float(
                group["distance_based_avg_speed_kmh_clean"].median()
            ),
            "median_track_count": float(group["track_count"].median()),
            "median_elapsed_span_hours": float(
                group[TARGET_COLUMN].median()
            ),
        }

    # Derive descriptive names from fitted cluster profiles, rather than
    # assuming KMeans cluster IDs have a permanent semantic meaning.
    ordered_clusters = sorted(
        profiles,
        key=lambda cid: profiles[cid]["median_distance_km"],
        reverse=True,
    )
    cluster_names = {}
    if len(ordered_clusters) == 2:
        cluster_names[ordered_clusters[0]] = (
            "Longer-distance / higher-speed pattern"
        )
        cluster_names[ordered_clusters[1]] = (
            "Shorter-distance / lower-speed pattern"
        )
    else:
        cluster_names = {cid: f"Operational pattern {cid}" for cid in profiles}

    bundle = {
        "model_version": MODEL_VERSION,
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "training_data": str(data_path),
        "training_rows": int(len(data)),
        "cluster_features": list(CLUSTER_FEATURES),
        "regression_features": list(REGRESSION_FEATURES),
        "target": TARGET_COLUMN,
        "target_transform": "log1p; inverse with expm1",
        "cluster_transform": "median imputation -> log1p(nonnegative features) -> StandardScaler",
        "imputer": imputer,
        "scaler": scaler,
        "kmeans": kmeans,
        "regressor": regressor,
        "cluster_profiles": profiles,
        "cluster_names": cluster_names,
        "kmeans_params": dict(KMEANS_PARAMS),
        "decision_tree_params": dict(DECISION_TREE_PARAMS),
        "python_version": platform.python_version(),
        "scikit_learn_version": sklearn.__version__,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, output_path)

    print("\nCluster profiles:")
    print(json.dumps(profiles, indent=2))
    print(f"\nSaved model artifact: {output_path}")
    print(f"Model version: {MODEL_VERSION}")

    return bundle


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train DT-CARGO hybrid tour clustering-regression model."
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help="Dataset B CSV path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help="Output joblib artifact path.",
    )
    args = parser.parse_args()

    train_model(args.data, args.output)


if __name__ == "__main__":
    main()
