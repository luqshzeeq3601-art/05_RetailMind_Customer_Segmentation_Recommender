"""Tests for temporal split protocol and data isolation."""

import pandas as pd

from retailmind.features import build_snapshot_rfm


def test_temporal_cutoff_boundary_isolation() -> None:
    # Build dataset with records on, before, and after cutoff
    cutoff_str = "2011-10-15 00:00:00"
    cutoff = pd.to_datetime(cutoff_str)

    records = [
        {"InvoiceNo": "1", "StockCode": "10001", "Quantity": 1, "InvoiceDate": pd.to_datetime("2011-10-14 23:59:59"), "UnitPrice": 10.0, "CustomerID": "C1", "Country": "UK", "purchase_value_gbp": 10.0},
        # Record exactly at cutoff should NOT be in history
        {"InvoiceNo": "2", "StockCode": "10001", "Quantity": 1, "InvoiceDate": pd.to_datetime("2011-10-15 00:00:00"), "UnitPrice": 10.0, "CustomerID": "C1", "Country": "UK", "purchase_value_gbp": 10.0},
        # Record after cutoff
        {"InvoiceNo": "3", "StockCode": "10001", "Quantity": 1, "InvoiceDate": pd.to_datetime("2011-10-15 00:00:01"), "UnitPrice": 10.0, "CustomerID": "C1", "Country": "UK", "purchase_value_gbp": 10.0},
    ]
    df = pd.DataFrame(records)

    profiles, meta = build_snapshot_rfm(df, cutoff=cutoff, rfm_window_days=180)
    prof_c1 = profiles[profiles["customer_id"] == "C1"].iloc[0]

    # Frequency should be 1 (only Invoice 1 before cutoff)
    assert prof_c1["frequency_invoices"] == 1
    assert prof_c1["monetary_gbp"] == 10.0
