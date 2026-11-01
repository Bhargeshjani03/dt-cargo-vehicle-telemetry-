
"""
Visualization utilities for clustering experiments.

Supported plots:
- Elbow curve
- Silhouette score comparison
- Cluster-size distribution
- 2D cluster scatter plot

This module only visualizes supplied results.
It does not perform clustering or preprocessing.
"""

import matplotlib.pyplot as plt
import pandas as pd


class ClusteringVisualizer:

    # --------------------------------------------------
    # 1. Elbow plot
    # --------------------------------------------------

    @staticmethod
    def plot_elbow(results, title="Elbow Method"):

        required = {"k", "inertia"}

        if not required.issubset(results.columns):
            raise ValueError(
                f"Results must contain columns: {required}"
            )

        if results.empty:
            raise ValueError("Results are empty.")

        data = results.sort_values("k")

        fig, ax = plt.subplots(figsize=(8, 5))

        ax.plot(
            data["k"],
            data["inertia"],
            marker="o",
        )

        ax.set_title(title)
        ax.set_xlabel("Number of clusters (k)")
        ax.set_ylabel("Inertia")
        ax.set_xticks(data["k"])
        ax.grid(True, alpha=0.3)

        fig.tight_layout()

        return fig, ax

    # --------------------------------------------------
    # 2. Silhouette comparison plot
    # --------------------------------------------------

    @staticmethod
    def plot_silhouette(
        results,
        title="Silhouette Score Analysis",
    ):

        required = {"k", "silhouette_score"}

        if not required.issubset(results.columns):
            raise ValueError(
                f"Results must contain columns: {required}"
            )

        if results.empty:
            raise ValueError("Results are empty.")

        data = results.dropna(
            subset=["silhouette_score"]
        ).sort_values("k")

        if data.empty:
            raise ValueError(
                "No valid silhouette scores are available."
            )

        fig, ax = plt.subplots(figsize=(8, 5))

        ax.plot(
            data["k"],
            data["silhouette_score"],
            marker="o",
        )

        ax.set_title(title)
        ax.set_xlabel("Number of clusters (k)")
        ax.set_ylabel("Silhouette Score")
        ax.set_xticks(data["k"])
        ax.grid(True, alpha=0.3)

        fig.tight_layout()

        return fig, ax

    # --------------------------------------------------
    # 3. Cluster-size distribution
    # --------------------------------------------------

    @staticmethod
    def plot_cluster_sizes(
        cluster_sizes,
        title="Cluster Size Distribution",
    ):

        required = {"cluster", "sample_count"}

        if not required.issubset(cluster_sizes.columns):
            raise ValueError(
                f"Input must contain columns: {required}"
            )

        if cluster_sizes.empty:
            raise ValueError("Cluster sizes are empty.")

        data = cluster_sizes.sort_values("cluster")

        fig, ax = plt.subplots(figsize=(8, 5))

        ax.bar(
            data["cluster"].astype(str),
            data["sample_count"],
        )

        ax.set_title(title)
        ax.set_xlabel("Cluster")
        ax.set_ylabel("Number of observations")
        ax.grid(axis="y", alpha=0.3)

        fig.tight_layout()

        return fig, ax

    # --------------------------------------------------
    # 4. 2D cluster visualization
    # --------------------------------------------------

    @staticmethod
    def plot_clusters_2d(
        X,
        labels,
        x_column="PC1",
        y_column="PC2",
        title="2D Cluster Visualization",
    ):

        if not isinstance(X, pd.DataFrame):
            raise TypeError(
                "X must be a pandas DataFrame."
            )

        if x_column not in X.columns:
            raise ValueError(
                f"Column '{x_column}' not found."
            )

        if y_column not in X.columns:
            raise ValueError(
                f"Column '{y_column}' not found."
            )

        if isinstance(labels, pd.Series):
            if not X.index.equals(labels.index):
                raise ValueError(
                    "X and labels must have matching indices."
                )

            label_values = labels.to_numpy()

        else:
            label_values = list(labels)

        if len(X) != len(label_values):
            raise ValueError(
                "X and labels must have the same number of rows."
            )

        if X[[x_column, y_column]].isna().any().any():
            raise ValueError(
                "Selected plotting columns contain missing values."
            )

        fig, ax = plt.subplots(figsize=(8, 6))

        scatter = ax.scatter(
            X[x_column],
            X[y_column],
            c=label_values,
            alpha=0.6,
        )

        ax.set_title(title)
        ax.set_xlabel(x_column)
        ax.set_ylabel(y_column)

        ax.legend(
            *scatter.legend_elements(),
            title="Cluster",
        )

        ax.grid(True, alpha=0.2)

        fig.tight_layout()

        return fig, ax
