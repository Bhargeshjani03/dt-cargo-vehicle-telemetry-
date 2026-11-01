
import numpy as np
import pandas as pd
import pytest

from src.clustering.kMeans import KMeansClusterer


def create_dataset():

    np.random.seed(42)

    cluster_1 = np.random.normal(
        loc=[0, 0], scale=0.5, size=(50, 2)
    )

    cluster_2 = np.random.normal(
        loc=[5, 5], scale=0.5, size=(50, 2)
    )

    cluster_3 = np.random.normal(
        loc=[10, 0], scale=0.5, size=(50, 2)
    )

    data = np.vstack([
        cluster_1,
        cluster_2,
        cluster_3,
    ])

    return pd.DataFrame(
        data,
        columns=["feature_1", "feature_2"],
    )


def test_kmeans_fit_predict():

    X = create_dataset()

    clusterer = KMeansClusterer(
        n_clusters=3,
        random_state=42,
    )

    labels = clusterer.fit_predict(X)

    assert len(labels) == len(X)
    assert labels.nunique() == 3
    assert labels.name == "cluster"

    print("K-Means fit and predict passed.")


def test_cluster_sizes():

    X = create_dataset()

    clusterer = KMeansClusterer(n_clusters=3)
    clusterer.fit(X)

    sizes = clusterer.get_cluster_sizes()

    assert len(sizes) == 3
    assert sizes["sample_count"].sum() == len(X)

    assert np.isclose(
        sizes["percentage"].sum(),
        100.0,
    )

    print("Cluster-size distribution passed.")


def test_evaluation():

    X = create_dataset()

    clusterer = KMeansClusterer(
        n_clusters=3,
        silhouette_sample_size=None,
    )

    clusterer.fit(X)

    metrics = clusterer.evaluate(X)

    assert metrics["n_clusters_found"] == 3
    assert metrics["inertia"] >= 0
    assert metrics["silhouette_score"] is not None

    assert -1 <= metrics["silhouette_score"] <= 1

    assert metrics["silhouette_status"] == "Computed"

    print("K-Means evaluation passed.")
    print("Inertia:", metrics["inertia"])
    print("Silhouette:", metrics["silhouette_score"])


def test_evaluate_new_dataset():

    X_train = create_dataset()

    X_test = pd.DataFrame({
        "feature_1": [0.0, 5.0, 10.0],
        "feature_2": [0.0, 5.0, 0.0],
    })

    clusterer = KMeansClusterer(n_clusters=3)
    clusterer.fit(X_train)

    metrics = clusterer.evaluate(X_test)

    assert metrics["n_clusters_found"] == 3
    assert sum(
        metrics["cluster_sizes"].values()
    ) == len(X_test)

    assert metrics["inertia"] >= 0

    print("Evaluation on new data passed.")


def test_reproducibility():

    X = create_dataset()

    model_1 = KMeansClusterer(
        n_clusters=3,
        random_state=42,
    )

    model_2 = KMeansClusterer(
        n_clusters=3,
        random_state=42,
    )

    labels_1 = model_1.fit_predict(X)
    labels_2 = model_2.fit_predict(X)

    assert np.array_equal(
        labels_1.values,
        labels_2.values,
    )

    print("Reproducibility passed.")


def test_predict_new_data():

    X = create_dataset()

    clusterer = KMeansClusterer(n_clusters=3)
    clusterer.fit(X)

    new_data = X.iloc[:5].copy()

    predictions = clusterer.predict(new_data)

    assert len(predictions) == 5
    assert predictions.between(0, 2).all()

    print("Prediction on new observations passed.")


def test_invalid_input():

    X = create_dataset()

    X.loc[0, "feature_1"] = np.nan

    clusterer = KMeansClusterer(n_clusters=3)

    with pytest.raises(ValueError):
        clusterer.fit(X)

    print("Invalid input validation passed.")


def test_invalid_configuration():

    with pytest.raises(ValueError):
        KMeansClusterer(n_clusters=1)

    with pytest.raises(ValueError):
        KMeansClusterer(n_clusters=3, n_init=0)

    with pytest.raises(ValueError):
        KMeansClusterer(
            n_clusters=3,
            silhouette_sample_size=1,
        )

    print("Configuration validation passed.")


def test_not_fitted():

    X = create_dataset()

    clusterer = KMeansClusterer(n_clusters=3)

    with pytest.raises(RuntimeError):
        clusterer.predict(X)

    with pytest.raises(RuntimeError):
        clusterer.evaluate(X)

    print("Unfitted model validation passed.")


if __name__ == "__main__":

    test_kmeans_fit_predict()
    test_cluster_sizes()
    test_evaluation()
    test_evaluate_new_dataset()
    test_reproducibility()
    test_predict_new_data()
    test_invalid_input()
    test_invalid_configuration()
    test_not_fitted()

    print("\nAll K-Means tests passed!")
