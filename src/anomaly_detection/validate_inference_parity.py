
"""Full-dataset parity validation for DT-CARGO inference."""

from pathlib import Path
import sys
import json

import numpy as np
import pandas as pd

ANOMALY_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ANOMALY_DIR.parents[1]

sys.path.insert(0, str(ANOMALY_DIR))

from src.inference import (
    load_cluster_model_bundles,
    score_track,
)

DATASET_PATH = ANOMALY_DIR / "reports" / "modeling_dataset.csv"
PREDICTION_DIR = ANOMALY_DIR / "reports" / "cluster_models"
SPEED_ROOT = PROJECT_ROOT / "data" / "raw" / "speed"
ARTIFACT_DIR = ANOMALY_DIR / "artifacts"

OUTPUT_DIR = ANOMALY_DIR / "reports" / "cluster_models"

FEATURES = [
    "raw_speed_mean_kmh",
    "raw_speed_std",
    "low_speed_time_pct_03",
    "stop_episode_count_03",
]


def main():
    dataset = pd.read_csv(DATASET_PATH, low_memory=False)

    bundles = load_cluster_model_bundles(
        ARTIFACT_DIR,
        clusters=(0, 1, 2),
    )

    all_results = []
    cluster_summaries = []

    for cluster in (0, 1, 2):
        print(f"\n{'=' * 55}")
        print(f"VALIDATING CLUSTER {cluster}")
        print("=" * 55)

        reference = pd.read_csv(
            PREDICTION_DIR
            / f"validation_predictions_cluster_{cluster}.csv",
            low_memory=False,
        )

        metadata = dataset[
            dataset["track_id"].isin(reference["track_id"])
        ].copy()

        reference_ids = set(reference["track_id"])
        metadata_ids = set(metadata["track_id"])

        missing_metadata = reference_ids - metadata_ids

        if missing_metadata:
            raise ValueError(
                f"Cluster {cluster}: "
                f"{len(missing_metadata)} validation tracks "
                "are missing from modeling_dataset.csv."
            )

        metadata = metadata.set_index("track_id").loc[
            reference["track_id"]
        ].reset_index()

        reference_lookup = reference.set_index("track_id")

        cluster_results = []
        missing_files = []
        processing_errors = []

        for index, row in metadata.iterrows():
            track = row.to_dict()

            track_id = track["track_id"]
            vehicle_id = track["vehicle_id"]

            speed_path = (
                SPEED_ROOT
                / str(int(vehicle_id))
                / f"{int(track_id)}.csv"
            )

            if not speed_path.is_file():
                missing_files.append(track_id)
                continue

            try:
                speed = pd.read_csv(speed_path)

                inferred = score_track(
                    track,
                    speed,
                    bundles[cluster],
                )

                original = reference_lookup.loc[track_id]

                feature_differences = {}

                for feature in FEATURES:
                    old_value = original[feature]
                    new_value = inferred["features"][feature]

                    if pd.isna(old_value) and new_value is None:
                        difference = 0.0
                    elif pd.isna(old_value) or new_value is None:
                        difference = np.inf
                    else:
                        difference = abs(
                            float(old_value) - float(new_value)
                        )

                    feature_differences[feature] = difference

                original_score = float(
                    original["anomaly_score"]
                )

                inferred_score = inferred["anomaly_score"]

                score_difference = (
                    abs(original_score - inferred_score)
                    if inferred_score is not None
                    else np.inf
                )

                original_flag = bool(
                    original["is_anomaly"]
                )

                inferred_flag = inferred["is_anomaly"]

                result = {
                    "track_id": track_id,
                    "vehicle_id": vehicle_id,
                    "cluster": cluster,
                    "original_quality_status": original[
                        "quality_status"
                    ],
                    "inference_quality_status": inferred[
                        "quality_status"
                    ],
                    "original_score": original_score,
                    "inference_score": inferred_score,
                    "score_difference": score_difference,
                    "original_flag": original_flag,
                    "inference_flag": inferred_flag,
                    "flag_match": (
                        inferred_flag is not None
                        and original_flag == inferred_flag
                    ),
                    "quality_match": (
                        original["quality_status"]
                        == inferred["quality_status"]
                    ),
                    **{
                        f"{feature}_difference": difference
                        for feature, difference
                        in feature_differences.items()
                    },
                }

                cluster_results.append(result)

            except Exception as error:
                processing_errors.append({
                    "track_id": track_id,
                    "vehicle_id": vehicle_id,
                    "error": f"{type(error).__name__}: {error}",
                })

            if (index + 1) % 1000 == 0:
                print(
                    f"Processed {index + 1}/{len(metadata)} tracks"
                )

        results = pd.DataFrame(cluster_results)

        if not results.empty:
            all_results.append(results)

            score_differences = results[
                "score_difference"
            ].to_numpy(dtype=float)

            cluster_summary = {
                "cluster": cluster,
                "reference_tracks": len(reference),
                "compared_tracks": len(results),
                "missing_telemetry_files": len(missing_files),
                "processing_errors": len(processing_errors),
                "score_parity": bool(
                    np.allclose(
                        results["original_score"],
                        results["inference_score"],
                        atol=1e-8,
                        rtol=1e-8,
                    )
                ),
                "flag_agreement": float(
                    results["flag_match"].mean()
                ),
                "quality_status_agreement": float(
                    results["quality_match"].mean()
                ),
                "maximum_score_difference": float(
                    np.max(score_differences)
                ),
                "maximum_feature_differences": {
                    feature: float(
                        results[
                            f"{feature}_difference"
                        ].max()
                    )
                    for feature in FEATURES
                },
            }

        else:
            cluster_summary = {
                "cluster": cluster,
                "reference_tracks": len(reference),
                "compared_tracks": 0,
                "missing_telemetry_files": len(missing_files),
                "processing_errors": len(processing_errors),
                "score_parity": False,
                "flag_agreement": None,
                "quality_status_agreement": None,
            }

        cluster_summaries.append(cluster_summary)

        print(
            json.dumps(
                cluster_summary,
                indent=2,
            )
        )

        if missing_files:
            print(
                f"Missing telemetry examples: "
                f"{missing_files[:10]}"
            )

        if processing_errors:
            print(
                f"Processing error examples: "
                f"{processing_errors[:5]}"
            )

    # Combine all clusters.
    if all_results:
        final_results = pd.concat(
            all_results,
            ignore_index=True,
        )
    else:
        raise RuntimeError(
            "No validation tracks could be compared."
        )

    # Overall summary.
    overall_summary = {
        "reference_tracks": int(
            sum(item["reference_tracks"] for item in cluster_summaries)
        ),
        "compared_tracks": int(len(final_results)),
        "missing_telemetry_files": int(
            sum(
                item["missing_telemetry_files"]
                for item in cluster_summaries
            )
        ),
        "processing_errors": int(
            sum(
                item["processing_errors"]
                for item in cluster_summaries
            )
        ),
        "score_parity": bool(
            np.allclose(
                final_results["original_score"],
                final_results["inference_score"],
                atol=1e-8,
                rtol=1e-8,
            )
        ),
        "flag_agreement": float(
            final_results["flag_match"].mean()
        ),
        "quality_status_agreement": float(
            final_results["quality_match"].mean()
        ),
        "maximum_score_difference": float(
            final_results["score_difference"].max()
        ),
    }

    # Save outputs.
    results_path = OUTPUT_DIR / "full_inference_parity.csv"

    summary_path = OUTPUT_DIR / "full_inference_parity_summary.json"

    final_results.to_csv(
        results_path,
        index=False,
    )

    summary = {
        "overall": overall_summary,
        "clusters": cluster_summaries,
    }

    with open(summary_path, "w") as file:
        json.dump(
            summary,
            file,
            indent=2,
        )

    print("\n========== OVERALL PARITY SUMMARY ==========")
    print(json.dumps(summary, indent=2))

    print("\nSaved detailed results:", results_path)
    print("Saved summary:", summary_path)


if __name__ == "__main__":
    main()
