"""Build the quality-aware modelling table."""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


ANOMALY_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ANOMALY_DIR))

from src.modeling_dataset import build_modeling_table, save_modeling_outputs


def main() -> None:
    parser = argparse.ArgumentParser()
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
    args = parser.parse_args()

    if args.limit is not None and args.limit <= 0:
        raise ValueError("--limit must be a positive integer.")

    enriched_path = (
        args.data_root / "processed" / "tracks_with_behavioral_features.csv"
    )
    speed_root = args.data_root / "raw" / "speed"

    tracks = pd.read_csv(enriched_path)
    if args.limit is not None:
        tracks = tracks.sample(
            n=min(args.limit, len(tracks)),
            random_state=42,
        )

    table, summary = build_modeling_table(
        enriched_tracks=tracks,
        speed_root=str(speed_root),
    )

    save_modeling_outputs(
        modeling_table=table,
        eligibility_summary=summary,
        output_directory=str(args.output_dir),
    )

    print(f"Input tracks processed: {len(tracks)}")
    print(f"Reports saved to: {args.output_dir}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()