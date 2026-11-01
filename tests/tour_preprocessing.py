
import pandas as pd

from src.preprocessing.tour import (
    prepare_tour_clustering_data,
)


def test_tour_preprocessing():

    track_data = pd.DataFrame({
        "track_id": [101, 102, 103, 104],
        "tour_id": [1, 1, 1, 2],

        # Distance in metres
        "distance": [10000, 20000, 30000, 40000],

        # Mean raw telemetry speed in km/h
        "raw_speed_mean_kmh": [10.0, 20.0, 30.0, 15.0],

        # Maximum speed in m/s
        "max_speed": [10.0, 15.0, 20.0, 12.0],

        "quality_status": [
            "eligible",
            "eligible_with_warnings",
            "ineligible",
            "ineligible",
        ],

        # Duration must not enter tour clustering
        "elapsed_span_hours": [2.0, 3.0, 4.0, 5.0],
    })

    tours, excluded = prepare_tour_clustering_data(
        track_data
    )

    # Two unique tours
    assert len(tours) == 2

    # Tour 1 distance includes all valid distances:
    # (10000 + 20000 + 30000) / 1000 = 60 km
    tour_1 = tours[tours["tour_id"] == 1].iloc[0]

    assert abs(tour_1["total_distance_km"] - 60.0) < 1e-9

    # Speed statistics use only eligible and warning tracks:
    # Mean = (10 + 20) / 2 = 15 km/h
    assert abs(tour_1["mean_track_speed_kmh"] - 15.0) < 1e-9

    # Maximum = 15 m/s * 3.6 = 54 km/h
    assert abs(tour_1["max_track_speed_kmh"] - 54.0) < 1e-9

    # Track counts
    assert tour_1["track_count"] == 3
    assert tour_1["speed_eligible_track_count"] == 2
    assert tour_1["ineligible_track_count"] == 1

    # Tour 1 has partial quality coverage
    assert tour_1["partial_quality_coverage"]

    # Tour 2 has no eligible speed observations
    tour_2 = tours[tours["tour_id"] == 2].iloc[0]

    assert pd.isna(tour_2["mean_track_speed_kmh"])
    assert not tour_2["clustering_ready"]

    # Two ineligible tracks
    assert len(excluded) == 2

    # Duration must not appear in output
    assert "elapsed_span_hours" not in tours.columns

    print("\nAll tour preprocessing tests passed!")


def test_duration_feature_rejected():

    track_data = pd.DataFrame({
        "track_id": [101],
        "tour_id": [1],
        "distance": [10000],
        "raw_speed_mean_kmh": [20.0],
        "max_speed": [10.0],
        "quality_status": ["eligible"],
    })

    try:
        prepare_tour_clustering_data(
            track_data,
            feature_columns=[
                "total_distance_km",
                "elapsed_span_hours",
            ],
        )
    except ValueError:
        print("Duration feature correctly rejected.")
    else:
        raise AssertionError(
            "Duration feature should not be allowed."
        )


if __name__ == "__main__":
    test_tour_preprocessing()
    test_duration_feature_rejected()
