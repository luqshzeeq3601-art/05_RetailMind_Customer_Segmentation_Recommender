"""Ranking metrics, macro evaluation, cohort construction, and bootstrap significance testing."""

import math
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd


def compute_ranking_metrics_for_user(
    recommended_items: List[str],
    ground_truth_items: Set[str],
    k: int = 10,
) -> Dict[str, float]:
    """Compute Recall@K, Precision@K, HitRate@K, DCG@K, IDCG@K, and NDCG@K for a single user."""
    if not ground_truth_items:
        raise ValueError("ground_truth_items must not be empty")

    top_items = recommended_items[:k]
    hits = [1 if item in ground_truth_items else 0 for item in top_items]
    num_hits = sum(hits)

    recall = num_hits / float(len(ground_truth_items))
    precision = num_hits / float(k)
    hit_rate = 1.0 if num_hits > 0 else 0.0

    # DCG
    dcg = 0.0
    for r, h in enumerate(hits):
        if h > 0:
            dcg += 1.0 / math.log2((r + 1) + 1)

    # IDCG: ideal ranking where min(k, |G|) items are relevant at ranks 1..min(k, |G|)
    ideal_hits_count = min(k, len(ground_truth_items))
    idcg = 0.0
    for r in range(ideal_hits_count):
        idcg += 1.0 / math.log2((r + 1) + 1)

    ndcg = (dcg / idcg) if idcg > 0.0 else 0.0

    return {
        "recall_at_k": recall,
        "precision_at_k": precision,
        "hit_rate_at_k": hit_rate,
        "dcg_at_k": dcg,
        "idcg_at_k": idcg,
        "ndcg_at_k": ndcg,
    }


def paired_bootstrap_ci(
    scores_a: np.ndarray,
    scores_b: np.ndarray,
    n_bootstraps: int = 1000,
    seed: int = 42,
    alpha: float = 0.05,
) -> Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]]:
    """Compute 95% percentile confidence intervals for mean(A), mean(B), and mean(A - B).

    Returns:
        ((a_low, a_high), (b_low, b_high), (diff_low, diff_high))
    """
    n = len(scores_a)
    assert len(scores_b) == n, "Scores arrays must have equal length for paired bootstrap"

    rng = np.random.RandomState(seed)
    diffs = scores_a - scores_b

    means_a = np.empty(n_bootstraps, dtype=np.float64)
    means_b = np.empty(n_bootstraps, dtype=np.float64)
    means_diff = np.empty(n_bootstraps, dtype=np.float64)

    for i in range(n_bootstraps):
        sample_idx = rng.randint(0, n, size=n)
        means_a[i] = np.mean(scores_a[sample_idx])
        means_b[i] = np.mean(scores_b[sample_idx])
        means_diff[i] = np.mean(diffs[sample_idx])

    low_pct = 100.0 * (alpha / 2.0)
    high_pct = 100.0 * (1.0 - alpha / 2.0)

    ci_a = (float(np.percentile(means_a, low_pct)), float(np.percentile(means_a, high_pct)))
    ci_b = (float(np.percentile(means_b, low_pct)), float(np.percentile(means_b, high_pct)))
    ci_diff = (float(np.percentile(means_diff, low_pct)), float(np.percentile(means_diff, high_pct)))

    return ci_a, ci_b, ci_diff


def extract_evaluation_cohorts(
    df_purchases: pd.DataFrame,
    cutoff: pd.Timestamp,
    future_start: pd.Timestamp,
    future_end: pd.Timestamp,
    catalog_items: List[str],
) -> Dict[str, Any]:
    """Extract primary known-customer cohort, cold-start cohort, and new-product ground truth sets."""
    catalog_set = set(catalog_items)

    # History prior to cutoff
    history = df_purchases[df_purchases["InvoiceDate"] < cutoff]
    known_customers = set(history["CustomerID"].unique())
    customer_history_items = history.groupby("CustomerID")["StockCode"].unique().to_dict()

    # Future purchases in [future_start, future_end)
    future = df_purchases[
        (df_purchases["InvoiceDate"] >= future_start) & (df_purchases["InvoiceDate"] < future_end)
    ]
    future_customers = set(future["CustomerID"].unique())
    future_customer_items = future.groupby("CustomerID")["StockCode"].unique().to_dict()

    # Total future customer-item pairs and in-catalog future pairs
    total_future_pairs = len(future[["CustomerID", "StockCode"]].drop_duplicates())
    future_in_cat = future[future["StockCode"].isin(catalog_set)]
    in_cat_future_pairs = len(future_in_cat[["CustomerID", "StockCode"]].drop_duplicates())
    future_item_coverage = in_cat_future_pairs / total_future_pairs if total_future_pairs > 0 else 0.0

    # 1. Primary cohort: known customers with non-empty in-catalog future purchases
    primary_cohort_users = []
    primary_ground_truth: Dict[str, Set[str]] = {}

    for cid in sorted(known_customers):
        if cid in future_customer_items:
            f_items = set(future_customer_items[cid])
            in_cat = f_items.intersection(catalog_set)
            if in_cat:
                primary_cohort_users.append(cid)
                primary_ground_truth[cid] = in_cat

    # 2. Cold start cohort: unknown customers with non-empty in-catalog future purchases
    cold_start_users = []
    cold_start_ground_truth: Dict[str, Set[str]] = {}

    for cid in sorted(future_customers):
        if cid not in known_customers:
            f_items = set(future_customer_items[cid])
            in_cat = f_items.intersection(catalog_set)
            if in_cat:
                cold_start_users.append(cid)
                cold_start_ground_truth[cid] = in_cat

    # 3. New-product view cohort: known customers with future in-catalog items they haven't bought before
    new_product_users = []
    new_product_ground_truth: Dict[str, Set[str]] = {}

    for cid in sorted(known_customers):
        if cid in future_customer_items:
            f_items = set(future_customer_items[cid])
            h_items = set(customer_history_items.get(cid, []))
            in_cat_new = (f_items.intersection(catalog_set)) - h_items
            if in_cat_new:
                new_product_users.append(cid)
                new_product_ground_truth[cid] = in_cat_new

    return {
        "primary_cohort_users": primary_cohort_users,
        "primary_ground_truth": primary_ground_truth,
        "cold_start_users": cold_start_users,
        "cold_start_ground_truth": cold_start_ground_truth,
        "new_product_users": new_product_users,
        "new_product_ground_truth": new_product_ground_truth,
        "total_future_pairs": total_future_pairs,
        "in_cat_future_pairs": in_cat_future_pairs,
        "future_item_coverage": future_item_coverage,
        "total_known_customers": len(known_customers),
        "total_future_customers": len(future_customers),
    }


