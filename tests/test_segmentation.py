"""Tests for customer segmentation models, RFM rules, and profiling."""

import numpy as np
import pandas as pd

from retailmind.segmentation import (
    RFMRulesSegmenter,
    evaluate_clustering_candidates,
    fit_and_profile_selected_segmenter,
)


def test_rfm_rules_segmenter() -> None:
    # Synthetic active population
    rng = np.random.RandomState(42)
    n = 100
    df_active = pd.DataFrame(
        {
            "customer_id": [f"CUST_{i}" for i in range(n)],
            "recency_days": rng.uniform(1, 100, size=n),
            "frequency_invoices": rng.randint(1, 20, size=n),
            "monetary_gbp": rng.uniform(50, 5000, size=n),
            "status": ["known_active"] * n,
        }
    )

    segmenter = RFMRulesSegmenter()
    segmenter.fit(df_active)
    assert segmenter.is_fitted
    assert len(segmenter.r_cutpoints) == 3
    assert len(segmenter.f_cutpoints) == 3
    assert len(segmenter.m_cutpoints) == 3

    # Include an inactive customer
    df_test = df_active.copy()
    df_test.loc[0, "status"] = "known_inactive"

    seg_ids, seg_labels = segmenter.predict(df_test)
    assert seg_ids[0] == "SG_INACTIVE"
    assert "Inactive" in seg_labels[0]

    # Active customers should receive SG01, SG02, SG03, or SG04
    active_ids = set(seg_ids[1:])
    assert active_ids.issubset({"SG01", "SG02", "SG03", "SG04"})


def test_clustering_evaluation_and_ordering() -> None:
    rng = np.random.RandomState(42)
    n = 200
    df_active = pd.DataFrame(
        {
            "customer_id": [f"CUST_{i}" for i in range(n)],
            "recency_days": rng.uniform(1, 150, size=n),
            "frequency_invoices": rng.randint(1, 15, size=n),
            "monetary_gbp": rng.exponential(scale=500, size=n) + 10,
            "status": ["known_active"] * n,
        }
    )

    df_comp, selected_info = evaluate_clustering_candidates(
        df_active,
        seeds=[42, 43, 44],
        kmeans_k_candidates=[3, 4],
        gmm_components_candidates=[3],
        gmm_covariance_types=["full"],
        min_cluster_share=0.01,
        min_median_ari=0.50,
        min_mean_silhouette=0.20,
    )

    assert not df_comp.empty
    assert "mean_silhouette" in df_comp.columns
    assert "median_ari" in df_comp.columns

    estimator, scaler, df_profiles, profiles_dict = fit_and_profile_selected_segmenter(
        df_active, selected_info, seed=42
    )

    assert not df_profiles.empty
    assert "segment_id" in df_profiles.columns
    assert "campaign_hypothesis" in df_profiles.columns

    # Verify segment ID ordering: SG01 must have higher median monetary or frequency than lower ranked
    if len(df_profiles) >= 2:
        m0 = df_profiles.iloc[0]["median_monetary"]
        m1 = df_profiles.iloc[1]["median_monetary"]
        assert m0 >= m1 or df_profiles.iloc[0]["median_frequency"] >= df_profiles.iloc[1]["median_frequency"]


def test_rfm_transformation_methods() -> None:
    rng = np.random.RandomState(42)
    n = 100
    df_active = pd.DataFrame(
        {
            "customer_id": [f"CUST_{i}" for i in range(n)],
            "recency_days": rng.uniform(1, 100, size=n),
            "frequency_invoices": rng.randint(1, 20, size=n),
            "monetary_gbp": rng.exponential(scale=300, size=n) + 10,
            "status": ["known_active"] * n,
        }
    )

    for method in ["yeo_johnson", "quantile", "log1p"]:
        df_comp, sel_info = evaluate_clustering_candidates(
            df_active,
            seeds=[42, 43],
            kmeans_k_candidates=[3],
            gmm_components_candidates=[],
            gmm_covariance_types=[],
            transform_method=method,
            min_cluster_share=0.01,
            min_median_ari=0.50,
            min_mean_silhouette=0.10,
        )
        assert not df_comp.empty
        assert sel_info["transform_method"] == method
