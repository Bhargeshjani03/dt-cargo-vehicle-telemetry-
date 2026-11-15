"""Operator-friendly model notes backed by the saved evaluation reports."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.webapp.charts import render_metric_grid
from src.webapp.data import DISPLAY_CLUSTER_NAMES, resolve_runtime_path
from src.webapp.navigation import get_page_link
from src.webapp.regression_insights import render_tour_level_benchmark


ANOMALY_SUMMARY_PATH = "src/anomaly_detection/reports/full/validation_summary.json"
DURATION_METADATA_PATH = "src/tour_duration/artifacts/tour_duration_v1.json"


@st.cache_data(show_spinner=False)
def _read_json(path: str, modified_ns: int) -> dict:
    del modified_ns
    return json.loads(Path(path).read_text(encoding="utf-8"))


def render_methodology() -> None:
    st.caption("UNDERSTAND")
    st.title("Model Insights & Methodology")
    st.write("A plain-language guide to what each result can tell you, and what it cannot.")
    st.markdown(
        """
        <style>
          .model-guide{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin:.7rem 0 1.5rem}
          .model-guide article{min-width:0;padding:18px;border:1px solid #d9dfe4;border-radius:18px;background:linear-gradient(155deg,#172331,#101820);color:#f4f7fa;box-shadow:0 12px 30px rgba(20,30,40,.12)}
          .model-guide .step{display:block;color:#ffc45e;font-size:11px;font-weight:800;letter-spacing:.12em;text-transform:uppercase}
          .model-guide h3{margin:9px 0 7px;color:#fff;font-size:20px;line-height:1.2}
          .model-guide p{margin:.4rem 0;color:#d5dce4;font-size:14px;line-height:1.5}
          .model-guide .flow{display:flex;align-items:center;gap:8px;margin:14px 0;padding:10px;border-radius:12px;background:rgba(255,255,255,.07);font-size:12px;font-weight:700}
          .model-guide .flow span{flex:1;text-align:center}
          .model-guide .flow b{color:#69c9e6;font-size:18px}
          .model-guide .meaning{padding-top:9px;border-top:1px solid rgba(255,255,255,.14)}
          .model-guide .method{display:block;margin-top:11px;color:#aeb9c4;font-size:11px;line-height:1.4}
          @media(max-width:760px){.model-guide{grid-template-columns:1fr}.model-guide article{padding:16px}}
          @media(prefers-reduced-motion:reduce){.model-guide *{scroll-behavior:auto!important;animation:none!important;transition:none!important}}
        </style>
        <section class="model-guide" aria-label="What each model does">
          <article role="group" aria-label="Unusual-track review: compare a trip to historical tracks and decide what to check first">
            <span class="step">01 · Review a track</span><h3>Find trips to check</h3>
            <p>Compares a recorded track with past tracks using speed, stops, duration, and distance.</p>
            <div class="flow"><span>Recorded trip</span><b aria-hidden="true">→</b><span>Review first</span></div>
            <p class="meaning"><strong>What it means:</strong> A prompt to investigate, not proof of an incident or unsafe driving.</p>
            <small class="method">Method used: Isolation Forest · score means unusualness, not probability.</small>
          </article>
          <article role="group" aria-label="Movement patterns: group similar twelve-hour episodes into saved patterns">
            <span class="step">02 · Compare patterns</span><h3>Group similar trips</h3>
            <p>Places similar saved 12-hour episodes together so common movement patterns are easier to see.</p>
            <div class="flow"><span>Longer-distance travel</span><b aria-hidden="true">·</b><span>Low movement + gaps</span></div>
            <p class="meaning"><strong>What it means:</strong> A summary of past movement; it is not a driver rating or a fault label.</p>
            <small class="method">Method used: saved movement clustering · two display groups are shown.</small>
          </article>
          <article role="group" aria-label="Tour duration estimate: use pre-departure inputs to estimate elapsed tour time">
            <span class="step">03 · Plan a tour</span><h3>Estimate elapsed time</h3>
            <p>Uses vehicle details, planned distance, and departure time to estimate a tour’s total elapsed span.</p>
            <div class="flow"><span>Plan details</span><b aria-hidden="true">→</b><span>Time estimate</span></div>
            <p class="meaning"><strong>What it means:</strong> A planning guide that includes waiting and gaps, not only driving time.</p>
            <small class="method">Model used: HistGradientBoosting regression · based on pre-departure inputs.</small>
          </article>
        </section>
        """,
        unsafe_allow_html=True,
    )

    anomaly_path = resolve_runtime_path(ANOMALY_SUMMARY_PATH)
    duration_path = resolve_runtime_path(DURATION_METADATA_PATH)
    anomaly_report = _read_json(str(anomaly_path), anomaly_path.stat().st_mtime_ns) if anomaly_path.is_file() else {}
    duration = _read_json(str(duration_path), duration_path.stat().st_mtime_ns) if duration_path.is_file() else {}
    anomaly = anomaly_report.get("extended_six_feature", {})
    anomaly_features = [
        ("Average speed", "Typical speed during the track."),
        ("Speed variation", "How much speed changed during the track."),
        ("Time nearly stopped", "Share of valid samples below 0.3 m/s."),
        ("Stop periods", "Periods of at least 30 seconds below 0.3 m/s."),
        ("Track duration", "Elapsed time for the track."),
        ("Recorded distance", "Distance recorded for the track."),
    ]

    st.subheader("Unusual-track review")
    if anomaly:
        render_metric_grid([
            ("Tracks assessed", f"{anomaly.get('validation_tracks', 0):,}"),
            ("Saved review flags", f"{anomaly.get('validation_flagged_tracks', 0):,}"),
            ("Review cutoff", f"{anomaly.get('threshold', 0):.3f}"),
        ], label="Unusual-track review summary")
    st.markdown(
        "The model looks for track records that differ from other historical records on speed, stops, duration, and distance. "
        "A high score means ‘less like the usual data’—it does not mean a breakdown, unsafe driving, or a confirmed anomaly."
    )
    st.markdown("**Signals it looks at**")
    st.dataframe(pd.DataFrame(anomaly_features, columns=["Signal", "In everyday terms"]), hide_index=True, width="stretch")
    if anomaly:
        st.info(
            f"The saved validation used a {anomaly.get('threshold_policy', {}).get('target_review_rate', .02):.0%} review-queue target. "
            "There are no confirmed incident labels, so this is not an accuracy score and the queue size is not anomaly prevalence."
        )

    st.subheader("Tour duration estimate")
    if duration:
        metrics = duration.get("holdoutMetrics", {})
        render_metric_grid([
            ("Past episodes used to train", f"{duration.get('trainingExamples', 0):,}"),
            ("Average miss on past tours", f"{metrics.get('maeHours', 0):.1f} h"),
            ("Past tours tested", f"{metrics.get('holdoutEpisodes', 0):,}"),
        ], label="Tour duration model summary")
    st.markdown(
        "The regressor estimates the time from tour start to tour end using vehicle specifications, planned distance, "
        "vehicle ID, and planned departure timing. It uses only those pre-departure inputs."
    )
    st.warning(
        "Training records contain completed-tour distance; planned distance is substituted when you ask for an estimate. "
        "That is a proxy, so treat the result as a planning guide. The target includes waiting and gaps, not just driving time."
    )
    if duration and metrics:
        st.caption(
            f"On a later-in-time historical holdout, the model’s R² was {metrics.get('r2', 0):.3f} and RMSE was "
            f"{metrics.get('rmseHours', 0):.2f} hours. This describes the saved holdout only; it is not a guarantee for a new route."
        )

    render_tour_level_benchmark(expanded=True)

    st.subheader("Movement patterns")
    st.markdown(
        f"**Cluster 0 · {DISPLAY_CLUSTER_NAMES[0]}**\n\n"
        "Typically a larger distance covered over a few hours. In the saved episodes, the middle episode covers about 156 km in 6.3 hours.\n\n"
        f"**Cluster 1 · {DISPLAY_CLUSTER_NAMES[1]}**\n\n"
        "Typically very little recorded distance spread across a much longer elapsed period. The middle episode covers about 3.5 km over 16.3 hours, with a longest within-episode gap of about 6.2 hours. Check the schedule and telemetry before calling this a delay."
    )
    st.caption(
        "These names summarize medians in the saved 12-hour assignment file. They are descriptive patterns, not operating classes. "
        "Display Cluster 1 maps to saved source cluster 2; the source assignments are unchanged."
    )

    st.subheader("How an operator should use the results")
    st.markdown(
        "1. Start with the recorded data and any quality warnings.\n"
        "2. Use a model flag to decide which record to inspect first.\n"
        "3. Compare with the vehicle schedule, adjacent tracks, and known operating conditions.\n"
        "4. Confirm the finding with an operator before taking action."
    )
    for page_name, label in zip(
        ["Anomaly Monitoring", "Tour Duration Prediction", "Cluster Analysis"],
        ["Review unusual tracks", "Estimate tour duration", "Compare movement patterns"],
    ):
        page = get_page_link(page_name)
        if page is not None:
            st.page_link(page, label=label, icon=":material/arrow_forward:")
