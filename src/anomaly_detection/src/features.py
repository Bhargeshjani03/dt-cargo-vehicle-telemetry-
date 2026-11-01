
"""Movement feature extraction from one track's raw speed telemetry."""

from typing import Any

import numpy as np
import pandas as pd


LOW_SPEED_THRESHOLD_MPS = 0.3
MAX_VALID_INTERVAL_SECONDS = 2.0
MIN_STOP_DURATION_SECONDS = 30.0

# Keep this interface stable for modeling_dataset.py and existing imports.
FEATURE_COLUMNS = (
    "raw_speed_mean_kmh",
    "raw_speed_std",
    "low_speed_time_pct_03",
    "stop_episode_count_03",
)


def _empty_result(
    invalid_timestamp_count: int,
    invalid_speed_count: int,
    invalid_observation_count: int,
    duplicate_timestamp_count: int,
    observation_count: int,
) -> dict:
    """Return features when no valid telemetry intervals are available."""

    return {
        "raw_speed_mean_kmh": None,
        "raw_speed_std": None,
        "low_speed_time_pct_03": np.nan,
        "stop_episode_count_03": np.nan,
        "stop_time_pct_03": np.nan,
        "longest_stop_seconds_03": np.nan,
        "stop_episode_durations_seconds_03": [],
        "observation_count": observation_count,
        "invalid_observation_count": invalid_observation_count,
        "invalid_timestamp_count": invalid_timestamp_count,
        "invalid_speed_count": invalid_speed_count,
        "negative_speed_count": 0,
        "duplicate_timestamp_count": duplicate_timestamp_count,
        "telemetry_span_seconds": 0.0,
        "valid_interval_count": 0,
        "valid_telemetry_time_seconds": 0.0,
        "excluded_interval_count": 0,
    }


