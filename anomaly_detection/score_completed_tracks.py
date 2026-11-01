"""Command-line batch scoring for new completed DT-CARGO tracks."""

import argparse
import json
from pathlib import Path

import pandas as pd

from src.inference import load_model_bundle, score_batch


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tracks-csv", required=True, help="New track metadata CSV.")
    parser.add_argument("--speed-root", required=True, help="Root containing vehicle/track speed CSVs.")
    parser.add_argument("--model-bundle", required=True, help="Trusted local .joblib bundle.")
    parser.add_argument("--output-csv", required=True, help="Where to save scored results.")
    parser.add_argument(
        "--existing-predictions",
        help="Optional CSV used to skip track_id/model_version pairs already scored.",
    )
    args = parser.parse_args()

    tracks = pd.read_csv(args.tracks_csv)
    existing = (
        pd.read_csv(args.existing_predictions)
        if args.existing_predictions
        else None
    )
    bundle = load_model_bundle(args.model_bundle)
    results = score_batch(
        track_metadata=tracks,
        speed_root=args.speed_root,
        model_bundle=bundle,
        existing_predictions=existing,
    )

    output = Path(args.output_csv)
    output.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output, index=False)

    summary = {
        "model_version": bundle["model_version"],
        "scored_rows": int(len(results)),
        "eligible_rows": int(results["quality_status"].isin(
            ["eligible", "eligible_with_warnings"]
        ).sum()) if not results.empty else 0,
        "ineligible_rows": int((results["quality_status"] == "ineligible").sum())
        if not results.empty else 0,
        "flagged_rows": int(results["is_anomaly"].fillna(False).sum())
        if not results.empty else 0,
        "processing_errors": int(results["processing_error"].notna().sum())
        if not results.empty else 0,
        "output_csv": str(output),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
