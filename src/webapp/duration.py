"""Pre-departure tour duration prediction interface."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import json

import joblib
import numpy as np
import pandas as pd
import streamlit as st

from src.webapp.data import resolve_runtime_path
from src.webapp.regression_insights import render_tour_level_benchmark
from src.webapp.charts import render_metric_grid


MODEL_PATH = "src/tour_duration/artifacts/tour_duration_v1.joblib"
METADATA_PATH = "src/tour_duration/artifacts/tour_duration_v1.json"
TRAINING_DATA_PATH = "data/processed/tour_level/telemetry_flagged_episodes_12h.csv"
FEATURE_COLUMNS = [
    "total_distance_km", "gross_vehicle_weight", "total_mass_with_trailer",
    "axle_class", "start_year", "start_month", "start_weekday", "start_hour",
    "vehicle_id",
]
OPTION_COLUMNS = [
    "vehicle_id", "gross_vehicle_weight", "total_mass_with_trailer", "axle_class",
]


@st.cache_resource(show_spinner="Loading the duration model…")
def _load_model(path: str, modified_ns: int):
    del modified_ns
    return joblib.load(path)


@st.cache_data(show_spinner=False)
def _load_metadata(path: str, modified_ns: int) -> dict:
    del modified_ns
    return json.loads(open(path, encoding="utf-8").read())


@st.cache_data(show_spinner="Loading available vehicle profiles…")
def _load_options(path: str, modified_ns: int) -> pd.DataFrame:
    del modified_ns
    frame = pd.read_csv(path, usecols=OPTION_COLUMNS, low_memory=False)
    for column in OPTION_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.dropna(subset=OPTION_COLUMNS).drop_duplicates().reset_index(drop=True)


def _format_integer(value: float) -> str:
    number = float(value)
    return f"{number:,.0f}" if number.is_integer() else f"{number:,.1f}"


def _options(frame: pd.DataFrame, column: str) -> list[float]:
    return sorted(pd.to_numeric(frame[column], errors="coerce").dropna().unique().tolist())


def render_tour_duration() -> None:
    st.caption("PLAN")
    st.title("Tour Duration")
    st.write(
        "Estimate a planned tour’s elapsed duration using vehicle details, planned distance, "
        "and departure timing available before the tour begins."
    )

    model_path = resolve_runtime_path(MODEL_PATH)
    metadata_path = resolve_runtime_path(METADATA_PATH)
    options_path = resolve_runtime_path(TRAINING_DATA_PATH)
    missing = [
        label for label, path in (
            ("duration model", model_path),
            ("model metadata", metadata_path),
            ("historical vehicle profiles", options_path),
        ) if not path.is_file()
    ]
    if missing:
        st.warning(
            "The prediction page needs the following local model files: "
            + ", ".join(missing)
            + "."
        )
        return

    metadata = _load_metadata(str(metadata_path), metadata_path.stat().st_mtime_ns)
    profiles = _load_options(str(options_path), options_path.stat().st_mtime_ns)
    if profiles.empty:
        st.warning("No complete historical vehicle profiles are available for the form.")
        return

    vehicle_ids = _options(profiles, "vehicle_id")
    weights = _options(profiles, "gross_vehicle_weight")
    masses = _options(profiles, "total_mass_with_trailer")
    axle_classes = _options(profiles, "axle_class")
    if not all((vehicle_ids, weights, masses, axle_classes)):
        st.warning("The historical data does not contain every input required by this model.")
        return

    st.caption("Departure date and time are interpreted as UTC to match model training timestamps.")
    with st.form("tour-duration-prediction"):
        vehicle_col, distance_col = st.columns(2)
        with vehicle_col:
            vehicle_id = st.selectbox(
                "Historical vehicle profile",
                vehicle_ids,
                format_func=lambda value: f"Vehicle {_format_integer(value)}",
                help="Vehicle ID is one of the model’s pre-departure inputs.",
            )
        with distance_col:
            planned_distance = st.number_input(
                "Planned distance (km)",
                min_value=1.0,
                max_value=5000.0,
                value=400.0,
                step=10.0,
            )

        spec_columns = st.columns(2)
        with spec_columns[0]:
            gross_weight = st.selectbox(
                "Gross vehicle weight",
                weights,
                format_func=lambda value: f"{_format_integer(value)} kg",
            )
        with spec_columns[1]:
            total_mass = st.selectbox(
                "Total mass with trailer",
                masses,
                format_func=lambda value: f"{_format_integer(value)} kg",
            )
        axle_class = st.selectbox(
            "Axle class",
            axle_classes,
            format_func=lambda value: _format_integer(value),
        )

        departure_columns = st.columns(2)
        with departure_columns[0]:
            departure_date = st.date_input("Planned departure date", value=date.today())
        with departure_columns[1]:
            departure_time = st.time_input("Planned departure time", value=time(8, 0))

        submitted = st.form_submit_button("Estimate duration", type="primary")

    st.info(metadata.get("distanceFeatureNote", "Planned distance is substituted for historical completed-tour distance."))

    if submitted:
        departure = datetime.combine(departure_date, departure_time).replace(tzinfo=timezone.utc)
        model_inputs = {
            "total_distance_km": float(planned_distance),
            "gross_vehicle_weight": float(gross_weight),
            "total_mass_with_trailer": float(total_mass),
            "axle_class": float(axle_class),
            "start_year": float(departure.year),
            "start_month": float(departure.month),
            "start_weekday": float(departure.weekday()),
            "start_hour": float(departure.hour),
            "vehicle_id": float(vehicle_id),
        }
        input_frame = pd.DataFrame([model_inputs], columns=FEATURE_COLUMNS)
        model = _load_model(str(model_path), model_path.stat().st_mtime_ns)
        estimate = float(model.predict(input_frame)[0])
        if not np.isfinite(estimate):
            st.error("The model did not return a usable duration for these inputs.")
            return
        estimate = max(0.0, estimate)

        render_metric_grid([
            ("Estimated total time", f"{estimate:.1f} h"),
            ("Average miss on past tours", f"{metadata['holdoutMetrics']['maeHours']:.1f} h"),
            ("Past tours tested", f"{metadata['holdoutMetrics']['holdoutEpisodes']:,}"),
        ], label="Tour duration estimate")
        estimated_arrival = departure + timedelta(hours=estimate)
        departure_label = departure.strftime("%d %b · %H:%M UTC")
        arrival_label = estimated_arrival.strftime("%d %b · %H:%M UTC")
        st.markdown(
            f"""
            <section role="img" aria-label="Estimated trip timeline. Depart {departure_label}; expected arrival {arrival_label}; estimated elapsed time {estimate:.1f} hours."
              style="margin:.65rem 0 1rem;padding:18px 20px;border:1px solid rgba(183,201,219,.2);border-radius:18px;background:linear-gradient(140deg,#162330,#101820);color:#f4f7fa;">
              <div style="display:flex;justify-content:space-between;gap:12px;align-items:baseline;flex-wrap:wrap;">
                <strong style="font-size:16px;">Your estimated trip window</strong>
                <span style="color:#c0ccd7;font-size:13px;">{estimate:.1f} hours elapsed</span>
              </div>
              <div style="display:flex;align-items:center;gap:9px;margin:17px 3px 10px;">
                <span style="width:13px;height:13px;border:3px solid #74d3e8;border-radius:50%;background:#17232e;flex:0 0 auto;"></span>
                <span style="height:5px;flex:1;border-radius:9px;background:linear-gradient(90deg,#74d3e8,#63a9ff,#ffc45e);position:relative;overflow:hidden;">
                  <i style="position:absolute;inset:0;background:linear-gradient(90deg,transparent,rgba(255,255,255,.6),transparent);animation:trip-pulse 2.8s ease-in-out infinite;"></i>
                </span>
                <span style="width:13px;height:13px;border:3px solid #ffc45e;border-radius:50%;background:#17232e;flex:0 0 auto;"></span>
              </div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:12px;">
                <span><b style="display:block;color:#74d3e8;letter-spacing:.08em;">DEPART</b>{departure_label}</span>
                <span style="text-align:right;"><b style="display:block;color:#ffc45e;letter-spacing:.08em;">EXPECTED ARRIVAL</b>{arrival_label}</span>
              </div>
              <p style="margin:13px 0 0;color:#c0ccd7;font-size:13px;line-height:1.45;">This estimate includes the elapsed time between recorded tracks. It is a planning guide, not a promised arrival time.</p>
            </section>
            <style>@keyframes trip-pulse{{from{{transform:translateX(-100%)}}to{{transform:translateX(100%)}}}}@media(prefers-reduced-motion:reduce){{i{{animation:none!important;display:none}}}}</style>
            """,
            unsafe_allow_html=True,
        )
        st.caption("The average miss is measured on past tours; it is not a guaranteed range for this estimate.")

        bounds = metadata.get("inputBounds", {})
        labels = {
            "total_distance_km": "Planned distance",
            "gross_vehicle_weight": "Gross vehicle weight",
            "total_mass_with_trailer": "Total mass with trailer",
            "axle_class": "Axle class",
            "start_year": "Departure year",
            "start_month": "Departure month",
            "start_weekday": "Departure weekday",
            "start_hour": "Departure hour",
            "vehicle_id": "Vehicle ID",
        }
        out_of_range = []
        for feature, value in model_inputs.items():
            feature_bounds = bounds.get(feature)
            if feature_bounds and (
                value < feature_bounds["min"] or value > feature_bounds["max"]
            ):
                out_of_range.append(labels[feature])
        if out_of_range:
            st.warning(
                "These inputs are outside the historical training range: "
                + ", ".join(out_of_range)
                + ". Treat the estimate cautiously."
            )

    st.info(
        "The new notebook’s completed-tour study averaged a 2.01-hour miss when tested "
        "on held-out vehicles. It uses recorded average speed and track count, so this "
        "result does not measure the pre-departure estimate above."
    )
    render_tour_level_benchmark()

    with st.expander("How to interpret this estimate"):
        st.markdown(
            "The estimate comes from a HistGradientBoosting regression model trained on "
            f"{metadata['trainingExamples']:,} historical tour episodes. It predicts elapsed span, "
            "which includes gaps and pauses as well as driving time. The model does not provide "
            "causal feature attribution for an individual estimate."
        )
        metrics = metadata.get("holdoutMetrics", {})
        if metrics:
            st.caption(
                f"Chronological holdout: R² {metrics['r2']:.3f}; "
                f"MAE {metrics['maeHours']:.2f} hours; "
                f"RMSE {metrics['rmseHours']:.2f} hours."
            )
        limitations = metadata.get("limitations", [])
        if limitations:
            st.markdown("\n".join(f"- {item}" for item in limitations))
