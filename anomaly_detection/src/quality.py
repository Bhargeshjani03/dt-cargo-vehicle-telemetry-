"""Quality checks for completed DT-CARGO tracks."""

from typing import Any, Mapping, Optional, Sequence
import math

import numpy as np
import pandas as pd


CORE_FEATURES = (
    "raw_speed_mean_kmh",
    "raw_speed_std",
    "low_speed_time_pct_03",
    "stop_episode_count_03",
)
# Coverage = valid telemetry interval time / recorded track duration.
TELEMETRY_COVERAGE_INELIGIBLE_BELOW = 0.50
TELEMETRY_COVERAGE_WARNING_BELOW = 0.80

QUALITY_FLAG_NAMES = (
    "insufficient_telemetry",
    "telemetry_coverage_low",
    "telemetry_coverage_inadequate",
    "duration_invalid",
    "distance_missing",
    "avg_speed_missing",
    "avg_speed_negative",
    "avg_speed_gt_max_speed",
    "n_signal_loss_negative",
    "d_signal_loss_invalid",
    "r_signal_loss_missing",
    "r_signal_loss_out_of_range",
    "zero_distance",
    "zero_distance_speed_issue",
    "track_gap_missing",
)


def _get_value(row: Mapping[str, Any], key: str) -> Any:
    """Return a value from a dict-like row, including a pandas Series."""
    try:
        return row.get(key)
    except AttributeError:
        return None


def _as_finite_float(value: Any) -> Optional[float]:
    """Convert a value to a finite float, or return None."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _duration_seconds(track: Mapping[str, Any]) -> Optional[float]:
    """Use the saved duration when present; otherwise derive it from timestamps."""
    duration = _as_finite_float(_get_value(track, "duration_seconds"))
    if duration is not None:
        return duration

    start = pd.to_datetime(_get_value(track, "start_time"), utc=True, errors="coerce")
    stop = pd.to_datetime(_get_value(track, "stop_time"), utc=True, errors="coerce")

    if pd.isna(start) or pd.isna(stop):
        return None

    return float((stop - start).total_seconds())


def _telemetry_evidence(speed: Any) -> dict:
    """Summarize valid observations and intervals from one track's speed file."""
    empty_result = {
        "valid_observations": 0,
        "telemetry_span_seconds": 0.0,
        "valid_interval_count": 0,
        "valid_telemetry_time_seconds": 0.0,
    }

    if speed is None or not hasattr(speed, "columns"):
        return empty_result

    if not {"epoch", "speed"}.issubset(speed.columns):
        return empty_result

    rows = speed.loc[:, ["epoch", "speed"]].copy()
    rows["epoch"] = pd.to_numeric(rows["epoch"], errors="coerce")
    rows["speed"] = pd.to_numeric(rows["speed"], errors="coerce")
    rows = rows.replace([np.inf, -np.inf], np.nan).dropna(subset=["epoch", "speed"])

    if rows.empty:
        return empty_result

    rows = rows.sort_values("epoch", kind="mergesort")
    times = rows["epoch"].to_numpy(dtype=float)
    span = float(times[-1] - times[0]) if len(times) > 1 else 0.0

    intervals = np.diff(times)
    valid_intervals = intervals[(intervals > 0) & (intervals <= 2)]

    return {
        "valid_observations": int(len(rows)),
        "telemetry_span_seconds": span,
        "valid_interval_count": int(len(valid_intervals)),
        "valid_telemetry_time_seconds": float(valid_intervals.sum()),
    }


