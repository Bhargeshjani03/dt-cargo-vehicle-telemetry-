"""Plain-language distributions of actual processed track measurements."""

import numpy as np
import pandas as pd
import streamlit as st

from src.webapp.charts import render_horizontal_bars, render_metric_grid
from src.webapp.data import DISPLAY_CLUSTER_NAMES, load_cluster_assignments, load_track_records


TRACK_COLUMNS = ["track_id", "distance_km", "avg_speed_kmh", "duration_minutes"]
DISTRIBUTIONS = {
    "Distance per track (km)": ("distance_km", "km", "distance"),
    "Average speed per track (km/h)": ("avg_speed_kmh", "km/h", "speed"),
    "Track duration (minutes)": ("duration_minutes", "min", "duration"),
}


def _histogram(values: pd.Series) -> pd.DataFrame:
    values = pd.to_numeric(values, errors="coerce").dropna()
    if values.empty:
        return pd.DataFrame(columns=["Range", "Tracks"])
    lower = float(values.min())
    cap = float(values.quantile(.99))
    if cap <= lower:
        return pd.DataFrame({"Range": [f"{lower:,.2f}"], "Tracks": [len(values)]})
    clipped = values.clip(upper=cap)
    counts, edges = np.histogram(clipped, bins=12, range=(lower, cap))
    tail_count = int((values > cap).sum())
    counts[-1] += tail_count
    labels = [f"{edges[index]:,.1f}–{edges[index + 1]:,.1f}" for index in range(len(edges) - 1)]
    labels[-1] = f"{edges[-2]:,.1f}+"
    return pd.DataFrame({"Range": labels, "Tracks": counts})


def _operator_reading(values: pd.Series, kind: str, p50: float, p90: float) -> str:
    if kind == "distance" and p50 < 1:
        return (
            "Many rows are short recorded track segments, not complete delivery tours. "
            "Use the tour and cluster pages to understand a full movement episode."
        )
    if kind == "speed" and p90 > 3 * max(p50, .1):
        return (
            "A small number of tracks have much higher speeds than most. Open those tracks "
            "and check the speed trace and data-quality notes before drawing a conclusion."
        )
    if kind == "duration" and p90 > 3 * max(p50, .1):
        return (
            "A small number of tracks last much longer than most. Check whether they contain "
            "long gaps or a data-quality warning."
        )
    return (
        f"About half of recorded tracks are at or below {p50:,.1f} {DISTRIBUTIONS_LABELS[kind]}; "
        f"nine out of ten are at or below {p90:,.1f} {DISTRIBUTIONS_LABELS[kind]}."
    )


DISTRIBUTIONS_LABELS = {"distance": "km", "speed": "km/h", "duration": "minutes"}


def render_distributions() -> None:
    st.caption("UNDERSTAND")
    st.title("Data Distribution")
    st.write("See what a typical recorded track looks like and where less common values appear.")

    tracks = load_track_records(TRACK_COLUMNS)
    if tracks.empty:
        st.warning("Processed track measurements are not available in the current data folder.")
        return

    choice = st.selectbox("Measurement", list(DISTRIBUTIONS))
    column, unit, kind = DISTRIBUTIONS[choice]
    values = pd.to_numeric(tracks[column], errors="coerce")
    valid = values.dropna()
    if valid.empty:
        st.info("There are no usable values for this measurement.")
        return

    p50 = float(valid.quantile(.50))
    p90 = float(valid.quantile(.90))
    p99 = float(valid.quantile(.99))
    render_metric_grid([
        ("Tracks with a value", f"{len(valid):,}"),
        ("Missing values", f"{values.isna().sum():,}"),
        ("Middle of the fleet", f"{p50:,.1f} {unit}"),
        ("Upper 10% begins above", f"{p90:,.1f} {unit}"),
    ], label="Distribution summary")

    st.subheader("How the recorded values are spread")
    chart = _histogram(valid).set_index("Range")
    render_horizontal_bars(
        f"Tracks by {choice.lower()}",
        f"Each bar counts track segments in a {unit} range. Longer bars mean more recorded tracks. "
        f"The last range includes values above {p99:,.1f} {unit} (the top 1% boundary).",
        chart.index.astype(str).tolist(),
        chart["Tracks"].tolist(),
        colors=["#63a9ff"] * len(chart),
        show_rank=False,
    )
    st.caption("This view shows recorded track segments, not necessarily whole delivery tours. Quality-flagged values remain included.")
    st.info(_operator_reading(valid, kind, p50, p90))

    assignments = load_cluster_assignments()
    if assignments is not None and not assignments.empty:
        st.subheader("How common are the selected movement patterns?")
        counts = (
            assignments.groupby("cluster", as_index=False).size()
            .rename(columns={"cluster": "Display cluster", "size": "Episodes"})
        )
        counts["Movement pattern"] = counts["Display cluster"].map(DISPLAY_CLUSTER_NAMES)
        counts = counts[["Movement pattern", "Episodes"]]
        render_horizontal_bars(
            "Saved episodes by movement pattern",
            "Each bar counts saved 12-hour episodes. A longer bar means that pattern appears more often in the saved assignments.",
            counts["Movement pattern"].tolist(),
            counts["Episodes"].tolist(),
            colors=["#63a9ff", "#ffc45e"],
        )

    with st.expander("How to read this chart"):
        st.markdown(
            "- The middle value is a useful ‘typical track’ reference.\n"
            "- The upper range helps spot values worth checking; it does not prove a problem.\n"
            "- A track is one recorded segment. A tour can contain many tracks.\n"
            "- Open Data Quality or Track Explorer to inspect individual records."
        )
