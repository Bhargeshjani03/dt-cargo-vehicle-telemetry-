
"""Live pre-trip tour-duration inference."""

from pathlib import Path
from typing import Any, Mapping

import joblib
import numpy as np
import pandas as pd

from .config import DEFAULT_MODEL_PATH, MODEL_VERSION


class TourRegressionPredictor:

    def __init__(self, model_path=DEFAULT_MODEL_PATH):
        self.model_path = Path(model_path)

        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"Model not found: {self.model_path}. "
                "Run python -m src.tour_regression.train first."
            )

        self.bundle = joblib.load(self.model_path)
        self._validate_bundle()

    def _validate_bundle(self):
        required = [
            "model_version",
            "regressor",
            "cluster_names",
            "cluster_profiles",
            "gap_threshold_hours",
            "distance_min_km",
            "distance_max_km",
        ]

        missing = [
            key for key in required
            if key not in self.bundle
        ]

        if missing:
            raise ValueError(
                f"Invalid model artifact. Missing keys: {missing}"
            )

    def predict_one(
        self,
        values: Mapping[str, Any],
    ) -> dict[str, Any]:

        try:
            distance = float(values["total_distance_km"])
            cluster_id = int(values["cluster_id"])
        except (KeyError, TypeError, ValueError):
            raise ValueError(
                "Provide total_distance_km and cluster_id."
            )

        if not np.isfinite(distance) or distance <= 0:
            raise ValueError(
                "Distance must be a positive finite number."
            )

        if cluster_id not in (0, 1):
            raise ValueError(
                "Operational category must be 0 or 1."
            )

        minimum = float(self.bundle["distance_min_km"])
        maximum = float(self.bundle["distance_max_km"])

        if distance < minimum or distance > maximum:
            raise ValueError(
                f"Distance must be within the historical range "
                f"of {minimum:.2f} to {maximum:.2f} km."
            )

        # Exactly the two inputs used by the live predictor.
        features = pd.DataFrame([{
            "total_distance_km": distance,
            "cluster": cluster_id,
        }])

        predicted_log = self.bundle["regressor"].predict(
            features
        )[0]

        predicted_hours = max(
            float(np.expm1(predicted_log)),
            0.0,
        )

        cluster_names = self.bundle["cluster_names"]
        cluster_profiles = self.bundle["cluster_profiles"]

        return {
            "predicted_elapsed_span_hours": predicted_hours,
            "predicted_elapsed_span_minutes": (
                predicted_hours * 60.0
            ),
            "distance_km": distance,
            "cluster_id": cluster_id,
            "cluster_name": cluster_names.get(
                cluster_id,
                f"Operational pattern {cluster_id}",
            ),
            "model_version": self.bundle["model_version"],
            "gap_threshold_hours": float(
                self.bundle["gap_threshold_hours"]
            ),
            "prediction_assumption": (
                "Conditional regular-tour estimate. Cluster 1 "
                "training excluded historical tours with gaps above "
                "the configured threshold. A future tour's gap is "
                "not known at dispatch."
            ),
            "cluster_profile": cluster_profiles.get(
                cluster_id,
                {},
            ),
        }

    @property
    def model_version(self):
        return str(
            self.bundle.get("model_version", MODEL_VERSION)
        )


_predictor = None


def load_predictor(model_path=DEFAULT_MODEL_PATH):
    global _predictor

    if _predictor is None:
        _predictor = TourRegressionPredictor(model_path)

    return _predictor
