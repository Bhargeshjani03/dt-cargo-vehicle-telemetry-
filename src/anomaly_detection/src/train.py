
"""Train three cluster-specific DT-CARGO Isolation Forest models."""

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
from sklearn.ensemble import IsolationForest


ANOMALY_DIR = Path(__file__).resolve().parents[1]

FEATURES = [
    "raw_speed_mean_kmh",
    "raw_speed_std",
    "low_speed_time_pct_03",
    "stop_episode_count_03",
]

CLUSTERS = [0, 1, 2]


def score_summary(scores: np.ndarray) -> dict:
    percentiles = np.percentile(scores, [0, 50, 90, 95, 98, 100])
    names = ["min", "median", "p90", "p95", "p98", "max"]

    return {
        name: float(value)
        for name, value in zip(names, percentiles)
    }


def train_cluster(
    data: pd.DataFrame,
    cluster_id: int,
    report_dir: Path,
    artifact_dir: Path,
    review_rate: float,
    validation_fraction: float,
) -> dict:

    cluster_data = data.loc[
        pd.to_numeric(data["cluster"], errors="coerce") == cluster_id
    ].copy()

    status = cluster_data["quality_status_core"].fillna("missing")

    accepted = status.isin([
        "eligible",
        "eligible_with_warnings",
    ])

    candidates = cluster_data.loc[accepted].copy()

    numeric = candidates[FEATURES].apply(
        pd.to_numeric,
        errors="coerce",
    )

    values = numeric.to_numpy(dtype=float)
    finite_rows = np.isfinite(values).all(axis=1)

    missing_counts = {
        feature: int((~np.isfinite(values[:, index])).sum())
        for index, feature in enumerate(FEATURES)
    }

    candidates[FEATURES] = numeric

    candidates["_split_time"] = pd.to_datetime(
        candidates["start_time"],
        format="mixed",
        errors="coerce",
        utc=True,
    )

    valid_time = candidates["_split_time"].notna().to_numpy()

    usable = finite_rows & valid_time

    candidates = candidates.loc[usable].copy()

    candidates = candidates.sort_values(
        "_split_time",
        kind="stable",
    )

    if len(candidates) < 1000:
        raise ValueError(
            f"Cluster {cluster_id}: only {len(candidates)} "
            "usable tracks. At least 1,000 are required."
        )

    split_at = int(
        len(candidates) * (1.0 - validation_fraction)
    )

    if split_at < 100 or len(candidates) - split_at < 20:
        raise ValueError(
            f"Cluster {cluster_id}: insufficient data for splitting."
        )

    train_rows = candidates.iloc[:split_at]
    validation_rows = candidates.iloc[split_at:]

    x_train = train_rows[FEATURES].astype(float)
    x_validation = validation_rows[FEATURES].astype(float)

    model = IsolationForest(
        n_estimators=300,
        max_samples="auto",
        max_features=1.0,
        contamination="auto",
        random_state=42,
        n_jobs=-1,
    )

    model.fit(x_train)

    # Higher scores indicate more unusual observations.
    training_scores = -model.decision_function(x_train)
    validation_scores = -model.decision_function(x_validation)

    # Calibrate the threshold using training data only.
    threshold = float(
        np.quantile(training_scores, 1.0 - review_rate)
    )

    is_anomaly = validation_scores >= threshold

    prediction_columns = [
        "track_id",
        "vehicle_id",
        "fleet_test_id",
        "cluster",
        "start_time",
        "stop_time",
        "quality_status_core",
        "quality_status",
        "reason_codes",
        *FEATURES,
    ]

    prediction_columns.extend(
        column
        for column in data.columns
        if column.startswith("flag_")
    )

    prediction_columns = list(dict.fromkeys(
        column
        for column in prediction_columns
        if column in validation_rows.columns
    ))

    predictions = validation_rows[prediction_columns].copy()

    predictions["anomaly_score"] = validation_scores
    predictions["anomaly_threshold"] = threshold
    predictions["is_anomaly"] = is_anomaly
    predictions["model_cluster"] = cluster_id

    report_dir.mkdir(parents=True, exist_ok=True)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    predictions.to_csv(
        report_dir / f"validation_predictions_cluster_{cluster_id}.csv",
        index=False,
    )

    training_period = {
        "start": train_rows["_split_time"].min().isoformat(),
        "end": train_rows["_split_time"].max().isoformat(),
    }

    validation_period = {
        "start": validation_rows["_split_time"].min().isoformat(),
        "end": validation_rows["_split_time"].max().isoformat(),
    }

    summary = {
        "cluster": cluster_id,
        "candidate_tracks": int(len(cluster_data)),
        "eligible": int((status == "eligible").sum()),
        "eligible_with_warnings": int(
            (status == "eligible_with_warnings").sum()
        ),
        "missing_required_feature_counts": missing_counts,
        "usable_tracks": int(len(candidates)),
        "training_tracks": int(len(train_rows)),
        "validation_tracks": int(len(validation_rows)),
        "training_period": training_period,
        "validation_period": validation_period,
        "features": FEATURES,
        "transform": "identity",
        "score_definition": (
            "Negative Isolation Forest decision_function; "
            "higher means more unusual, not a probability."
        ),
        "threshold": threshold,
        "threshold_policy": {
            "target_review_rate": review_rate,
            "calibration": "training_score_quantile",
            "training_alert_rate": float(
                (training_scores >= threshold).mean()
            ),
            "actual_validation_alert_rate": float(
                is_anomaly.mean()
            ),
        },
        "training_score_summary": score_summary(training_scores),
        "validation_score_summary": score_summary(validation_scores),
        "validation_flagged_tracks": int(is_anomaly.sum()),
        "known_limitations": [
            "No verified anomaly labels are available.",
            "Review rate is a policy choice, not anomaly prevalence.",
            "Scores from different cluster models are not directly comparable.",
            "Flagged tracks require analyst investigation.",
        ],
    }

    bundle = {
        "model": model,
        "model_version": f"dt_cargo_iforest_cluster_{cluster_id}_v1",
        "cluster": cluster_id,
        "feature_names": FEATURES,
        "transform": "identity",
        "score_direction": "higher_is_more_anomalous",
        "threshold": threshold,
        "threshold_policy": summary["threshold_policy"],
        "training_period": training_period,
        "dataset_version": "full modeling_dataset.csv",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "scikit_learn_version": sklearn.__version__,
        "validation_summary": summary,
    }

    joblib.dump(
        bundle,
        artifact_dir / f"isolation_forest_cluster_{cluster_id}_v1.joblib",
    )

    return summary


