"""Tests for time-safe RFM feature engineering and catalog snapshot extraction."""

import pandas as pd

from retailmind.features import build_catalog_and_interactions, build_snapshot_rfm


def test_rfm_snapshot_invariance_and_correctness() -> None:
    # Build synthetic transactions
    df = pd.DataFrame(
        [
            # Customer A: active, 2 lines in 1 invoice on 2011-09-01
            {"InvoiceNo": "1001", "StockCode": "10001", "Description": "Item 1", "Quantity": 2, "InvoiceDate": pd.to_datetime("2011-09-01 10:00:00"), "UnitPrice": 10.0, "CustomerID": "CUST_A", "Country": "UK", "purchase_value_gbp": 20.0},
            {"InvoiceNo": "1001", "StockCode": "10002", "Description": "Item 2", "Quantity": 1, "InvoiceDate": pd.to_datetime("2011-09-01 10:00:00"), "UnitPrice": 15.0, "CustomerID": "CUST_A", "Country": "UK", "purchase_value_gbp": 15.0},
            # Customer A: second invoice on 2011-10-01
            {"InvoiceNo": "1002", "StockCode": "10001", "Description": "Item 1", "Quantity": 1, "InvoiceDate": pd.to_datetime("2011-10-01 10:00:00"), "UnitPrice": 10.0, "CustomerID": "CUST_A", "Country": "UK", "purchase_value_gbp": 10.0},
            # Customer B: inactive (bought in Jan 2011, >180 days before 2011-10-15)
            {"InvoiceNo": "1003", "StockCode": "10001", "Description": "Item 1", "Quantity": 5, "InvoiceDate": pd.to_datetime("2011-01-15 10:00:00"), "UnitPrice": 10.0, "CustomerID": "CUST_B", "Country": "UK", "purchase_value_gbp": 50.0},
            # Future transaction on/after cutoff 2011-10-15
            {"InvoiceNo": "1004", "StockCode": "10001", "Description": "Item 1", "Quantity": 10, "InvoiceDate": pd.to_datetime("2011-10-20 10:00:00"), "UnitPrice": 10.0, "CustomerID": "CUST_A", "Country": "UK", "purchase_value_gbp": 100.0},
        ]
    )

    cutoff = "2011-10-15 00:00:00"
    df_profiles, meta = build_snapshot_rfm(df, cutoff=cutoff, rfm_window_days=180)

    # Customer A checks
    prof_a = df_profiles[df_profiles["customer_id"] == "CUST_A"].iloc[0]
    assert prof_a["status"] == "known_active"
    assert prof_a["frequency_invoices"] == 2  # 2 distinct invoices (1001 and 1002), not 3 product lines
    assert prof_a["monetary_gbp"] == 45.0  # 20 + 15 + 10 = 45.0 (excluding future 100.0)
    # Recency: floor of (2011-10-15 00:00:00 - 2011-10-01 10:00:00) = 13 days
    assert prof_a["recency_days"] == 13.0

    # Customer B checks
    prof_b = df_profiles[df_profiles["customer_id"] == "CUST_B"].iloc[0]
    assert prof_b["status"] == "known_inactive"
    assert prof_b["frequency_invoices"] == 0
    assert prof_b["monetary_gbp"] == 0.0
    assert prof_b["recency_days"] > 180.0

    # Test future row invariance: drop the future row and check that profiles are identical
    df_no_future = df[df["InvoiceDate"] < pd.to_datetime(cutoff)]
    df_profiles_no_future, meta_no_future = build_snapshot_rfm(df_no_future, cutoff=cutoff, rfm_window_days=180)

    pd.testing.assert_frame_equal(df_profiles, df_profiles_no_future)


def test_catalog_builder() -> None:
    # 5 customers buy item 10001 in last 90 days -> eligible
    # Only 1 customer buys item 10002 -> not eligible (buyers < 5)
    records = []
    for i in range(5):
        records.append({
            "InvoiceNo": f"INV_{i}",
            "StockCode": "10001",
            "Description": f"Item 1 v{i}",
            "Quantity": 1,
            "InvoiceDate": pd.to_datetime("2011-09-01 10:00:00"),
            "UnitPrice": 5.0,
            "CustomerID": f"CUST_{i}",
            "Country": "UK",
            "purchase_value_gbp": 5.0,
        })
    records.append({
        "InvoiceNo": "INV_99",
        "StockCode": "10002",
        "Description": "Item 2",
        "Quantity": 1,
        "InvoiceDate": pd.to_datetime("2011-09-01 10:00:00"),
        "UnitPrice": 5.0,
        "CustomerID": "CUST_0",
        "Country": "UK",
        "purchase_value_gbp": 5.0,
    })
    df = pd.DataFrame(records)
    cutoff = "2011-10-15 00:00:00"

    catalog, descriptions, user_items, csr, cust_map, item_map = build_catalog_and_interactions(
        df, cutoff=cutoff, min_distinct_buyers=5, active_window_days=90
    )

    assert "10001" in catalog
    assert "10002" not in catalog
    assert len(catalog) == 1
    assert csr.shape == (5, 1)
    assert csr.sum() == 5
