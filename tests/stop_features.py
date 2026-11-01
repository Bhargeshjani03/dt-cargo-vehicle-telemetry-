
import unittest

import pandas as pd

from src.preprocessing.stop_features import extract_stop_features


def make_track(speeds, epochs=None):

    if epochs is None:
        epochs = list(range(len(speeds)))

    return pd.DataFrame({
        "epoch": epochs,
        "speed": speeds
    })


class StopFeatureTests(unittest.TestCase):

    def test_35_second_stop(self):

        result = extract_stop_features(
            make_track([0.1] * 36)
        )

        self.assertEqual(
            result["stop_episode_count_03"], 1
        )

        self.assertAlmostEqual(
            result["longest_stop_seconds_03"], 35.0
        )

    def test_29_second_stop(self):

        result = extract_stop_features(
            make_track([0.1] * 30)
        )

        self.assertEqual(
            result["stop_episode_count_03"], 0
        )

    def test_two_separate_stops(self):

        speeds = (
            [0.1] * 36
            + [5.0]
            + [0.1] * 36
        )

        result = extract_stop_features(
            make_track(speeds)
        )

        self.assertEqual(
            result["stop_episode_count_03"], 2
        )

    def test_missing_speed_breaks_episode(self):

        speeds = (
            [0.1] * 20
            + [None]
            + [0.1] * 20
        )

        result = extract_stop_features(
            make_track(speeds)
        )

        self.assertEqual(
            result["stop_episode_count_03"], 0
        )

    def test_negative_speed_breaks_episode(self):

        speeds = (
            [0.1] * 20
            + [-1.0]
            + [0.1] * 20
        )

        result = extract_stop_features(
            make_track(speeds)
        )

        self.assertEqual(
            result["stop_episode_count_03"], 0
        )

    def test_large_gap_breaks_episode(self):

        result = extract_stop_features(
            make_track(
                [0.1, 0.1, 0.1, 0.1],
                [0, 1, 4, 5]
            )
        )

        self.assertEqual(
            result["stop_episode_count_03"], 0
        )

    def test_invalid_timestamp_breaks_episode(self):

        result = extract_stop_features(
            make_track(
                [0.1] * 41,
                list(range(20))
                + [None]
                + list(range(20, 40))
            )
        )

        self.assertEqual(
            result["stop_episode_count_03"], 0
        )

    def test_low_speed_percentage(self):

        result = extract_stop_features(
            make_track(
                [0.1, 0.1, 2.0],
                [0, 1, 2]
            )
        )

        self.assertAlmostEqual(
            result["low_speed_time_pct_03"],
            50.0
        )

    def test_episode_durations_are_returned(self):

        speeds = (
            [0.1] * 36
            + [5.0]
            + [0.1] * 46
        )

        result = extract_stop_features(
            make_track(speeds)
        )

        self.assertEqual(
            result["stop_episode_count_03"], 2
        )

        self.assertEqual(
            len(result["stop_episode_durations_seconds_03"]),
            2
        )

        self.assertAlmostEqual(
            result["stop_episode_durations_seconds_03"][0],
            35.0
        )

        self.assertAlmostEqual(
            result["stop_episode_durations_seconds_03"][1],
            45.0
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
