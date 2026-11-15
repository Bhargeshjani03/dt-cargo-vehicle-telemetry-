"""Project and dataset orientation for fleet operators."""

import pandas as pd
import streamlit as st

from src.webapp.data import load_cluster_assignments, load_overview_data
from src.webapp.charts import render_metric_grid


def render_project_overview() -> None:
    st.caption("START HERE")
    st.title("Project & Dataset")
    st.write(
        "DT-CARGO turns recorded vehicle telemetry into a practical fleet review: "
        "what moved, what looks different, and how long a planned tour may take."
    )

    loaded = load_overview_data()
    if loaded is None:
        st.warning("The processed DT-CARGO track data is not available in the current data folder.")
        return
    tracks, _ = loaded
    start = tracks["start_time"].min()
    end = tracks["start_time"].max()
    render_metric_grid([
        ("Recorded tracks", f"{len(tracks):,}"),
        ("Vehicles", f"{tracks['vehicle_id'].nunique():,}"),
        ("Tours", f"{tracks['tour_id'].nunique():,}"),
        ("Fleet groups", f"{tracks['fleet_test_id'].nunique():,}"),
    ], label="Dataset summary")
    if pd.notna(start) and pd.notna(end):
        st.caption(f"Recorded from {start:%d %b %Y} through {end:%d %b %Y} (UTC-normalized for analysis).")

    st.subheader("What data is included")
    source_col, meaning_col = st.columns([1, 1.7])
    with source_col:
        st.markdown(
            "**Dataset: DT-CARGO V2.0**\n\n"
            "The project analysis log identifies the source as the DT-CARGO V2.0 vehicle telemetry dataset."
        )
    with meaning_col:
        st.markdown(
            "- **Track records:** vehicle and tour IDs, timestamps, distance, speed, and quality checks.\n"
            "- **Vehicle details:** weight, axle class, and fleet test group.\n"
            "- **Speed samples:** timestamped speed and HDOP readings stored by vehicle and track.\n"
            "- **Movement episodes:** grouped 12-hour tour episodes used for the saved movement patterns."
        )

    st.info(
        "This is historical telemetry, not a live fleet feed. The source has no latitude/longitude, "
        "so the 3D route paths and truck positions are illustrations rather than recorded roads."
    )

    st.subheader("What the app helps an operator do")
    st.markdown(
        "1. **See the fleet** — review recorded activity, distance, and fleet groups.\n\n"
        "2. **Check unusual tracks** — compare a review prompt with its speed, stops, distance, and data notes.\n\n"
        "3. **Understand movement patterns** — compare longer-distance travel with low-movement episodes that contain long gaps.\n\n"
        "4. **Plan a tour** — estimate elapsed time from vehicle details, planned distance, and departure time."
    )

    assignments = load_cluster_assignments()
    if assignments is not None:
        st.subheader("Movement patterns currently shown")
        st.write(
            f"The selected source groups contain {len(assignments):,} saved 12-hour episodes. "
            "For this operator view, saved source cluster 0 is called Cluster 0, and source cluster 2 is shown as Cluster 1."
        )

    with st.expander("Important limits"):
        st.markdown(
            "- Anomaly flags are review prompts. The saved validation set has no confirmed incident labels.\n"
            "- Duration estimates predict elapsed span, which includes pauses and gaps. Planned distance is used as a proxy for completed-tour distance in the training data.\n"
            "- Cluster names describe common movement patterns; they are not driver ratings or fault categories.\n"
            "- The source speed files contain no GPS coordinates, so maps cannot show the actual route."
        )
