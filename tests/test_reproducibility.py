"""Tests for strict seed reproducibility and metric determinism."""

import numpy as np
import pandas as pd

from retailmind.segmentation import (
    evaluate_clustering_candidates,
)


def test_clustering_seed_reproducibility() -> None:
    rng = np.random.RandomState(42)
    n = 100
    df_active = pd.DataFrame(
        {
            "customer_id": [f"CUST_{i}" for i in range(n)],
            "recency_days": rng.uniform(1, 100, size=n),
            "frequency_invoices": rng.randint(1, 10, size=n),
            "monetary_gbp": rng.uniform(10, 1000, size=n),
            "status": ["known_active"] * n,
        }
    )

    _, info1 = evaluate_clustering_candidates(
        df_active,
        seeds=[42, 43],
        kmeans_k_candidates=[3],
        gmm_components_candidates=[3],
        gmm_covariance_types=["full"],
        min_cluster_share=0.01,
        min_median_ari=0.50,
        min_mean_silhouette=0.20,
    )

    _, info2 = evaluate_clustering_candidates(
        df_active,
        seeds=[42, 43],
        kmeans_k_candidates=[3],
        gmm_components_candidates=[3],
        gmm_covariance_types=["full"],
        min_cluster_share=0.01,
        min_median_ari=0.50,
        min_mean_silhouette=0.20,
    )

    assert info1["mean_silhouette"] == info2["mean_silhouette"]
    assert info1["median_ari"] == info2["median_ari"]
