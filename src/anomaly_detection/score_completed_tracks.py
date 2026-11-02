
"""Command-line cluster-aware batch scoring for DT-CARGO tracks."""

import argparse
import json
from pathlib import Path

import pandas as pd

from src.inference import (
    load_cluster_model_bundles,
    score_batch,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=__doc__
    )

    parser.add_argument(
        "--tracks-csv",
        required=True,
        help="Track metadata CSV containing cluster assignments.",
    )

    parser.add_argument(
        "--speed-root",
        required=True,
        help=(
            "Root directory containing "
            "vehicle_id/track_id.csv telemetry files."
        ),
    )

    parser.add_argument(
        "--model-dir",
        required=True,
        help="Directory containing cluster-specific model bundles.",
    )

    parser.add_argument(
        "--output-csv",
        required=True,
        help="Path where scored predictions will be saved.",
    )

    parser.add_argument(
        "--existing-predictions",
        default=None,
        help=(
            "Optional CSV used to skip track_id/model_version "
            "pairs already scored."
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Optional number of tracks to sample for testing. "
            "Uses random_state=42 for reproducibility."
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Validate limit.
    if args.limit is not None and args.limit <= 0:
        raise SystemExit("--limit must be greater than 0.")

    # --------------------------------------------------
    # 1. Load track metadata
    # --------------------------------------------------

    print("Loading track metadata...")

    tracks = pd.read_csv(
        args.tracks_csv,
        low_memory=False,
    )

    original_track_count = len(tracks)

    print(f"Total available tracks: {original_track_count}")

    # Optional reproducible sample.
    if args.limit is not None:
        tracks = tracks.sample(
            n=min(args.limit, len(tracks)),
            random_state=42,
        ).reset_index(drop=True)

        print(
            f"Smoke-test mode: selected {len(tracks)} tracks."
        )

    # --------------------------------------------------
    # 2. Load existing predictions
    # --------------------------------------------------

    existing = None

    if args.existing_predictions:
        print("Loading existing predictions...")

        existing = pd.read_csv(
            args.existing_predictions,
            low_memory=False,
        )

        print(
            f"Existing prediction rows: {len(existing)}"
        )

    # --------------------------------------------------
    # 3. Load cluster-specific model bundles
    # --------------------------------------------------

    print("Loading cluster-specific models...")

    model_bundles = load_cluster_model_bundles(
        args.model_dir,
        clusters=(0, 1, 2),
    )

    print(
        f"Loaded models: {list(model_bundles.keys())}"
    )

    # --------------------------------------------------
    # 4. Score tracks
    # --------------------------------------------------

    print("Starting batch inference...")

    results = score_batch(
        track_metadata=tracks,
        speed_root=args.speed_root,
        model_bundles=model_bundles,
        existing_predictions=existing,
    )

    print("Batch inference completed.")

    # --------------------------------------------------
    # 5. Save predictions
    # --------------------------------------------------

    output = Path(args.output_csv)

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    results.to_csv(
        output,
        index=False,
    )

    print(f"Predictions saved to: {output}")

    # --------------------------------------------------
    # 6. Prepare summary
    # --------------------------------------------------

    summary = {
        "input_tracks": int(len(tracks)),
        "available_tracks_before_sampling": int(
            original_track_count
        ),
        "sample_limit": args.limit,
        "scored_rows": int(len(results)),
        "model_versions": {
            str(cluster): bundle["model_version"]
            for cluster, bundle in model_bundles.items()
        },
        "cluster_counts": {},
        "quality_status_counts": {},
        "eligible_rows": 0,
        "ineligible_rows": 0,
        "unassigned_cluster_rows": 0,
        "unsupported_cluster_rows": 0,
        "flagged_rows": 0,
        "processing_errors": 0,
        "missing_telemetry_files": 0,
        "output_csv": str(output),
    }

    if not results.empty:

        # Cluster distribution.
        if "cluster" in results.columns:
            summary["cluster_counts"] = {
                str(key): int(value)
                for key, value in (
                    results["cluster"]
                    .value_counts(dropna=False)
                    .items()
                )
            }

        # Quality status distribution.
        if "quality_status" in results.columns:
            summary["quality_status_counts"] = {
                str(key): int(value)
                for key, value in (
                    results["quality_status"]
                    .value_counts(dropna=False)
                    .items()
                )
            }

            summary["eligible_rows"] = int(
                results["quality_status"].isin(
                    [
                        "eligible",
                        "eligible_with_warnings",
                    ]
                ).sum()
            )

            summary["ineligible_rows"] = int(
                (
                    results["quality_status"]
                    == "ineligible"
                ).sum()
            )

            summary["unassigned_cluster_rows"] = int(
                (
                    results["quality_status"]
                    == "unassigned_cluster"
                ).sum()
            )

            summary["unsupported_cluster_rows"] = int(
                (
                    results["quality_status"]
                    == "unsupported_cluster"
                ).sum()
            )

        # Anomaly flags.
        if "is_anomaly" in results.columns:
            summary["flagged_rows"] = int(
                results["is_anomaly"]
                .fillna(False)
                .sum()
            )

        # Processing errors.
        if "processing_error" in results.columns:
            errors = results["processing_error"]

            summary["processing_errors"] = int(
                errors.notna().sum()
            )

            summary["missing_telemetry_files"] = int(
                (
                    errors == "missing_speed_file"
                ).sum()
            )

    # --------------------------------------------------
    # 7. Print summary
    # --------------------------------------------------

    summary_path = output.with_name(
        f"{output.stem}_summary.json"
    )

    with open(summary_path, "w") as file:
        json.dump(
            summary,
            file,
            indent=2,
            default=str,
        )

    print("\n========== BATCH INFERENCE SUMMARY ==========")

    print(
        json.dumps(
            summary,
            indent=2,
            default=str,
        )
    )

    print("\nSummary saved to:", summary_path)


if __name__ == "__main__":
    main()
