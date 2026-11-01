from pathlib import Path

import pandas as pd


report_dir = Path("anomaly_detection/reports/full")
vehicles_to_review = [116, 121, 80, 59, 137]

variants = {
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

profiles = []

for variant, settings in variants.items():
    path = report_dir / f"validation_predictions_{variant}.csv"
    data = pd.read_csv(path, low_memory=False)
    data["is_anomaly"] = (
        data["is_anomaly"].astype(str).str.lower().eq("true")
    )
    data["quality_warning"] = (
        data[settings["quality_column"]] == "eligible_with_warnings"
    )

    subset = data[data["vehicle_id"].isin(vehicles_to_review)].copy()

    metrics = {
        "track_count": ("track_id", "size"),
        "quality_warning_rate_pct": (
            "quality_warning",
            lambda values: 100 * values.mean(),
        ),
    }
    for feature in settings["features"]:
        metrics[f"median_{feature}"] = (feature, "median")

    grouped = (
        subset.groupby(["vehicle_id", "is_anomaly"])
        .agg(**metrics)
        .reset_index()
    )
    grouped["model_variant"] = variant
    profiles.append(grouped)

result = pd.concat(profiles, ignore_index=True)
result.to_csv(report_dir / "vehicle_flag_profiles.csv", index=False)
print(result.to_string(index=False))
print(f"\nSaved: {report_dir / 'vehicle_flag_profiles.csv'}")