def main() -> None:

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input-csv",
        default=str(
            ANOMALY_DIR / "reports" / "modeling_dataset.csv"
        ),
    )

    parser.add_argument(
        "--report-dir",
        default=str(
            ANOMALY_DIR / "reports" / "cluster_models"
        ),
    )

    parser.add_argument(
        "--artifact-dir",
        default=str(ANOMALY_DIR / "artifacts"),
    )

    parser.add_argument(
        "--review-rate",
        type=float,
        default=0.02,
    )

    parser.add_argument(
        "--validation-fraction",
        type=float,
        default=0.20,
    )

    args = parser.parse_args()

    if not 0 < args.review_rate < 1:
        raise ValueError("Review rate must be between 0 and 1.")

    if not 0 < args.validation_fraction < 0.5:
        raise ValueError(
            "Validation fraction must be between 0 and 0.5."
        )

    input_path = Path(args.input_csv)
    report_dir = Path(args.report_dir)
    artifact_dir = Path(args.artifact_dir)

    if not input_path.exists():
        raise FileNotFoundError(
            f"Modelling dataset not found: {input_path}"
        )

    data = pd.read_csv(input_path, low_memory=False)

    required_columns = [
        "cluster",
        "quality_status_core",
        "start_time",
        *FEATURES,
    ]

    missing = [
        column
        for column in required_columns
        if column not in data.columns
    ]

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    summaries = {}

    for cluster_id in CLUSTERS:

        print(f"\nTraining Isolation Forest for cluster {cluster_id}...")

        summary = train_cluster(
            data=data,
            cluster_id=cluster_id,
            report_dir=report_dir,
            artifact_dir=artifact_dir,
            review_rate=args.review_rate,
            validation_fraction=args.validation_fraction,
        )

        summaries[f"cluster_{cluster_id}"] = summary

        print(
            f"Training tracks: {summary['training_tracks']:,} | "
            f"Validation tracks: {summary['validation_tracks']:,} | "
            f"Flagged: {summary['validation_flagged_tracks']:,}"
        )

    report_dir.mkdir(parents=True, exist_ok=True)

    with (report_dir / "validation_summary.json").open("w") as file:
        json.dump(summaries, file, indent=2)

    print("\n========== TRAINING COMPLETE ==========")
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
