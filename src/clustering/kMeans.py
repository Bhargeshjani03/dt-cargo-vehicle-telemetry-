
"""
Reusable K-Means clustering utilities.

Features:
- K-Means++ initialization
- Configurable number of clusters
- Reproducible clustering
- Cluster assignments
- Inertia
- Silhouette score (optionally sampled)
- Cluster-size distribution
"""

import numpy as np
import pandas as pd

from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score


class KMeansClusterer:

    def __init__(
        self,
        n_clusters=3,
        init="k-means++",
        n_init=10,
        max_iter=300,
        random_state=42,
        silhouette_sample_size=10000,
    ):
        """
        Parameters
        ----------
        n_clusters : int
            Number of clusters.

        init : str
            Initialization method.

        n_init : int
            Number of independent initializations.

        max_iter : int
            Maximum iterations per initialization.

        random_state : int
            Random seed for reproducibility.

        silhouette_sample_size : int or None
            Number of samples used for silhouette calculation.
            None means use the entire dataset.
        """

        if not isinstance(n_clusters, int) or n_clusters < 2:
            raise ValueError(
                "n_clusters must be an integer >= 2."
            )

        if init not in {"k-means++", "random"}:
            raise ValueError(
                "init must be 'k-means++' or 'random'."
            )

        if not isinstance(n_init, int) or n_init < 1:
            raise ValueError("n_init must be >= 1.")

        if not isinstance(max_iter, int) or max_iter < 1:
            raise ValueError("max_iter must be >= 1.")

        if (
            silhouette_sample_size is not None
            and (
                not isinstance(silhouette_sample_size, int)
                or silhouette_sample_size < 2
            )
        ):
            raise ValueError(
                "silhouette_sample_size must be an integer >= 2 "
                "or None."
            )

        self.n_clusters = n_clusters
        self.init = init
        self.n_init = n_init
        self.max_iter = max_iter
        self.random_state = random_state
        self.silhouette_sample_size = silhouette_sample_size

        self.model = None
        self.feature_columns = None
        self.labels_ = None
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

        values = X.to_numpy(dtype=float)

        if not np.isfinite(values).all():
            raise ValueError(
                "Input contains NaN or infinite values. "
                "Apply imputation before clustering."
            )

        if X.shape[1] == 0:
            raise ValueError(
                "At least one feature is required."
            )

        return X.astype(float)

    # --------------------------------------------------
    # 2. Fit K-Means
    # --------------------------------------------------

    def fit(self, X):

        X = self._validate_input(X)

        if self.n_clusters >= len(X):
            raise ValueError(
                "n_clusters must be smaller than the number "
                "of observations."
            )

        self.feature_columns = X.columns.tolist()

        self.model = KMeans(
            n_clusters=self.n_clusters,
            init=self.init,
            n_init=self.n_init,
            max_iter=self.max_iter,
            random_state=self.random_state,
        )

        self.model.fit(X)

        self.labels_ = pd.Series(
            self.model.labels_,
            index=X.index,
            name="cluster",
        )

        self._is_fitted = True

        return self

    # --------------------------------------------------
    # 3. Fit and return cluster assignments
    # --------------------------------------------------

    def fit_predict(self, X):

        self.fit(X)

        return self.labels_.copy()

    # --------------------------------------------------
    # 4. Predict clusters for new observations
    # --------------------------------------------------

    def predict(self, X):

        if not self._is_fitted:
            raise RuntimeError(
                "K-Means has not been fitted. Call fit() first."
            )

        X = self._validate_input(X)

        if X.columns.tolist() != self.feature_columns:
            raise ValueError(
                "Input feature columns or their order do not "
                "match the training data."
            )

        predictions = self.model.predict(X)

        return pd.Series(
            predictions,
            index=X.index,
            name="cluster",
        )

    # --------------------------------------------------
    # 5. Cluster-size distribution
    # --------------------------------------------------

    def get_cluster_sizes(self):

        if not self._is_fitted:
            raise RuntimeError(
                "K-Means has not been fitted."
            )

        counts = self.labels_.value_counts().sort_index()

        result = pd.DataFrame({
            "cluster": counts.index,
            "sample_count": counts.values,
            "percentage": (
                counts.values / len(self.labels_) * 100
            ),
        })

        return result.reset_index(drop=True)

    # --------------------------------------------------
    # 6. Evaluate clustering
    # --------------------------------------------------

    
    def evaluate(self, X):

        if not self._is_fitted:
            raise RuntimeError(
                "K-Means has not been fitted."
            )

        X = self._validate_input(X)

        if X.columns.tolist() != self.feature_columns:
            raise ValueError(
                "Input feature columns or their order do not "
                "match the training data."
            )

        labels = self.model.predict(X)
        unique_labels = np.unique(labels)

        # Calculate inertia for the supplied dataset.
        values = X.to_numpy()
        assigned_centers = self.model.cluster_centers_[labels]

        inertia = float(
            np.sum((values - assigned_centers) ** 2)
        )

        silhouette = None
        silhouette_status = None
        silhouette_n_samples = 0

        if len(unique_labels) < 2:
            silhouette_status = (
                "Undefined: fewer than two distinct clusters."
            )

        elif len(unique_labels) >= len(X):
            silhouette_status = (
                "Undefined: every observation has its own cluster."
            )

        else:
            sample_size = self.silhouette_sample_size

            if sample_size is not None:
                sample_size = min(sample_size, len(X))

                if sample_size <= len(unique_labels):
                    sample_size = None

            silhouette = float(
                silhouette_score(
                    X,
                    labels,
                    sample_size=sample_size,
                    random_state=self.random_state,
                )
            )

            silhouette_n_samples = (
                len(X) if sample_size is None else sample_size
            )

            silhouette_status = "Computed"

        cluster_counts = (
            pd.Series(labels)
            .value_counts()
            .sort_index()
            .to_dict()
        )

        return {
            "n_clusters_requested": self.n_clusters,
            "n_clusters_found": len(unique_labels),
            "inertia": inertia,
            "silhouette_score": silhouette,
            "silhouette_status": silhouette_status,
            "silhouette_sample_size": silhouette_n_samples,
            "cluster_sizes": cluster_counts,
        }

    # --------------------------------------------------
    # 7. Model summary
    # --------------------------------------------------

    def get_summary(self):

        if not self._is_fitted:
            raise RuntimeError(
                "K-Means has not been fitted."
            )

        return {
            "n_clusters": self.n_clusters,
            "n_features": len(self.feature_columns),
            "n_iterations": self.model.n_iter_,
            "inertia": float(self.model.inertia_),
            "random_state": self.random_state,
            "init": self.init,
            "n_init": self.n_init,
            "max_iter": self.max_iter,
        }
