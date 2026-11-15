"""Read-only data access for the web application."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[2]
CLUSTER_ASSIGNMENTS_PATH = "data/processed/tour_level_clustering/12h_kernelpca_k3_tour_clusters.csv"
DISPLAY_CLUSTER_MAP = {0: 0, 2: 1}
DISPLAY_CLUSTER_NAMES = {
    0: "Longer-distance travel",
    1: "Low movement with long gaps",
}
DISPLAY_CLUSTER_LABELS = {
    cluster: f"Cluster {cluster} · {name}"
    for cluster, name in DISPLAY_CLUSTER_NAMES.items()
}
TRACKS_PATH = "data/processed/engineered_tracks.csv"


def remap_display_clusters(assignments: pd.DataFrame) -> pd.DataFrame:
    """Show saved source clusters 0 and 2 as display clusters 0 and 1."""
    if assignments.empty or "cluster" not in assignments.columns:
        return assignments.copy()

    display = assignments.copy()
    display["source_cluster_id"] = pd.to_numeric(display["cluster"], errors="coerce")
    display = display.loc[display["source_cluster_id"].isin(DISPLAY_CLUSTER_MAP.keys())].copy()
    display["source_cluster_id"] = display["source_cluster_id"].astype("Int64")
    display["cluster"] = display["source_cluster_id"].map(DISPLAY_CLUSTER_MAP).astype("Int64")
    return display


@st.cache_resource(show_spinner="Loading data from Kuberns Storage…")
def _materialize_bucket_file(
    bucket_id: str,
    object_key: str,
    access_key_id: str,
    secret: str,
) -> str:
    """Download a private Kuberns bucket object to the pod's temporary disk."""
    encoded_key = quote(object_key, safe="/")
    url = f"https://gateway.kuberns.cloud/{quote(bucket_id, safe='')}/{encoded_key}"
    try:
        response = requests.get(
            url,
            auth=(access_key_id, secret),
            timeout=(15, 180),
        )
    except requests.RequestException as exc:
        raise RuntimeError("Could not reach the configured Kuberns data bucket.") from exc
    if response.status_code == 404:
        return ""
    try:
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(
            "Kuberns could not provide a data file. Check the bucket ID, key, and read-only credential."
        ) from exc

    relative_key = Path(object_key)
    if relative_key.is_absolute() or ".." in relative_key.parts:
        raise ValueError("Bucket object paths must stay inside the configured data prefix.")
    destination = Path(tempfile.gettempdir()) / "dt-cargo-data" / relative_key
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.content)
    return str(destination)


def resolve_runtime_path(repository_path: str) -> Path:
    """Resolve a local data file, with an optional private Kuberns bucket fallback.

    For local development, DT_CARGO_DATA_DIR can point at a mounted data folder.
    In Kuberns, set the three KUBERNS_* credential variables and optionally
    KUBERNS_DATA_PREFIX; bucket objects mirror their repository-relative paths.
    """
    relative = Path(repository_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Data paths must be repository-relative.")

    if relative.parts and relative.parts[0] == "data":
        data_root = Path(os.environ.get("DT_CARGO_DATA_DIR", REPO_ROOT / "data"))
        local_path = data_root.joinpath(*relative.parts[1:])
    else:
        local_path = REPO_ROOT / relative
    if local_path.is_file():
        return local_path

    bucket_id = os.environ.get("KUBERNS_BUCKET_ID", "").strip()
    access_key_id = os.environ.get("KUBERNS_ACCESS_KEY_ID", "").strip()
    secret = os.environ.get("KUBERNS_SECRET", "").strip()
    if not all((bucket_id, access_key_id, secret)):
        return local_path

    prefix = os.environ.get("KUBERNS_DATA_PREFIX", "").strip("/")
    object_key = f"{prefix}/{relative.as_posix()}" if prefix else relative.as_posix()
    resolved = _materialize_bucket_file(bucket_id, object_key, access_key_id, secret)
    return Path(resolved) if resolved else local_path


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
        usecols=["track_id", "vehicle_id", "tour_id", "start_time", "distance_km", "fleet_test_id"],
    )
    tracks["start_time"] = pd.to_datetime(tracks["start_time"], utc=True, errors="coerce")
    tracks["distance_km"] = pd.to_numeric(tracks["distance_km"], errors="coerce")

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


@st.cache_data(show_spinner=False)
def _read_cluster_assignments(path: str, modified_ns: int) -> pd.DataFrame:
    """Load the compact episode-level cluster labels used by the overview."""
    del modified_ns
    assignments = pd.read_csv(
        path,
        usecols=["vehicle_id", "tour_id", "start_time", "cluster"],
    )
    assignments["start_time"] = pd.to_datetime(
        assignments["start_time"], utc=True, errors="coerce"
    )
    assignments["cluster"] = pd.to_numeric(assignments["cluster"], errors="coerce")
    return assignments


def load_cluster_assignments() -> pd.DataFrame | None:
    """Load the selected saved groups with display labels 0 and 1."""
    path = resolve_runtime_path(CLUSTER_ASSIGNMENTS_PATH)
    if not path.is_file():
        return None
    assignments = _read_cluster_assignments(str(path), path.stat().st_mtime_ns)
    return remap_display_clusters(assignments)


@st.cache_data(show_spinner="Loading fleet records…")
def _read_track_records(path: str, modified_ns: int, columns: tuple[str, ...]) -> pd.DataFrame:
    del modified_ns
    return pd.read_csv(path, usecols=list(columns), low_memory=False)


