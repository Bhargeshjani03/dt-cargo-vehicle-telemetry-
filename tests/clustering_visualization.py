
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from src.clustering.visualization import ClusteringVisualizer


def create_evaluation_results():

    return pd.DataFrame({
        "k": [2, 3, 4, 5],
        "inertia": [1000, 600, 400, 350],
        "silhouette_score": [0.45, 0.72, 0.61, 0.55],
    })


def test_elbow_plot():

    results = create_evaluation_results()

    fig, ax = ClusteringVisualizer.plot_elbow(results)

    assert fig is not None
    assert ax.get_xlabel() == "Number of clusters (k)"
    assert ax.get_ylabel() == "Inertia"

    plt.close(fig)

    print("Elbow plot passed.")


def test_silhouette_plot():

    results = create_evaluation_results()

    fig, ax = ClusteringVisualizer.plot_silhouette(
        results
    )

    assert fig is not None
    assert ax.get_ylabel() == "Silhouette Score"

    plt.close(fig)

    print("Silhouette plot passed.")


def test_silhouette_plot_with_missing_scores():

    results = create_evaluation_results()

    results.loc[0, "silhouette_score"] = np.nan

    fig, ax = ClusteringVisualizer.plot_silhouette(
        results
    )

    assert len(ax.lines[0].get_xdata()) == 3

    plt.close(fig)

    print("Missing silhouette values handled.")


def test_cluster_size_plot():

    cluster_sizes = pd.DataFrame({
        "cluster": [0, 1, 2],
        "sample_count": [50, 60, 40],
        "percentage": [33.33, 40.0, 26.67],
    })

    fig, ax = ClusteringVisualizer.plot_cluster_sizes(
        cluster_sizes
    )

    assert fig is not None
    assert len(ax.patches) == 3
    assert ax.get_ylabel() == "Number of observations"

    plt.close(fig)

    print("Cluster-size plot passed.")


def test_2d_cluster_plot():

    X = pd.DataFrame({
        "PC1": [1, 2, 3, 8, 9, 10],
        "PC2": [1, 2, 3, 8, 9, 10],
    })

    labels = pd.Series(
        [0, 0, 0, 1, 1, 1],
        index=X.index,
    )

    fig, ax = ClusteringVisualizer.plot_clusters_2d(
        X,
        labels,
    )

    assert fig is not None
    assert ax.get_xlabel() == "PC1"
    assert ax.get_ylabel() == "PC2"

    plt.close(fig)

    print("2D cluster plot passed.")


def test_2d_plot_with_custom_columns():

    X = pd.DataFrame({
        "speed": [10, 20, 30, 40],
        "distance": [100, 200, 300, 400],
    })

    labels = [0, 0, 1, 1]

    fig, ax = ClusteringVisualizer.plot_clusters_2d(
        X,
        labels,
        x_column="speed",
        y_column="distance",
    )

    assert ax.get_xlabel() == "speed"
    assert ax.get_ylabel() == "distance"

    plt.close(fig)

    print("Custom-column visualization passed.")


def test_invalid_evaluation_columns():

    invalid_data = pd.DataFrame({
        "k": [2, 3],
    })

    with pytest.raises(ValueError):
        ClusteringVisualizer.plot_elbow(invalid_data)

    with pytest.raises(ValueError):
        ClusteringVisualizer.plot_silhouette(invalid_data)

    print("Evaluation column validation passed.")


def test_empty_silhouette_results():

    results = pd.DataFrame({
        "k": [2, 3],
        "silhouette_score": [np.nan, np.nan],
    })

    with pytest.raises(ValueError):
        ClusteringVisualizer.plot_silhouette(results)

    print("Empty silhouette validation passed.")


def test_invalid_cluster_size_columns():

    invalid_data = pd.DataFrame({
        "cluster": [0, 1],
    })

    with pytest.raises(ValueError):
        ClusteringVisualizer.plot_cluster_sizes(
            invalid_data
        )

    print("Cluster-size validation passed.")


def test_invalid_2d_columns():

    X = pd.DataFrame({
        "PC1": [1, 2, 3],
    })

    labels = [0, 0, 1]

    with pytest.raises(ValueError):
        ClusteringVisualizer.plot_clusters_2d(
            X,
            labels,
        )

    print("2D column validation passed.")


def test_mismatched_labels():

    X = pd.DataFrame({
        "PC1": [1, 2, 3],
        "PC2": [4, 5, 6],
    })

    labels = [0, 1]

    with pytest.raises(ValueError):
        ClusteringVisualizer.plot_clusters_2d(
            X,
            labels,
        )

    print("Label length validation passed.")


def test_mismatched_series_index():

    X = pd.DataFrame({
        "PC1": [1, 2, 3],
        "PC2": [4, 5, 6],
    })

    labels = pd.Series(
        [0, 1, 1],
        index=[10, 11, 12],
    )

    with pytest.raises(ValueError):
        ClusteringVisualizer.plot_clusters_2d(
            X,
            labels,
        )

    print("Series index validation passed.")


def test_missing_plot_values():

    X = pd.DataFrame({
        "PC1": [1, np.nan, 3],
        "PC2": [4, 5, 6],
    })

    labels = [0, 1, 1]

    with pytest.raises(ValueError):
        ClusteringVisualizer.plot_clusters_2d(
            X,
            labels,
        )

    print("Missing plotting values validation passed.")


if __name__ == "__main__":

    test_elbow_plot()
    test_silhouette_plot()
    test_silhouette_plot_with_missing_scores()
    test_cluster_size_plot()
    test_2d_cluster_plot()
    test_2d_plot_with_custom_columns()
    test_invalid_evaluation_columns()
    test_empty_silhouette_results()
    test_invalid_cluster_size_columns()
    test_invalid_2d_columns()
    test_mismatched_labels()
    test_mismatched_series_index()
    test_missing_plot_values()

    print("\nAll clustering visualization tests passed!")
