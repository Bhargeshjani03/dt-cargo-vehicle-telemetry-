"""Plain-language review queue for saved Isolation Forest validation scores."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.webapp.charts import render_horizontal_bars, render_metric_grid
from src.webapp.data import DISPLAY_CLUSTER_LABELS, attach_display_cluster_labels, resolve_runtime_path


PREDICTIONS_PATH = "src/anomaly_detection/reports/full/validation_predictions_extended_six_feature.csv"
SUMMARY_PATH = "src/anomaly_detection/reports/full/validation_summary.json"
PREDICTION_COLUMNS = [
    "track_id", "vehicle_id", "fleet_test_id", "start_time", "quality_status_extended",
    "reason_codes", "raw_speed_mean_kmh", "raw_speed_std", "low_speed_time_pct_03",
    "stop_episode_count_03", "duration_minutes", "distance_km", "anomaly_score",
    "is_anomaly", "model_variant",
]
FEATURE_GUIDE = {
    "raw_speed_mean_kmh": ("Average speed", "Average speed recorded during this track, in km/h."),
    "raw_speed_std": ("Speed variation", "How much the recorded speed changed during this track."),
    "low_speed_time_pct_03": ("Time nearly stopped", "Share of valid speed samples below 0.3 m/s."),
    "stop_episode_count_03": ("Stop periods", "Count of stop periods lasting at least 30 seconds."),
    "duration_minutes": ("Track duration", "Elapsed time for this track, in minutes."),
    "distance_km": ("Recorded distance", "Distance recorded for this track, in kilometres."),
}
QUALITY_NOTE_LABELS = {
    "telemetry_coverage_low": "Some speed readings are missing.",
    "telemetry_coverage_inadequate": "Too many speed readings are missing for a reliable movement score.",
    "avg_speed_gt_max_speed": "The recorded average speed is higher than the recorded maximum speed.",
    "n_signal_loss_negative": "A signal-loss counter is negative.",
    "d_signal_loss_invalid": "A signal-loss counter is outside its expected range.",
    "r_signal_loss_missing": "A signal-loss reading is missing.",
    "r_signal_loss_out_of_range": "A signal-loss reading is outside its expected range.",
    "zero_distance_speed_issue": "The track has zero distance but also contains speed readings.",
    "zero_distance": "The recorded distance is zero.",
    "track_gap_missing": "The gap between track records is missing.",
}


@st.cache_data(show_spinner="Loading saved anomaly reviews…")
def _read_predictions(path: str, modified_ns: int) -> pd.DataFrame:
    del modified_ns
    frame = pd.read_csv(path, usecols=PREDICTION_COLUMNS, low_memory=False)
    frame["start_time"] = pd.to_datetime(frame["start_time"], utc=True, errors="coerce")
    frame["anomaly_score"] = pd.to_numeric(frame["anomaly_score"], errors="coerce")
    frame["is_anomaly"] = frame["is_anomaly"].astype("string").str.lower().isin(["true", "1", "yes"])
    return frame


@st.cache_data(show_spinner=False)
def _read_summary(path: str, modified_ns: int) -> dict:
    del modified_ns
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_anomaly_data() -> tuple[pd.DataFrame, dict] | None:
    """Return saved validation predictions joined to available display groups."""
    predictions_path = resolve_runtime_path(PREDICTIONS_PATH)
    summary_path = resolve_runtime_path(SUMMARY_PATH)
    if not predictions_path.is_file() or not summary_path.is_file():
        return None
    frame = _read_predictions(str(predictions_path), predictions_path.stat().st_mtime_ns)
    frame = attach_display_cluster_labels(frame)
    summary = _read_summary(str(summary_path), summary_path.stat().st_mtime_ns)
    return frame, summary.get("extended_six_feature", {})


def _friendly_quality_notes(value: object) -> list[str]:
    if pd.isna(value) or not str(value).strip():
        return []
    notes = []
    for code in str(value).split(";"):
        code = code.strip()
        if code:
            notes.append(QUALITY_NOTE_LABELS.get(code, code.replace("_", " ").capitalize()))
    return notes


def render_anomaly_monitoring() -> None:
    st.caption("INVESTIGATE")
    st.title("Anomaly Monitoring")
    st.write("Review tracks whose movement looks unusual compared with the model’s historical examples.")

    loaded = load_anomaly_data()
    if loaded is None:
        st.warning("Saved anomaly validation results are not available in the current data folder.")
        return
    data, model_summary = loaded
    if data.empty:
        st.info("The saved validation file contains no records.")
        return

    threshold = float(model_summary.get("threshold", data["anomaly_score"].quantile(.98)))
    total_flagged = int(model_summary.get("validation_flagged_tracks", data["is_anomaly"].sum()))
    target_rate = float(model_summary.get("threshold_policy", {}).get("target_review_rate", .02))
    score_definition = model_summary.get(
        "score_definition",
        "Higher scores mean more unusual movement; the score is not a probability.",
    )

    render_metric_grid([
        ("Tracks scored", f"{len(data):,}"),
        ("Flagged for review", f"{total_flagged:,}"),
        ("Review cutoff", f"{threshold:.3f}"),
        ("Review queue setting", f"{target_rate:.0%}"),
    ], label="Anomaly review summary")
    st.info(
        "A flag means ‘please check this track,’ not ‘the vehicle did something wrong.’ "
        + score_definition
        + " The queue target is a review setting, not the percentage of real-world problems."
    )

    dates = data["start_time"].dropna().dt.date
    if dates.empty:
        st.warning("The saved validation records do not have usable dates.")
        return
    min_date, max_date = dates.min(), dates.max()
    vehicle_query = st.text_input("Vehicle ID", placeholder="Search a vehicle")
    status = st.selectbox("Review status", ["All records", "Flagged for review", "Below threshold"])
    groups = ["All groups", *DISPLAY_CLUSTER_LABELS.values(), "Outside the two displayed groups"]
    group_choice = st.selectbox("Movement pattern", groups)
    date_range = st.date_input(
        "Track date range (UTC)",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    filtered = data.copy()
    if vehicle_query.strip():
        filtered = filtered.loc[
            filtered["vehicle_id"].astype("string").str.contains(vehicle_query.strip(), regex=False, na=False)
        ]
    if status == "Flagged for review":
        filtered = filtered.loc[filtered["is_anomaly"]]
    elif status == "Below threshold":
        filtered = filtered.loc[~filtered["is_anomaly"]]
    if group_choice in DISPLAY_CLUSTER_LABELS.values():
        filtered = filtered.loc[filtered["cluster_name"] == group_choice]
    elif group_choice == "Outside the two displayed groups":
        filtered = filtered.loc[~filtered["cluster_name"].isin(DISPLAY_CLUSTER_LABELS.values())]
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        filtered = filtered.loc[
            filtered["start_time"].dt.date.between(start_date, end_date)
        ]

    selected_flags = filtered.loc[filtered["is_anomaly"]]
    render_metric_grid([
        ("Records in this view", f"{len(filtered):,}"),
        ("Review candidates", f"{len(selected_flags):,}"),
        ("Vehicles in this view", f"{filtered['vehicle_id'].nunique():,}"),
    ], label="Filtered review summary")

    st.subheader("Tracks to check")
    if filtered.empty:
        st.info("No saved records match these filters.")
    else:
        table = filtered.sort_values("anomaly_score", ascending=False).head(300).copy()
        table["Review status"] = table["is_anomaly"].map({True: "Check this track", False: "Below review threshold"})
        table = table.rename(columns={
            "track_id": "Track ID", "vehicle_id": "Vehicle ID", "fleet_test_id": "Fleet group",
            "start_time": "Start time (UTC)", "cluster_name": "Movement pattern",
            "distance_km": "Distance (km)", "duration_minutes": "Duration (min)",
            "anomaly_score": "Unusualness score", "reason_codes": "Saved data checks",
        })
        visible = [
            "Track ID", "Vehicle ID", "Fleet group", "Start time (UTC)", "Movement pattern",
            "Distance (km)", "Duration (min)", "Unusualness score", "Review status", "Saved data checks",
        ]
        st.caption("Sorted by the highest unusualness score. Showing up to 300 records; the total above reflects the filters.")
        st.dataframe(table[[column for column in visible if column in table]], hide_index=True, width="stretch")

    if not selected_flags.empty:
        st.subheader("Vehicles appearing most in this review list")
        top_vehicles = (
            selected_flags.groupby("vehicle_id", as_index=False)
            .agg(flagged_tracks=("track_id", "nunique"))
            .sort_values("flagged_tracks", ascending=False)
            .head(8)
        )
        render_horizontal_bars(
            "Review candidates by vehicle",
            "A higher count means more tracks from this vehicle entered the review list; it is not a fault finding.",
            [f"Vehicle {int(value)}" for value in top_vehicles["vehicle_id"]],
            top_vehicles["flagged_tracks"].tolist(),
            colors=["#ffc45e"] * len(top_vehicles),
        )

        flagged_ids = selected_flags.sort_values("anomaly_score", ascending=False).head(500)
        id_to_vehicle = dict(zip(flagged_ids["track_id"].astype(str), flagged_ids["vehicle_id"]))
        chosen_id = st.selectbox(
            "Open a flagged track",
            list(id_to_vehicle),
            format_func=lambda track_id: f"Track {track_id} · Vehicle {int(id_to_vehicle[track_id])}",
        )
        record = flagged_ids.loc[flagged_ids["track_id"].astype(str) == chosen_id].iloc[0]
        st.subheader(f"Track {chosen_id} · review details")
        render_metric_grid([
            ("Recorded distance", f"{record['distance_km']:.1f} km"),
            ("Elapsed time", f"{record['duration_minutes']:.1f} min"),
            ("Unusualness score", f"{record['anomaly_score']:.3f}"),
        ], label=f"Track {chosen_id} review details")
        st.caption(f"Scores above {threshold:.3f} entered this saved review queue. The score is not a probability.")

        feature_rows = []
        for key, (label, meaning) in FEATURE_GUIDE.items():
            value = record.get(key)
            feature_rows.append({
                "Signal": label,
                "Recorded value": f"{float(value):,.2f}" if pd.notna(value) else "Not available",
                "What it describes": meaning,
            })
        st.dataframe(pd.DataFrame(feature_rows), hide_index=True, width="stretch")
        notes = _friendly_quality_notes(record.get("reason_codes"))
        if notes:
            st.markdown("**Saved data checks**")
            for note in notes:
                st.write(f"• {note}")
        else:
            st.caption("No separate data-quality note is saved for this track. The score does not explain the cause by itself.")

    with st.expander("How to use this review list"):
        st.markdown(
            "1. Open a high-scoring track and check its speed, stops, duration, distance, and data-quality notes.\n"
            "2. Compare it with the vehicle’s schedule and surrounding tracks.\n"
            "3. Record an operational conclusion only after a person reviews the evidence.\n\n"
            "The saved validation file has no confirmed anomaly labels, so these flags are candidates for review rather than proven incidents."
        )
