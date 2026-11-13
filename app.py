"""DT-CARGO multi-page analytics app."""

import streamlit as st

from src.webapp.overview import render_overview


st.set_page_config(
    page_title="DT-CARGO | Fleet Intelligence",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      :root {
        --canvas: #f4f6f4;
        --surface: #ffffff;
        --ink: #1b2926;
        --muted: #62716d;
        --line: #dce4e0;
        --accent: #176b5b;
      }
      .stApp { background: var(--canvas); color: var(--ink); }
      .block-container { max-width: 1440px; padding-top: 1.6rem; }
      [data-testid="stSidebar"] {
        background: #f8faf8;
        border-right: 1px solid var(--line);
      }
      h1, h2, h3 { color: var(--ink); letter-spacing: -0.02em; }
      p, label, [data-testid="stCaptionContainer"] { color: var(--muted); }
      [data-testid="stMetric"] {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 10px;
        padding: 1rem 1.1rem;
      }
      [data-testid="stMetricLabel"] { color: var(--muted); }
      [data-testid="stMetricValue"] { color: var(--ink); }
      [data-testid="stSidebarNav"] { padding-top: 0.4rem; }
      div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--line);
        background: var(--surface);
      }
      @media (max-width: 760px) {
        .block-container { padding: 1rem 1rem 2rem; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown("### DT-CARGO")
st.sidebar.caption("Vehicle telemetry intelligence")
st.sidebar.divider()


def placeholder_page(
    section: str,
    title: str,
    description: str,
    primary_action: str,
    phase: str,
):
    """Create a consistent page shell while its analysis is being connected."""

    def render() -> None:
        st.caption(section.upper())
        st.title(title)
        st.write(description)
        with st.container(border=True):
            st.caption("PRIMARY ACTION")
            st.markdown(f"**{primary_action}**")
        if phase == "prediction":
            st.warning(
                "Pre-departure estimates are not ready yet. The current training "
                "template has no planned-distance or cargo values, so this page "
                "will wait for populated pre-trip data and a matching model."
            )
        else:
            st.info(
                "This page is in the first app shell. Its analysis and interactive "
                "controls will be added in the next build phases."
            )

    return render


PAGES = {
    "Overview": [
        st.Page(
            render_overview,
            title="Fleet Overview",
            icon=":material/dashboard:",
            default=True,
            help="Review fleet activity and open a summary to investigate its vehicles or tracks.",
        ),
    ],
    "Investigate": [
        st.Page(
            placeholder_page(
                "Investigate",
                "Anomaly Monitoring",
                "Find unusual vehicle and track records, review their scores, and follow the evidence behind each flag.",
                "Filter the review queue and open a flagged record.",
                "planned",
            ),
            title="Anomaly Monitoring",
            icon=":material/warning:",
            help="Filter flagged records, identify repeated signals, and open a record for review.",
        ),
        st.Page(
            placeholder_page(
                "Investigate",
                "Vehicle Explorer",
                "Follow one vehicle across its tours, movement clusters, and anomaly history.",
                "Search for a vehicle and inspect its activity timeline.",
                "planned",
            ),
            title="Vehicle Explorer",
            icon=":material/directions_car:",
            help="Search for a vehicle and inspect its activity, cluster mix, and anomaly history.",
        ),
        st.Page(
            placeholder_page(
                "Investigate",
                "Track Explorer",
                "Inspect an individual track's movement, telemetry quality, and model results.",
                "Find a track and review its speed, stops, and quality warnings.",
                "planned",
            ),
            title="Track Explorer",
            icon=":material/route:",
            help="Find a track, inspect its telemetry, and compare it with typical movement.",
        ),
    ],
    "Plan": [
        st.Page(
            placeholder_page(
                "Plan",
                "Tour Duration",
                "Configure a hypothetical tour with information available before departure.",
                "Enter planned distance and operating context, then request an estimate.",
                "prediction",
            ),
            title="Tour Duration",
            icon=":material/schedule:",
            help="Estimate elapsed tour duration from planned, pre-departure inputs.",
        ),
    ],
    "Understand": [
        st.Page(
            placeholder_page(
                "Understand",
                "Cluster Analysis",
                "Compare the movement patterns represented by the project's behavioral clusters.",
                "Choose a cluster and compare its operating profile.",
                "planned",
            ),
            title="Cluster Analysis",
            icon=":material/scatter_plot:",
            help="Compare movement clusters by distance, speed, stops, duration, and population.",
        ),
        st.Page(
            placeholder_page(
                "Understand",
                "Data Quality",
                "See missingness, quality flags, and how data issues affect each analysis.",
                "Filter quality issues and inspect affected records and eligibility.",
                "planned",
            ),
            title="Data Quality",
            icon=":material/fact_check:",
            help="Inspect data-quality issues and see which records each analysis can use.",
        ),
        st.Page(
            placeholder_page(
                "Understand",
                "Model Insights",
                "Review how the anomaly, regression, and clustering methods work and where their results apply.",
                "Select a model and review its inputs, validation, and limitations.",
                "planned",
            ),
            title="Model Insights",
            icon=":material/insights:",
            help="Understand model inputs, evaluation results, thresholds, and limitations.",
        ),
    ],
}

page = st.navigation(PAGES, position="sidebar", expanded=True)
page.run()
