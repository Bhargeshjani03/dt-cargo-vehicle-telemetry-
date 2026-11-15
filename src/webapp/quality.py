"""Data quality summaries and record-level review."""

from pathlib import Path

import pandas as pd
import streamlit as st

from src.webapp.charts import render_horizontal_bars, render_metric_grid
from src.webapp.data import resolve_runtime_path


TOUR_QUALITY_PATH = "data/processed/tour_level/retained_tours_quality_checked.csv"
TRACK_QUALITY_PATH = "data/processed/engineered_tracks.csv"

TOUR_FLAG_LABELS = {
    "negative_elapsed_span": "Negative elapsed span",
    "non_positive_distance": "Zero or negative distance",
    "duration_incomplete": "Incomplete recorded duration",
    "duration_unusable": "Unusable duration",
    "high_distance_based_speed": "High distance-based speed",
    "requires_quality_review": "Requires quality review",
}

TRACK_FLAG_LABELS = {
    "insufficient_telemetry": "Insufficient telemetry",
    "limited_telemetry": "Limited telemetry",
    "insufficient_core_telemetry": "Insufficient core telemetry",
    "duration_invalid": "Invalid duration",
    "distance_missing": "Missing distance",
    "zero_distance": "Zero distance",
    "avg_speed_implausible": "Implausible average speed",
    "avg_speed_negative": "Negative average speed",
    "avg_speed_gt_max_speed": "Average speed exceeds maximum",
    "track_gap_missing": "Missing track gap",
}


@st.cache_data(show_spinner="Reviewing data quality…")
def _read_csv(path: str, modified_ns: int) -> pd.DataFrame:
    del modified_ns
    return pd.read_csv(path, low_memory=False)


def _load(path: str) -> pd.DataFrame:
    resolved = resolve_runtime_path(path)
    if not resolved.is_file():
        return pd.DataFrame()
    return _read_csv(str(resolved), resolved.stat().st_mtime_ns)


def _flag_mask(frame: pd.DataFrame, column: str) -> pd.Series:
    return frame[column].astype("string").str.lower().isin(["true", "1", "yes"])


def _record_table(frame: pd.DataFrame, columns: list[str], search: str, flag: str) -> pd.DataFrame:
    result = frame
    if search and "vehicle_id" in result.columns:
        result = result.loc[result["vehicle_id"].astype("string").str.contains(search, na=False, regex=False)]
    if flag != "All quality flags" and flag in result.columns:
        result = result.loc[_flag_mask(result, flag)]
    visible = [column for column in columns if column in result.columns]
    return result[visible].head(500)


def render_quality() -> None:
    st.caption("UNDERSTAND")
    st.title("Data Quality")
    st.write("Review the quality flags behind tour summaries and track level analyses.")

    tours = _load(TOUR_QUALITY_PATH)
    tracks = _load(TRACK_QUALITY_PATH)
    if tours.empty and tracks.empty:
        st.warning("Quality data is not available yet. Configure the processed data folder or Kuberns Storage bucket.")
        return

    tour_flags = [name for name in TOUR_FLAG_LABELS if name in tours.columns]
    track_flags = [name for name in TRACK_FLAG_LABELS if name in tracks.columns]
    flagged_tours = (
        tours["requires_quality_review"].astype("string").str.lower().isin(["true", "1", "yes"]).sum()
        if "requires_quality_review" in tours.columns
        else 0
    )
    insufficient_tracks = (
        tracks["insufficient_telemetry"].astype("string").str.lower().isin(["true", "1", "yes"]).sum()
        if "insufficient_telemetry" in tracks.columns
        else 0
    )

    render_metric_grid([
        ("Tours reviewed", f"{len(tours):,}" if not tours.empty else "—"),
        ("Tours flagged for review", f"{int(flagged_tours):,}"),
        ("Tracks assessed", f"{len(tracks):,}" if not tracks.empty else "—"),
        ("Tracks with limited telemetry", f"{int(insufficient_tracks):,}"),
    ], label="Data quality summary")

    st.subheader("Flag counts")
    flag_rows = []
    for column in tour_flags:
        flag_rows.append({"Level": "Tour", "Quality flag": TOUR_FLAG_LABELS[column], "Affected records": int(_flag_mask(tours, column).sum())})
    for column in track_flags:
        flag_rows.append({"Level": "Track", "Quality flag": TRACK_FLAG_LABELS[column], "Affected records": int(_flag_mask(tracks, column).sum())})
    if flag_rows:
        flag_counts = pd.DataFrame(flag_rows)
        tour_rows = flag_counts.loc[flag_counts["Level"] == "Tour"].sort_values("Affected records", ascending=False)
        track_rows = flag_counts.loc[flag_counts["Level"] == "Track"].sort_values("Affected records", ascending=False)
        tour_column, track_column = st.columns(2)
        if not tour_rows.empty:
            with tour_column:
                render_horizontal_bars(
                    "Tour review signals",
                    "Tours carrying each saved quality flag. One tour can carry more than one flag.",
                    tour_rows["Quality flag"].tolist(),
                    tour_rows["Affected records"].tolist(),
                    colors=["#ffc45e"] * len(tour_rows),
                )
        if not track_rows.empty:
            with track_column:
                render_horizontal_bars(
                    "Track telemetry signals",
                    "Tracks carrying each saved quality flag. Counts can overlap across checks.",
                    track_rows["Quality flag"].tolist(),
                    track_rows["Affected records"].tolist(),
                    colors=["#63a9ff"] * len(track_rows),
                )
        st.dataframe(flag_counts, hide_index=True, width="stretch")
    else:
        st.info("No recognized quality flag columns were found in the available files.")

    st.subheader("Inspect affected records")
    filters = st.columns([1, 1, 2])
    level = filters[0].selectbox("Record level", ["Tours", "Tracks"])
    flags = tour_flags if level == "Tours" else track_flags
    labels = {**TOUR_FLAG_LABELS, **TRACK_FLAG_LABELS}
    options = ["All quality flags", *flags]
    selected_flag = filters[1].selectbox("Quality flag", options, format_func=lambda value: "All quality flags" if value == "All quality flags" else labels[value])
    vehicle_search = filters[2].text_input("Vehicle ID", placeholder="Search a vehicle")

    frame = tours if level == "Tours" else tracks
    columns = (
        ["vehicle_id", "tour_id", "start_time", "end_time", "total_distance_km", "elapsed_span_hours", *tour_flags]
        if level == "Tours"
        else ["track_id", "vehicle_id", "tour_id", "start_time", "distance_km", "avg_speed_kmh", "duration_minutes", *track_flags]
    )
    shown = _record_table(frame, columns, vehicle_search.strip(), selected_flag)
    if shown.empty:
        st.info("No records match these filters.")
    else:
        st.caption("Showing up to 500 matching records.")
        st.dataframe(shown, hide_index=True, width="stretch")

    with st.expander("How to interpret these flags"):
        st.markdown(
            "- Tour quality flags can overlap; their counts are not additive.\n"
            "- Track telemetry flags describe source coverage or consistency and may affect model eligibility.\n"
            "- A flag is a review signal. It does not, by itself, prove an operational problem."
        )