def evaluate_model_on_cohort(
    model: Any,
    users: List[str],
    ground_truth: Dict[str, Set[str]],
    catalog_items: List[str],
    customer_segments: Dict[str, str],
    seg_pop: Any,
    global_pop: Any,
    customer_history: Optional[Dict[str, Set[str]]] = None,
    mode: str = "repeat_allowed",
    k: int = 10,
    model_name: str = "model",
) -> Dict[str, Any]:
    """Evaluate a recommender model across a cohort of users with macro ranking metrics."""
    if not users:
        return {
            "model_name": model_name,
            "cohort_size": 0,
            "mean_ndcg": 0.0,
            "mean_recall": 0.0,
            "mean_precision": 0.0,
            "mean_hit_rate": 0.0,
            "catalog_coverage": 0.0,
            "fallback_item_share": 0.0,
            "personalized_customer_share": 0.0,
            "per_user_metrics": [],
        }

    all_recommended_items: Set[str] = set()
    total_returned_slots = 0
    total_fallback_slots = 0
    personalized_users_count = 0

    per_user_metrics = []

    for cid in users:
        gt = ground_truth[cid]
        seg_id = customer_segments.get(cid)

        exclude: Set[str] = set()
        if mode == "new_items_only" and customer_history:
            exclude = set(customer_history.get(cid, set()))

        if hasattr(model, "recommend_for_customer"):
            # ItemItem CF
            recs = model.recommend_for_customer(
                customer_id=cid,
                k=k,
                segment_id=seg_id,
                seg_pop=seg_pop,
                global_pop=global_pop,
                mode=mode,
            )
        elif hasattr(model, "segment_rankings"):
            # Segment Popularity
            recs = model.recommend(
                segment_id=seg_id,
                k=k,
                global_pop=global_pop,
                exclude_items=exclude,
            )
        else:
            # Global Popularity
            recs = model.recommend(k=k, exclude_items=exclude)

        rec_codes = [r.stock_code for r in recs]
        all_recommended_items.update(rec_codes)
        total_returned_slots += len(recs)

        num_fb = sum(1 for r in recs if r.is_fallback)
        total_fallback_slots += num_fb

        if any(not r.is_fallback for r in recs):
            personalized_users_count += 1

        metrics = compute_ranking_metrics_for_user(rec_codes, gt, k=k)
        metrics["customer_id"] = cid
        per_user_metrics.append(metrics)

    df_user_metrics = pd.DataFrame(per_user_metrics)

    mean_ndcg = float(df_user_metrics["ndcg_at_k"].mean())
    mean_recall = float(df_user_metrics["recall_at_k"].mean())
    mean_precision = float(df_user_metrics["precision_at_k"].mean())
    mean_hit_rate = float(df_user_metrics["hit_rate_at_k"].mean())

    catalog_coverage = (
        len(all_recommended_items) / float(len(catalog_items)) if catalog_items else 0.0
    )
    fallback_item_share = (
        total_fallback_slots / float(total_returned_slots) if total_returned_slots > 0 else 0.0
    )
    personalized_customer_share = (
        personalized_users_count / float(len(users)) if users else 0.0
    )

    return {
        "model_name": model_name,
        "cohort_size": len(users),
        "mean_ndcg": round(mean_ndcg, 6),
        "mean_recall": round(mean_recall, 6),
        "mean_precision": round(mean_precision, 6),
        "mean_hit_rate": round(mean_hit_rate, 6),
        "catalog_coverage": round(catalog_coverage, 4),
        "fallback_item_share": round(fallback_item_share, 4),
        "personalized_customer_share": round(personalized_customer_share, 4),
        "per_user_metrics": per_user_metrics,
    }
