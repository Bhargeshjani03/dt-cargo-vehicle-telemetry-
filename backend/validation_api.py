
from pathlib import Path
from typing import Any

import json
import joblib
import numpy as np
import pandas as pd

from fastapi import APIRouter, HTTPException, Query


router = APIRouter(
    prefix="/api/regression/validation",
    tags=["Tour Regression Validation"],
)

# Project structure:
# project/
#   backend/
#       main.py
#       validation_api.py
#   src/
#       tour_regression/
#           artifacts/
#               hybrid_tour_regression.joblib
#               holdout_validation/
#                   holdout_metrics.json
#                   holdout_predictions.csv
#                   holdout_cluster_evaluation.csv

PROJECT_ROOT = Path(__file__).resolve().parents[1]

ARTIFACT_DIR = (
    PROJECT_ROOT
    / "src"
    / "tour_regression"
    / "artifacts"
)

VALIDATION_DIR = ARTIFACT_DIR / "holdout_validation"

MODEL_FILE = ARTIFACT_DIR / "hybrid_tour_regression.joblib"

METRICS_FILE = VALIDATION_DIR / "holdout_metrics.json"
PREDICTIONS_FILE = VALIDATION_DIR / "holdout_predictions.csv"
CLUSTERS_FILE = VALIDATION_DIR / "holdout_cluster_evaluation.csv"


def require_file(path: Path):
    if not path.is_file():
        raise HTTPException(
            status_code=503,
            detail=f"Required validation artifact not found: {path}",
        )


def read_metrics() -> dict:
    require_file(METRICS_FILE)

    try:
        with METRICS_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not read validation metrics: {exc}",
        )


def read_predictions() -> pd.DataFrame:
    require_file(PREDICTIONS_FILE)

    try:
        data = pd.read_csv(
            PREDICTIONS_FILE,
            low_memory=False,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not read holdout predictions: {exc}",
        )

    required = [
        "tour_id",
        "vehicle_id",
        "fleet_test_id",
        "actual_elapsed_span_hours",
        "predicted_elapsed_span_hours",
        "predicted_elapsed_span_minutes",
        "predicted_cluster_id",
        "predicted_cluster_name",
        "prediction_error_hours",
        "absolute_error_hours",
        "absolute_error_minutes",
        "absolute_percentage_error_pct",
    ]

    missing = [
        column for column in required
        if column not in data.columns
    ]

    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Holdout predictions are missing columns: {missing}",
        )

    return data


def read_clusters() -> pd.DataFrame:
    require_file(CLUSTERS_FILE)

    try:
        data = pd.read_csv(CLUSTERS_FILE)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not read cluster evaluation: {exc}",
        )

    required = [
        "cluster_id",
        "cluster_name",
        "sample_count",
        "mae_hours",
        "rmse_hours",
        "median_absolute_error_hours",
        "r2_score",
        "mape_percentage",
        "mean_actual_hours",
        "mean_predicted_hours",
        "mean_error_hours",
        "maximum_absolute_error_hours",
    ]

    missing = [
        column for column in required
        if column not in data.columns
    ]

    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Cluster evaluation is missing columns: {missing}",
        )

    return data


def json_safe(value: Any):
    """Convert NumPy and pandas values into JSON-compatible values."""

    if isinstance(value, dict):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]

    if isinstance(value, np.ndarray):
        return value.tolist()

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.floating):
        return float(value)

    if isinstance(value, np.bool_):
        return bool(value)

    if pd.isna(value):
        return None

    return value


# ---------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------

@router.get("/summary")
def validation_summary():
    metrics = read_metrics()

    return {
        "evaluation_type": metrics.get("evaluation_type"),
        "model_version": metrics.get("model_version"),
        "evaluated_at_utc": metrics.get("evaluated_at_utc"),
        "total_usable_tours": metrics.get("total_usable_tours"),
        "train_test_split": metrics.get("train_test_split"),
        "preprocessing": metrics.get("preprocessing"),
        "clustering": metrics.get("clustering"),
        "regression": metrics.get("regression"),
        "training_metrics": metrics.get("training_metrics"),
        "test_metrics": metrics.get("test_metrics"),
        "training_cluster_profiles": metrics.get(
            "training_cluster_profiles"
        ),
        "training_cluster_names": metrics.get(
            "training_cluster_names"
        ),
    }


# ---------------------------------------------------------
# HOLDOUT PREDICTIONS
# ---------------------------------------------------------

@router.get("/predictions")
def validation_predictions(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    sort_by_error: bool = True,
):
    data = read_predictions()

    if sort_by_error:
        data = data.sort_values(
            "absolute_error_hours",
            ascending=False,
        )

    total = len(data)
    start = (page - 1) * page_size
    end = start + page_size

    selected = data.iloc[start:end].copy()

    selected = selected.replace(
        [np.inf, -np.inf],
        np.nan,
    )

    selected = selected.astype(object).where(
        pd.notna(selected),
        None,
    )

    return {
        "page": page,
        "page_size": page_size,
        "total_records": total,
        "total_pages": (total + page_size - 1) // page_size,
        "records": selected.to_dict(orient="records"),
    }


# ---------------------------------------------------------
# CLUSTER-WISE EVALUATION
# ---------------------------------------------------------

