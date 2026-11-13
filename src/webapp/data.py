"""Read-only data access for the web application."""

from pathlib import Path

import pandas as pd
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[2]
TRACKS_PATH = REPO_ROOT / "data/processed/engineered_tracks.csv"
ANOMALY_PATH = (
    REPO_ROOT
    / "src/anomaly_detection/reports/full/validation_predictions_extended_six_feature.csv"
)


@st.cache_data(show_spinner="Loading fleet activity…")
def _read_overview_data(
    tracks_path: str,
    tracks_mtime: int,
    anomaly_path: str,
    anomaly_mtime: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Cache compact overview columns; file timestamps invalidate stale data."""
    tracks = pd.read_csv(
        tracks_path,
        usecols=["track_id", "vehicle_id", "start_time", "distance", "fleet_test_id", "cid"],
    )
    tracks["start_time"] = pd.to_datetime(tracks["start_time"], utc=True, errors="coerce")
    tracks["distance"] = pd.to_numeric(tracks["distance"], errors="coerce")

    if anomaly_path:
        anomalies = pd.read_csv(
            anomaly_path,
            usecols=["track_id", "vehicle_id", "is_anomaly"],
        )
        anomalies["is_anomaly"] = (
            anomalies["is_anomaly"].astype("string").str.lower().isin(["true", "1", "yes"])
        )
    else:
        anomalies = pd.DataFrame(columns=["track_id", "vehicle_id", "is_anomaly"])
    return tracks, anomalies


def load_overview_data() -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """Load the processed track table and optional scored validation tracks."""
    if not TRACKS_PATH.is_file():
        return None
    anomaly_file = ANOMALY_PATH if ANOMALY_PATH.is_file() else None
    return _read_overview_data(
        str(TRACKS_PATH),
        TRACKS_PATH.stat().st_mtime_ns,
        str(anomaly_file) if anomaly_file else "",
        anomaly_file.stat().st_mtime_ns if anomaly_file else 0,
    )
