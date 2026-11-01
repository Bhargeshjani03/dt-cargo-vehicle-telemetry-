from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


DATA_PATH = Path("anomaly_detection/reports/full/modeling_dataset.csv")
REPORT_DIR = Path("anomaly_detection/reports/full")
SEEDS = [42, 7, 123]

MODEL_SPECS = {
    "core_four_feature": {
        "quality_column": "quality_status_core",
        "features": [
            "raw_speed_mean_kmh",
            "raw_speed_std",
            "low_speed_time_pct_03",
            "stop_episode_count_03",
        ],
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
    },
}


def jaccard(left, right):
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def main():
    data = pd.read_csv(DATA_PATH, low_memory=False)
    results = []

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
        x_train = train[spec["features"]].astype(float)
        x_validation = validation[spec["features"]].astype(float)

        baseline_scores = None
        baseline_alerts = None

        for seed in SEEDS:
            print(f"Fitting {variant}, random_state={seed}...", flush=True)

            model = IsolationForest(
                n_estimators=300,
                max_samples="auto",
                max_features=1.0,
                contamination="auto",
                random_state=seed,
                n_jobs=-1,
            )
            model.fit(x_train)

            scores = -model.decision_function(x_validation)
            threshold = float(np.quantile(scores, 0.98))
            alerts = set(
                validation.loc[scores >= threshold, "track_id"].astype(str)
            )

            if seed == 42:
                baseline_scores = scores.copy()
                baseline_alerts = alerts

            rows = {
                "model_variant": variant,
                "random_state": seed,
                "training_tracks": len(train),
                "validation_tracks": len(validation),
                "threshold": threshold,
                "flagged_tracks": len(alerts),
                "alert_rate_pct": 100 * len(alerts) / len(validation),
            }

            if seed == 42:
                rows["jaccard_vs_seed_42"] = 1.0
                rows["score_rank_correlation_vs_seed_42"] = 1.0
            else:
                rows["jaccard_vs_seed_42"] = jaccard(alerts, baseline_alerts)
                rows["score_rank_correlation_vs_seed_42"] = pd.Series(
                    scores
                ).corr(pd.Series(baseline_scores), method="spearman")

            results.append(rows)

    summary = pd.DataFrame(results)
    output_path = REPORT_DIR / "seed_stability_summary.csv"
    summary.to_csv(output_path, index=False)
    print("\nSeed stability summary:")
    print(summary.to_string(index=False))
    print(f"\nSaved: {output_path}")


if __name__ == "__main__":
    main()