"""Train and calibrate the DT-CARGO movement Isolation Forest models."""

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


CORE_FEATURES = [
    "raw_speed_mean_kmh",
    "raw_speed_std",
    "low_speed_time_pct_03",
    "stop_episode_count_03",
]
EXTENDED_FEATURES = CORE_FEATURES + ["duration_minutes", "distance_km"]

MODEL_SPECS = {
    "core_four_feature": {
        "features": CORE_FEATURES,
        "quality_column": "quality_status_core",
    },
    "extended_six_feature": {
        "features": EXTENDED_FEATURES,
        "quality_column": "quality_status_extended",
    },
}


def _score_summary(scores: np.ndarray) -> dict:
    percentiles = np.percentile(scores, [0, 50, 90, 95, 98, 100])
    names = ["min", "median", "p90", "p95", "p98", "max"]
    return {name: float(value) for name, value in zip(names, percentiles)}


def train_variant(
    data: pd.DataFrame,
    variant: str,
    features: list[str],
    quality_column: str,
    output_dir: Path,
    review_rate: float,
    validation_fraction: float,
) -> dict:
    status = data[quality_column].fillna("missing")
    accepted = status.isin(["eligible", "eligible_with_warnings"])
    candidates = data.loc[accepted].copy()

    numeric = candidates[features].apply(pd.to_numeric, errors="coerce")
    values = numeric.to_numpy(dtype=float)
    finite_rows = np.isfinite(values).all(axis=1)

    missing_counts = {}
    for index, feature in enumerate(features):
        missing_counts[feature] = int((~np.isfinite(values[:, index])).sum())

    candidates["_split_time"] = pd.to_datetime(
        candidates["start_time"], format="mixed", errors="coerce", utc=True
    )
    valid_time = candidates["_split_time"].notna().to_numpy()
    usable = finite_rows & valid_time
    candidates = candidates.loc[usable].copy()
    candidates = candidates.sort_values("_split_time", kind="stable")

    if len(candidates) < 1000:
        raise ValueError(
            f"{variant}: found {len(candidates)} usable tracks. "
            "At least 1,000 are required; check that the full dataset, "
            "not the 100-track smoke run, is being used."
        )

    split_at = int(len(candidates) * (1.0 - validation_fraction))
    if split_at < 100 or len(candidates) - split_at < 20:
        raise ValueError(f"{variant}: not enough tracks for a time-based split.")

    train_rows = candidates.iloc[:split_at]
    validation_rows = candidates.iloc[split_at:]

    x_train = train_rows[features].astype(float)
    x_validation = validation_rows[features].astype(float)

    model = IsolationForest(
        n_estimators=300,
        max_samples="auto",
        max_features=1.0,
        contamination="auto",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(x_train)

    # Higher scores mean more unusual. These scores are not probabilities.
    validation_scores = -model.decision_function(x_validation)

    # Provisional policy: set the threshold at the validation score percentile
    # corresponding to the requested manual-review rate.
    threshold = float(np.quantile(validation_scores, 1.0 - review_rate))
    is_anomaly = validation_scores >= threshold

    prediction_columns = [
        "track_id",
        "vehicle_id",
        "fleet_test_id",
        "start_time",
        "stop_time",
        quality_column,
        "quality_status",
        "reason_codes",
        *features,
    ]
    prediction_columns.extend(
        column for column in data.columns if column.startswith("flag_")
    )
    prediction_columns = list(dict.fromkeys(
        column for column in prediction_columns if column in validation_rows.columns
    ))

    predictions = validation_rows[prediction_columns].copy()
    predictions["anomaly_score"] = validation_scores
    predictions["is_anomaly"] = is_anomaly
    predictions["model_variant"] = variant

    output_dir.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(
        output_dir / f"validation_predictions_{variant}.csv", index=False
    )

    summary = {
        "model_variant": variant,
        "input_tracks": int(len(data)),
        "eligible": int((status == "eligible").sum()),
        "eligible_with_warnings": int((status == "eligible_with_warnings").sum()),
        "ineligible_or_missing_status": int((~accepted).sum()),
        "missing_required_feature_counts": missing_counts,
        "usable_tracks_with_valid_start_time": int(len(candidates)),
        "training_tracks": int(len(train_rows)),
        "validation_tracks": int(len(validation_rows)),
        "training_period": {
            "start": train_rows["_split_time"].min().isoformat(),
            "end": train_rows["_split_time"].max().isoformat(),
        },
        "validation_period": {
            "start": validation_rows["_split_time"].min().isoformat(),
            "end": validation_rows["_split_time"].max().isoformat(),
        },
        "features": features,
        "transform": "identity",
        "score_definition": (
            "Negative Isolation Forest decision_function; "
            "higher means more unusual, not a probability."
        ),
        "threshold": threshold,
        "threshold_policy": {
            "target_review_rate": review_rate,
            "validation_score_quantile": 1.0 - review_rate,
            "actual_validation_alert_rate": float(is_anomaly.mean()),
        },
        "validation_score_summary": _score_summary(validation_scores),
        "validation_flagged_tracks": int(is_anomaly.sum()),
        "known_limitations": [
            "There are no verified anomaly labels; this is not an accuracy measure.",
            "The review rate is a policy choice, not anomaly prevalence.",
            "Flagged tracks are candidates for investigation, not diagnoses.",
        ],
    }

    bundle = {
        "model": model,
        "model_version": f"movement_iforest_{variant}_v1",
        "feature_names": features,
        "feature_engineering_version": "dt_cargo_movement_v1",
        "quality_rules_version": "dt_cargo_quality_v1",
        "transform": "identity",
        "score_direction": "higher_is_more_anomalous",
        "threshold": threshold,
        "threshold_policy": summary["threshold_policy"],
        "training_period": summary["training_period"],
        "dataset_version": "full modeling_dataset.csv",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "scikit_learn_version": sklearn.__version__,
        "validation_summary": summary,
    }

    joblib.dump(
        bundle,
        output_dir.parent.parent
        / "artifacts"
        / f"movement_iforest_{variant}_v1.joblib",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-csv",
        default="anomaly_detection/reports/full/modeling_dataset.csv",
    )
    parser.add_argument(
        "--report-dir",
        default="anomaly_detection/reports/full",
    )
    parser.add_argument(
        "--review-rate",
        type=float,
        default=0.02,
        help="Provisional share of validation tracks marked for manual review.",
    )
    parser.add_argument("--validation-fraction", type=float, default=0.20)
    args = parser.parse_args()

    if not 0.0 < args.review_rate < 1.0:
        raise ValueError("--review-rate must be between 0 and 1.")
    if not 0.0 < args.validation_fraction < 0.5:
        raise ValueError("--validation-fraction must be between 0 and 0.5.")

    input_path = Path(args.input_csv)
    report_dir = Path(args.report_dir)
    artifact_dir = Path("anomaly_detection/artifacts")
    artifact_dir.mkdir(parents=True, exist_ok=True)

    data = pd.read_csv(input_path, low_memory=False)
    summaries = {}

    for variant, spec in MODEL_SPECS.items():
        missing_columns = [
            column
            for column in [*spec["features"], spec["quality_column"], "start_time"]
            if column not in data.columns
        ]
        if missing_columns:
            raise ValueError(f"Missing columns in {input_path}: {missing_columns}")

        summaries[variant] = train_variant(
            data=data,
            variant=variant,
            features=spec["features"],
            quality_column=spec["quality_column"],
            output_dir=report_dir,
            review_rate=args.review_rate,
            validation_fraction=args.validation_fraction,
        )

    with (report_dir / "validation_summary.json").open("w") as file:
        json.dump(summaries, file, indent=2)

    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()