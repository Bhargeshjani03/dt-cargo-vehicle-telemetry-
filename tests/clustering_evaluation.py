
import numpy as np
import pandas as pd
import pytest

from src.clustering.evaluation import ClusteringEvaluator


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


def test_evaluate_k_range():

    X = create_dataset()

    evaluator = ClusteringEvaluator(
        silhouette_sample_size=None
    )

    results = evaluator.evaluate_k_range(
        X,
        k_values=[2, 3, 4, 5],
    )

    assert len(results) == 4

    assert list(results["k"]) == [2, 3, 4, 5]

    assert results["inertia"].notna().all()

    assert results["silhouette_score"].notna().all()

    assert results["n_clusters_found"].between(2, 5).all()

    print("K range evaluation passed.")


def test_inertia_decreases():

    X = create_dataset()

    evaluator = ClusteringEvaluator()

    results = evaluator.evaluate_k_range(
        X,
        k_values=[2, 3, 4, 5],
    )

    inertia = results["inertia"].values

    # Inertia should not increase as k increases.
    assert np.all(np.diff(inertia) <= 1e-8)

    print("Inertia trend passed.")


def test_cluster_balance():

    X = create_dataset()

    evaluator = ClusteringEvaluator()

    results = evaluator.evaluate_k_range(
        X,
        k_values=[3],
    )

    row = results.iloc[0]

    assert row["smallest_cluster_size"] > 0

    assert row["largest_cluster_size"] >= (
        row["smallest_cluster_size"]
    )

    assert row["min_cluster_pct"] > 0

    assert row["max_cluster_pct"] <= 100

    assert sum(row["cluster_sizes"]) == len(X)

    print("Cluster balance evaluation passed.")


def test_compare_representations():

    X = create_dataset()

    X_pca = pd.DataFrame({
        "PC1": X["feature_1"] * 0.8,
        "PC2": X["feature_2"] * 0.8,
    })

    evaluator = ClusteringEvaluator()

    results = evaluator.compare_representations(
        {
            "Original": X,
            "PCA_2PC": X_pca,
        },
        k_values=[2, 3, 4],
    )

    assert len(results) == 6

    assert set(
        results["representation"]
    ) == {"Original", "PCA_2PC"}

    assert set(results["k"]) == {2, 3, 4}

    print("Representation comparison passed.")


def test_sort_by_silhouette():

    X = create_dataset()

    evaluator = ClusteringEvaluator()

    results = evaluator.evaluate_k_range(
        X,
        k_values=[2, 3, 4],
    )

    sorted_results = evaluator.sort_by_silhouette(
        results
    )

    scores = sorted_results[
        "silhouette_score"
    ].dropna().values

    assert np.all(np.diff(scores) <= 0)

    print("Silhouette sorting passed.")


def test_invalid_k_values():

    X = create_dataset()

    evaluator = ClusteringEvaluator()

    with pytest.raises(ValueError):
        evaluator.evaluate_k_range(X, [])

    with pytest.raises(ValueError):
        evaluator.evaluate_k_range(X, [2, 2, 3])

    with pytest.raises(ValueError):
        evaluator.evaluate_k_range(X, [1, 3])

    with pytest.raises(ValueError):
        evaluator.evaluate_k_range(X, [2, 150])

    with pytest.raises(ValueError):
        evaluator.evaluate_k_range(X, [2.5, 3])

    print("Invalid k validation passed.")


def test_invalid_data():

    X = create_dataset()

    X.loc[0, "feature_1"] = np.nan

    evaluator = ClusteringEvaluator()

    with pytest.raises(ValueError):
        evaluator.evaluate_k_range(X, [2, 3])

    print("Invalid data validation passed.")


def test_empty_representations():

    evaluator = ClusteringEvaluator()

    with pytest.raises(ValueError):
        evaluator.compare_representations(
            {},
            k_values=[2, 3],
        )

    print("Empty representation validation passed.")


def test_invalid_configuration():

    with pytest.raises(ValueError):
        ClusteringEvaluator(n_init=0)

    with pytest.raises(ValueError):
        ClusteringEvaluator(silhouette_sample_size=1)

    print("Configuration validation passed.")


if __name__ == "__main__":

    test_evaluate_k_range()
    test_inertia_decreases()
    test_cluster_balance()
    test_compare_representations()
    test_sort_by_silhouette()
    test_invalid_k_values()
    test_invalid_data()
    test_empty_representations()
    test_invalid_configuration()

    print("\nAll clustering evaluation tests passed!")
