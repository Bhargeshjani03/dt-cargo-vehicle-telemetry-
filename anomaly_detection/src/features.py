"""Movement feature extraction from one track's raw speed telemetry."""

from typing import Any

import numpy as np
import pandas as pd


LOW_SPEED_THRESHOLD_MPS = 0.3
MAX_VALID_INTERVAL_SECONDS = 2.0
MIN_STOP_DURATION_SECONDS = 30.0

FEATURE_COLUMNS = (
    "raw_speed_mean_kmh",
    "raw_speed_std",
    "low_speed_time_pct_03",
    "stop_episode_count_03",
)


def _count_stop_episodes(
    intervals: np.ndarray,
    valid_interval_mask: np.ndarray,
    speeds_mps: np.ndarray,
) -> int:
    """Count contiguous low-speed interval runs lasting at least 30 seconds."""
    episode_count = 0
    current_episode_seconds = 0.0

    for index, interval_seconds in enumerate(intervals):
        is_low_speed_interval = (
            valid_interval_mask[index]
            and speeds_mps[index] < LOW_SPEED_THRESHOLD_MPS
        )

        if is_low_speed_interval:
            current_episode_seconds += float(interval_seconds)
        else:
            if current_episode_seconds >= MIN_STOP_DURATION_SECONDS:
                episode_count += 1
            current_episode_seconds = 0.0

    if current_episode_seconds >= MIN_STOP_DURATION_SECONDS:
        episode_count += 1

    return episode_count


def extract_track_features(raw_speed_telemetry: Any) -> dict:
    """Calculate the four core movement features for one track.

    Each interval is assigned the speed observed at its starting timestamp.
    Only intervals satisfying 0 < dt <= 2 seconds contribute to the
    low-speed percentage and stop-episode count.
    """
    if raw_speed_telemetry is None or not hasattr(raw_speed_telemetry, "columns"):
        raise TypeError("raw_speed_telemetry must be a pandas DataFrame.")

    required_columns = {"epoch", "speed"}
    missing_columns = required_columns.difference(raw_speed_telemetry.columns)
    if missing_columns:
        raise ValueError(
            "Speed telemetry is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    rows = raw_speed_telemetry.loc[:, ["epoch", "speed"]].copy()
    rows["epoch"] = pd.to_numeric(rows["epoch"], errors="coerce")
    rows["speed"] = pd.to_numeric(rows["speed"], errors="coerce")
    rows = rows.replace([np.inf, -np.inf], np.nan)

    input_observation_count = int(len(rows))
    rows = rows.dropna(subset=["epoch", "speed"])
    invalid_observation_count = input_observation_count - int(len(rows))

    if rows.empty:
        return {
            "raw_speed_mean_kmh": None,
            "raw_speed_std": None,
            "low_speed_time_pct_03": None,
            "stop_episode_count_03": None,
            "observation_count": 0,
            "invalid_observation_count": invalid_observation_count,
            "telemetry_span_seconds": 0.0,
            "valid_interval_count": 0,
            "valid_telemetry_time_seconds": 0.0,
            "excluded_interval_count": 0,
        }

    rows = rows.sort_values("epoch", kind="mergesort")
    times = rows["epoch"].to_numpy(dtype=float)
    speeds_mps = rows["speed"].to_numpy(dtype=float)

    speed_mean = (
        float(np.mean(speeds_mps) * 3.6)
        if len(speeds_mps) >= 1
        else None
    )
    speed_std = (
        float(np.std(speeds_mps, ddof=1))
        if len(speeds_mps) >= 2
        else None
    )

    intervals = np.diff(times)
    valid_interval_mask = (
        (intervals > 0) & (intervals <= MAX_VALID_INTERVAL_SECONDS)
    )
    valid_intervals = intervals[valid_interval_mask]
    valid_time_seconds = float(np.sum(valid_intervals))
    telemetry_span_seconds = (
        float(times[-1] - times[0]) if len(times) >= 2 else 0.0
    )

    if valid_time_seconds > 0:
        low_speed_time_seconds = float(
            np.sum(
                intervals[
                    valid_interval_mask
                    & (speeds_mps[:-1] < LOW_SPEED_THRESHOLD_MPS)
                ]
            )
        )
        low_speed_pct = 100.0 * low_speed_time_seconds / valid_time_seconds
    else:
        low_speed_pct = None

    stop_episode_count = (
        _count_stop_episodes(intervals, valid_interval_mask, speeds_mps)
        if len(intervals) > 0
        else 0
    )

    return {
        "raw_speed_mean_kmh": speed_mean,
        "raw_speed_std": speed_std,
        "low_speed_time_pct_03": low_speed_pct,
        "stop_episode_count_03": int(stop_episode_count),
        "observation_count": int(len(rows)),
        "invalid_observation_count": invalid_observation_count,
        "telemetry_span_seconds": telemetry_span_seconds,
        "valid_interval_count": int(np.sum(valid_interval_mask)),
        "valid_telemetry_time_seconds": valid_time_seconds,
        "excluded_interval_count": int(len(intervals) - np.sum(valid_interval_mask)),
    }