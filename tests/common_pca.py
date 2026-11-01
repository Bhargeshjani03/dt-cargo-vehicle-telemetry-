
import numpy as np
import pandas as pd
import pytest

from src.common.pca import PCAProcessor


def create_dataset():

    np.random.seed(42)

    return pd.DataFrame({
        "speed": np.random.normal(50, 10, 100),
        "distance": np.random.normal(100, 20, 100),
        "stops": np.random.normal(5, 2, 100),
        "variation": np.random.normal(10, 3, 100),
    })


def test_fixed_component_pca():

    X = create_dataset()

    processor = PCAProcessor(n_components=2)

    result = processor.fit_transform(X)

    assert result.shape == (100, 2)
    assert list(result.columns) == ["PC1", "PC2"]

    print("Fixed component PCA passed.")


def test_variance_threshold():

    X = create_dataset()

    processor = PCAProcessor(
        variance_threshold=0.90
    )

    result = processor.fit_transform(X)

    summary = processor.get_summary()

    assert result.shape[1] <= X.shape[1]
    assert summary["explained_variance"] >= 0.90

    print("Variance threshold PCA passed.")


def test_explained_variance():

    X = create_dataset()

    processor = PCAProcessor(n_components=3)

    processor.fit(X)

    variance = processor.get_explained_variance()

    assert len(variance) == 3

    assert (
        variance["cumulative_explained_variance"]
        .is_monotonic_increasing
    )

    assert np.all(
        variance["explained_variance_ratio"] >= 0
    )

    print("Explained variance analysis passed.")


def test_train_test_leakage():

    X_train = create_dataset()

    X_test = pd.DataFrame({
        "speed": [1000.0],
        "distance": [2000.0],
        "stops": [100.0],
        "variation": [500.0],
    })

    processor = PCAProcessor(n_components=2)

    processor.fit(X_train)

    original_components = processor.pca.components_.copy()

    processor.transform(X_test)

    assert np.array_equal(
        original_components,
        processor.pca.components_,
    )

    print("PCA train/test leakage prevention passed.")


def test_column_mismatch():

    X = create_dataset()

    processor = PCAProcessor(n_components=2)

    processor.fit(X)

    wrong_columns = X[
        ["speed", "distance", "stops"]
    ]

    with pytest.raises(ValueError):
        processor.transform(wrong_columns)

    print("Feature validation passed.")


def test_invalid_input():

    X = create_dataset()

    X.loc[0, "speed"] = np.nan

    processor = PCAProcessor(n_components=2)

    with pytest.raises(ValueError):
        processor.fit(X)

    print("Invalid input validation passed.")


def test_invalid_configuration():

    with pytest.raises(ValueError):
        PCAProcessor(
            n_components=2,
            variance_threshold=0.95,
        )

    with pytest.raises(ValueError):
        PCAProcessor(
            variance_threshold=1.5
        )

    print("PCA configuration validation passed.")


if __name__ == "__main__":

    test_fixed_component_pca()
    test_variance_threshold()
    test_explained_variance()
    test_train_test_leakage()
    test_column_mismatch()
    test_invalid_input()
    test_invalid_configuration()

    print("\nAll PCA tests passed!")
