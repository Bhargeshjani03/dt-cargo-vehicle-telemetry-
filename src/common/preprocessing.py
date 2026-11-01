
"""
Reusable numeric preprocessing utilities.

Features:
- Median imputation
- Standard scaling
- Robust scaling
- Optional log1p transformation
- Train/test leakage prevention

Fit the preprocessor on training data only.
Use transform() for validation and test data.
"""

import numpy as np
import pandas as pd

from sklearn.preprocessing import StandardScaler, RobustScaler


class NumericPreprocessor:
    """
    Reusable preprocessing for numeric DataFrames.

    Parameters
    ----------
    scaling : str
        "standard", "robust", or "none".

    log_columns : list, optional
        Columns to transform using log1p.
        Values must be non-negative.

    """

    def __init__(
        self,
        scaling="standard",
        log_columns=None,
    ):

        allowed_scaling = {"standard", "robust", "none"}

        if scaling not in allowed_scaling:
            raise ValueError(
                f"scaling must be one of {allowed_scaling}"
            )

        self.scaling = scaling
        self.log_columns = log_columns or []

        self.feature_columns = None
        self.imputation_values = None
        self.scaler = None
        self._is_fitted = False

    # --------------------------------------------------
    # 1. Validate input
    # --------------------------------------------------

    def _validate_input(self, X):

        if not isinstance(X, pd.DataFrame):
            raise TypeError("Input must be a pandas DataFrame.")

        if X.empty:
            raise ValueError("Input DataFrame is empty.")

        if X.columns.duplicated().any():
            raise ValueError("Duplicate feature columns found.")

        non_numeric = X.select_dtypes(
            exclude=np.number
        ).columns.tolist()

        if non_numeric:
            raise ValueError(
                f"Non-numeric columns found: {non_numeric}"
            )

        missing_log_columns = (
            set(self.log_columns) - set(X.columns)
        )

        if missing_log_columns:
            raise ValueError(
                f"Log columns not found: {sorted(missing_log_columns)}"
            )

        return X.astype(float).replace(
            [np.inf, -np.inf], np.nan
        )

    # --------------------------------------------------
    # 2. Apply optional log transformation
    # --------------------------------------------------

    def _apply_log_transform(self, X):

        X = X.copy()

        for column in self.log_columns:

            observed_values = X[column].dropna()

            if (observed_values < 0).any():
                raise ValueError(
                    f"Column '{column}' contains negative values. "
                    "log1p requires non-negative values."
                )

            X[column] = np.log1p(X[column])

        return X

    # --------------------------------------------------
    # 3. Fit on training data
    # --------------------------------------------------

    def fit(self, X):

        X = self._validate_input(X)

        self.feature_columns = X.columns.tolist()

        X = self._apply_log_transform(X)

        # Calculate medians using training data only.
        self.imputation_values = X.median()

        # An entirely missing training feature cannot provide
        # a reliable median for future observations.
        all_missing = self.imputation_values[
            self.imputation_values.isna()
        ].index.tolist()

        if all_missing:
            raise ValueError(
                "Cannot impute columns that are entirely missing "
                f"in training data: {all_missing}"
            )

        X = X.fillna(self.imputation_values)

        # Fit the selected scaler using training data only.
        if self.scaling == "standard":
            self.scaler = StandardScaler()

        elif self.scaling == "robust":
            self.scaler = RobustScaler()

        else:
            self.scaler = None

        if self.scaler is not None:
            self.scaler.fit(X)

        self._is_fitted = True

        return self

    # --------------------------------------------------
    # 4. Transform data using fitted parameters
    # --------------------------------------------------

    def transform(self, X):

        if not self._is_fitted:
            raise RuntimeError(
                "Preprocessor has not been fitted. "
                "Call fit() before transform()."
            )

        X = self._validate_input(X)

        if X.columns.tolist() != self.feature_columns:
            raise ValueError(
                "Input feature columns or their order do not match "
                "the training data."
            )

        X = self._apply_log_transform(X)

        # Use training medians.
        X = X.fillna(self.imputation_values)

        # Use training scaling parameters.
        if self.scaler is not None:
            transformed = self.scaler.transform(X)

            X = pd.DataFrame(
                transformed,
                columns=self.feature_columns,
                index=X.index,
            )

        return X

    # --------------------------------------------------
    # 5. Fit and transform training data
    # --------------------------------------------------

    def fit_transform(self, X):

        self.fit(X)

        return self.transform(X)
