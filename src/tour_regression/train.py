
from __future__ import annotations

import argparse
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn

from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    median_absolute_error,
    r2_score,
)
from sklearn.model_selection import KFold, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeRegressor

from .config import (
    CLUSTER_FEATURES,
    DECISION_TREE_PARAMS,
    DEFAULT_DATA_PATH,
    DEFAULT_MODEL_PATH,
    GAP_COLUMN,
    GAP_THRESHOLD_CANDIDATES,
    KMEANS_PARAMS,
    MODEL_VERSION,
    REGRESSION_FEATURES,
    TARGET_COLUMN,
    TREE_FEATURES,
)


def load_data(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(
            f"Dataset not found: {path}\n"
            "Expected: data/processed/tour_level/"
            "pca_experiments/experiment_B_75pct_without_extreme.csv"
        )

    data = pd.read_csv(path, low_memory=False)

    required = [
        "tour_id",
        "vehicle_id",
        "fleet_test_id",
        *CLUSTER_FEATURES,
        TARGET_COLUMN,
        GAP_COLUMN,
    ]

    missing = [column for column in required if column not in data.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    numeric_columns = [
        *CLUSTER_FEATURES,
        TARGET_COLUMN,
        GAP_COLUMN,
    ]

    for column in numeric_columns:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce",
        )

    data = data.replace([np.inf, -np.inf], np.nan)
    before = len(data)
    data = data.dropna(subset=required).copy()

    # log1p-based clustering and duration regression require
    # non-negative values. Do not silently clip invalid records.
    valid = (data[numeric_columns] >= 0).all(axis=1)
    data = data.loc[valid].copy()

    data = data[data["total_distance_km"] > 0].copy()

    if len(data) < 100:
        raise ValueError(
            f"Only {len(data)} usable tours remain after cleaning."
        )

    print(f"Rows read: {before:,}")
    print(f"Rows retained: {len(data):,}")
    print(f"Rows removed: {before - len(data):,}")

    return data.reset_index(drop=True)


def fit_clusterer(frame):
    raw = frame[CLUSTER_FEATURES].astype(float)

    imputer = SimpleImputer(strategy="median")
    imputed = imputer.fit_transform(raw)

    logged = np.log1p(imputed)

    scaler = StandardScaler()
    scaled = scaler.fit_transform(logged)

    kmeans = KMeans(**KMEANS_PARAMS)
    raw_labels = kmeans.fit_predict(scaled)

    # Stable semantic category IDs:
    # 0 = higher median distance
    # 1 = lower median distance
    medians = {
        int(label): float(
            frame.loc[
                raw_labels == label,
                "total_distance_km",
            ].median()
        )
        for label in np.unique(raw_labels)
    }

    high_label = max(medians, key=medians.get)
    low_label = min(medians, key=medians.get)

    mapping = {
        int(high_label): 0,
        int(low_label): 1,
    }

    labels = np.array([
        mapping[int(label)]
        for label in raw_labels
    ], dtype=int)

    return imputer, scaler, kmeans, mapping, labels


def assign_clusters(frame, imputer, scaler, kmeans, mapping):
    raw = frame[CLUSTER_FEATURES].astype(float)

    imputed = imputer.transform(raw)
    logged = np.log1p(imputed)
    scaled = scaler.transform(logged)

    raw_labels = kmeans.predict(scaled)

    return np.array([
        mapping[int(label)]
        for label in raw_labels
    ], dtype=int)


def apply_regular_tour_filter(frame, threshold):
    """
    Keep all Cluster 0 tours.
    Keep Cluster 1 tours only when historical unrecorded gap
    is at or below the selected threshold.

    This is a retrospective training/evaluation filter.
    It is never an inference input.
    """
    keep = (
        (frame["cluster"] == 0)
        | (
            (frame["cluster"] == 1)
            & (frame[GAP_COLUMN] <= threshold)
        )
    )

    return frame.loc[keep].copy()


def feature_frame(frame):
    return pd.DataFrame({
        "total_distance_km": frame["total_distance_km"].astype(float),
        "cluster": frame["cluster"].astype(int),
    })


def calculate_metrics(actual, predicted):
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)

    return {
        "sample_count": int(len(actual)),
        "r2_score": float(r2_score(actual, predicted)),
        "mae_hours": float(
            mean_absolute_error(actual, predicted)
        ),
        "rmse_hours": float(
            np.sqrt(mean_squared_error(actual, predicted))
        ),
        "median_absolute_error_hours": float(
            median_absolute_error(actual, predicted)
        ),
    }


