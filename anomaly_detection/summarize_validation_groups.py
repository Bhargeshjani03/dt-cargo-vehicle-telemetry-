from pathlib import Path

import pandas as pd


report_dir = Path("anomaly_detection/reports/full")
results = []

for variant in ["core_four_feature", "extended_six_feature"]:
    path = report_dir / f"validation_predictions_{variant}.csv"
    data = pd.read_csv(path, low_memory=False)
    data["is_anomaly"] = (
        data["is_anomaly"].astype(str).str.lower().eq("true")
    )

    for group_column, group_type in [
        ("vehicle_id", "vehicle"),
        ("fleet_test_id", "fleet_test"),
    ]:
        grouped = (
            data.groupby(group_column, dropna=False)
            .agg(
                validation_tracks=("track_id", "size"),
                flagged_tracks=("is_anomaly", "sum"),
            )
            .reset_index()
            .rename(columns={group_column: "group_id"})
        )
        grouped["flag_rate_pct"] = (
            100 * grouped["flagged_tracks"] / grouped["validation_tracks"]
        )
        grouped["model_variant"] = variant
        grouped["group_type"] = group_type
        results.append(grouped)

summary = pd.concat(results, ignore_index=True)
summary.to_csv(report_dir / "validation_group_summary.csv", index=False)

for variant in ["core_four_feature", "extended_six_feature"]:
    for group_type in ["vehicle", "fleet_test"]:
        selected = summary[
            (summary["model_variant"] == variant)
            & (summary["group_type"] == group_type)
            & (summary["validation_tracks"] >= 50)
        ].sort_values("flag_rate_pct", ascending=False).head(10)

        print(f"\n{variant} — highest {group_type} flag rates (groups with 50+ tracks):")
        print(selected.to_string(index=False))

print(f"\nFull group report saved to {report_dir / 'validation_group_summary.csv'}")