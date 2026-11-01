
"""Shared preprocessing utilities for DT-CARGO clustering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, RobustScaler


@dataclass
class NumericPreprocessor:
    """
    Median imputation followed by optional feature scaling.

    Each clustering pipeline must fit its own preprocessor.
    """

    scaling: str = "standard"

    imputer: SimpleImputer | None = None
    scaler: StandardScaler | RobustScaler | None = None
    feature_names_: list[str] | None = None

    def fit(self, X: pd.DataFrame) -> "NumericPreprocessor":

        self._validate_frame(X)

        self.feature_names_ = list(X.columns)

        # Handle missing values using training-data medians.
        self.imputer = SimpleImputer(strategy="median")

        imputed = self.imputer.fit_transform(X)

        # Select scaling strategy.
        if self.scaling == "standard":
            self.scaler = StandardScaler()

        elif self.scaling == "robust":
            self.scaler = RobustScaler()

        elif self.scaling == "none":
            self.scaler = None

        else:
            raise ValueError(
                "scaling must be 'standard', 'robust', or 'none'"
            )

        if self.scaler is not None:
            self.scaler.fit(imputed)

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:

        self._validate_frame(X)

        if self.imputer is None or self.feature_names_ is None:
            raise RuntimeError(
                "Preprocessor must be fitted before transform."
            )

        if list(X.columns) != self.feature_names_:
            raise ValueError(
                f"Feature mismatch. Expected {self.feature_names_}, "
                f"received {list(X.columns)}"
            )

        values = self.imputer.transform(X)

        if self.scaler is not None:
            values = self.scaler.transform(values)

        return pd.DataFrame(
            values,
            index=X.index,
            columns=self.feature_names_
        )

    def fit_transform(self, X: pd.DataFrame) -> pd.DataFrame:

        return self.fit(X).transform(X)

    @staticmethod
    def _validate_frame(X: pd.DataFrame) -> None:

        if not isinstance(X, pd.DataFrame):
            raise TypeError("X must be a pandas DataFrame.")

        if X.empty or X.shape[1] == 0:
            raise ValueError(
                "X must contain rows and feature columns."
            )

        if not X.columns.is_unique:
            raise ValueError(
                "Feature column names must be unique."
            )

        non_numeric = [
            col for col in X.columns
            if not pd.api.types.is_numeric_dtype(X[col])
        ]

        if non_numeric:
            raise TypeError(
                f"Non-numeric feature columns: {non_numeric}"
            )


def numeric_feature_frame(
    data: pd.DataFrame,
    feature_columns: Iterable[str]
) -> tuple[pd.DataFrame, pd.Series]:
    """
    Select numeric features and identify usable rows.

    Rows with all selected features missing are excluded.
    Other missing values are retained for median imputation.
    """

    feature_columns = list(feature_columns)

    missing = [
        col for col in feature_columns
        if col not in data.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required features: {missing}"
        )

    X = data.loc[:, feature_columns].apply(
        pd.to_numeric,
        errors="coerce"
    )

    X = X.replace([np.inf, -np.inf], np.nan)

    usable = ~X.isna().all(axis=1)

    return X.loc[usable].copy(), usable


def log1p_nonnegative(
    X: pd.DataFrame,
    columns: Iterable[str]
) -> pd.DataFrame:
    """
    Apply log1p to selected non-negative features.

    Negative values become NaN in the model-input copy.
    The original dataset must remain unchanged.
    """

    result = X.copy()

    for column in columns:

        if column not in result.columns:
            raise ValueError(
                f"Unknown transformation column: {column}"
            )

        values = pd.to_numeric(
            result[column],
            errors="coerce"
        )

        result[column] = np.log1p(
            values.where(values >= 0)
        )

    return result
