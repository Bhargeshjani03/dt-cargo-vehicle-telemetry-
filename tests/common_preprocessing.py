
import numpy as np
import pandas as pd
import pytest

from src.common.preprocessing import NumericPreprocessor


def test_standard_preprocessing():

    train = pd.DataFrame({
        "distance": [10.0, 20.0, np.nan, 40.0],
        "speed": [30.0, 40.0, 50.0, 60.0],
    })

    test = pd.DataFrame({
        "distance": [50.0, np.nan],
        "speed": [70.0, 80.0],
    })

    preprocessor = NumericPreprocessor(
        scaling="standard"
    )

    train_processed = preprocessor.fit_transform(train)
    test_processed = preprocessor.transform(test)

    assert train_processed.shape == train.shape
    assert test_processed.shape == test.shape

    assert train_processed.isna().sum().sum() == 0
    assert test_processed.isna().sum().sum() == 0

    # StandardScaler should produce zero mean on training data.
    assert np.allclose(
        train_processed.mean().values,
        [0.0, 0.0],
        atol=1e-9,
    )

    # DataFrame indices should be preserved.
    assert list(test_processed.index) == list(test.index)

    print("Standard scaling and imputation passed.")


def test_robust_scaling():

    train = pd.DataFrame({
        "distance": [10.0, 20.0, 30.0, 1000.0],
        "speed": [20.0, 30.0, 40.0, 50.0],
    })

    preprocessor = NumericPreprocessor(
        scaling="robust"
    )

    result = preprocessor.fit_transform(train)

    assert result.shape == train.shape
    assert result.isna().sum().sum() == 0

    print("Robust scaling passed.")


def test_log_transformation():

    train = pd.DataFrame({
        "distance": [0.0, 10.0, 100.0, 1000.0],
        "speed": [10.0, 20.0, 30.0, 40.0],
    })

    preprocessor = NumericPreprocessor(
        scaling="none",
        log_columns=["distance"],
    )

    result = preprocessor.fit_transform(train)

    expected = np.log1p(train["distance"])

    assert np.allclose(
        result["distance"].values,
        expected.values,
    )

    print("Log transformation passed.")


def test_no_data_leakage():

    train = pd.DataFrame({
        "distance": [10.0, 20.0, 30.0],
    })

    test = pd.DataFrame({
        "distance": [1000.0],
    })

    preprocessor = NumericPreprocessor(
        scaling="standard"
    )

    preprocessor.fit(train)

    # Test values must not change fitted training statistics.
    original_mean = preprocessor.scaler.mean_.copy()

    preprocessor.transform(test)

    assert np.array_equal(
        original_mean,
        preprocessor.scaler.mean_,
    )

    print("Train/test leakage prevention passed.")


def test_negative_log_values_rejected():

    train = pd.DataFrame({
        "distance": [10.0, -5.0, 20.0],
    })

    preprocessor = NumericPreprocessor(
        scaling="none",
        log_columns=["distance"],
    )

    with pytest.raises(ValueError):
        preprocessor.fit(train)

    print("Negative log input validation passed.")


def test_all_missing_column_rejected():

    train = pd.DataFrame({
        "distance": [10.0, 20.0, 30.0],
        "speed": [np.nan, np.nan, np.nan],
    })

    preprocessor = NumericPreprocessor()

    with pytest.raises(ValueError):
        preprocessor.fit(train)

    print("All-missing feature validation passed.")


if __name__ == "__main__":

    test_standard_preprocessing()
    test_robust_scaling()
    test_log_transformation()
    test_no_data_leakage()
    test_negative_log_values_rejected()
    test_all_missing_column_rejected()

    print("\nAll common preprocessing tests passed!")