def load_track_records(columns: list[str]) -> pd.DataFrame:
    """Load only the requested columns from the processed track table."""
    path = resolve_runtime_path(TRACKS_PATH)
    if not path.is_file():
        return pd.DataFrame(columns=columns)
    return _read_track_records(str(path), path.stat().st_mtime_ns, tuple(columns))


@st.cache_data(show_spinner=False)
def _read_cluster_episode_ranges(path: str, modified_ns: int) -> pd.DataFrame:
    del modified_ns
    episodes = pd.read_csv(
        path,
        usecols=["vehicle_id", "tour_id", "start_time", "end_time", "cluster"],
        low_memory=False,
    )
    episodes["start_time"] = pd.to_datetime(episodes["start_time"], utc=True, errors="coerce")
    episodes["end_time"] = pd.to_datetime(episodes["end_time"], utc=True, errors="coerce")
    episodes["cluster"] = pd.to_numeric(episodes["cluster"], errors="coerce")
    return episodes


@st.cache_data(show_spinner="Matching tracks to saved movement groups…")
def _read_track_cluster_map(
    tracks_path: str,
    tracks_modified_ns: int,
    episodes_path: str,
    episodes_modified_ns: int,
) -> pd.DataFrame:
    del tracks_modified_ns, episodes_modified_ns
    tracks = pd.read_csv(
        tracks_path,
        usecols=["track_id", "vehicle_id", "tour_id", "start_time"],
        low_memory=False,
    )
    tracks["start_time"] = pd.to_datetime(tracks["start_time"], utc=True, errors="coerce")
    episodes = _read_cluster_episode_ranges(episodes_path, Path(episodes_path).stat().st_mtime_ns)
    left = tracks.dropna(subset=["start_time", "vehicle_id", "tour_id"]).rename(
        columns={"start_time": "track_start"}
    ).sort_values("track_start")
    right = episodes.dropna(subset=["start_time", "end_time", "vehicle_id", "tour_id"]).rename(
        columns={"start_time": "episode_start", "end_time": "episode_end", "cluster": "source_cluster_id"}
    ).sort_values("episode_start")
    if left.empty or right.empty:
        return pd.DataFrame(columns=["track_id", "vehicle_id", "source_cluster_id", "cluster", "cluster_name"])

    matched = pd.merge_asof(
        left,
        right,
        by=["vehicle_id", "tour_id"],
        left_on="track_start",
        right_on="episode_start",
        direction="backward",
    )
    matched = matched.loc[matched["track_start"].le(matched["episode_end"])]
    result = matched[["track_id", "vehicle_id", "source_cluster_id"]].drop_duplicates("track_id").copy()
    result["source_cluster_id"] = pd.to_numeric(result["source_cluster_id"], errors="coerce").astype("Int64")
    result["cluster"] = result["source_cluster_id"].map(DISPLAY_CLUSTER_MAP).astype("Int64")
    result["cluster_name"] = result["cluster"].map(DISPLAY_CLUSTER_LABELS)
    result["cluster_name"] = result["cluster_name"].fillna("Outside the two displayed groups")
    return result


def load_track_cluster_map() -> pd.DataFrame:
    """Return source-aware movement labels matched to individual tracks."""
    tracks_path = resolve_runtime_path(TRACKS_PATH)
    episodes_path = resolve_runtime_path(CLUSTER_ASSIGNMENTS_PATH)
    columns = ["track_id", "vehicle_id", "source_cluster_id", "cluster", "cluster_name"]
    if not tracks_path.is_file() or not episodes_path.is_file():
        return pd.DataFrame(columns=columns)
    return _read_track_cluster_map(
        str(tracks_path), tracks_path.stat().st_mtime_ns,
        str(episodes_path), episodes_path.stat().st_mtime_ns,
    )


def attach_display_cluster_labels(records: pd.DataFrame) -> pd.DataFrame:
    """Attach two-group display labels to records with track and vehicle IDs."""
    if records.empty or not {"track_id", "vehicle_id"}.issubset(records.columns):
        return records.copy()
    cluster_map = load_track_cluster_map()
    if cluster_map.empty:
        result = records.copy()
        result["source_cluster_id"] = pd.Series(pd.NA, index=result.index, dtype="Int64")
        result["cluster"] = pd.Series(pd.NA, index=result.index, dtype="Int64")
        result["cluster_name"] = "No saved episode match"
        return result
    return records.merge(
        cluster_map,
        on=["track_id", "vehicle_id"],
        how="left",
        validate="many_to_one",
    ).assign(cluster_name=lambda frame: frame["cluster_name"].fillna("No saved episode match"))


def load_overview_data() -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """Load the processed track table and optional scored validation tracks."""
    tracks_path = resolve_runtime_path("data/processed/engineered_tracks.csv")
    if not tracks_path.is_file():
        return None
    anomaly_file = resolve_runtime_path(
        "src/anomaly_detection/reports/full/validation_predictions_extended_six_feature.csv"
    )
    if not anomaly_file.is_file():
        anomaly_file = None
    return _read_overview_data(
        str(tracks_path),
        tracks_path.stat().st_mtime_ns,
        str(anomaly_file) if anomaly_file else "",
        anomaly_file.stat().st_mtime_ns if anomaly_file else 0,
    )
