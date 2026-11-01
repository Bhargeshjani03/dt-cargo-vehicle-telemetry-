
import pandas as pd

from src.preprocessing.track import (
    prepare_track_clustering_data,
)


def test_track_preprocessing():

    track_features = pd.DataFrame({
        "track_id": [101, 102, 103, 104],
        "raw_speed_mean_kmh": [35.2, 42.1, 28.5, 31.0],
        "raw_speed_std": [4.2, 5.1, 3.8, 4.0],
        "low_speed_time_pct_03": [10.0, 5.0, 20.0, 15.0],
        "stop_episode_count_03": [2, 1, 4, 3],
    })

    quality_results = pd.DataFrame({
        "track_id": [101, 102, 103, 104],
        "quality_status": [
            "eligible",
            "eligible_with_warnings",
            "ineligible",
            "eligible",
        ],
        "reason_codes": [
            [],
            ["telemetry_coverage_low"],
            ["insufficient_telemetry"],
            [],
        ],
    })

    eligible, excluded = prepare_track_clustering_data(
        track_features,
        quality_results,
    )

    assert len(eligible) == 3
    assert len(excluded) == 1

    assert 103 not in eligible["track_id"].values
    assert 103 in excluded["track_id"].values

    assert 102 in eligible["track_id"].values

    assert "quality_status" in eligible.columns
    assert "reason_codes" in eligible.columns

    print("\nAll track preprocessing tests passed!")


if __name__ == "__main__":
    test_track_preprocessing()
