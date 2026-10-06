"""Tests for ranking metrics, NDCG/Recall calculations, and bootstrap intervals."""

import numpy as np

from retailmind.evaluation import compute_ranking_metrics_for_user, paired_bootstrap_ci


def test_compute_ranking_metrics_for_user_hand_calculated() -> None:
    # Recommended: [A, B, C, D, E] (k=5)
    # Ground truth: {B, D, F} (3 items)
    # Ranks of hits:
    # rank 2 (B): discount = 1 / log2(2 + 1) = 1 / log2(3) = 1 / 1.58496 = 0.63093
    # rank 4 (D): discount = 1 / log2(4 + 1) = 1 / log2(5) = 1 / 2.32193 = 0.43068
    # DCG = 0.63093 + 0.43068 = 1.06161
    # Ideal hits: min(5, 3) = 3 items at ranks 1, 2, 3
    # rank 1: 1 / log2(2) = 1.0
    # rank 2: 1 / log2(3) = 0.63093
    # rank 3: 1 / log2(4) = 0.50
    # IDCG = 1.0 + 0.63093 + 0.50 = 2.13093
    # NDCG = 1.06161 / 2.13093 = 0.49819
    # Recall = 2 / 3 = 0.66667
    # Precision = 2 / 5 = 0.40
    # HitRate = 1.0

    recs = ["A", "B", "C", "D", "E"]
    gt = {"B", "D", "F"}

    metrics = compute_ranking_metrics_for_user(recs, gt, k=5)

    assert abs(metrics["recall_at_k"] - 2.0 / 3.0) < 1e-4
    assert abs(metrics["precision_at_k"] - 2.0 / 5.0) < 1e-4
    assert metrics["hit_rate_at_k"] == 1.0
    assert abs(metrics["ndcg_at_k"] - 0.49819) < 1e-3


def test_short_list_precision_penalty() -> None:
    # Returning only 1 item which is a hit should give Precision@10 = 0.10, not 1.0
    recs = ["A"]
    gt = {"A", "B"}
    metrics = compute_ranking_metrics_for_user(recs, gt, k=10)
    assert metrics["precision_at_k"] == 0.10
    assert metrics["recall_at_k"] == 0.50


def test_paired_bootstrap_ci() -> None:
    scores_cf = np.array([0.5, 0.6, 0.7, 0.8, 0.9, 0.4, 0.5, 0.6, 0.7, 0.8])
    scores_base = np.array([0.2, 0.3, 0.3, 0.4, 0.5, 0.2, 0.3, 0.4, 0.3, 0.4])

    ci_cf, ci_base, ci_diff = paired_bootstrap_ci(scores_cf, scores_base, n_bootstraps=500, seed=42)

    assert ci_cf[0] <= ci_cf[1]
    assert ci_base[0] <= ci_base[1]
    assert ci_diff[0] > 0.0  # CF is significantly higher than baseline
