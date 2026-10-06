"""Tests for RetailMindService bundle loading, serving contracts, and CSV exports."""

from pathlib import Path

from retailmind.contracts import RecommendationRequest
from retailmind.service import RetailMindService, escape_csv_formula


def test_escape_csv_formula() -> None:
    assert escape_csv_formula("=SUM(A1:A10)") == "'=SUM(A1:A10)"
    assert escape_csv_formula("+12345") == "'+12345"
    assert escape_csv_formula("-cmd|' /C calc'!A0") == "'-cmd|' /C calc'!A0"
    assert escape_csv_formula("@SUM(B1)") == "'@SUM(B1)"
    assert escape_csv_formula("Regular Text") == "Regular Text"


def test_service_bundle_loading_and_serving() -> None:
    bundle_path = Path("artifacts/release")
    assert bundle_path.exists(), "Release bundle must exist"

    service = RetailMindService(bundle_path)
    assert service.manifest.stage == "test"
    assert len(service.catalog_items) > 0
    assert len(service.df_segment_summaries) > 0

    # 1. Known active customer
    active_cid = service.df_profiles[service.df_profiles["status"] == "known_active"].iloc[0]["customer_id"]
    req = RecommendationRequest(customer_id=active_cid, top_k=10, mode="repeat_allowed", bundle=str(bundle_path))
    resp = service.recommend(req)

    assert resp.customer_id == active_cid
    assert resp.customer_status == "known_active"
    assert resp.returned_k == 10
    assert resp.status in ("ok", "fallback_only")
    assert len(resp.items) == 10
    assert resp.items[0].rank == 1

    # 2. Known inactive customer
    inactive_df = service.df_profiles[service.df_profiles["status"] == "known_inactive"]
    if not inactive_df.empty:
        inactive_cid = inactive_df.iloc[0]["customer_id"]
        req_in = RecommendationRequest(customer_id=inactive_cid, top_k=5, mode="repeat_allowed", bundle=str(bundle_path))
        resp_in = service.recommend(req_in)
        assert resp_in.customer_status == "known_inactive"
        assert resp_in.returned_k == 5

    # 3. Unknown customer
    req_unk = RecommendationRequest(customer_id="UNKNOWN_CUST_9999", top_k=10, mode="repeat_allowed", bundle=str(bundle_path))
    resp_unk = service.recommend(req_unk)
    assert resp_unk.customer_status == "unknown_customer"
    assert resp_unk.segment_id is None
    assert resp_unk.status == "fallback_only"
    assert resp_unk.fallback_count == 10
    assert all(item.method == "global_popularity" for item in resp_unk.items)

    # 4. New items only mode
    req_new = RecommendationRequest(customer_id=active_cid, top_k=10, mode="new_items_only", bundle=str(bundle_path))
    resp_new = service.recommend(req_new)
    user_history = set(service.customer_history.get(active_cid, []))
    for item in resp_new.items:
        assert item.stock_code not in user_history

    # 5. CSV export checks
    csv_recs = service.export_recommendations_csv(resp)
    assert "stock_code" in csv_recs
    assert "reason_code" in csv_recs

    csv_segs = service.export_segments_csv()
    assert "segment_id" in csv_segs
    assert "campaign_hypothesis" in csv_segs
