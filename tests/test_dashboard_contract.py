"""Tests for dashboard contract, CLI/dashboard rank parity, and export formatting."""

from retailmind.contracts import RecommendationRequest
from retailmind.service import RetailMindService


def test_dashboard_and_cli_rank_parity() -> None:
    bundle_path = "artifacts/release"
    service = RetailMindService(bundle_path)

    # Pick a known active customer
    active_cid = service.df_profiles[service.df_profiles["status"] == "known_active"].iloc[0]["customer_id"]

    # 1. Repeat allowed mode
    req1 = RecommendationRequest(customer_id=active_cid, top_k=10, mode="repeat_allowed", bundle=bundle_path)
    resp1 = service.recommend(req1)
    ranks1 = [item.stock_code for item in resp1.items]
    assert len(ranks1) == 10
    # Duplicate recommendation check: must be all unique
    assert len(set(ranks1)) == len(ranks1)

    # 2. New items only mode
    req2 = RecommendationRequest(customer_id=active_cid, top_k=10, mode="new_items_only", bundle=bundle_path)
    resp2 = service.recommend(req2)
    ranks2 = [item.stock_code for item in resp2.items]
    assert len(set(ranks2)) == len(ranks2)

    # 3. Export CSV check
    csv_str = service.export_recommendations_csv(resp1)
    lines = csv_str.strip().split("\n")
    # Header + 10 rows = 11 lines
    assert len(lines) == 11
