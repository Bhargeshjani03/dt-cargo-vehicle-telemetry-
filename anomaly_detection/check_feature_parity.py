"""Compare the new raw-speed features with existing movement features."""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ANOMALY_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ANOMALY_DIR))

from src.features import FEATURE_COLUMNS, extract_track_features


TOLERANCES = {
    "raw_speed_mean_kmh": 0.01,
    "raw_speed_std": 0.01,
    "low_speed_time_pct_03": 0.05,
    "stop_episode_count_03": 0.0,
}


def id_token(value) -> str:
    number = float(value)
    return str(int(number)) if number.is_integer() else str(value).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-root",
        type=Path,
        required=True,
        help="Path to the existing data folder.",
    )
    parser.add_argument("--sample-size", type=int, default=20)
    args = parser.parse_args()

    enriched_path = (
        args.data_root / "processed" / "tracks_with_behavioral_features.csv"
    )
    speed_root = args.data_root / "raw" / "speed"

    columns = [
        "track_id",
        "vehicle_id",
        *FEATURE_COLUMNS,
    ]
    baseline = pd.read_csv(enriched_path, usecols=columns)
    baseline = baseline.dropna(subset=list(FEATURE_COLUMNS))

    if baseline.empty:
        raise ValueError("No rows have all four existing movement features.")

    sample = baseline.sample(
        n=min(args.sample_size, len(baseline)),
        random_state=42,
    )

    comparisons = []
    for _, row in sample.iterrows():
        vehicle_id = id_token(row["vehicle_id"])
        track_id = id_token(row["track_id"])
        speed_path = speed_root / vehicle_id / f"{track_id}.csv"

        if not speed_path.is_file():
            raise FileNotFoundError(f"Missing speed file: {speed_path}")

        raw_speed = pd.read_csv(speed_path)
        actual = extract_track_features(raw_speed)

        comparison = {
            "track_id": track_id,
            "vehicle_id": vehicle_id,
        }

        for feature in FEATURE_COLUMNS:
            expected_value = float(row[feature])
            actual_value = actual[feature]

            if actual_value is None:
                comparison[f"{feature}_match"] = False
                comparison[f"{feature}_abs_diff"] = None
                continue

            difference = abs(float(actual_value) - expected_value)
            comparison[f"{feature}_abs_diff"] = difference
            comparison[f"{feature}_match"] = bool(
                np.isclose(
                    float(actual_value),
                    expected_value,
                    rtol=0.0,
                    atol=TOLERANCES[feature],
                )
            )

        comparisons.append(comparison)

    results = pd.DataFrame(comparisons)

    print(f"Tracks compared: {len(results)}")
    for feature in FEATURE_COLUMNS:
        match_count = int(results[f"{feature}_match"].sum())
        differences = results[f"{feature}_abs_diff"].dropna()
        max_difference = (
            float(differences.max()) if not differences.empty else None
        )
        print(
            f"{feature}: {match_count}/{len(results)} within tolerance; "
            f"max absolute difference={max_difference}"
        )

    match_columns = [f"{feature}_match" for feature in FEATURE_COLUMNS]
    mismatches = results.loc[~results[match_columns].all(axis=1)]

    print(f"Tracks with any feature mismatch: {len(mismatches)}")
    if not mismatches.empty:
        print("First mismatches:")
        print(mismatches.head(5).to_string(index=False))


if __name__ == "__main__":
    main()