from pathlib import Path

import pandas as pd


report_dir = Path("anomaly_detection/reports/full")

comparisons = [
    ("core_four_feature", "identity", "log1p_stop"),
    ("extended_six_feature", "identity", "log1p_stop"),
    (
        "extended_six_feature",
        "identity",
        "log1p_stop_duration_distance",
    ),
]

for variant, baseline_transform, transformed_transform in comparisons:
    baseline_path = (
        report_dir
        / f"transform_predictions_{variant}_{baseline_transform}.csv"
    )
    transformed_path = (
        report_dir
        / f"transform_predictions_{variant}_{transformed_transform}.csv"
    )

    baseline = pd.read_csv(baseline_path, low_memory=False)[
        ["track_id", "is_anomaly", "anomaly_score"]
    ].rename(columns={
        "is_anomaly": "identity_is_anomaly",
        "anomaly_score": "identity_score",
    })

    transformed = pd.read_csv(transformed_path, low_memory=False).rename(
        columns={
            "is_anomaly": "transformed_is_anomaly",
            "anomaly_score": "transformed_score",
        }
    )

    merged = baseline.merge(
        transformed,
        on="track_id",
        validate="one_to_one",
    )

    identity_flag = (
        merged["identity_is_anomaly"].astype(str).str.lower().eq("true")
    )
    transformed_flag = (
        merged["transformed_is_anomaly"].astype(str).str.lower().eq("true")
    )

    changed = merged.loc[identity_flag ^ transformed_flag].copy()
    changed["flag_source"] = [
        "identity_only" if value else "transformed_only"
        for value in identity_flag.loc[changed.index]
    ]

    output_path = report_dir / (
        f"transform_disagreements_{variant}_{transformed_transform}.csv"
    )
    changed.to_csv(output_path, index=False)

    both = int((identity_flag & transformed_flag).sum())
    union = int((identity_flag | transformed_flag).sum())
    print(
        f"\n{variant}: identity vs {transformed_transform}\n"
        f"Flagged by both: {both}; changed: {len(changed)}; "
        f"Jaccard: {both / union:.4f}\n"
        f"Saved: {output_path}"
    )

    columns = [
        "track_id",
        "vehicle_id",
        "identity_score",
        "transformed_score",
        "raw_speed_mean_kmh",
        "raw_speed_std",
        "low_speed_time_pct_03",
        "stop_episode_count_03",
        "duration_minutes",
        "distance_km",
    ]
    columns = [column for column in columns if column in changed.columns]

    for source, score_column in [
        ("identity_only", "identity_score"),
        ("transformed_only", "transformed_score"),
    ]:
        print(f"\nTop {source}:")
        print(
            changed[changed["flag_source"] == source]
            .nlargest(5, score_column)[columns]
            .to_string(index=False)
        )