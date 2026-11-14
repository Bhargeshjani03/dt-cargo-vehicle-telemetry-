"""Tests for the DT-CARGO hybrid tour clustering-regression module.

Run from the repository root:
    python -m unittest discover -s tests -p 'test_tour_regression.py' -v

These tests train against a small synthetic dataset in a temporary directory.
They do not require the full DT-CARGO CSV and do not write model artifacts
into the project tree.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.tour_regression.config import (
    CLUSTER_FEATURES,
    DEFAULT_DATA_PATH,
    DEFAULT_MODEL_PATH,
    REGRESSION_FEATURES,
    TARGET_COLUMN,
)
from src.tour_regression.inference import TourRegressionPredictor, load_predictor
from src.tour_regression.train import train_model


class TourRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory(prefix="dt_cargo_tour_tests_")
        cls.temp_path = Path(cls.temp_dir.name)
        cls.csv_path = cls.temp_path / "synthetic_tours.csv"
        cls.model_path = cls.temp_path / "hybrid_model.joblib"

        rng = np.random.default_rng(42)
        row_count = 160
        distances = rng.uniform(2.0, 500.0, row_count)
        speeds = rng.uniform(5.0, 85.0, row_count)
        track_counts = rng.integers(1, 16, row_count)

        # A deterministic positive target with variation across tour inputs.
        elapsed_hours = (
            distances / np.maximum(speeds, 1.0)
            + 0.12 * track_counts
            + rng.uniform(0.1, 2.0, row_count)
        )

        synthetic_data = pd.DataFrame(
            {
                "total_distance_km": distances,
                "distance_based_avg_speed_kmh_clean": speeds,
                "track_count": track_counts,
                TARGET_COLUMN: elapsed_hours,
            }
        )
        synthetic_data.to_csv(cls.csv_path, index=False)

        train_model(cls.csv_path, cls.model_path)
        cls.predictor = load_predictor(cls.model_path)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()

    def test_default_paths_point_to_project_data_and_artifacts(self) -> None:
        self.assertTrue(str(DEFAULT_DATA_PATH).endswith(
            "data/processed/tour_level/pca_experiments/input/"
            "experiment_B_75pct_without_extreme.csv"
        ))
        self.assertTrue(str(DEFAULT_MODEL_PATH).endswith(
            "src/tour_regression/artifacts/hybrid_tour_regression.joblib"
        ))

    def test_training_creates_model_artifact(self) -> None:
        self.assertTrue(self.model_path.is_file())
        self.assertGreater(self.model_path.stat().st_size, 0)

    def test_single_prediction_returns_expected_fields(self) -> None:
        prediction = self.predictor.predict_one(
            {
                "total_distance_km": 188.4,
                "distance_based_avg_speed_kmh_clean": 45.33,
                "track_count": 5,
            }
        )

        self.assertIn("predicted_elapsed_span_hours", prediction)
        self.assertIn("predicted_elapsed_span_minutes", prediction)
        self.assertIn("cluster_id", prediction)
        self.assertIn("cluster_name", prediction)
        self.assertIn("model_version", prediction)
        self.assertGreaterEqual(prediction["predicted_elapsed_span_hours"], 0)
        self.assertAlmostEqual(
            prediction["predicted_elapsed_span_minutes"],
            prediction["predicted_elapsed_span_hours"] * 60,
            places=6,
        )
        self.assertIn(prediction["cluster_id"], (0, 1))

    def test_batch_prediction_preserves_number_of_rows(self) -> None:
        tours = pd.DataFrame(
            [
                {
                    "total_distance_km": 188.4,
                    "distance_based_avg_speed_kmh_clean": 45.33,
                    "track_count": 5,
                },
                {
                    "total_distance_km": 8.31,
                    "distance_based_avg_speed_kmh_clean": 10.06,
                    "track_count": 3,
                },
                {
                    "total_distance_km": 350.0,
                    "distance_based_avg_speed_kmh_clean": 55.0,
                    "track_count": 8,
                },
            ]
        )

        predictions = self.predictor.predict_many(tours)
        self.assertEqual(len(predictions), len(tours))
        self.assertTrue(predictions["predicted_elapsed_span_hours"].notna().all())
        self.assertTrue((predictions["predicted_elapsed_span_hours"] >= 0).all())

    def test_missing_feature_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Missing required prediction features"):
            self.predictor.predict_one(
                {
                    "total_distance_km": 100,
                    "track_count": 4,
                }
            )

    def test_non_finite_input_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "finite numeric values"):
            self.predictor.predict_one(
                {
                    "total_distance_km": np.inf,
                    "distance_based_avg_speed_kmh_clean": 40,
                    "track_count": 4,
                }
            )

    def test_negative_distance_or_speed_is_rejected(self) -> None:
        for feature in CLUSTER_FEATURES:
            values = {
                "total_distance_km": 100,
                "distance_based_avg_speed_kmh_clean": 40,
                "track_count": 4,
            }
            values[feature] = -1
            with self.subTest(feature=feature):
                with self.assertRaisesRegex(ValueError, "non-negative"):
                    self.predictor.predict_one(values)

    def test_non_positive_track_count_is_rejected(self) -> None:
        values = {
            "total_distance_km": 100,
            "distance_based_avg_speed_kmh_clean": 40,
            "track_count": 0,
        }
        with self.assertRaisesRegex(ValueError, "track_count must be greater than zero"):
            self.predictor.predict_one(values)

    def test_wrong_input_type_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            self.predictor.predict_many([1, 2, 3])  # type: ignore[arg-type]

    def test_missing_artifact_raises_clear_error(self) -> None:
        missing_path = self.temp_path / "does_not_exist.joblib"
        with self.assertRaisesRegex(FileNotFoundError, "Run `python -m src.tour_regression.train` first"):
            TourRegressionPredictor(missing_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
