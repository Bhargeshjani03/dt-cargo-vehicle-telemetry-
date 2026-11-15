"""Track-level telemetry, quality, and model-result explorer."""

import pandas as pd
import streamlit as st

from src.webapp.anomaly import load_anomaly_data
from src.webapp.charts import render_metric_grid
from src.webapp.data import attach_display_cluster_labels, load_track_records, resolve_runtime_path
from src.webapp.quality import TRACK_FLAG_LABELS


TRACK_COLUMNS = [
    "track_id", "vehicle_id", "tour_id", "start_time", "stop_time", "distance_km",
    "duration_minutes", "avg_speed_kmh", "max_speed_kmh", "fleet_test_id",
    "gross_vehicle_weight", "total_mass_with_trailer", "axle_class",
    "insufficient_telemetry", "limited_telemetry", "insufficient_core_telemetry",
    "duration_invalid", "distance_missing", "zero_distance", "avg_speed_implausible",
    "avg_speed_negative", "avg_speed_gt_max_speed", "track_gap_missing",
]


def _stop_summary(samples: pd.DataFrame) -> tuple[int, float]:
    if samples.empty or not {"epoch", "speed"}.issubset(samples.columns):
        return 0, 0.0
    frame = samples[["epoch", "speed"]].copy()
    frame["epoch"] = pd.to_numeric(frame["epoch"], errors="coerce")
    frame["speed"] = pd.to_numeric(frame["speed"], errors="coerce")
    frame = frame.dropna().sort_values("epoch").reset_index(drop=True)
    if len(frame) < 2:
        return 0, 0.0
    gaps = frame["epoch"].diff().fillna(0).gt(2.0)
    stopped = frame["speed"].lt(.3)
    new_run = stopped & (~stopped.shift(fill_value=False) | gaps)
    run_ids = new_run.cumsum()
    intervals = frame["epoch"].diff().fillna(0).clip(lower=0, upper=2.0)
    stopped_seconds = float(intervals.loc[stopped & ~gaps].sum())
    runs = frame.loc[stopped].assign(run=run_ids.loc[stopped]).groupby("run")["epoch"].agg(["min", "max"])
    typical_step = float(frame["epoch"].diff().dropna().clip(upper=2).median())
    stops = int(((runs["max"] - runs["min"] + typical_step) >= 30).sum())
    return stops, stopped_seconds / 60