def train_tree(frame):
    model = DecisionTreeRegressor(**DECISION_TREE_PARAMS)

    model.fit(
        feature_frame(frame),
        np.log1p(frame[TARGET_COLUMN].to_numpy(dtype=float)),
    )

    return model


def predict_hours(model, frame):
    prediction_log = model.predict(feature_frame(frame))
    return np.maximum(np.expm1(prediction_log), 0.0)


def cross_validate_threshold(train_frame, threshold):
    """
    Every fold fits its own imputer, scaler and K-Means model.
    No validation-fold data is used to fit clustering.
    """
    kfold = KFold(
        n_splits=5,
        shuffle=True,
        random_state=42,
    )

    actual_all = []
    predicted_all = []
    fold_counts = []

    for train_indices, valid_indices in kfold.split(train_frame):
        fold_train = (
            train_frame.iloc[train_indices]
            .copy()
            .reset_index(drop=True)
        )
        fold_valid = (
            train_frame.iloc[valid_indices]
            .copy()
            .reset_index(drop=True)
        )

        imputer, scaler, kmeans, mapping, train_labels = (
            fit_clusterer(fold_train)
        )

        valid_labels = assign_clusters(
            fold_valid,
            imputer,
            scaler,
            kmeans,
            mapping,
        )

        fold_train["cluster"] = train_labels
        fold_valid["cluster"] = valid_labels

        filtered_train = apply_regular_tour_filter(
            fold_train,
            threshold,
        )
        filtered_valid = apply_regular_tour_filter(
            fold_valid,
            threshold,
        )

        model = train_tree(filtered_train)
        predictions = predict_hours(model, filtered_valid)

        actual_all.extend(
            filtered_valid[TARGET_COLUMN].to_numpy()
        )
        predicted_all.extend(predictions)
        fold_counts.append(len(filtered_valid))

    result = calculate_metrics(actual_all, predicted_all)
    result["fold_evaluation_counts"] = [
        int(count) for count in fold_counts
    ]

    return result


def select_gap_threshold(train_frame):
    results = {}

    for threshold in GAP_THRESHOLD_CANDIDATES:
        print(f"Cross-validating gap threshold: {threshold} hours")

        results[str(threshold)] = cross_validate_threshold(
            train_frame,
            float(threshold),
        )

    # Threshold selection uses training CV only.
    selected = max(
        GAP_THRESHOLD_CANDIDATES,
        key=lambda value: (
            results[str(value)]["r2_score"],
            -results[str(value)]["mae_hours"],
        ),
    )

    return float(selected), results


