"""Tests for data cleaning pipeline and schema contracts."""

from pathlib import Path

import pandas as pd

from retailmind.data import canonicalize_customer_id, clean_transactions


def test_canonicalize_customer_id() -> None:
    assert canonicalize_customer_id(17850.0) == "17850"
    assert canonicalize_customer_id("17850.0") == "17850"
    assert canonicalize_customer_id("17850") == "17850"
    assert canonicalize_customer_id(None) is None
    assert canonicalize_customer_id(float("nan")) is None
    assert canonicalize_customer_id("") is None


def test_clean_transactions_synthetic_fixture() -> None:
    fixture_path = Path("tests/fixtures/transactions.csv")
    df_raw = pd.read_csv(fixture_path)
    total_raw = len(df_raw)

    df_clean, audit = clean_transactions(df_raw)

    # 1. Total rows must reconcile
    total_removals = sum(audit["disjoint_removals"].values())
    assert audit["total_raw_rows"] == total_raw
    assert total_raw == total_removals + len(df_clean)

    # 2. Rule 2 caught invalid core rows
    assert audit["disjoint_removals"]["rule2_invalid_core_values"] >= 4

    # 3. Rule 3 caught exact duplicates
    assert audit["disjoint_removals"]["rule3_exact_duplicates"] >= 1

    # 4. Rule 4 caught missing CustomerID
    assert audit["disjoint_removals"]["rule4_missing_customer_id"] >= 1
    assert audit["anonymous_transactions"]["row_count"] >= 1

    # 5. Rule 5 caught cancellations & negative quantities
    assert audit["disjoint_removals"]["rule5_cancellations_and_nonpositive_qty"] >= 2

    # 6. Rule 6 caught zero price
    assert audit["disjoint_removals"]["rule6_nonpositive_price"] >= 1

    # 7. Rule 7 caught non-merchandise codes (POST, D, BANK CHARGES)
    assert audit["disjoint_removals"]["rule7_excluded_merchandise_codes"] >= 3
    assert "POST" in audit["excluded_merchandise_codes"] or "D" in audit["excluded_merchandise_codes"]

    # 8. All retained rows have valid positive purchase value and match regex
    assert (df_clean["purchase_value_gbp"] > 0).all()
    assert df_clean["CustomerID"].notna().all()
    assert (~df_clean["InvoiceNo"].str.startswith("C")).all()
    assert (df_clean["Quantity"] > 0).all()
    assert (df_clean["UnitPrice"] > 0).all()
