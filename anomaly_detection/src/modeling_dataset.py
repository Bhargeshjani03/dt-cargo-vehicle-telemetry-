"""Build the track-level modelling table from metadata and raw speed files."""

from collections import Counter
import json
import math
from pathlib import Path
from typing import Any, Optional, Tuple

import pandas as pd

from src.features import FEATURE_COLUMNS, extract_track_features
from src.quality import CORE_FEATURES, QUALITY_FLAG_NAMES, assess_track_quality


EXTENDED_FEATURES = CORE_FEATURES + ("duration_minutes", "distance_km")

CONTEXT_COLUMNS = (
    "start_time",
    "stop_time",
    "distance",
    "track_gap",
    "avg_speed",
    "max_speed",
    "avg_hdop",
    "n_signal_loss",
    "d_signal_loss",
    "r_signal_loss",
    "home_base",
    "long_haul",
    "rest_area",
    "service_area_fuel",
    "industrial_area",
    "cid",
    "gross_vehicle_weight",
    "total_mass_with_trailer",
    "axle_class",
)


def _finite_number(value: Any) -> Optional[float]:
    """Convert a scalar to a finite float, or return None."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _id_component(value: Any, column_name: str) -> str:
    """Format numeric track/vehicle IDs for speed-file paths."""
    number = _finite_number(value)
    if number is None:
        raise ValueError(f"{column_name} is missing or invalid: {value!r}")
    if number.is_integer():
        return str(int(number))
    return str(value).strip()


def _duration_seconds(track: pd.Series) -> Optional[float]:
    """Get duration from the saved field or derive it from timestamps."""
    duration = _finite_number(track.get("duration_seconds"))
    if duration is not None:
        return duration

    start = pd.to_datetime(track.get("start_time"), utc=True, errors="coerce")
    stop = pd.to_datetime(track.get("stop_time"), utc=True, errors="coerce")
    if pd.isna(start) or pd.isna(stop):
        return None

    return float((stop - start).total_seconds())


def _status_with_feature_check(
    quality_result: dict,
    feature_values: dict,
    required_features: Tuple[str, ...],
) -> tuple:
    """Mark a model-specific row ineligible if any required feature is missing."""
    missing_features = [
        name
        for name in required_features
        if _finite_number(feature_values.get(name)) is None
    ]

    reasons = list(quality_result["ineligible_reasons"])
    reasons.extend(
        f"missing_required_feature:{name}" for name in missing_features
    )

    if reasons:
        status = "ineligible"
    else:
        status = quality_result["quality_status"]

    return status, reasons, missing_features


def _summarize_model(table: pd.DataFrame, model_name: str) -> dict:
    status_column = f"quality_status_{model_name}"
    reason_column = f"ineligible_reasons_{model_name}"
    missing_column = f"missing_required_features_{model_name}"

    status_counts = table[status_column].value_counts().to_dict()

    reason_counts = Counter()
    for value in table[reason_column]:
        if value:
            reason_counts.update(value.split(";"))

    missing_counts = Counter()
    for value in table[missing_column]:
        if value:
            missing_counts.update(value.split(";"))

    return {
        "eligible": int(status_counts.get("eligible", 0)),
        "eligible_with_warnings": int(
            status_counts.get("eligible_with_warnings", 0)
        ),
        "ineligible": int(status_counts.get("ineligible", 0)),
        "ineligibility_reasons": dict(sorted(reason_counts.items())),
        "missing_required_feature_counts": dict(sorted(missing_counts.items())),
    }


def build_modeling_table(
    enriched_tracks: pd.DataFrame,
    speed_root: str,
    min_valid_telemetry_seconds: Optional[float] = None,
) -> tuple:
    """Build core and extended modelling rows, reading one speed file at a time.

    Speed files must be stored as:
        speed_root/<vehicle_id>/<track_id>.csv

    Returns:
        (modeling_table, eligibility_summary)
    """
    required_metadata_columns = {"track_id", "vehicle_id"}
    missing_columns = required_metadata_columns.difference(enriched_tracks.columns)
    if missing_columns:
        raise ValueError(
            "Enriched tracks are missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    if enriched_tracks["track_id"].isna().any():
        raise ValueError("Enriched tracks contain missing track_id values.")
    if enriched_tracks["track_id"].duplicated().any():
        raise ValueError("Enriched tracks contain duplicate track_id values.")
    if enriched_tracks["vehicle_id"].isna().any():
        raise ValueError("Enriched tracks contain missing vehicle_id values.")

    speed_root_path = Path(speed_root)
    records = []

    for _, track in enriched_tracks.iterrows():
        track_id = track["track_id"]
        vehicle_id = track["vehicle_id"]
        vehicle_folder = _id_component(vehicle_id, "vehicle_id")
        track_file = _id_component(track_id, "track_id")
        speed_path = speed_root_path / vehicle_folder / f"{track_file}.csv"

        processing_error = None
        if not speed_path.is_file():
            speed = pd.DataFrame(columns=["epoch", "speed"])
            processing_error = "missing_speed_file"
        else:
            try:
                speed = pd.read_csv(speed_path)
            except Exception as exc:
                speed = pd.DataFrame(columns=["epoch", "speed"])
                processing_error = f"speed_read_error:{type(exc).__name__}"

        feature_values = extract_track_features(speed)

        duration_seconds = _duration_seconds(track)
        duration_minutes = (
            duration_seconds / 60.0
            if duration_seconds is not None and duration_seconds >= 0
            else None
        )

        distance = _finite_number(track.get("distance"))
        distance_km = distance / 1000.0 if distance is not None else None

        feature_values["duration_minutes"] = duration_minutes
        feature_values["distance_km"] = distance_km

        quality_core = assess_track_quality(
            track,
            speed,
            required_features=CORE_FEATURES,
            min_valid_telemetry_seconds=min_valid_telemetry_seconds,
        )
        quality_extended = assess_track_quality(
            track,
            speed,
            required_features=EXTENDED_FEATURES,
            min_valid_telemetry_seconds=min_valid_telemetry_seconds,
        )

        status_core, reasons_core, missing_core = _status_with_feature_check(
            quality_core, feature_values, CORE_FEATURES
        )
        status_extended, reasons_extended, missing_extended = (
            _status_with_feature_check(
                quality_extended, feature_values, EXTENDED_FEATURES
            )
        )

        record = {
            "track_id": track_id,
            "vehicle_id": vehicle_id,
            "fleet_test_id": track.get("fleet_test_id"),
            **{name: feature_values.get(name) for name in FEATURE_COLUMNS},
            "duration_minutes": duration_minutes,
            "distance_km": distance_km,
            "quality_status": status_core,
            "quality_status_core": status_core,
            "quality_status_extended": status_extended,
            "reason_codes": ";".join(quality_core["reason_codes"]),
            "ineligible_reasons_core": ";".join(reasons_core),
            "ineligible_reasons_extended": ";".join(reasons_extended),
            "missing_required_features_core": ";".join(missing_core),
            "missing_required_features_extended": ";".join(missing_extended),
            "processing_error": processing_error,
            "telemetry_coverage_ratio": quality_core["telemetry_coverage_ratio"],
        }

        for name in CONTEXT_COLUMNS:
            if name in enriched_tracks.columns:
                record[name] = track.get(name)

        for name, value in quality_core["quality_flags"].items():
            record[f"flag_{name}"] = bool(value)

        for name, value in feature_values.items():
            if name not in FEATURE_COLUMNS and name not in {
                "duration_minutes",
                "distance_km",
            }:
                record[name] = value

        records.append(record)

    table = pd.DataFrame.from_records(records)

    summary = {
        "input_tracks": int(len(enriched_tracks)),
        "models": {
            "core_four_feature": _summarize_model(table, "core"),
            "extended_six_feature": _summarize_model(table, "extended"),
        },
        "feature_definitions": {
            "raw_speed_mean_kmh": "Mean raw speed in km/h",
            "raw_speed_std": "Sample standard deviation in m/s",
            "low_speed_time_pct_03": "0-100 percentage of valid time below 0.3 m/s",
            "stop_episode_count_03": "Stop episodes of at least 30 seconds",
            "duration_minutes": "Track duration in minutes",
            "distance_km": "Recorded distance in kilometres; zero is retained",
        },
        "quality_metric_definitions": {
            "telemetry_coverage_ratio": (
                "Valid speed interval time divided by recorded track duration; "
                "quality diagnostic, not a movement-model input"
            ),
            "telemetry_coverage_low": (
                "Coverage below 80%; review warning only, no coverage-ratio exclusion"
            ),
            "telemetry_coverage_inadequate": (
                "Coverage below 50%; review warning only"
            ),
        },
    }

    return table, summary


def save_modeling_outputs(
    modeling_table: pd.DataFrame,
    eligibility_summary: dict,
    output_directory: str,
) -> None:
    """Write the modelling table and eligibility summary to a report folder."""
    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)

    modeling_table.to_csv(output_path / "modeling_dataset.csv", index=False)

    with (output_path / "eligibility_summary.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(eligibility_summary, file, indent=2)