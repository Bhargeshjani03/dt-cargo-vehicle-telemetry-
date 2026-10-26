import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.features import extract_track_features


class FeatureExtractionTests(unittest.TestCase):
    def test_speed_statistics_and_low_speed_percentage(self):
        speed = pd.DataFrame({
            "epoch": [0.0, 1.0, 2.0],
            "speed": [0.0, 1.0, 2.0],
        })

        features = extract_track_features(speed)

        self.assertAlmostEqual(features["raw_speed_mean_kmh"], 3.6)
        self.assertAlmostEqual(features["raw_speed_std"], 1.0)
        self.assertAlmostEqual(features["low_speed_time_pct_03"], 50.0)
        self.assertEqual(features["stop_episode_count_03"], 0)

    def test_exactly_thirty_seconds_counts_as_a_stop_episode(self):
        speed = pd.DataFrame({
            "epoch": np.arange(31, dtype=float),
            "speed": np.full(31, 0.1),
        })

        features = extract_track_features(speed)

        self.assertEqual(features["stop_episode_count_03"], 1)
        self.assertAlmostEqual(features["low_speed_time_pct_03"], 100.0)

    def test_shorter_than_thirty_seconds_does_not_count_as_stop(self):
        speed = pd.DataFrame({
            "epoch": np.arange(30, dtype=float),
            "speed": np.full(30, 0.1),
        })

        features = extract_track_features(speed)

        self.assertEqual(features["stop_episode_count_03"], 0)

    def test_intervals_over_two_seconds_are_excluded(self):
        speed = pd.DataFrame({
            "epoch": [0.0, 2.0, 4.1, 6.1],
            "speed": [0.1, 0.1, 0.5, 0.5],
        })

        features = extract_track_features(speed)

        self.assertEqual(features["valid_interval_count"], 2)
        self.assertEqual(features["excluded_interval_count"], 1)
        self.assertAlmostEqual(features["valid_telemetry_time_seconds"], 4.0)
        self.assertAlmostEqual(features["low_speed_time_pct_03"], 50.0)

    def test_gap_splits_stop_episodes(self):
        epochs = list(range(15)) + list(range(20, 35))
        speed = pd.DataFrame({
            "epoch": epochs,
            "speed": np.full(len(epochs), 0.1),
        })

        features = extract_track_features(speed)

        self.assertEqual(features["stop_episode_count_03"], 0)
        self.assertAlmostEqual(features["low_speed_time_pct_03"], 100.0)

    def test_invalid_rows_are_counted_and_excluded(self):
        speed = pd.DataFrame({
            "epoch": [0.0, 1.0, None, 2.0],
            "speed": [0.1, 0.5, 1.0, "invalid"],
        })

        features = extract_track_features(speed)

        self.assertEqual(features["observation_count"], 2)
        self.assertEqual(features["invalid_observation_count"], 2)
        self.assertAlmostEqual(features["raw_speed_mean_kmh"], 1.08)

    def test_input_dataframe_is_not_modified(self):
        speed = pd.DataFrame({
            "epoch": [2.0, 0.0, 1.0],
            "speed": [2.0, 0.0, 1.0],
        })
        original = speed.copy(deep=True)

        extract_track_features(speed)

        pd.testing.assert_frame_equal(speed, original)

    def test_missing_columns_raise_clear_error(self):
        speed = pd.DataFrame({"time": [0.0, 1.0], "speed": [1.0, 2.0]})

        with self.assertRaisesRegex(ValueError, "epoch"):
            extract_track_features(speed)


if __name__ == "__main__":
    unittest.main()