def assess_track_quality(
    track_metadata: Mapping[str, Any],
    raw_speed_telemetry: Any,
    required_features: Sequence[str] = CORE_FEATURES,
    min_valid_telemetry_seconds: Optional[float] = None,
) -> dict:
    """Return quality flags and a model-specific track eligibility status.

    Coverage thresholds are diagnostic warnings, not standalone eligibility
    cutoffs: the faculty brief does not establish a minimum coverage ratio.
    Coverage is valid interval time divided by recorded track duration. Tracks
    still require sufficient valid telemetry and every required feature. An
    optional minimum valid-time cutoff remains available for explicit studies.
    """
    if (
        min_valid_telemetry_seconds is not None
        and min_valid_telemetry_seconds < 0
    ):
        raise ValueError("min_valid_telemetry_seconds must be non-negative.")

    evidence = _telemetry_evidence(raw_speed_telemetry)
    flags = {name: False for name in QUALITY_FLAG_NAMES}

    insufficient = (
        evidence["valid_observations"] < 3
        or evidence["valid_interval_count"] == 0
    )
    if (
        min_valid_telemetry_seconds is not None
        and evidence["valid_telemetry_time_seconds"] < min_valid_telemetry_seconds
    ):
        insufficient = True
    flags["insufficient_telemetry"] = bool(insufficient)

    duration = _duration_seconds(track_metadata)
    flags["duration_invalid"] = duration is None or duration < 0

    telemetry_coverage_ratio = None
    if duration is not None and duration > 0:
        telemetry_coverage_ratio = (
            evidence["valid_telemetry_time_seconds"] / duration
        )
        flags["telemetry_coverage_low"] = (
            telemetry_coverage_ratio < TELEMETRY_COVERAGE_WARNING_BELOW
        )
        flags["telemetry_coverage_inadequate"] = (
            telemetry_coverage_ratio < TELEMETRY_COVERAGE_INELIGIBLE_BELOW
        )
    distance = _as_finite_float(_get_value(track_metadata, "distance"))
    avg_speed = _as_finite_float(_get_value(track_metadata, "avg_speed"))
    max_speed = _as_finite_float(_get_value(track_metadata, "max_speed"))
    n_signal_loss = _as_finite_float(_get_value(track_metadata, "n_signal_loss"))
    d_signal_loss = _as_finite_float(_get_value(track_metadata, "d_signal_loss"))
    r_signal_loss = _as_finite_float(_get_value(track_metadata, "r_signal_loss"))
    track_gap = _as_finite_float(_get_value(track_metadata, "track_gap"))

    flags["distance_missing"] = distance is None
    flags["avg_speed_missing"] = avg_speed is None
    flags["avg_speed_negative"] = avg_speed is not None and avg_speed < 0
    flags["avg_speed_gt_max_speed"] = (
        avg_speed is not None
        and max_speed is not None
        and avg_speed > max_speed
    )
    flags["n_signal_loss_negative"] = (
        n_signal_loss is not None and n_signal_loss < 0
    )
    flags["d_signal_loss_invalid"] = (
        d_signal_loss is None
        or d_signal_loss < 0
        or (distance is not None and d_signal_loss > distance)
    )
    flags["r_signal_loss_missing"] = r_signal_loss is None
    flags["r_signal_loss_out_of_range"] = (
        r_signal_loss is not None
        and not 0 <= r_signal_loss <= 1
    )
    flags["zero_distance"] = distance == 0 if distance is not None else False
    flags["zero_distance_speed_issue"] = (
        distance == 0 and max_speed is not None and max_speed > 1
    )
    flags["track_gap_missing"] = track_gap is None

    blocking_reasons = []
    if flags["insufficient_telemetry"]:
        blocking_reasons.append("insufficient_telemetry")
    if "duration_minutes" in required_features and flags["duration_invalid"]:
        blocking_reasons.append("duration_invalid")
    if "distance_km" in required_features and flags["distance_missing"]:
        blocking_reasons.append("distance_missing")

    reason_codes = [name for name, value in flags.items() if value]

    if blocking_reasons:
        status = "ineligible"
    elif reason_codes:
        status = "eligible_with_warnings"
    else:
        status = "eligible"

    return {
        "track_id": _get_value(track_metadata, "track_id"),
        "quality_status": status,
        "quality_flags": flags,
        "reason_codes": reason_codes,
        "ineligible_reasons": blocking_reasons,
        "telemetry_evidence": evidence,
        "telemetry_coverage_ratio": telemetry_coverage_ratio,
    }