"""Tests for drift and batch monitoring diagnostics."""

import json
from pathlib import Path

import pandas as pd

from retailmind.monitoring import compute_snapshot_summary, run_drift_diagnostics


def test_compute_snapshot_summary_and_drift_diagnostics(tmp_path: Path) -> None:
    # Reference snapshot
    df_ref = pd.DataFrame(
        {
            "customer_id": [f"C_{i}" for i in range(100)],
            "recency_days": [20.0] * 100,
            "frequency_invoices": [5] * 100,
            "monetary_gbp": [200.0] * 100,
            "status": ["known_active"] * 100,
            "segment_id": ["SG01"] * 50 + ["SG02"] * 50,
        }
    )
    ref_summary = compute_snapshot_summary(df_ref, catalog_items=["10001", "10002", "10003"], fallback_share=0.10)
    ref_file = tmp_path / "reference.json"
    with open(ref_file, "w", encoding="utf-8") as f:
        json.dump(ref_summary, f)

    # Current snapshot with a shifted RFM (recency doubled to 45 days) and shifted segment share
    df_cur = pd.DataFrame(
        {
            "customer_id": [f"C_{i}" for i in range(100)],
            "recency_days": [45.0] * 100,
            "frequency_invoices": [5] * 100,
            "monetary_gbp": [200.0] * 100,
            "status": ["known_active"] * 100,
            "segment_id": ["SG01"] * 20 + ["SG02"] * 80,
        }
    )
    cur_summary = compute_snapshot_summary(df_cur, catalog_items=["10001", "10002"], fallback_share=0.25)
    cur_file = tmp_path / "current.json"
    with open(cur_file, "w", encoding="utf-8") as f:
        json.dump(cur_summary, f)

    out_file = tmp_path / "drift.json"
    diag = run_drift_diagnostics(ref_file, cur_file, output_path=out_file)

    assert diag["requires_analyst_review"] is True
    assert diag["review_alerts_count"] >= 3
    # Check that alert mentions recency change and fallback share change
    alerts_text = " ".join(diag["review_alerts"])
    assert "recency_days" in alerts_text
    assert "SG02" in alerts_text or "SG01" in alerts_text
    assert "fallback" in alerts_text.lower()