def build_cluster_profiles(frame):
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
            "median_elapsed_span_hours": float(
                group[TARGET_COLUMN].median()
            ),
        }

    return profiles


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA_PATH,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_MODEL_PATH,
    )
    args = parser.parse_args()

    data = load_data(args.data)

    # Reproduce the original split.
    train_frame, test_frame = train_test_split(
        data,
        test_size=0.20,
        random_state=42,
    )

    train_frame = train_frame.copy().reset_index(drop=True)
    test_frame = test_frame.copy().reset_index(drop=True)

    print("\nSelecting gap threshold using training-only CV...")
    selected_threshold, cv_results = select_gap_threshold(
        train_frame
    )

    print(f"\nSelected threshold: {selected_threshold} hours")

    # Fit the validation clustering pipeline on training only.
    imputer, scaler, kmeans, mapping, train_labels = (
        fit_clusterer(train_frame)
    )

    test_labels = assign_clusters(
        test_frame,
        imputer,
        scaler,
        kmeans,
        mapping,
    )

    train_frame["cluster"] = train_labels
    test_frame["cluster"] = test_labels

    filtered_train = apply_regular_tour_filter(
        train_frame,
        selected_threshold,
    )

    filtered_test = apply_regular_tour_filter(
        test_frame,
        selected_threshold,
    )

    # Original unfiltered baseline for fair comparison.
    baseline_model = train_tree(train_frame)

    # Proposed regular-tour model.
    validation_model = train_tree(filtered_train)

    filtered_predictions = predict_hours(
        validation_model,
        filtered_test,
    )

    baseline_filtered_predictions = predict_hours(
        baseline_model,
        filtered_test,
    )

    all_test_predictions = predict_hours(
        validation_model,
        test_frame,
    )

    filtered_metrics = calculate_metrics(
        filtered_test[TARGET_COLUMN],
        filtered_predictions,
    )

    baseline_same_subset_metrics = calculate_metrics(
        filtered_test[TARGET_COLUMN],
        baseline_filtered_predictions,
    )

    all_test_metrics = calculate_metrics(
        test_frame[TARGET_COLUMN],
        all_test_predictions,
    )

    training_predictions = predict_hours(
        validation_model,
        filtered_train,
    )

    training_metrics = calculate_metrics(
        filtered_train[TARGET_COLUMN],
        training_predictions,
    )

    # Per-cluster metrics on the filtered holdout.
    cluster_rows = []

    eval_frame = filtered_test.copy()
    eval_frame["predicted"] = filtered_predictions

    for cluster_id, group in eval_frame.groupby("cluster"):
        metrics = calculate_metrics(
            group[TARGET_COLUMN],
            group["predicted"],
        )

        absolute_errors = (
            group[TARGET_COLUMN] - group["predicted"]
        ).abs()

        nonzero = group[TARGET_COLUMN] > 0
        mape = (
            (
                absolute_errors[nonzero]
                / group.loc[nonzero, TARGET_COLUMN]
            ).mean() * 100
            if nonzero.any()
            else None
        )

        cluster_rows.append({
            "cluster_id": int(cluster_id),
            "cluster_name": (
                "Longer-distance / higher-speed pattern"
                if int(cluster_id) == 0
                else "Shorter-distance / lower-speed pattern"
            ),
            **metrics,
            "mape_percentage": (
                float(mape) if mape is not None else None
            ),
            "mape_sample_count": int(nonzero.sum()),
            "mean_actual_hours": float(
                group[TARGET_COLUMN].mean()
            ),
            "mean_predicted_hours": float(
                group["predicted"].mean()
            ),
            "mean_error_hours": float(
                (group["predicted"] - group[TARGET_COLUMN]).mean()
            ),
            "maximum_absolute_error_hours": float(
                absolute_errors.max()
            ),
        })

    # Save holdout predictions for existing dashboard endpoints.
    holdout = filtered_test.copy()
    holdout["predicted_elapsed_span_hours"] = filtered_predictions
    holdout["predicted_elapsed_span_minutes"] = (
        filtered_predictions * 60
    )
    holdout["prediction_error_hours"] = (
        filtered_predictions - holdout[TARGET_COLUMN]
    )
    holdout["absolute_error_hours"] = (
        holdout["prediction_error_hours"].abs()
    )
    holdout["absolute_error_minutes"] = (
        holdout["absolute_error_hours"] * 60
    )

    holdout["absolute_percentage_error_pct"] = np.where(
        holdout[TARGET_COLUMN] > 0,
        holdout["absolute_error_hours"]
        / holdout[TARGET_COLUMN] * 100,
        np.nan,
    )

    holdout["predicted_cluster_id"] = holdout["cluster"]
    holdout["predicted_cluster_name"] = holdout["cluster"].map({
        0: "Longer-distance / higher-speed pattern",
        1: "Shorter-distance / lower-speed pattern",
    })

    artifact_dir = args.output.parent
    validation_dir = artifact_dir / "holdout_validation"
    validation_dir.mkdir(parents=True, exist_ok=True)

    output_columns = [
        "tour_id",
        "vehicle_id",
        "fleet_test_id",
        TARGET_COLUMN,
        "predicted_elapsed_span_hours",
        "predicted_elapsed_span_minutes",
        "predicted_cluster_id",
        "predicted_cluster_name",
        "prediction_error_hours",
        "absolute_error_hours",
        "absolute_error_minutes",
        "absolute_percentage_error_pct",
    ]

    holdout[output_columns].rename(
        columns={
            TARGET_COLUMN: "actual_elapsed_span_hours",
        }
    ).to_csv(
        validation_dir / "holdout_predictions.csv",
        index=False,
    )

    pd.DataFrame(cluster_rows).to_csv(
        validation_dir / "holdout_cluster_evaluation.csv",
        index=False,
    )

    metrics_payload = {
        "evaluation_type": (
            "conditional_regular_tour_holdout_evaluation"
        ),
        "model_version": MODEL_VERSION,
        "evaluated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "dataset_path": str(args.data),
        "total_usable_tours": int(len(data)),
        "train_test_split": {
            "train_percentage": 80,
            "test_percentage": 20,
            "train_count": int(len(train_frame)),
            "test_count": int(len(test_frame)),
            "evaluated_train_count": int(len(filtered_train)),
            "evaluated_test_count": int(len(filtered_test)),
            "excluded_test_count": int(
                len(test_frame) - len(filtered_test)
            ),
            "random_state": 42,
        },
        "preprocessing": (
            "Median imputation, log1p and StandardScaler fitted "
            "inside each training fold and on training split only."
        ),
        "clustering": (
            "K-Means uses distance and cleaned historical "
            "distance-based speed. Semantic cluster IDs are ordered "
            "by training median distance."
        ),
        "regression": (
            "Decision Tree uses only total_distance_km and the "
            "operational category. Target uses log1p transformation."
        ),
        "gap_filter": {
            "column": GAP_COLUMN,
            "threshold_hours": selected_threshold,
            "scope": "Cluster 1 only",
            "purpose": "Historical training and conditional evaluation only",
            "user_input_required": False,
            "cross_validation_results": cv_results,
        },
        "training_metrics": training_metrics,
        "test_metrics": filtered_metrics,
        "baseline_on_same_filtered_test_subset": (
            baseline_same_subset_metrics
        ),
        "test_metrics_on_all_tours": all_test_metrics,
        "evaluation_warning": (
            "Filtered test metrics are conditional on tours that "
            "retrospectively satisfy the gap threshold. The gap is "
            "not available before dispatch. Do not interpret this "
            "as unconditional performance on all future tours."
        ),
    }

    with (
        validation_dir / "holdout_metrics.json"
    ).open("w", encoding="utf-8") as file:
        json.dump(metrics_payload, file, indent=2)

    # -----------------------------------------------------
    # Final production fit using all available historical data.
    # K-Means is fit on all tours; regression is fit on the
    # regular-tour training population.
    # -----------------------------------------------------

    final_imputer, final_scaler, final_kmeans, final_mapping, final_labels = (
        fit_clusterer(data)
    )

    production_frame = data.copy()
    production_frame["cluster"] = final_labels

    regular_production_frame = apply_regular_tour_filter(
        production_frame,
        selected_threshold,
    )

    production_model = train_tree(regular_production_frame)

    profiles = build_cluster_profiles(production_frame)

    cluster_names = {
        0: "Longer-distance / higher-speed pattern",
        1: "Shorter-distance / lower-speed pattern",
    }

    bundle = {
        "model_version": MODEL_VERSION,
        "trained_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "training_data": str(args.data),
        "training_rows": int(len(regular_production_frame)),
        "original_rows": int(len(data)),
        "cluster_features": list(CLUSTER_FEATURES),
        "regression_features": list(REGRESSION_FEATURES),
        "tree_features": list(TREE_FEATURES),
        "target": TARGET_COLUMN,
        "target_transform": "log1p; inverse with expm1",
        "cluster_transform": (
            "median imputation -> log1p -> StandardScaler -> KMeans"
        ),
        "imputer": final_imputer,
        "scaler": final_scaler,
        "kmeans": final_kmeans,
        "cluster_label_mapping": final_mapping,
        "regressor": production_model,
        "cluster_profiles": profiles,
        "cluster_names": cluster_names,
        "gap_threshold_hours": selected_threshold,
        "gap_filter_scope": "Cluster 1 historical training rows only",
        "distance_min_km": float(
            data["total_distance_km"].min()
        ),
        "distance_max_km": float(
            data["total_distance_km"].max()
        ),
        "kmeans_params": dict(KMEANS_PARAMS),
        "decision_tree_params": dict(DECISION_TREE_PARAMS),
        "python_version": platform.python_version(),
        "scikit_learn_version": sklearn.__version__,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, args.output)

    print("\n================ VALIDATION ================")
    print(f"Selected gap threshold: {selected_threshold} hours")
    print(f"Filtered training tours: {len(filtered_train):,}")
    print(f"Filtered holdout tours: {len(filtered_test):,}")
    print(f"Excluded holdout tours: {len(test_frame) - len(filtered_test):,}")

    print("\nFiltered model on regular-tour holdout:")
    print(json.dumps(filtered_metrics, indent=2))

    print("\nOriginal baseline on same holdout subset:")
    print(json.dumps(baseline_same_subset_metrics, indent=2))

    print("\nFiltered model on all holdout tours:")
    print(json.dumps(all_test_metrics, indent=2))

    print("\nSaved production model:")
    print(args.output)

    print("\nSaved validation artifacts:")
    print(validation_dir)


if __name__ == "__main__":
    main()
