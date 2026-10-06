"""Tests for global and segment popularity recommenders."""

import pandas as pd

from retailmind.recommenders import GlobalPopularityRecommender, SegmentPopularityRecommender


def test_global_popularity_recommender() -> None:
    cutoff = pd.to_datetime("2011-10-15 00:00:00")
    # 3 items, item 10001 bought by 10 users, 10002 by 5 users, 10003 by 2 users
    records = []
    for i in range(10):
        records.append({"CustomerID": f"C_{i}", "StockCode": "10001", "InvoiceDate": pd.to_datetime("2011-09-01")})
    for i in range(5):
        records.append({"CustomerID": f"C_{i}", "StockCode": "10002", "InvoiceDate": pd.to_datetime("2011-09-01")})
    for i in range(2):
        records.append({"CustomerID": f"C_{i}", "StockCode": "10003", "InvoiceDate": pd.to_datetime("2011-09-01")})

    df = pd.DataFrame(records)
    catalog = ["10001", "10002", "10003"]
    descs = {"10001": "Product 1", "10002": "Product 2", "10003": "Product 3"}

    pop = GlobalPopularityRecommender()
    pop.fit(df, catalog, cutoff=cutoff, active_window_days=90)

    recs = pop.recommend(k=2, item_descriptions=descs)
    assert len(recs) == 2
    assert recs[0].stock_code == "10001"
    assert recs[0].score == 10.0
    assert recs[0].rank == 1
    assert recs[0].is_fallback is True
    assert recs[1].stock_code == "10002"
    assert recs[1].score == 5.0
    assert recs[1].rank == 2

    # Test exclusion (e.g. new_items_only mode)
    recs_ex = pop.recommend(k=2, exclude_items={"10001"}, item_descriptions=descs)
    assert recs_ex[0].stock_code == "10002"
    assert recs_ex[1].stock_code == "10003"


def test_segment_popularity_recommender() -> None:
    cutoff = pd.to_datetime("2011-10-15 00:00:00")
    records = []
    # Segment SG01 users buy 10002 more than 10001
    for i in range(5):
        records.append({"CustomerID": f"VIP_{i}", "StockCode": "10002", "InvoiceDate": pd.to_datetime("2011-09-01")})
    for i in range(2):
        records.append({"CustomerID": f"VIP_{i}", "StockCode": "10001", "InvoiceDate": pd.to_datetime("2011-09-01")})
    # Other users buy 10001
    for i in range(10):
        records.append({"CustomerID": f"STD_{i}", "StockCode": "10001", "InvoiceDate": pd.to_datetime("2011-09-01")})

    df = pd.DataFrame(records)
    catalog = ["10001", "10002"]
    cust_segments = {f"VIP_{i}": "SG01" for i in range(5)}
    cust_segments.update({f"STD_{i}": "SG02" for i in range(10)})

    global_pop = GlobalPopularityRecommender().fit(df, catalog, cutoff=cutoff)
    seg_pop = SegmentPopularityRecommender().fit(df, cust_segments, catalog, cutoff=cutoff)

    # For SG01 customer, 10002 should rank #1
    recs_sg01 = seg_pop.recommend(segment_id="SG01", k=2, global_pop=global_pop)
    assert recs_sg01[0].stock_code == "10002"
    assert recs_sg01[0].method == "segment_popularity"
    assert recs_sg01[1].stock_code == "10001"

    # Unknown segment should fall back to global popularity (where 10001 is #1)
    recs_unk = seg_pop.recommend(segment_id=None, k=2, global_pop=global_pop)
    assert recs_unk[0].stock_code == "10001"
