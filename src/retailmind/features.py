"""Time-safe feature engineering: RFM profiles, customer states, and catalog snapshot extraction."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix


def build_snapshot_rfm(
    df_purchases: pd.DataFrame,
    cutoff: str | datetime,
    rfm_window_days: int = 180,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Build time-safe RFM profiles strictly before the cutoff timestamp.

    Args:
        df_purchases: Cleaned purchases dataframe.
        cutoff: Exclusive cutoff timestamp.
        rfm_window_days: Number of days for the active RFM window (default: 180).

    Returns:
        (df_profiles, metadata_dict)
    """
    cutoff_dt = pd.to_datetime(cutoff)
    rfm_start_dt = cutoff_dt - timedelta(days=rfm_window_days)

    # Strictly prior history
    history = df_purchases[df_purchases["InvoiceDate"] < cutoff_dt].copy()
    if history.empty:
        raise ValueError(f"No transactions found before cutoff {cutoff_dt}")

    # RFM window history
    rfm_history = history[history["InvoiceDate"] >= rfm_start_dt].copy()

    # All known customers prior to cutoff
    all_known_customers = sorted(history["CustomerID"].unique().tolist())
    active_customers = sorted(rfm_history["CustomerID"].unique().tolist())
    active_set = set(active_customers)
    inactive_customers = [c for c in all_known_customers if c not in active_set]

    # Compute latest purchase across all history (for recency)
    latest_all = history.groupby("CustomerID")["InvoiceDate"].max()

    # Active customer aggregations
    active_grouped = rfm_history.groupby("CustomerID")
    active_freq = active_grouped["InvoiceNo"].nunique()
    active_monetary = active_grouped["purchase_value_gbp"].sum().round(4)
    active_latest = active_grouped["InvoiceDate"].max()

    profiles: List[Dict[str, Any]] = []

    # Process active customers
    for cid in active_customers:
        latest_dt = active_latest[cid]
        recency_days = float(np.floor((cutoff_dt - latest_dt).total_seconds() / 86400.0))
        freq = int(active_freq[cid])
        monetary = float(active_monetary[cid])
        profiles.append(
            {
                "customer_id": str(cid),
                "recency_days": recency_days,
                "frequency_invoices": freq,
                "monetary_gbp": monetary,
                "status": "known_active",
            }
        )

    # Process inactive customers
    for cid in inactive_customers:
        latest_dt = latest_all[cid]
        recency_days = float(np.floor((cutoff_dt - latest_dt).total_seconds() / 86400.0))
        profiles.append(
            {
                "customer_id": str(cid),
                "recency_days": recency_days,
                "frequency_invoices": 0,
                "monetary_gbp": 0.0,
                "status": "known_inactive",
            }
        )

    df_profiles = pd.DataFrame(profiles)
    df_profiles = df_profiles.sort_values("customer_id").reset_index(drop=True)

    # Value reconciliation check:
    total_active_monetary = float(df_profiles[df_profiles["status"] == "known_active"]["monetary_gbp"].sum())
    total_rfm_history_val = float(rfm_history["purchase_value_gbp"].sum())
    assert abs(total_active_monetary - total_rfm_history_val) < 0.05, (
        f"RFM monetary sum ({total_active_monetary:.2f}) does not match "
        f"window transaction sum ({total_rfm_history_val:.2f})"
    )

    metadata = {
        "cutoff": str(cutoff_dt),
        "rfm_start": str(rfm_start_dt),
        "total_known_customers": len(all_known_customers),
        "active_customers": len(active_customers),
        "inactive_customers": len(inactive_customers),
        "total_window_monetary_gbp": round(total_active_monetary, 2),
    }

    return df_profiles, metadata


def build_catalog_and_interactions(
    df_purchases: pd.DataFrame,
    cutoff: str | datetime,
    min_distinct_buyers: int = 5,
    active_window_days: int = 90,
) -> Tuple[List[str], Dict[str, str], pd.DataFrame, csr_matrix, Dict[str, int], Dict[str, int]]:
    """Extract eligible product catalog and binary customer-item CSR interaction matrix.

    Eligibility rules:
    1. Bought before cutoff.
    2. Distinct buyers before cutoff >= min_distinct_buyers (5).
    3. At least 1 purchase in [cutoff - 90 days, cutoff).

    Returns:
        catalog_items: List of StockCodes
        item_descriptions: Dict[StockCode, latest Description]
        df_interactions: DataFrame of (CustomerID, StockCode)
        interaction_csr: Sparse binary CSR matrix (shape: n_known_customers, n_catalog_items)
        customer_to_idx: Dict[CustomerID, row_idx]
        item_to_idx: Dict[StockCode, col_idx]
    """
    cutoff_dt = pd.to_datetime(cutoff)
    active_window_start = cutoff_dt - timedelta(days=active_window_days)

    history = df_purchases[df_purchases["InvoiceDate"] < cutoff_dt].copy()
    if history.empty:
        raise ValueError(f"No transactions found before cutoff {cutoff_dt}")

    # Distinct buyers before cutoff
    buyer_counts = history.groupby("StockCode")["CustomerID"].nunique()
    support_mask = buyer_counts >= min_distinct_buyers
    support_items = set(buyer_counts[support_mask].index)

    # 90-day activity
    recent_history = history[history["InvoiceDate"] >= active_window_start]
    recent_items = set(recent_history["StockCode"].unique())

    eligible_items_set = support_items.intersection(recent_items)
    catalog_items = sorted(list(eligible_items_set))

    # Descriptions: latest non-empty description before cutoff
    desc_history = history[history["Description"].notna() & (history["Description"] != "")].copy()
    # Sort by InvoiceDate, InvoiceNo, Description to break ties deterministically
    desc_history = desc_history.sort_values(
        by=["InvoiceDate", "InvoiceNo", "Description"], ascending=[True, True, True]
    )
    latest_desc_df = desc_history.drop_duplicates(subset=["StockCode"], keep="last")
    item_descriptions = dict(zip(latest_desc_df["StockCode"], latest_desc_df["Description"]))

    # Fill any missing catalog description with stock code
    for sc in catalog_items:
        if sc not in item_descriptions or not item_descriptions[sc]:
            item_descriptions[sc] = str(sc)

    # Known customers before cutoff
    all_customers = sorted(history["CustomerID"].unique().tolist())
    customer_to_idx = {cid: idx for idx, cid in enumerate(all_customers)}
    item_to_idx = {sc: idx for idx, sc in enumerate(catalog_items)}

    # Filter history to eligible catalog items
    catalog_history = history[history["StockCode"].isin(eligible_items_set)]
    user_item_pairs = (
        catalog_history[["CustomerID", "StockCode"]].drop_duplicates().sort_values(["CustomerID", "StockCode"])
    )

    row_indices = [customer_to_idx[cid] for cid in user_item_pairs["CustomerID"]]
    col_indices = [item_to_idx[sc] for sc in user_item_pairs["StockCode"]]
    data = np.ones(len(row_indices), dtype=np.float32)

    n_users = len(all_customers)
    n_items = len(catalog_items)
    interaction_csr = csr_matrix((data, (row_indices, col_indices)), shape=(n_users, n_items))

    return (
        catalog_items,
        item_descriptions,
        user_item_pairs,
        interaction_csr,
        customer_to_idx,
        item_to_idx,
    )
