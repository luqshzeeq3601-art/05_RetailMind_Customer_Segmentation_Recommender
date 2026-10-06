"""Tests for item-item collaborative filtering recommender."""

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix

from retailmind.recommenders import (
    GlobalPopularityRecommender,
    ItemItemCollaborativeFiltering,
    SegmentPopularityRecommender,
)


def test_item_item_collaborative_filtering_math() -> None:
    # 4 customers, 3 items (10001, 10002, 10003)
    # Customers C1 and C2 buy (10001, 10002)
    # Customer C3 buys (10002, 10003)
    # Customer C4 buys (10001)
    catalog = ["10001", "10002", "10003"]
    customer_to_idx = {"C1": 0, "C2": 1, "C3": 2, "C4": 3}
    item_to_idx = {"10001": 0, "10002": 1, "10003": 2}

    rows = [0, 0, 1, 1, 2, 2, 3]
    cols = [0, 1, 0, 1, 1, 2, 0]
    data = np.ones(len(rows), dtype=np.float32)
    csr = csr_matrix((data, (rows, cols)), shape=(4, 3))

    df_hist = pd.DataFrame(
        [
            {"CustomerID": "C1", "StockCode": "10001", "InvoiceDate": pd.to_datetime("2011-09-01")},
            {"CustomerID": "C1", "StockCode": "10002", "InvoiceDate": pd.to_datetime("2011-09-01")},
            {"CustomerID": "C2", "StockCode": "10001", "InvoiceDate": pd.to_datetime("2011-09-01")},
            {"CustomerID": "C2", "StockCode": "10002", "InvoiceDate": pd.to_datetime("2011-09-01")},
            {"CustomerID": "C3", "StockCode": "10002", "InvoiceDate": pd.to_datetime("2011-09-01")},
            {"CustomerID": "C3", "StockCode": "10003", "InvoiceDate": pd.to_datetime("2011-09-01")},
            {"CustomerID": "C4", "StockCode": "10001", "InvoiceDate": pd.to_datetime("2011-09-01")},
        ]
    )

    cutoff = pd.to_datetime("2011-10-15 00:00:00")
    global_pop = GlobalPopularityRecommender().fit(df_hist, catalog, cutoff=cutoff)
    seg_pop = SegmentPopularityRecommender().fit(df_hist, {"C4": "SG01"}, catalog, cutoff=cutoff)

    cf = ItemItemCollaborativeFiltering(top_n_neighbors=10, min_co_buyers=2, block_size=10)
    cf.fit(csr, catalog, customer_to_idx, item_to_idx, df_hist)

    # For customer C4 (who bought 10001):
    # 10001 and 10002 co-bought by C1 and C2 (co_buyers=2 >= 2)
    # Cosine similarity between 10001 (norm sqrt(3)) and 10002 (norm sqrt(3)) = 2 / 3 = 0.6667
    # 10001 and 10003 co-bought by 0 users -> similarity 0
    # Customer C4's candidate score for 10002 is 0.6667 > 0
    recs = cf.recommend_for_customer(
        customer_id="C4",
        k=3,
        segment_id="SG01",
        seg_pop=seg_pop,
        global_pop=global_pop,
        mode="repeat_allowed",
    )

    assert len(recs) == 3
    # Top rec should be 10002 via item_cf
    assert recs[0].stock_code == "10002"
    assert recs[0].method == "item_cf"
    assert recs[0].is_fallback is False
    assert "10001" in recs[0].supporting_stock_codes

    # In new_items_only mode, C4 should not receive 10001 anywhere
    recs_new = cf.recommend_for_customer(
        customer_id="C4",
        k=3,
        segment_id="SG01",
        seg_pop=seg_pop,
        global_pop=global_pop,
        mode="new_items_only",
    )
    assert "10001" not in [r.stock_code for r in recs_new]


def test_item_item_collaborative_filtering_tfidf_weighting() -> None:
    catalog = ["10001", "10002", "10003"]
    customer_to_idx = {"C1": 0, "C2": 1, "C3": 2, "C4": 3}
    item_to_idx = {"10001": 0, "10002": 1, "10003": 2}

    rows = [0, 0, 1, 1, 2, 2, 3]
    cols = [0, 1, 0, 1, 1, 2, 0]
    data = np.ones(len(rows), dtype=np.float32)
    csr = csr_matrix((data, (rows, cols)), shape=(4, 3))

    df_hist = pd.DataFrame(
        [
            {"CustomerID": "C1", "StockCode": "10001", "InvoiceDate": pd.to_datetime("2011-09-01")},
            {"CustomerID": "C1", "StockCode": "10002", "InvoiceDate": pd.to_datetime("2011-09-01")},
            {"CustomerID": "C2", "StockCode": "10001", "InvoiceDate": pd.to_datetime("2011-09-01")},
            {"CustomerID": "C2", "StockCode": "10002", "InvoiceDate": pd.to_datetime("2011-09-01")},
            {"CustomerID": "C3", "StockCode": "10002", "InvoiceDate": pd.to_datetime("2011-09-01")},
            {"CustomerID": "C3", "StockCode": "10003", "InvoiceDate": pd.to_datetime("2011-09-01")},
            {"CustomerID": "C4", "StockCode": "10001", "InvoiceDate": pd.to_datetime("2011-09-01")},
        ]
    )

    cf_tfidf = ItemItemCollaborativeFiltering(top_n_neighbors=10, min_co_buyers=2, block_size=10, weighting_method="tfidf")
    cf_tfidf.fit(csr, catalog, customer_to_idx, item_to_idx, df_hist)
    assert cf_tfidf.weighting_method == "tfidf"
    assert len(cf_tfidf.neighbor_index) > 0
