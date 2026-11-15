"""Plain-language summary of the latest saved tour-level regression study."""

from __future__ import annotations

import streamlit as st

from src.webapp.charts import render_metric_grid


def render_tour_level_benchmark(*, expanded: bool = False) -> None:
    """Show notebook evaluation results without presenting them as the planner model."""
    with st.expander("New tour-level regression study", expanded=expanded):
        st.write(
            "The latest analysis checked a single decision-tree model against new vehicles "
            "across five validation rounds. It used 7,563 completed tours from 97 vehicles "
            "in the notebook’s filtered Dataset B cohort."
        )
        render_metric_grid([
            ("Average miss", "2.01 h"),
            ("Miss when large errors count more", "8.02 h"),
            ("Fit across held-out vehicles", "0.762"),
        ], label="Completed-tour research benchmark")
        st.caption(
            "Average miss is the mean absolute error. The large-error-sensitive measure "
            "rises when a few predictions are far off. The fit score describes how well "
            "predictions follow differences in the historical durations; it is not a "
            "probability that an estimate is correct."
        )
        st.markdown(
            "**A split by movement pattern was mixed.** It lowered the average miss by "
            "2.22% (2.01 h to 1.96 h), but increased the large-error-sensitive miss "
            "(8.02 h to 8.25 h) and reduced the fit score (0.762 to 0.748)."
        )
        st.warning(
            "This is a completed-tour benchmark, not the pre-departure predictor above. "
            "It uses recorded distance, average speed, and track count—signals known after "
            "a tour. Its scores also come from a filtered dataset and a different validation "
            "setup, so they should not be compared directly with the planner model’s "
            "later-in-time holdout."
        )
        st.caption(
            "Source: saved results in notebooks/tour_level_analysis.ipynb. "
            "The notebook contains validation results, not a ready-to-use model artifact."
        )