@router.get("/clusters")
def validation_clusters():
    data = read_clusters()

    data = data.replace(
        [np.inf, -np.inf],
        np.nan,
    )

    data = data.astype(object).where(
        pd.notna(data),
        None,
    )

    return data.to_dict(orient="records")


# ---------------------------------------------------------
# ABSOLUTE ERROR DISTRIBUTION
# ---------------------------------------------------------

@router.get("/error-distribution")
def error_distribution():
    data = read_predictions()

    errors = pd.to_numeric(
        data["absolute_error_hours"],
        errors="coerce",
    ).dropna()

    bins = [
        0,
        0.25,
        0.5,
        1,
        2,
        4,
        8,
        16,
        32,
        64,
        128,
        float("inf"),
    ]

    labels = [
        "0–15 min",
        "15–30 min",
        "30–60 min",
        "1–2 hours",
        "2–4 hours",
        "4–8 hours",
        "8–16 hours",
        "16–32 hours",
        "32–64 hours",
        "64–128 hours",
        "Above 128 hours",
    ]

    categories = pd.cut(
        errors,
        bins=bins,
        labels=labels,
        include_lowest=True,
        right=True,
    )

    counts = categories.value_counts(
        sort=False,
    )

    return [
        {
            "error_range": str(label),
            "count": int(counts.get(label, 0)),
        }
        for label in labels
    ]


# ---------------------------------------------------------
# ERROR BY ACTUAL TOUR DURATION
# ---------------------------------------------------------

@router.get("/duration-reliability")
def duration_reliability():
    data = read_predictions()

    actual = pd.to_numeric(
        data["actual_elapsed_span_hours"],
        errors="coerce",
    )

    absolute_error = pd.to_numeric(
        data["absolute_error_hours"],
        errors="coerce",
    )

    frame = pd.DataFrame({
        "actual_hours": actual,
        "absolute_error": absolute_error,
    }).dropna()

    bins = [
        0,
        1,
        2,
        4,
        8,
        12,
        24,
        48,
        72,
        float("inf"),
    ]

    labels = [
        "0–1 hour",
        "1–2 hours",
        "2–4 hours",
        "4–8 hours",
        "8–12 hours",
        "12–24 hours",
        "24–48 hours",
        "48–72 hours",
        "Above 72 hours",
    ]

    frame["duration_group"] = pd.cut(
        frame["actual_hours"],
        bins=bins,
        labels=labels,
        include_lowest=True,
        right=True,
    )

    output = []

    for label in labels:
        group = frame.loc[
            frame["duration_group"] == label,
            "absolute_error",
        ]

        if group.empty:
            output.append({
                "duration_range": label,
                "sample_count": 0,
                "mae_hours": None,
                "p90_absolute_error_hours": None,
            })
            continue

        output.append({
            "duration_range": label,
            "sample_count": int(len(group)),
            "mae_hours": float(group.mean()),
            "p90_absolute_error_hours": float(
                group.quantile(0.90)
            ),
        })

    return output


# ---------------------------------------------------------
# MODEL INFORMATION
# ---------------------------------------------------------

@router.get("/model-info")
def model_information():
    require_file(MODEL_FILE)

    try:
        bundle = joblib.load(MODEL_FILE)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not load regression model: {exc}",
        )

    required = [
        "model_version",
        "imputer",
        "scaler",
        "kmeans",
        "regressor",
        "cluster_features",
        "regression_features",
        "cluster_profiles",
        "cluster_names",
        "target_transform",
    ]

    missing = [
        key for key in required
        if key not in bundle
    ]

    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Model artifact is missing keys: {missing}",
        )

    kmeans = bundle["kmeans"]
    regressor = bundle["regressor"]
    imputer = bundle["imputer"]
    scaler = bundle["scaler"]

    regression_features = list(
        bundle["regression_features"]
    )

    tree_features = regression_features + ["cluster"]

    importances = []

    for feature, importance in zip(
        tree_features,
        regressor.feature_importances_,
    ):
        importances.append({
            "feature": feature,
            "importance": float(importance),
        })

    importances.sort(
        key=lambda item: item["importance"],
        reverse=True,
    )

    return json_safe({
        "model_version": bundle["model_version"],
        "target": bundle.get(
            "target",
            "elapsed_span_hours",
        ),
        "target_transform": bundle["target_transform"],
        "cluster_transform": bundle.get(
            "cluster_transform"
        ),
        "training_rows": bundle.get("training_rows"),
        "trained_at_utc": bundle.get("trained_at_utc"),
        "python_version": bundle.get("python_version"),
        "scikit_learn_version": bundle.get(
            "scikit_learn_version"
        ),

        "cluster_features": bundle["cluster_features"],
        "regression_features": regression_features,
        "tree_features": tree_features,

        "kmeans_parameters": kmeans.get_params(),
        "decision_tree_parameters": regressor.get_params(),

        "tree_structure": {
            "actual_depth": regressor.get_depth(),
            "leaf_count": regressor.get_n_leaves(),
            "node_count": regressor.tree_.node_count,
        },

        "feature_importances": importances,

        "cluster_centers_standardized": (
            kmeans.cluster_centers_
        ),

        "imputer_statistics": imputer.statistics_,
        "scaler_mean_after_log1p": scaler.mean_,
        "scaler_scale_after_log1p": scaler.scale_,

        "cluster_profiles": bundle["cluster_profiles"],
        "cluster_names": bundle["cluster_names"],
    })
