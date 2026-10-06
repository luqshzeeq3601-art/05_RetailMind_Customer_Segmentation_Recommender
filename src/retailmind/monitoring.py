"""Batch drift and distribution diagnostics between reference and current snapshots."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


def compute_snapshot_summary(
    df_profiles: pd.DataFrame,
    catalog_items: List[str],
    fallback_share: float,
) -> Dict[str, Any]:
    """Compute summary statistics for a snapshot for drift monitoring."""
    active = df_profiles[df_profiles["status"] == "known_active"]

    rfm_stats = {}
    for col in ["recency_days", "frequency_invoices", "monetary_gbp"]:
        vals = active[col].to_numpy() if not active.empty else np.array([])
        if len(vals) > 0:
            rfm_stats[col] = {
                "count": int(len(vals)),
                "median": round(float(np.median(vals)), 2),
                "q25": round(float(np.percentile(vals, 25)), 2),
                "q75": round(float(np.percentile(vals, 75)), 2),
            }
        else:
            rfm_stats[col] = {"count": 0, "median": 0.0, "q25": 0.0, "q75": 0.0}

    # Segment shares
    if "segment_id" in active.columns and not active.empty:
        seg_counts = active["segment_id"].value_counts().to_dict()
        total_active = len(active)
        seg_shares = {k: round(v / total_active, 4) for k, v in seg_counts.items()}
    else:
        seg_shares = {}

    return {
        "total_known": len(df_profiles),
        "total_active": len(active),
        "rfm_stats": rfm_stats,
        "segment_shares": seg_shares,
        "catalog_size": len(catalog_items),
        "catalog_items": list(catalog_items),
        "fallback_item_share": round(fallback_share, 4),
    }


def run_drift_diagnostics(
    ref_path: str | Path,
    cur_path: str | Path,
    output_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """Compare reference and current snapshots against operational review heuristics."""
    with open(ref_path, "r", encoding="utf-8") as f:
        ref = json.load(f)
    with open(cur_path, "r", encoding="utf-8") as f:
        cur = json.load(f)

    review_alerts: List[str] = []

    # 1. RFM Distribution Comparison
    rfm_diffs: Dict[str, Any] = {}
    for feat in ["recency_days", "frequency_invoices", "monetary_gbp"]:
        ref_med = ref.get("rfm_stats", {}).get(feat, {}).get("median", 0.0)
        cur_med = cur.get("rfm_stats", {}).get(feat, {}).get("median", 0.0)

        if ref_med > 0:
            rel_change = (cur_med - ref_med) / ref_med
            rel_change_str = f"{rel_change:+.2%}"
            if abs(rel_change) > 0.25:
                review_alerts.append(
                    f"Median {feat} changed by {rel_change_str} (exceeds 25% review threshold)."
                )
        else:
            rel_change = None
            rel_change_str = "N/A (zero reference)"
            if abs(cur_med - ref_med) > 0.01:
                review_alerts.append(
                    f"Median {feat} shifted from 0 to {cur_med} (review recommended)."
                )

        rfm_diffs[feat] = {
            "reference_median": ref_med,
            "current_median": cur_med,
            "absolute_diff": round(cur_med - ref_med, 2),
            "relative_change": rel_change,
        }

    # 2. Segment Share Comparison
    ref_segs = ref.get("segment_shares", {})
    cur_segs = cur.get("segment_shares", {})
    all_segs = sorted(set(ref_segs.keys()).union(set(cur_segs.keys())))

    seg_diffs: Dict[str, Any] = {}
    for seg in all_segs:
        r_share = ref_segs.get(seg, 0.0)
        c_share = cur_segs.get(seg, 0.0)
        diff_pp = round(c_share - r_share, 4)
        seg_diffs[seg] = {
            "reference_share": r_share,
            "current_share": c_share,
            "diff_percentage_points": diff_pp,
        }
        if abs(diff_pp) > 0.10:
            review_alerts.append(
                f"Segment {seg} share shifted by {diff_pp:+.2%} (exceeds 10pp threshold)."
            )

    # 3. Catalog Churn & Jaccard Overlap
    ref_cat = set(ref.get("catalog_items", []))
    cur_cat = set(cur.get("catalog_items", []))

    additions = cur_cat - ref_cat
    removals = ref_cat - cur_cat
    intersection = ref_cat.intersection(cur_cat)
    union = ref_cat.union(cur_cat)
    jaccard = len(intersection) / float(len(union)) if union else 1.0

    catalog_diff = {
        "reference_catalog_size": len(ref_cat),
        "current_catalog_size": len(cur_cat),
        "items_added": len(additions),
        "items_removed": len(removals),
        "jaccard_overlap": round(jaccard, 4),
    }
    if jaccard < 0.70:
        review_alerts.append(
            f"Catalog Jaccard overlap {jaccard:.2f} is below 0.70 review threshold."
        )

    # 4. Fallback Share Comparison
    ref_fb = ref.get("fallback_item_share", 0.0)
    cur_fb = cur.get("fallback_item_share", 0.0)
    fb_diff_pp = round(cur_fb - ref_fb, 4)
    fallback_diff = {
        "reference_fallback_share": ref_fb,
        "current_fallback_share": cur_fb,
        "diff_percentage_points": fb_diff_pp,
    }
    if fb_diff_pp > 0.10:
        review_alerts.append(
            f"Popularity fallback share increased by {fb_diff_pp:+.2%} (exceeds 10pp threshold)."
        )

    diagnostic_report = {
        "diagnostics_timestamp_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "requires_analyst_review": len(review_alerts) > 0,
        "review_alerts_count": len(review_alerts),
        "review_alerts": review_alerts,
        "rfm_differences": rfm_diffs,
        "segment_share_differences": seg_diffs,
        "catalog_differences": catalog_diff,
        "fallback_differences": fallback_diff,
        "disclaimer": "Thresholds are operational review heuristics for analysts, not automated retraining triggers.",
    }

    if output_path is not None:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(diagnostic_report, f, indent=2)

    return diagnostic_report
