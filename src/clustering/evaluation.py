
"""
Clustering evaluation utilities.

Evaluates K-Means across different values of k.

Metrics:
- Inertia
- Silhouette score
- Cluster-size distribution
- Cluster balance

Supports comparing multiple feature representations,
such as original scaled features and PCA representations.
"""

import numpy as np
import pandas as pd

from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score


class ClusteringEvaluator:

    def __init__(
        self,
        init="k-means++",
        n_init=10,
        max_iter=300,
        random_state=42,
        silhouette_sample_size=10000,
    ):
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
                "silhouette_sample_size must be >= 2 or None."
            )

        self.init = init
        self.n_init = n_init
        self.max_iter = max_iter
        self.random_state = random_state
        self.silhouette_sample_size = silhouette_sample_size

    # --------------------------------------------------
    # 1. Validate input data
    # --------------------------------------------------

    @staticmethod
    def _validate_input(X):

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
                "Preprocess the data before evaluation."
            )

        return X.astype(float)

    # --------------------------------------------------
    # 2. Calculate silhouette score
    # --------------------------------------------------

    def _calculate_silhouette(self, X, labels):

        unique_labels = np.unique(labels)

        if len(unique_labels) < 2:
            return None, "Undefined: fewer than two clusters."

        if len(unique_labels) >= len(X):
            return None, "Undefined: each observation is a cluster."

        sample_size = self.silhouette_sample_size

        if sample_size is not None:
            sample_size = min(sample_size, len(X))

            # Use all observations if the requested sample
            # is too small to contain at least two clusters.
            if sample_size <= len(unique_labels):
                sample_size = None

        try:
            score = silhouette_score(
                X,
                labels,
                sample_size=sample_size,
                random_state=self.random_state,
            )

            return (
                float(score),
                "Computed",
            )

        except ValueError as error:
            return (
                None,
                f"Could not compute silhouette: {error}",
            )

    # --------------------------------------------------
    # 3. Evaluate one value of k
    # --------------------------------------------------

    def _evaluate_single_k(self, X, k):

        model = KMeans(
            n_clusters=k,
            init=self.init,
            n_init=self.n_init,
            max_iter=self.max_iter,
            random_state=self.random_state,
        )

        labels = model.fit_predict(X)

        cluster_counts = np.bincount(
            labels,
            minlength=k,
        )

        cluster_percentages = (
            cluster_counts / len(X) * 100
        )

        silhouette, silhouette_status = (
            self._calculate_silhouette(X, labels)
        )

        return {
            "k": k,
            "inertia": float(model.inertia_),
            "silhouette_score": silhouette,
            "silhouette_status": silhouette_status,
            "n_clusters_found": int(
                len(np.unique(labels))
            ),
            "smallest_cluster_size": int(
                cluster_counts.min()
            ),
            "largest_cluster_size": int(
                cluster_counts.max()
            ),
            "min_cluster_pct": float(
                cluster_percentages.min()
            ),
            "max_cluster_pct": float(
                cluster_percentages.max()
            ),
            "cluster_size_std": float(
                cluster_counts.std()
            ),
            "cluster_sizes": cluster_counts.tolist(),
        }

    # --------------------------------------------------
    # 4. Evaluate a range of k values
    # --------------------------------------------------

    def evaluate_k_range(self, X, k_values):

        X = self._validate_input(X)

        if not k_values:
            raise ValueError(
                "k_values must contain at least one value."
            )

        if len(set(k_values)) != len(k_values):
            raise ValueError(
                "k_values must not contain duplicates."
            )

        for k in k_values:

            if not isinstance(k, (int, np.integer)) or isinstance(
                k, (bool, np.bool_)
            ):
                raise ValueError(
                    "Every k must be an integer."
                )

            if k < 2 or k >= len(X):
                raise ValueError(
                    f"Each k must be >= 2 and smaller than "
                    f"the number of observations ({len(X)}). "
                    f"Invalid k: {k}"
                )

        results = []

        for k in k_values:

            result = self._evaluate_single_k(X, int(k))
            results.append(result)

        return pd.DataFrame(results)

    # --------------------------------------------------
    # 5. Compare multiple feature representations
    # --------------------------------------------------

    def compare_representations(
        self,
        representations,
        k_values,
    ):
        """
        Parameters
        ----------
        representations : dict
            Dictionary containing named DataFrames.

            Example:
            {
                "Original": X_original,
                "PCA_2PC": X_pca
            }

        k_values : list
            Values of k to evaluate for each representation.

        Returns
        -------
        pandas.DataFrame
            Combined evaluation results.
        """

        if not isinstance(representations, dict):
            raise TypeError(
                "representations must be a dictionary."
            )

        if not representations:
            raise ValueError(
                "At least one representation is required."
            )

        results = []

        for representation_name, X in representations.items():

            representation_results = self.evaluate_k_range(
                X,
                k_values,
            )

            representation_results.insert(
                0,
                "representation",
                representation_name,
            )

            results.append(representation_results)

        return pd.concat(
            results,
            ignore_index=True,
        )

    # --------------------------------------------------
    # 6. Sort results for inspection
    # --------------------------------------------------

    @staticmethod
    def sort_by_silhouette(results):

        required_columns = {
            "silhouette_score",
            "k",
        }

        if not required_columns.issubset(results.columns):
            raise ValueError(
                "Results must contain silhouette_score and k."
            )

        return results.sort_values(
            by="silhouette_score",
            ascending=False,
            na_position="last",
        ).reset_index(drop=True)
