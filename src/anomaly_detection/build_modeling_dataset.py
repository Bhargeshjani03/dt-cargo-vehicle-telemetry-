
"""Build the quality-aware modelling table."""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


ANOMALY_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ANOMALY_DIR))

from src.modeling_dataset import (
    build_modeling_table,
    save_modeling_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build the track-level modelling dataset "
            "with quality assessment and cluster assignments."
        )
    )

    parser.add_argument(
        "--data-root",
        type=Path,
        required=True,
        help="Path to the existing data folder.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional random sample size for a smoke run.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ANOMALY_DIR / "reports",
        help="Where to save the modelling table and summary.",
    )

    parser.add_argument(
        "--cluster-assignments",
        type=Path,
        default=(
            ANOMALY_DIR
            / "data"
            / "track_cluster_assignments.csv"
        ),
        help="Path to the previously generated cluster assignments CSV.",
    )

    args = parser.parse_args()

    # Validate optional sample size.
    if args.limit is not None and args.limit <= 0:
        raise ValueError(
            "--limit must be a positive integer."
        )

    # Input paths.
    project_root = Path(__file__).resolve().parents[2]
    enriched_path = (
        project_root / "data" / "processed" / "tracks_with_behavioral_features.csv"
    )

    speed_root = project_root / "data" / "raw" / "speed"

    cluster_path = (
        ANOMALY_DIR / "data" / "track_cluster_assignments.csv"
    )

    

    # Validate input files and directories.
    if not enriched_path.is_file():
        raise FileNotFoundError(
            f"Enriched tracks file not found: {enriched_path}"
        )

    if not speed_root.is_dir():
        raise FileNotFoundError(
            f"Speed data directory not found: {speed_root}"
        )

    if not cluster_path.is_file():
        raise FileNotFoundError(
            f"Cluster assignments file not found: {cluster_path}"
        )

    # Load enriched track metadata.
    print("Loading enriched track metadata...")

    tracks = pd.read_csv(enriched_path)

    print(f"Total enriched tracks: {len(tracks)}")

    # Load previously generated cluster assignments.
    print("Loading cluster assignments...")

    cluster_assignments = pd.read_csv(cluster_path)

    print(
        "Total cluster assignments: "
        f"{len(cluster_assignments)}"
    )

    print("\nCluster distribution:")

    print(
        cluster_assignments["cluster"]
        .value_counts()
        .sort_index()
    )

    # Optional sample for smoke testing.
    if args.limit is not None:
        tracks = tracks.sample(
            n=min(args.limit, len(tracks)),
            random_state=42,
        )

        print(
            f"\nSmoke run enabled. Processing "
            f"{len(tracks)} sampled tracks."
        )

    # Build the modelling dataset.
    print("\nBuilding modelling dataset...")

    table, summary = build_modeling_table(
        enriched_tracks=tracks,
        speed_root=str(speed_root),
        cluster_assignments=cluster_assignments,
    )

    # Save modelling outputs.
    save_modeling_outputs(
        modeling_table=table,
        eligibility_summary=summary,
        output_directory=str(args.output_dir),
    )

    # Display final summary.
    print("\n========== MODELLING DATASET SUMMARY ==========")

    print(f"Input tracks processed: {len(tracks)}")
    print(f"Output tracks: {len(table)}")

    print(
        "Cluster-assigned tracks: "
        f"{summary['cluster_assignments']['assigned']}"
    )

    print(
        "Unassigned tracks: "
        f"{summary['cluster_assignments']['unassigned']}"
    )

    print("\nCluster distribution:")

    print(
        json.dumps(
            summary["cluster_assignments"]["distribution"],
            indent=2,
        )
    )

    print(f"\nReports saved to: {args.output_dir}")

    print("\nComplete eligibility summary:")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
