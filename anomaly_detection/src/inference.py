"""Reusable scoring for completed DT-CARGO tracks."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Union

import joblib
import numpy as np
import pandas as pd

from src.features import FEATURE_COLUMNS, extract_track_features
from src.quality import CORE_FEATURES, assess_track_quality


EXTENDED_FEATURES = CORE_FEATURES + ("duration_minutes", "distance_km")
SUPPORTED_FEATURES = set(FEATURE_COLUMNS) | {"duration_minutes", "distance_km"}


def _metadata_dict(track_metadata: Any) -> dict:
    if isinstance(track_metadata, pd.Series):
        return track_metadata.to_dict()
    if isinstance(track_metadata, Mapping):
        return dict(track_metadata)
    raise TypeError("track_metadata must be a mapping or pandas Series.")


def _finite_float(value: Any) -> Optional[float]:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _duration_seconds(track: Mapping[str, Any]) -> Optional[float]:
    duration = _finite_float(track.get("duration_seconds"))
    if duration is not None:
        return duration

    start = pd.to_datetime(track.get("start_time"), utc=True, errors="coerce")
    stop = pd.to_datetime(track.get("stop_time"), utc=True, errors="coerce")
    if pd.isna(start) or pd.isna(stop):
        return None
    return float((stop - start).total_seconds())


def _validate_bundle(bundle: Mapping[str, Any]) -> tuple:
    required = {"model", "feature_names", "threshold", "model_version"}
    missing = required.difference(bundle)
    if missing:
        raise ValueError("Model bundle is missing: " + ", ".join(sorted(missing)))

    model = bundle["model"]
    if not hasattr(model, "decision_function"):
        raise TypeError("Model bundle does not contain a decision_function model.")

    feature_names = tuple(bundle["feature_names"])
    if not feature_names:
        raise ValueError("Model bundle feature_names cannot be empty.")
    if len(set(feature_names)) != len(feature_names):
        raise ValueError("Model bundle feature_names contains duplicates.")
    unsupported = set(feature_names).difference(SUPPORTED_FEATURES)
    if unsupported:
        raise ValueError(
            "Unsupported model features: " + ", ".join(sorted(unsupported))
        )

    expected_width = getattr(model, "n_features_in_", None)
    if expected_width is not None and int(expected_width) != len(feature_names):
        raise ValueError("Model feature count does not match bundle feature_names.")

    transform = bundle.get("transform", "identity")
    if transform != "identity":
        raise ValueError(
            f"Unsupported saved transform {transform!r}; only identity bundles "
            "are currently supported by this inference module."
        )

    score_direction = bundle.get("score_direction", "higher_is_more_anomalous")
    if score_direction != "higher_is_more_anomalous":
        raise ValueError(f"Unsupported score direction: {score_direction!r}")

    threshold = _finite_float(bundle["threshold"])
    if threshold is None:
        raise ValueError("Model bundle threshold must be a finite number.")

    return model, feature_names, threshold


def load_model_bundle(model_path: Union[str, Path]) -> dict:
    """Load a trusted local joblib model bundle."""
    bundle = joblib.load(model_path)
    if not isinstance(bundle, Mapping):
        raise TypeError("The saved artifact must contain a mapping model bundle.")
    _validate_bundle(bundle)
    return dict(bundle)


def score_track(
    track_metadata: Any,
    raw_speed_telemetry: Any,
    model_bundle: Mapping[str, Any],
) -> dict:
    """Assess and score one completed track using a saved model bundle.

    The returned anomaly score is the negative Isolation Forest
    decision_function: higher values are more unusual, not probabilities.
    Ineligible tracks receive no anomaly score.
    """
    metadata = _metadata_dict(track_metadata)
    model, feature_names, threshold = _validate_bundle(model_bundle)

    track_id = metadata.get("track_id")
    if track_id is None or pd.isna(track_id) or str(track_id).strip() == "":
        raise ValueError("track_metadata must contain a valid track_id.")

    quality = assess_track_quality(
        metadata,
        raw_speed_telemetry,
        required_features=feature_names,
    )

    feature_values = {name: None for name in feature_names}
    if raw_speed_telemetry is not None:
        extracted = extract_track_features(raw_speed_telemetry)
        feature_values.update(extracted)

    duration = _duration_seconds(metadata)
    if "duration_minutes" in feature_names:
        feature_values["duration_minutes"] = (
            duration / 60.0 if duration is not None and duration >= 0 else None
        )

    if "distance_km" in feature_names:
        distance_m = _finite_float(metadata.get("distance"))
        feature_values["distance_km"] = (
            distance_m / 1000.0 if distance_m is not None else None
        )

    reason_codes = list(quality["reason_codes"])
    missing_features = [
        name for name in feature_names
        if _finite_float(feature_values.get(name)) is None
    ]
    for name in missing_features:
        code = f"missing_required_feature:{name}"
        if code not in reason_codes:
            reason_codes.append(code)

    quality_status = quality["quality_status"]
    if missing_features:
        quality_status = "ineligible"

    result = {
        "track_id": track_id,
        "vehicle_id": metadata.get("vehicle_id"),
        "start_time": metadata.get("start_time"),
        "stop_time": metadata.get("stop_time"),
        "quality_status": quality_status,
        "quality_flags": quality["quality_flags"],
        "reason_codes": reason_codes,
        "telemetry_evidence": quality["telemetry_evidence"],
        "telemetry_coverage_ratio": quality["telemetry_coverage_ratio"],
        "features": {name: feature_values.get(name) for name in feature_names},
        "anomaly_score": None,
        "is_anomaly": None,
        "threshold": threshold,
        "model_version": model_bundle["model_version"],
        "feature_engineering_version": model_bundle.get(
            "feature_engineering_version"
        ),
        "scored_at": datetime.now(timezone.utc).isoformat(),
        "processing_error": None,
    }

    if quality_status == "ineligible":
        return result

    row = pd.DataFrame(
        [[float(feature_values[name]) for name in feature_names]],
        columns=list(feature_names),
        dtype=float,
    )
    result["anomaly_score"] = float(-model.decision_function(row)[0])
    result["is_anomaly"] = bool(result["anomaly_score"] >= threshold)
    return result


def _id_component(value: Any, column_name: str) -> str:
    if value is None or pd.isna(value):
        raise ValueError(f"{column_name} is missing.")
    number = _finite_float(value)
    if number is not None and number.is_integer():
        component = str(int(number))
    else:
        component = str(value).strip()

    if (
        not component
        or component in {".", ".."}
        or "/" in component
        or "\\" in component
    ):
        raise ValueError(f"Unsafe {column_name} for a telemetry file path.")
    return component


def _flatten_result(result: Mapping[str, Any]) -> dict:
    flattened = {
        key: value
        for key, value in result.items()
        if key not in {"quality_flags", "reason_codes", "telemetry_evidence", "features"}
    }
    flattened["quality_flags"] = json.dumps(result["quality_flags"], sort_keys=True)
    flattened["reason_codes"] = json.dumps(result["reason_codes"])
    flattened["telemetry_evidence"] = json.dumps(result["telemetry_evidence"], sort_keys=True)
    flattened.update(result["features"])
    return flattened


def score_batch(
    track_metadata: pd.DataFrame,
    speed_root: Union[str, Path],
    model_bundle: Mapping[str, Any],
    existing_predictions: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Score new completed tracks from metadata and speed/<vehicle>/<track>.csv.

    Existing rows with the same track_id and model_version are skipped when
    existing_predictions is supplied. Missing or unreadable speed files are
    retained as ineligible/error rows for traceability.
    """
    if not isinstance(track_metadata, pd.DataFrame):
        raise TypeError("track_metadata must be a pandas DataFrame.")
    required_columns = {"track_id", "vehicle_id"}
    missing_columns = required_columns.difference(track_metadata.columns)
    if missing_columns:
        raise ValueError(
            "track_metadata is missing columns: "
            + ", ".join(sorted(missing_columns))
        )
    if track_metadata["track_id"].isna().any():
        raise ValueError("track_metadata contains a missing track_id.")
    if track_metadata["track_id"].duplicated().any():
        raise ValueError("track_metadata must contain unique track_id values.")
    if track_metadata["vehicle_id"].isna().any():
        raise ValueError("track_metadata contains a missing vehicle_id.")

    _validate_bundle(model_bundle)
    model_version = str(model_bundle.get("model_version", ""))
    if not model_version:
        raise ValueError("Model bundle must have a model_version.")

    already_processed = set()
    if existing_predictions is not None and not existing_predictions.empty:
        needed = {"track_id", "model_version"}
        if not needed.issubset(existing_predictions.columns):
            raise ValueError(
                "existing_predictions must contain track_id and model_version."
            )
        already_processed = {
            (_id_component(row.track_id, "track_id"), str(row.model_version))
            for row in existing_predictions[["track_id", "model_version"]].itertuples(
                index=False
            )
        }

    root = Path(speed_root)
    results = []
    for _, row in track_metadata.iterrows():
        metadata = row.to_dict()
        track_component = _id_component(metadata.get("track_id"), "track_id")
        vehicle_component = _id_component(metadata.get("vehicle_id"), "vehicle_id")
        processing_key = (track_component, model_version)
        if processing_key in already_processed:
            continue

        speed_path = root / vehicle_component / f"{track_component}.csv"
        if not speed_path.is_file():
            result = score_track(metadata, None, model_bundle)
            result["processing_error"] = "missing_speed_file"
        else:
            try:
                speed = pd.read_csv(speed_path)
                result = score_track(metadata, speed, model_bundle)
            except Exception as error:
                result = {
                    "track_id": metadata.get("track_id"),
                    "vehicle_id": metadata.get("vehicle_id"),
                    "start_time": metadata.get("start_time"),
                    "stop_time": metadata.get("stop_time"),
                    "quality_status": "ineligible",
                    "quality_flags": {},
                    "reason_codes": ["processing_error"],
                    "telemetry_evidence": {},
                    "telemetry_coverage_ratio": None,
                    "features": {name: None for name in model_bundle["feature_names"]},
                    "anomaly_score": None,
                    "is_anomaly": None,
                    "threshold": model_bundle["threshold"],
                    "model_version": model_version,
                    "feature_engineering_version": model_bundle.get(
                        "feature_engineering_version"
                    ),
                    "scored_at": datetime.now(timezone.utc).isoformat(),
                    "processing_error": f"{type(error).__name__}: {error}",
                }

        result["raw_speed_path"] = str(speed_path)
        results.append(_flatten_result(result))
        already_processed.add(processing_key)

    return pd.DataFrame(results)
