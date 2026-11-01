
"""
Reusable PCA utilities for track-level and tour-level analysis.

Features:
- PCA with a fixed number of components
- PCA based on an explained variance threshold
- Explained variance analysis
- Cumulative explained variance
- Train/test leakage prevention
- DataFrame output with preserved indices
"""

import numpy as np
import pandas as pd

from sklearn.decomposition import PCA


class PCAProcessor:

    def __init__(
        self,
        n_components=None,
        variance_threshold=None,
        random_state=42,
    ):
        """
        Parameters
        ----------
        n_components : int, optional
            Explicit number of principal components.

        variance_threshold : float, optional
            Minimum cumulative explained variance to retain.
            Example: 0.95 retains enough components to explain 95%.

        random_state : int
            Random state for reproducibility.
        """

        if n_components is not None and variance_threshold is not None:
            raise ValueError(
                "Specify either n_components or variance_threshold, "
                "not both."
            )

        if n_components is not None:
            if not isinstance(n_components, int) or n_components < 1:
                raise ValueError(
                    "n_components must be a positive integer."
                )

        if variance_threshold is not None:
            if not 0 < variance_threshold <= 1:
                raise ValueError(
                    "variance_threshold must be between 0 and 1."
                )

        self.n_components = n_components
        self.variance_threshold = variance_threshold
        self.random_state = random_state

        self.pca = None
        self.feature_columns = None
        self._is_fitted = False

    # --------------------------------------------------
    # 1. Validate input
    # --------------------------------------------------

    def _validate_input(self, X):

        if not isinstance(X, pd.DataFrame):
            raise TypeError(
                "Input must be a pandas DataFrame."
            )

        if X.empty:
            raise ValueError("Input DataFrame is empty.")

        if X.columns.duplicated().any():
            raise ValueError(
                "Duplicate feature columns found."
            )

        non_numeric = X.select_dtypes(
            exclude=np.number
        ).columns.tolist()

        if non_numeric:
            raise ValueError(
                f"Non-numeric columns found: {non_numeric}"
            )

        if not np.isfinite(X.to_numpy(dtype=float)).all():
            raise ValueError(
                "PCA input contains NaN or infinite values. "
                "Apply imputation before PCA."
            )

        return X.astype(float)

    # --------------------------------------------------
    # 2. Fit PCA on training data
    # --------------------------------------------------

    def fit(self, X):

        X = self._validate_input(X)

        self.feature_columns = X.columns.tolist()

        max_components = min(X.shape[0], X.shape[1])

        if self.n_components is not None:

            if self.n_components > max_components:
                raise ValueError(
                    f"n_components cannot exceed {max_components}."
                )

            selected_components = self.n_components

        elif self.variance_threshold is not None:

            # Fit all possible components first to calculate
            # the cumulative explained variance.
            exploratory_pca = PCA(
                n_components=max_components,
                random_state=self.random_state,
            )

            exploratory_pca.fit(X)

            cumulative_variance = np.cumsum(
                exploratory_pca.explained_variance_ratio_
            )

            selected_components = (
                np.searchsorted(
                    cumulative_variance,
                    self.variance_threshold,
                ) + 1
            )

        else:
            selected_components = max_components

        self.pca = PCA(
            n_components=selected_components,
            random_state=self.random_state,
        )

        self.pca.fit(X)

        self._is_fitted = True

        return self

    # --------------------------------------------------
    # 3. Transform data
    # --------------------------------------------------

    def transform(self, X):

        if not self._is_fitted:
            raise RuntimeError(
                "PCA has not been fitted. Call fit() first."
            )

        X = self._validate_input(X)

        if X.columns.tolist() != self.feature_columns:
            raise ValueError(
                "Input feature columns or their order do not "
                "match the training data."
            )

        transformed = self.pca.transform(X)

        component_names = [
            f"PC{i + 1}"
            for i in range(transformed.shape[1])
        ]

        return pd.DataFrame(
            transformed,
            columns=component_names,
            index=X.index,
        )

    # --------------------------------------------------
    # 4. Fit and transform
    # --------------------------------------------------

    def fit_transform(self, X):

        self.fit(X)

        return self.transform(X)

    # --------------------------------------------------
    # 5. Explained variance information
    # --------------------------------------------------

    def get_explained_variance(self):

        if not self._is_fitted:
            raise RuntimeError(
                "PCA has not been fitted."
            )

        explained = self.pca.explained_variance_ratio_

        result = pd.DataFrame({
            "principal_component": [
                f"PC{i + 1}"
                for i in range(len(explained))
            ],
            "explained_variance_ratio": explained,
            "cumulative_explained_variance": np.cumsum(
                explained
            ),
        })

        return result

    # --------------------------------------------------
    # 6. Get PCA summary
    # --------------------------------------------------

    def get_summary(self):

        if not self._is_fitted:
            raise RuntimeError(
                "PCA has not been fitted."
            )

        return {
            "original_feature_count": len(self.feature_columns),
            "selected_component_count": self.pca.n_components_,
            "explained_variance": float(
                self.pca.explained_variance_ratio_.sum()
            ),
            "feature_columns": self.feature_columns,
        }
