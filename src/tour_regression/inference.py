"""Prediction interface for the saved DT-CARGO hybrid model.

This module has no web-framework dependency. A future API layer can import
TourRegressionPredictor and call predict_one() or predict_many().
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Mapping

import joblib
import numpy as np
import pandas as pd

from .config import (
    CLUSTER_FEATURES,
    DEFAULT_MODEL_PATH,
    MODEL_VERSION,
    REGRESSION_FEATURES,
)


class TourRegressionPredictor:
    """Load once, then reuse for single-tour or batch predictions."""

    def __init__(self, model_path: str | Path = DEFAULT_MODEL_PATH):
        self.model_path = Path(model_path)
        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"Trained model artifact not found: {self.model_path}. "
                "Run `python -m src.tour_regression.train` first."
            )

        # joblib/pickle artifacts must only be loaded from trusted sources.
        self.bundle = joblib.load(self.model_path)
        self._validate_bundle()

    def _validate_bundle(self) -> None:
        required = {
            "model_version", "imputer", "scaler", "kmeans", "regressor",
            "cluster_features", "regression_features", "cluster_profiles",
            "cluster_names", "target_transform",
        }
        missing = required.difference(self.bundle)
        if missing:
            raise ValueError(
                f"Model artifact is missing required keys: {sorted(missing)}"
            )

        if list(self.bundle["cluster_features"]) != CLUSTER_FEATURES:
            raise ValueError("Saved cluster feature schema does not match this code.")
        if list(self.bundle["regression_features"]) != REGRESSION_FEATURES:
            raise ValueError("Saved regression feature schema does not match this code.")
        if self.bundle["target_transform"] != "log1p; inverse with expm1":
            raise ValueError("Unsupported target transformation in model artifact.")

    @staticmethod
    def _coerce_input(values: Mapping[str, Any] | pd.DataFrame) -> pd.DataFrame:
        if isinstance(values, Mapping):
            frame = pd.DataFrame([dict(values)])
        elif isinstance(values, pd.DataFrame):
            frame = values.copy()
        else:
            raise TypeError("Input must be a mapping or pandas DataFrame.")

        missing = [c for c in REGRESSION_FEATURES if c not in frame.columns]
        if missing:
            raise ValueError(f"Missing required prediction features: {missing}")

        frame = frame[REGRESSION_FEATURES].apply(pd.to_numeric, errors="coerce")
        frame = frame.replace([np.inf, -np.inf], np.nan)

        if frame.isna().any().any():
            bad_columns = frame.columns[frame.isna().any()].tolist()
            raise ValueError(
                "Prediction inputs must be finite numeric values. "
                f"Invalid or missing values in: {bad_columns}"
            )

        if (frame[CLUSTER_FEATURES] < 0).any().any():
            raise ValueError("Distance and average speed must be non-negative.")
        if (frame["track_count"] <= 0).any():
            raise ValueError("track_count must be greater than zero.")

        return frame.astype(float)

    def predict_many(self, values: pd.DataFrame) -> pd.DataFrame:
        """Return one prediction and cluster assignment per input row."""
        frame = self._coerce_input(values)

        cluster_raw = frame[CLUSTER_FEATURES]
        cluster_imputed = self.bundle["imputer"].transform(cluster_raw)
        cluster_logged = np.log1p(np.clip(cluster_imputed, 0, None))
        cluster_scaled = self.bundle["scaler"].transform(cluster_logged)
        cluster_ids = self.bundle["kmeans"].predict(cluster_scaled).astype(int)

        regression_frame = frame[REGRESSION_FEATURES].copy()
        regression_frame["cluster"] = cluster_ids

        predicted_log_hours = self.bundle["regressor"].predict(regression_frame)
        predicted_hours = np.expm1(predicted_log_hours)
        predicted_hours = np.maximum(predicted_hours, 0.0)

        rows = []
        for position, (cluster_id, hours) in enumerate(
            zip(cluster_ids, predicted_hours)
        ):
            profile = self.bundle["cluster_profiles"].get(int(cluster_id), {})
            rows.append({
                "row_index": frame.index[position],
                "predicted_elapsed_span_hours": float(hours),
                "predicted_elapsed_span_minutes": float(hours * 60.0),
                "cluster_id": int(cluster_id),
                "cluster_name": self.bundle["cluster_names"].get(
                    int(cluster_id), f"Operational pattern {cluster_id}"
                ),
                "cluster_profile": profile,
                "model_version": self.bundle["model_version"],
            })

        return pd.DataFrame(rows).set_index("row_index", drop=True)

    def predict_one(self, values: Mapping[str, Any]) -> dict[str, Any]:
        """Predict elapsed tour span for one tour from API-friendly inputs."""
        result = self.predict_many(pd.DataFrame([dict(values)]))
        return result.iloc[0].to_dict()

    @property
    def model_version(self) -> str:
        return str(self.bundle.get("model_version", MODEL_VERSION))


def load_predictor(
    model_path: str | Path = DEFAULT_MODEL_PATH,
) -> TourRegressionPredictor:
    """Convenience loader for a future API dependency/container."""
    return TourRegressionPredictor(model_path)
