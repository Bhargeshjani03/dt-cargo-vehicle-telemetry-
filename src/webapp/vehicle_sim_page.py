"""Data-backed trip replay for fleet-operations scenarios."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from src.webapp.charts import render_metric_grid
from src.webapp.data import (
    DISPLAY_CLUSTER_LABELS,
    DISPLAY_CLUSTER_NAMES,
    REPO_ROOT,
    load_track_cluster_map,
    load_track_records,
    resolve_runtime_path,
)
from src.webapp.navigation import get_page_link
from src.webapp.speed_sim_3d import render_3d_speed_simulator

TRACK_COLUMNS = [
    "track_id", "vehicle_id", "tour_id", "start_time", "stop_time",
    "distance_km", "duration_minutes", "avg_speed_kmh", "max_speed_kmh",
]


def _local_speed_path(vehicle_id: int, track_id: int) -> Path:
    root = Path(os.environ.get("DT_CARGO_DATA_DIR", str(REPO_ROOT / "data")))
    return root / "raw" / "speed" / str(vehicle_id) / f"{track_id}.csv"


def _load_replay_tracks() -> pd.DataFrame:
    tracks = load_track_records(TRACK_COLUMNS)
    cluster_map = load_track_cluster_map()
    if tracks.empty or cluster_map.empty:
        return pd.DataFrame(columns=[*TRACK_COLUMNS, "cluster", "cluster_name"])
    tracks["track_id"] = pd.to_numeric(tracks["track_id"], errors="coerce")
    tracks["vehicle_id"] = pd.to_numeric(tracks["vehicle_id"], errors="coerce")
    tracks["start_time"] = pd.to_datetime(tracks["start_time"], utc=True, errors="coerce")
    for column in ("distance_km", "duration_minutes", "avg_speed_kmh", "max_speed_kmh"):
        tracks[column] = pd.to_numeric(tracks[column], errors="coerce")
    joined = tracks.merge(
        cluster_map[["track_id", "vehicle_id", "cluster", "cluster_name"]],
        on=["track_id", "vehicle_id"],
        how="inner",
    )
    return joined.loc[joined["cluster"].isin([0, 1])].dropna(subset=["track_id", "vehicle_id"])


@st.cache_data(show_spinner=False)
def _read_speed_trace(path: str, modified_ns: int) -> pd.DataFrame:
    del modified_ns
    frame = pd.read_csv(path, usecols=["epoch", "speed"], low_memory=False)
    frame["epoch"] = pd.to_numeric(frame["epoch"], errors="coerce")
    frame["speed"] = pd.to_numeric(frame["speed"], errors="coerce")
    return frame.dropna(subset=["epoch", "speed"]).sort_values("epoch").reset_index(drop=True)


def _near_stop_summary(frame: pd.DataFrame) -> tuple[int, float]:
    if frame.empty or len(frame) < 2:
        return 0, 0.0
    elapsed = frame["epoch"].diff().fillna(0).clip(lower=0)
    gaps = elapsed.gt(2.0)
    nearly_stopped = frame["speed"].lt(0.3)
    new_run = nearly_stopped & (~nearly_stopped.shift(fill_value=False) | gaps)
    run_ids = new_run.cumsum()
    run_spans = (
        frame.loc[nearly_stopped]
        .assign(run=run_ids.loc[nearly_stopped].to_numpy())
        .groupby("run")["epoch"]
        .agg(["min", "max"])
    )
    typical_step = float(elapsed.loc[elapsed.gt(0)].clip(upper=2).median()) if elapsed.gt(0).any() else 0.0
    stop_periods = int(((run_spans["max"] - run_spans["min"] + typical_step) >= 30).sum())
    stopped_seconds = float(elapsed.loc[nearly_stopped & ~gaps].clip(upper=2).sum())
    return stop_periods, stopped_seconds / 60


def _trace_points(frame: pd.DataFrame, limit: int = 1200) -> list[list[float]]:
    """Create [seconds, km/h, distance progress] points from the raw speed samples."""
    if frame.empty:
        return []
    times = frame["epoch"].to_numpy(dtype=float)
    speeds_mps = np.clip(frame["speed"].to_numpy(dtype=float), 0, None)
    elapsed = times - times[0]
    delta = np.clip(np.diff(times, prepend=times[0]), 0, 2.0)
    previous = np.roll(speeds_mps, 1)
    previous[0] = speeds_mps[0]
    distance_steps = ((speeds_mps + previous) / 2) * delta
    distance_steps[0] = 0
    cumulative = np.cumsum(distance_steps)
    if cumulative[-1] > 0:
        progress = cumulative / cumulative[-1]
    elif elapsed[-1] > 0:
        progress = elapsed / elapsed[-1]
    else:
        progress = np.zeros_like(elapsed)
    if len(frame) > limit:
        indices = np.unique(np.linspace(0, len(frame) - 1, limit).astype(int))
    else:
        indices = np.arange(len(frame))
    return [
        [float(elapsed[i]), float(speeds_mps[i] * 3.6), float(progress[i])]
        for i in indices
    ]


def _format_track_option(row: pd.Series) -> str:
    date = row["start_time"].strftime("%d %b %Y") if pd.notna(row["start_time"]) else "date unavailable"
    distance = f"{row['distance_km']:,.1f} km" if pd.notna(row["distance_km"]) else "distance unavailable"
    duration = f"{row['duration_minutes']:,.0f} min" if pd.notna(row["duration_minutes"]) else "time unavailable"
    return f"Track {int(row['track_id'])} · Vehicle {int(row['vehicle_id'])} · {date} · {distance} · {duration}"


def _render_research_context() -> None:
    st.subheader("How fleets use this kind of telemetry")
    st.write(
        "The workflow follows a familiar fleet-operations sequence: plan the work, inspect a trip, "
        "then use the evidence to decide what needs a closer look. Each example below is tied to published work."
    )
    left, middle, right = st.columns(3, gap="medium")
    with left:
        st.markdown("**01 · Trip patterns**")
        st.write(
            "Repeated trip and stop patterns help teams understand the kind of work a vehicle usually does. "
            "Our saved movement groups are descriptive summaries, not driver grades."
        )
        st.markdown(
            "[Akter & Hernandez, *Representative truck activity patterns* (2023)]"
            "(https://doi.org/10.1016/j.ijtst.2022.05.002)"
        )
    with middle:
        st.markdown("**02 · Stop investigation**")
        st.write(
            "Research combines speed, time, location, and vehicle context to investigate stops. "
            "This app can show near-zero speed periods; it cannot tell whether a stop was traffic, loading, rest, or idling."
        )
        st.markdown(
            "[Farzaneh et al., *Vehicle telematics and truck idling* (2020)]"
            "(https://doi.org/10.1177/0361198120945990)"
        )
    with right:
        st.markdown("**03 · Speed-profile replay**")
        st.write(
            "The DT-CARGO research dataset includes anonymized trip summaries and high-resolution speed profiles. "
            "Published positions are removed, so the road here is a schematic backdrop, not the truck’s actual route."
        )
        st.markdown(
            "[Balke & Adenaw, *DT-CARGO dataset* (2023)]"
            "(https://doi.org/10.1016/j.dib.2023.109246)"
        )
    st.caption(
        "Fleet Edge reference: Tata Motors organizes fleet work around planning, track and trace, and analysis. "
        "This project uses that sequence for historical records; it does not provide live location, fuel, or vehicle-health feeds. "
        "[Fleet Edge features](https://fleetedge.tatamotors.com/features)"
    )


def render_vehicle_simulator() -> None:
    """Explore a real recorded trip as an operator-focused 3D speed replay."""
    st.caption("TRACK · ANALYSE · UNDERSTAND")
    st.title("Recorded Trip Replay")
    st.write(
        "Choose a real recorded track, replay its measured speed in 3D, and compare it with the movement pattern it belongs to. "
        "Use it as a team exercise: spot a slowdown, read the evidence, then decide what an operator should check next."
    )

    tracks = _load_replay_tracks()
    if tracks.empty:
        st.warning(
            "A replay needs the saved cluster assignments, processed track records, and raw speed trace files. "
            "No sample route or synthetic track will be shown when those records are missing."
        )
        _render_research_context()
        return

    available_clusters = sorted(int(value) for value in tracks["cluster"].dropna().unique())
    cluster = st.selectbox(
        "Choose a movement profile",
        available_clusters,
        format_func=lambda value: f"Cluster {value} · {DISPLAY_CLUSTER_NAMES.get(value, 'Saved movement profile')}",
        key="replay_cluster",
    )
    cluster_tracks = tracks.loc[tracks["cluster"] == cluster].sort_values("start_time", ascending=False)
    search = st.text_input("Optional: narrow by vehicle or track ID", placeholder="Type an ID to filter saved trips")
    if search.strip():
        query = search.strip()
        mask = (
            cluster_tracks["track_id"].astype("Int64").astype("string").str.contains(query, na=False, regex=False)
            | cluster_tracks["vehicle_id"].astype("Int64").astype("string").str.contains(query, na=False, regex=False)
        )
        cluster_tracks = cluster_tracks.loc[mask]

    if cluster_tracks.empty:
        st.info("No recorded tracks match that search in this movement profile.")
        _render_research_context()
        return

    candidates = cluster_tracks.head(500)
    local_candidates = [
        row for _, row in candidates.iterrows()
        if _local_speed_path(int(row["vehicle_id"]), int(row["track_id"])).is_file()
    ]
    option_rows = pd.DataFrame(local_candidates[:80]) if local_candidates else cluster_tracks.head(80)
    option_keys = [f"{int(row.track_id)}|{int(row.vehicle_id)}" for row in option_rows.itertuples()]
    option_lookup = {
        f"{int(row['track_id'])}|{int(row['vehicle_id'])}": row
        for _, row in option_rows.iterrows()
    }
    selected_key = st.selectbox(
        "Choose a recorded trip",
        option_keys,
        format_func=lambda key: _format_track_option(option_lookup[key]),
        key=f"replay_track_{cluster}",
    )
    selected = option_lookup[selected_key]
    track_id, vehicle_id = int(selected["track_id"]), int(selected["vehicle_id"])

    trace_path = resolve_runtime_path(f"data/raw/speed/{vehicle_id}/{track_id}.csv")
    if not trace_path.is_file():
        st.info(
            f"Track {track_id} has no accessible raw speed file, so it cannot be animated. "
            "Choose another recorded trip or open Track Explorer for its saved summary."
        )
        track_page = get_page_link("Track Explorer")
        if track_page is not None:
            st.page_link(track_page, label="Open Track Explorer", icon=":material/arrow_forward:")
        _render_research_context()
        return

    samples = _read_speed_trace(str(trace_path), trace_path.stat().st_mtime_ns)
    if samples.empty:
        st.warning("This track has no valid speed samples to replay.")
        _render_research_context()
        return

    samples["speed_kmh"] = samples["speed"].clip(lower=0) * 3.6
    stop_periods, near_stop_minutes = _near_stop_summary(samples)
    elapsed_minutes = float((samples["epoch"].iloc[-1] - samples["epoch"].iloc[0]) / 60)
    cluster_median_distance = float(pd.to_numeric(cluster_tracks["distance_km"], errors="coerce").median())
    cluster_median_speed = float(pd.to_numeric(cluster_tracks["avg_speed_kmh"], errors="coerce").median())
    selected_distance = float(selected["distance_km"]) if pd.notna(selected["distance_km"]) else None
    selected_duration = float(selected["duration_minutes"]) if pd.notna(selected["duration_minutes"]) else elapsed_minutes
    trace_points = _trace_points(samples)

    st.markdown(
        f"**Scenario briefing · {DISPLAY_CLUSTER_NAMES.get(cluster, 'Saved movement profile')}**  "
        f"Replay Track {track_id}, then compare its slowdowns with the group’s typical trip. "
        "The scene shows relative progress from speed samples; no GPS route is available."
    )
    render_metric_grid(
        [
            ("Recorded distance", f"{selected_distance:,.1f} km" if selected_distance is not None else "Not recorded"),
            ("Recorded duration", f"{selected_duration:,.1f} min" if pd.notna(selected_duration) else "Not recorded"),
            ("Median recorded speed", f"{samples['speed_kmh'].median():,.1f} km/h"),
            ("Near-stop periods · 30+ sec", f"{stop_periods:,}"),
        ],
        label="Selected recorded trip facts",
    )
    render_3d_speed_simulator(
        track_id=track_id,
        vehicle_id=vehicle_id,
        cluster_name=DISPLAY_CLUSTER_LABELS.get(cluster, f"Cluster {cluster}"),
        distance_km=selected_distance,
        duration_minutes=selected_duration,
        trace_points=trace_points,
        height=560,
    )

    chart_samples = samples.iloc[:: max(1, len(samples) // 1800)].copy()
    chart_samples["Elapsed time (min)"] = (chart_samples["epoch"] - samples["epoch"].iloc[0]) / 60
    chart_data = chart_samples[["Elapsed time (min)", "speed_kmh"]].rename(
        columns={"speed_kmh": "Recorded speed (km/h)"}
    )
    st.subheader("What the truck was doing")
    st.line_chart(
        chart_data,
        x="Elapsed time (min)",
        y="Recorded speed (km/h)",
        x_label="Minutes into this track",
        y_label="Recorded speed (km/h)",
        height=320,
    )
    st.markdown(
        "**Read the line:** higher points mean faster recorded movement. Points near zero mean the vehicle was nearly stopped. "
        "A near-stop does not explain why it happened; this dataset does not show the exact location, ignition state, or loading activity."
    )
    st.caption(
        f"{len(samples):,} raw speed samples · source speed is in m/s and is shown here in km/h · "
        f"{near_stop_minutes:,.1f} minutes at near-zero speed in the recorded samples."
    )

    if pd.notna(cluster_median_distance) and pd.notna(cluster_median_speed):
        distance_delta = selected_distance - cluster_median_distance if selected_distance is not None else None
        speed_delta = float(samples["speed_kmh"].median()) - cluster_median_speed
        distance_copy = (
            f"{abs(distance_delta):,.1f} km {'longer' if distance_delta >= 0 else 'shorter'} than the profile’s median distance"
            if distance_delta is not None else "distance is not available for this trip"
        )
        st.info(
            f"**Compared with {DISPLAY_CLUSTER_LABELS.get(cluster, f'Cluster {cluster}')}:** this track is {distance_copy}. "
            f"Its median recorded speed is {abs(speed_delta):,.1f} km/h {'higher' if speed_delta >= 0 else 'lower'} than the profile median "
            f"of {cluster_median_speed:,.1f} km/h. This comparison gives context; it is not a performance grade."
        )

    st.subheader("Team challenge · read the evidence")
    challenge_cols = st.columns(3, gap="small")
    prompts = [
        ("01 · NOTICE", f"Find one of the {stop_periods:,} near-stop periods in the speed line."),
        ("02 · COMPARE", "Check whether this trip’s distance and speed match its saved movement profile."),
        ("03 · DISCUSS", "Decide what extra context an operator would need before calling it a delay or an incident."),
    ]
    for column, (step, prompt) in zip(challenge_cols, prompts):
        with column:
            st.markdown(f"**{step}**")
            st.write(prompt)

    anomaly_page = get_page_link("Anomaly Monitoring")
    track_page = get_page_link("Track Explorer")
    actions = st.columns(2, gap="small")
    if anomaly_page is not None:
        actions[0].page_link(anomaly_page, label="Review unusual-track signals", icon=":material/search:")
    if track_page is not None:
        actions[1].page_link(track_page, label="Open the track record", icon=":material/arrow_forward:")

    _render_research_context()