def extract_track_features(raw_speed_telemetry: Any) -> dict:
    """Extract speed and stop features from one track's telemetry.

    Stop-related calculations follow these rules:
    - Valid intervals satisfy 0 < dt <= 2 seconds.
    - Both endpoint speeds must be below 0.3 m/s.
    - Invalid timestamps split the original sequence.
    - Invalid speeds and duplicate timestamps break interval continuity.
    - A stop episode qualifies when its duration is at least 30 seconds.

    Speed statistics use all valid non-negative speed observations,
    independently of timestamp validity.

    Returns:
        Speed statistics, stop features, and telemetry quality diagnostics.
    """

    if (
        raw_speed_telemetry is None
        or not hasattr(raw_speed_telemetry, "columns")
    ):
        raise TypeError(
            "raw_speed_telemetry must be a pandas DataFrame."
        )

    required_columns = {"epoch", "speed"}
    missing_columns = required_columns.difference(
        raw_speed_telemetry.columns
    )

    if missing_columns:
        raise ValueError(
            "Speed telemetry is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    rows = raw_speed_telemetry.loc[:, ["epoch", "speed"]].copy()

    rows["epoch"] = pd.to_numeric(
        rows["epoch"], errors="coerce"
    )
    rows["speed"] = pd.to_numeric(
        rows["speed"], errors="coerce"
    )

    rows = rows.replace([np.inf, -np.inf], np.nan)

    # Number of original input rows.
    observation_count = len(rows)

    invalid_timestamp_mask = rows["epoch"].isna()

    invalid_speed_mask = (
        rows["speed"].isna()
        | (rows["speed"] < 0)
    )

    invalid_timestamp_count = int(
        invalid_timestamp_mask.sum()
    )

    invalid_speed_count = int(
        invalid_speed_mask.sum()
    )

    negative_speed_count = int(
        (
            rows["speed"].notna()
            & (rows["speed"] < 0)
        ).sum()
    )

    # Count unique invalid rows, not individual invalid conditions.
    invalid_observation_count = int(
        (
            invalid_timestamp_mask
            | invalid_speed_mask
        ).sum()
    )

    duplicate_mask = (
        rows["epoch"].notna()
        & rows["epoch"].duplicated(keep=False)
    )

    duplicate_timestamp_count = int(
        duplicate_mask.sum()
    )

    # Speed statistics use valid non-negative speeds,
    # even if their timestamps are invalid.
    valid_speeds = rows.loc[
        rows["speed"].notna()
        & (rows["speed"] >= 0),
        "speed",
    ].to_numpy(dtype=float)

    speed_mean = (
        float(np.mean(valid_speeds) * 3.6)
        if len(valid_speeds) >= 1
        else None
    )

    speed_std = (
        float(np.std(valid_speeds, ddof=1) * 3.6)
        if len(valid_speeds) >= 2
        else None
    )

    # If fewer than two valid timestamps exist, no interval
    # can be evaluated.
    if (
        rows.empty
        or rows["epoch"].notna().sum() < 2
    ):
        result = _empty_result(
            invalid_timestamp_count,
            invalid_speed_count,
            invalid_observation_count,
            duplicate_timestamp_count,
            observation_count,
        )

        result["raw_speed_mean_kmh"] = speed_mean
        result["raw_speed_std"] = speed_std
        result["negative_speed_count"] = negative_speed_count

        return result

    # Invalid timestamps split the original observation sequence.
    # They must not be removed silently because that could bridge a gap.
    rows["_original_position"] = np.arange(len(rows))

    rows["_segment"] = invalid_timestamp_mask.cumsum()

    valid_timestamp_rows = rows.loc[
        ~invalid_timestamp_mask
    ].copy()

    # Every occurrence of a duplicate timestamp acts as a barrier.
    valid_timestamp_rows["_duplicate"] = duplicate_mask.loc[
        valid_timestamp_rows.index
    ]

    # Invalid speeds also act as barriers.
    valid_timestamp_rows["_invalid_speed"] = invalid_speed_mask.loc[
        valid_timestamp_rows.index
    ]

    # Sort observations within each original timestamp segment.
    valid_timestamp_rows = valid_timestamp_rows.sort_values(
        ["_segment", "epoch", "_original_position"],
        kind="mergesort",
    )

    times = valid_timestamp_rows["epoch"].to_numpy(
        dtype=float
    )

    speeds = valid_timestamp_rows["speed"].to_numpy(
        dtype=float
    )

    segments = valid_timestamp_rows["_segment"].to_numpy()

    duplicates = valid_timestamp_rows[
        "_duplicate"
    ].to_numpy(dtype=bool)

    invalid_speeds = valid_timestamp_rows[
        "_invalid_speed"
    ].to_numpy(dtype=bool)

    intervals = np.diff(times)

    same_segment = (
        segments[:-1] == segments[1:]
    )

    no_duplicate_barrier = ~(
        duplicates[:-1] | duplicates[1:]
    )

    no_invalid_speed_barrier = ~(
        invalid_speeds[:-1] | invalid_speeds[1:]
    )

    valid_interval_mask = (
        (intervals > 0)
        & (intervals <= MAX_VALID_INTERVAL_SECONDS)
        & same_segment
        & no_duplicate_barrier
        & no_invalid_speed_barrier
    )

    valid_intervals = intervals[valid_interval_mask]

    valid_time_seconds = float(
        valid_intervals.sum()
    )

    telemetry_span_seconds = float(
        times.max() - times.min()
    )

    valid_interval_count = int(
        valid_interval_mask.sum()
    )

    excluded_interval_count = int(
        len(intervals) - valid_interval_count
    )

    # If no valid telemetry time exists, stop metrics are unknown,
    # not zero. This matches the notebook helper's semantics.
    if valid_time_seconds <= 0:
        return {
            "raw_speed_mean_kmh": speed_mean,
            "raw_speed_std": speed_std,
            "low_speed_time_pct_03": np.nan,
            "stop_episode_count_03": np.nan,
            "stop_time_pct_03": np.nan,
            "longest_stop_seconds_03": np.nan,
            "stop_episode_durations_seconds_03": [],
            "observation_count": int(observation_count),
            "invalid_observation_count": invalid_observation_count,
            "invalid_timestamp_count": invalid_timestamp_count,
            "invalid_speed_count": invalid_speed_count,
            "negative_speed_count": negative_speed_count,
            "duplicate_timestamp_count": duplicate_timestamp_count,
            "telemetry_span_seconds": telemetry_span_seconds,
            "valid_interval_count": valid_interval_count,
            "valid_telemetry_time_seconds": valid_time_seconds,
            "excluded_interval_count": excluded_interval_count,
        }

    # Both interval endpoints must satisfy the low-speed threshold.
    low_speed_interval_mask = (
        valid_interval_mask
        & (speeds[:-1] < LOW_SPEED_THRESHOLD_MPS)
        & (speeds[1:] < LOW_SPEED_THRESHOLD_MPS)
    )

    low_speed_time_seconds = float(
        intervals[low_speed_interval_mask].sum()
    )

    low_speed_pct = (
        100.0 * low_speed_time_seconds / valid_time_seconds
    )

    # Detect contiguous qualifying stop episodes.
    episode_durations = []
    current_episode_seconds = 0.0

    for index, interval_seconds in enumerate(intervals):

        if low_speed_interval_mask[index]:
            current_episode_seconds += float(interval_seconds)

        else:
            if current_episode_seconds >= MIN_STOP_DURATION_SECONDS:
                episode_durations.append(
                    current_episode_seconds
                )

            current_episode_seconds = 0.0

    # Handle a stop episode that continues until the final observation.
    if current_episode_seconds >= MIN_STOP_DURATION_SECONDS:
        episode_durations.append(
            current_episode_seconds
        )

    stop_episode_count = len(episode_durations)

    qualifying_stop_time = float(
        sum(episode_durations)
    )

    longest_stop_seconds = (
        float(max(episode_durations))
        if episode_durations
        else 0.0
    )

    # Denominator is all valid telemetry time, not only low-speed time.
    stop_time_pct = (
        100.0 * qualifying_stop_time / valid_time_seconds
    )

    return {
        "raw_speed_mean_kmh": speed_mean,
        "raw_speed_std": speed_std,
        "low_speed_time_pct_03": low_speed_pct,
        "stop_episode_count_03": stop_episode_count,
        "stop_time_pct_03": stop_time_pct,
        "longest_stop_seconds_03": longest_stop_seconds,
        "stop_episode_durations_seconds_03": episode_durations,
        "observation_count": int(observation_count),
        "invalid_observation_count": invalid_observation_count,
        "invalid_timestamp_count": invalid_timestamp_count,
        "invalid_speed_count": invalid_speed_count,
        "negative_speed_count": negative_speed_count,
        "duplicate_timestamp_count": duplicate_timestamp_count,
        "telemetry_span_seconds": telemetry_span_seconds,
        "valid_interval_count": valid_interval_count,
        "valid_telemetry_time_seconds": valid_time_seconds,
        "excluded_interval_count": excluded_interval_count,
    }