def render_track_explorer() -> None:
    st.caption("INVESTIGATE")
    st.title("Track Explorer")
    st.write("Search a track or vehicle to inspect its speed trace, stops, data checks, and saved model result.")

    tracks = load_track_records(TRACK_COLUMNS)
    if tracks.empty:
        st.warning("Processed track records are not available in the current data folder.")
        return
    tracks["start_time"] = pd.to_datetime(tracks["start_time"], utc=True, errors="coerce")
    tracks = attach_display_cluster_labels(tracks)
    query = st.text_input("Track ID or Vehicle ID", placeholder="Enter an exact track ID or vehicle ID")
    if not query.strip():
        st.caption("The source contains 151,598 processed track records. Enter an ID to open one record.")
        return

    direct = tracks.loc[tracks["track_id"].astype("string") == query.strip()]
    if not direct.empty:
        record = direct.iloc[0]
    else:
        vehicle_rows = tracks.loc[tracks["vehicle_id"].astype("string") == query.strip()].sort_values("start_time", ascending=False)
        if vehicle_rows.empty:
            st.info("No track or vehicle ID matches that search.")
            return
        vehicle_rows = vehicle_rows.head(250)
        options = vehicle_rows["track_id"].astype(str).tolist()
        starts = dict(zip(vehicle_rows["track_id"].astype(str), vehicle_rows["start_time"]))
        chosen = st.selectbox(
            f"Recent tracks for Vehicle {query.strip()}", options,
            format_func=lambda track_id: f"Track {track_id} · {starts[track_id]:%d %b %Y %H:%M UTC}" if pd.notna(starts[track_id]) else f"Track {track_id}",
        )
        record = vehicle_rows.loc[vehicle_rows["track_id"].astype(str) == chosen].iloc[0]

    track_id = int(record["track_id"])
    vehicle_id = int(record["vehicle_id"])
    st.subheader(f"Track {track_id} · Vehicle {vehicle_id}")
    render_metric_grid([
        ("Recorded distance", f"{record['distance_km']:,.2f} km" if pd.notna(record["distance_km"]) else "Not recorded"),
        ("Elapsed time", f"{record['duration_minutes']:,.1f} min" if pd.notna(record["duration_minutes"]) else "Not recorded"),
        ("Average speed", f"{record['avg_speed_kmh']:,.1f} km/h" if pd.notna(record["avg_speed_kmh"]) else "Not recorded"),
        ("Movement pattern", record.get("cluster_name", "No saved episode match")),
    ], label="Selected track summary")
    st.caption("A track is one recorded segment; its movement pattern comes from the matched saved 12-hour episode when available.")

    speed_path = resolve_runtime_path(f"data/raw/speed/{vehicle_id}/{track_id}.csv")
    if speed_path.is_file():
        samples = pd.read_csv(speed_path, usecols=["epoch", "speed", "hdop"])
        samples["epoch"] = pd.to_numeric(samples["epoch"], errors="coerce")
        samples["speed"] = pd.to_numeric(samples["speed"], errors="coerce")
        samples = samples.dropna(subset=["epoch", "speed"]).sort_values("epoch")
        stops, stopped_minutes = _stop_summary(samples)
        if not samples.empty:
            sample_for_chart = samples.iloc[::max(1, len(samples) // 2500)].copy()
            sample_for_chart["time"] = pd.to_datetime(sample_for_chart["epoch"], unit="s", utc=True)
            sample_for_chart["Speed (km/h)"] = sample_for_chart["speed"] * 3.6
            st.subheader("Recorded speed pattern")
            st.line_chart(sample_for_chart.set_index("time")[["Speed (km/h)"]], height=360)
            st.caption(
                "This line shows recorded speed over time: higher peaks mean faster readings; stretches near zero show little movement. "
                "The saved trace is converted from m/s to km/h."
            )
        stop_cols = st.columns(2)
        stop_cols[0].metric("Stop periods (30+ sec)", f"{stops:,}")
        stop_cols[1].metric("Time nearly stopped", f"{stopped_minutes:,.1f} min")
        st.caption("A stop period is a continuous speed trace below 0.3 m/s for at least 30 seconds; gaps over 2 seconds break a period.")
    else:
        st.info("No raw speed file is available for this track, so the speed chart and stop count cannot be shown.")

    anomalies = load_anomaly_data()
    if anomalies is not None:
        anomaly_rows, summary = anomalies
        match = anomaly_rows.loc[anomaly_rows["track_id"].astype(str) == str(track_id)]
        if not match.empty:
            result = match.iloc[0]
            threshold = float(summary.get("threshold", 0))
            if bool(result["is_anomaly"]):
                st.warning(f"Saved model result: review this track. Its score is {result['anomaly_score']:.3f}; the review cutoff is {threshold:.3f}.")
            else:
                st.success(f"Saved model result: below the review cutoff (score {result['anomaly_score']:.3f}; cutoff {threshold:.3f}).")
        else:
            st.caption("This track is not part of the saved validation-score file, so there is no saved anomaly result to display.")

    active_flags = []
    for flag, label in TRACK_FLAG_LABELS.items():
        value = record.get(flag)
        if pd.notna(value) and str(value).lower() in {"true", "1", "yes"}:
            active_flags.append(label)
    st.subheader("Data checks")
    if active_flags:
        st.warning("Saved checks for this record: " + "; ".join(active_flags))
    else:
        st.success("No saved track-level quality flags were raised for this record.")

    peers = tracks
    group = record.get("cluster_name")
    if pd.notna(group) and group in peers["cluster_name"].values:
        peers = peers.loc[peers["cluster_name"] == group]
        reference_name = f"{group} middle value"
    else:
        peers = peers.loc[pd.to_numeric(peers["vehicle_id"], errors="coerce") == vehicle_id]
        reference_name = f"Vehicle {vehicle_id} middle value"
    comparison = []
    for field, label, unit in [
        ("distance_km", "Distance", "km"),
        ("duration_minutes", "Duration", "min"),
        ("avg_speed_kmh", "Average speed", "km/h"),
    ]:
        current = pd.to_numeric(pd.Series([record.get(field)]), errors="coerce").iloc[0]
        typical = pd.to_numeric(peers[field], errors="coerce").median() if field in peers else float("nan")
        comparison.append({
            "Measure": label,
            "This track": f"{current:,.1f} {unit}" if pd.notna(current) else "Not recorded",
            reference_name: f"{typical:,.1f} {unit}" if pd.notna(typical) else "Not available",
        })
    st.subheader("Compare with a typical track")
    st.dataframe(pd.DataFrame(comparison), hide_index=True, width="stretch")
    st.caption("The reference is the middle value for the same movement pattern, or the same vehicle when no group match exists. It is context, not a pass/fail rule.")
