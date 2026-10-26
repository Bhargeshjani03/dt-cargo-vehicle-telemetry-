from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


DATA_PATH = Path("anomaly_detection/reports/full/modeling_dataset.csv")
REPORT_DIR = Path("anomaly_detection/reports/full")
SEED = 42

MODEL_SPECS = {
    "core_four_feature": {
        "quality_column": "quality_status_core",
        "features": [
            "raw_speed_mean_kmh",
            "raw_speed_std",
            "low_speed_time_pct_03",
            "stop_episode_count_03",
        ],
        "transforms": ["identity", "log1p_stop"],
    },
    "extended_six_feature": {
        "quality_column": "quality_status_extended",
        "features": [
            "raw_speed_mean_kmh",
            "raw_speed_std",
            "low_speed_time_pct_03",
            "stop_episode_count_03",
            "duration_minutes",
            "distance_km",
        ],
        "transforms": [
            "identity",
            "log1p_stop",
            "log1p_stop_duration_distance",
        ],
    },
}


def apply_transform(frame, features, transform):
    result = frame[features].astype(float).copy()

    columns = []
    if transform in ["log1p_stop", "log1p_stop_duration_distance"]:
        columns.append("stop_episode_count_03")
    if transform == "log1p_stop_duration_distance":
        columns.extend(["duration_minutes", "distance_km"])

    for column in columns:
        if (result[column] < 0).any():
            raise ValueError(f"Cannot apply log1p to negative values in {column}")
        result[column] = np.log1p(result[column])

    return result


def jaccard(left, right):
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def main():
    data = pd.read_csv(DATA_PATH, low_memory=False)
    summaries = []

    for variant, spec in MODEL_SPECS.items():
        accepted = data[spec["quality_column"]].isin(
            ["eligible", "eligible_with_warnings"]
        )
        candidates = data.loc[accepted].copy()

        numeric = candidates[spec["features"]].apply(
            pd.to_numeric, errors="coerce"
        )
        valid_features = np.isfinite(numeric.to_numpy(dtype=float)).all(axis=1)
        candidates = candidates.loc[valid_features].copy()

        candidates["_split_time"] = pd.to_datetime(
            candidates["start_time"],
            format="mixed",
            errors="coerce",
            utc=True,
        )
        candidates = candidates.loc[candidates["_split_time"].notna()]
        candidates = candidates.sort_values("_split_time", kind="stable")

        split_at = int(len(candidates) * 0.80)
        train = candidates.iloc[:split_at]
        validation = candidates.iloc[split_at:]

        baseline_scores = None
        baseline_alerts = None

        for transform in spec["transforms"]:
            print(f"Fitting {variant}, transform={transform}...", flush=True)

            x_train = apply_transform(train, spec["features"], transform)
            x_validation = apply_transform(
                validation, spec["features"], transform
            )

            model = IsolationForest(
                n_estimators=300,
                max_samples="auto",
                max_features=1.0,
                contamination="auto",
                random_state=SEED,
                n_jobs=-1,
            )
            model.fit(x_train)

            scores = -model.decision_function(x_validation)
            threshold = float(np.quantile(scores, 0.98))
            alerts = set(
                validation.loc[scores >= threshold, "track_id"].astype(str)
            )
            prediction_columns = [
                "track_id",
                "vehicle_id",
                "fleet_test_id",
                spec["quality_column"],
                "quality_status",
                "reason_codes",
                *spec["features"],
                "duration_minutes",
                "distance_km",
                "home_base",
                "long_haul",
                "rest_area",
                "service_area_fuel",
                "industrial_area",
            ]
            prediction_columns.extend(
                column
                for column in validation.columns
                if column.startswith("flag_")
            )
            prediction_columns = list(dict.fromkeys(
                column
                for column in prediction_columns
                if column in validation.columns
            ))

            predictions = validation[prediction_columns].copy()
            predictions["anomaly_score"] = scores
            predictions["is_anomaly"] = scores >= threshold
            predictions.to_csv(
                REPORT_DIR
                / f"transform_predictions_{variant}_{transform}.csv",
                index=False,
            )

            if transform == "identity":
                baseline_scores = scores.copy()
                baseline_alerts = alerts
                jaccard_value = 1.0
                rank_correlation = 1.0
            else:
                jaccard_value = jaccard(alerts, baseline_alerts)
                rank_correlation = pd.Series(scores).corr(
                    pd.Series(baseline_scores), method="spearman"
                )

            summaries.append({
                "model_variant": variant,
                "transform": transform,
                "random_state": SEED,
                "training_tracks": len(train),
                "validation_tracks": len(validation),
                "threshold": threshold,
                "flagged_tracks": len(alerts),
                "alert_rate_pct": 100 * len(alerts) / len(validation),
                "jaccard_vs_identity": jaccard_value,
                "score_rank_correlation_vs_identity": rank_correlation,
            })

    summary = pd.DataFrame(summaries)
    output_path = REPORT_DIR / "feature_transform_summary.csv"
    summary.to_csv(output_path, index=False)
    print("\nFeature transformation summary:")
    print(summary.to_string(index=False))
    print(f"\nSaved: {output_path}")


if __name__ == "__main__":
    main()