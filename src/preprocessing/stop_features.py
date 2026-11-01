
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


# ==========================================
# STOP DETECTION PARAMETERS
# ==========================================

LOW_SPEED_THRESHOLD_MPS = 0.3
MAX_INTERVAL_SECONDS = 2.0
MIN_STOP_SECONDS = 30.0


# ==========================================
# MAIN FEATURE EXTRACTION FUNCTION
# ==========================================

def extract_stop_features(
    telemetry: pd.DataFrame,
    low_speed_threshold_mps: float = LOW_SPEED_THRESHOLD_MPS,
    max_interval_seconds: float = MAX_INTERVAL_SECONDS,
    min_stop_seconds: float = MIN_STOP_SECONDS,
) -> dict[str, Any]:

    """
    Extract stop-related features from one track's raw telemetry.

    Required columns:
        epoch : Unix timestamp in seconds
        speed : Speed in metres/second

    Returns:
        observation_count
        valid_interval_count
        valid_telemetry_time_seconds
        low_speed_time_pct_03
        stop_episode_count_03
        stop_time_pct_03
        longest_stop_seconds_03
        stop_episode_durations_seconds_03
        invalid_timestamp_count
        invalid_speed_count
        duplicate_timestamp_count
    """

    required = {"epoch", "speed"}

    if not required.issubset(telemetry.columns):
        raise ValueError(
            f"Missing columns: {required - set(telemetry.columns)}"
        )

    result = {
        "observation_count": len(telemetry),
        "valid_interval_count": 0,
        "valid_telemetry_time_seconds": 0.0,
        "low_speed_time_pct_03": np.nan,
        "stop_episode_count_03": np.nan,
        "stop_time_pct_03": np.nan,
        "longest_stop_seconds_03": np.nan,
        "stop_episode_durations_seconds_03": [],
        "invalid_timestamp_count": 0,
        "invalid_speed_count": 0,
        "duplicate_timestamp_count": 0,
    }

    if telemetry.empty:
        return result

    # --------------------------------------
    # 1. Prepare telemetry
    # --------------------------------------

    work = telemetry[["epoch", "speed"]].copy()

    work["_row_order"] = np.arange(len(work))

    work["epoch"] = pd.to_numeric(
        work["epoch"], errors="coerce"
    )

    work["speed"] = pd.to_numeric(
        work["speed"], errors="coerce"
    )

    epoch = work["epoch"].to_numpy(
        dtype=float, na_value=np.nan
    )

    speed = work["speed"].to_numpy(
        dtype=float, na_value=np.nan
    )

    epoch_valid = np.isfinite(epoch)

    speed_valid = (
        np.isfinite(speed) & (speed >= 0)
    )

    result["invalid_timestamp_count"] = int(
        (~epoch_valid).sum()
    )

    result["invalid_speed_count"] = int(
        (~speed_valid).sum()
    )

    # Invalid timestamp rows create boundaries.
    work["_timestamp_valid"] = epoch_valid

    work["_segment"] = (
        ~work["_timestamp_valid"]
    ).cumsum()

    work = work.loc[
        work["_timestamp_valid"]
    ].copy()

    if work.empty:
        return result

    # --------------------------------------
    # 2. Handle duplicate timestamps
    # --------------------------------------

    duplicate_mask = work.duplicated(
        "epoch", keep=False
    )

    result["duplicate_timestamp_count"] = int(
        duplicate_mask.sum()
    )

    # Duplicates become barriers.
    work.loc[duplicate_mask, "speed"] = np.nan

    # --------------------------------------
    # 3. Calculate consecutive intervals
    # --------------------------------------

    durations = []
    low_flags = []

    previous_segment_seen = False

    for _, segment in work.groupby(
        "_segment", sort=False
    ):

        # Preserve invalid timestamp boundaries.
        if previous_segment_seen:
            durations.append(np.nan)
            low_flags.append(False)

        previous_segment_seen = True

        segment = segment.sort_values(
            ["epoch", "_row_order"]
        ).reset_index(drop=True)

        if len(segment) < 2:
            continue

        timestamps = segment["epoch"].to_numpy(
            dtype=float
        )

        speeds = segment["speed"].to_numpy(
            dtype=float,
            na_value=np.nan
        )

        dt = np.diff(timestamps)

        left_speed = speeds[:-1]
        right_speed = speeds[1:]

        # Both endpoint speeds must be valid.
        endpoints_valid = (
            np.isfinite(left_speed)
            & np.isfinite(right_speed)
            & (left_speed >= 0)
            & (right_speed >= 0)
        )

        valid_interval = (
            (dt > 0)
            & (dt <= max_interval_seconds)
            & endpoints_valid
        )

        # Both endpoint speeds must be below threshold.
        low_speed_interval = (
            valid_interval
            & (left_speed < low_speed_threshold_mps)
            & (right_speed < low_speed_threshold_mps)
        )

        for duration, valid, low in zip(
            dt,
            valid_interval,
            low_speed_interval
        ):

            if valid:
                durations.append(float(duration))
                low_flags.append(bool(low))

            else:
                # Invalid interval breaks continuity.
                durations.append(np.nan)
                low_flags.append(False)

    if not durations:
        return result

    durations = np.asarray(
        durations, dtype=float
    )

    low_flags = np.asarray(
        low_flags, dtype=bool
    )

    valid_mask = np.isfinite(durations)

    # --------------------------------------
    # 4. Calculate telemetry coverage
    # --------------------------------------

    valid_time = float(
        durations[valid_mask].sum()
    )

    result["valid_interval_count"] = int(
        valid_mask.sum()
    )

    result["valid_telemetry_time_seconds"] = (
        valid_time
    )

    if valid_time <= 0:
        return result

    # --------------------------------------
    # 5. Calculate low-speed percentage
    # --------------------------------------

    low_time = float(
        durations[valid_mask & low_flags].sum()
    )

    result["low_speed_time_pct_03"] = (
        100 * low_time / valid_time
    )

    # --------------------------------------
    # 6. Detect stop episodes
    # --------------------------------------

    episodes = []

    current_duration = 0.0

    for duration, is_low in zip(
        durations, low_flags
    ):

        if np.isfinite(duration) and is_low:

            current_duration += duration

        else:

            if current_duration >= min_stop_seconds:
                episodes.append(current_duration)

            current_duration = 0.0

    # Handle the final episode.
    if current_duration >= min_stop_seconds:
        episodes.append(current_duration)

    # --------------------------------------
    # 7. Store stop-related features
    # --------------------------------------

    result["stop_episode_count_03"] = len(
        episodes
    )

    result["stop_episode_durations_seconds_03"] = (
        episodes
    )

    result["stop_time_pct_03"] = (
        100 * sum(episodes) / valid_time
    )

    result["longest_stop_seconds_03"] = (
        max(episodes) if episodes else 0.0
    )

    return result


# ==========================================
# CSV HELPER FUNCTION
# ==========================================

def extract_stop_features_from_csv(
    csv_path: str | Path
) -> dict[str, Any]:

    """
    Read one raw telemetry CSV and extract
    stop-related features.
    """

    telemetry = pd.read_csv(
        csv_path,
        usecols=["epoch", "speed"]
    )

    return extract_stop_features(telemetry)
