"""Data acquisition, provenance recording, schema validation, and cleaning pipeline."""

import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
import requests

REQUIRED_COLUMNS = [
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
    "Country",
]

DEFAULT_MERCHANDISE_REGEX = r"^[0-9]{5}[A-Z]?$"


def compute_file_sha256(file_path: Path | str) -> str:
    """Compute the SHA-256 hex digest of a local file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest().upper()


def download_official_dataset(
    source_url: str,
    raw_zip_path: Path | str,
    raw_xlsx_path: Path | str,
    provenance_path: Path | str,
    dataset_name: str = "UCI Online Retail",
    license_str: str = "Creative Commons Attribution 4.0 International (CC BY 4.0)",
) -> Dict[str, Any]:
    """Download the official UCI Online Retail dataset, verify, extract, and write provenance."""
    raw_zip = Path(raw_zip_path)
    raw_xlsx = Path(raw_xlsx_path)
    provenance = Path(provenance_path)

    raw_zip.parent.mkdir(parents=True, exist_ok=True)
    raw_xlsx.parent.mkdir(parents=True, exist_ok=True)
    provenance.parent.mkdir(parents=True, exist_ok=True)

    retrieval_time = datetime.now(timezone.utc).isoformat()

    # If raw xlsx does not exist or zip does not exist, download
    if not raw_xlsx.exists():
        response = requests.get(source_url, stream=True, timeout=60)
        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to download dataset from {source_url}, status code: {response.status_code}"
            )
        with open(raw_zip, "wb") as f:
            for chunk in response.iter_content(chunk_size=65536):
                f.write(chunk)

        # Extract xlsx from zip if it is a zip file
        if zipfile.is_zipfile(raw_zip):
            with zipfile.ZipFile(raw_zip, "r") as zip_ref:
                # Find xlsx file in zip
                xlsx_names = [n for n in zip_ref.namelist() if n.lower().endswith(".xlsx")]
                if not xlsx_names:
                    raise RuntimeError("No .xlsx file found in downloaded zip archive.")
                target_name = xlsx_names[0]
                extracted_path = zip_ref.extract(target_name, raw_zip.parent)
                # Rename if needed
                if Path(extracted_path).resolve() != raw_xlsx.resolve():
                    Path(extracted_path).replace(raw_xlsx)
        else:
            # If the downloaded file is directly the xlsx
            raw_zip.replace(raw_xlsx)

    if not raw_xlsx.exists():
        raise FileNotFoundError(f"Raw xlsx file does not exist at {raw_xlsx}")

    xlsx_sha256 = compute_file_sha256(raw_xlsx)

    # Read schema and structural stats without inspecting future outcomes
    df_raw = pd.read_excel(raw_xlsx, engine="openpyxl")
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df_raw.columns]
    if missing_cols:
        raise ValueError(f"Downloaded dataset is missing required columns: {missing_cols}")

    min_date = str(df_raw["InvoiceDate"].min())
    max_date = str(df_raw["InvoiceDate"].max())

    provenance_data = {
        "dataset_name": dataset_name,
        "source_url": source_url,
        "license": license_str,
        "retrieval_time_utc": retrieval_time,
        "raw_xlsx_path": str(raw_xlsx),
        "raw_xlsx_sha256": xlsx_sha256,
        "raw_row_count": int(len(df_raw)),
        "columns": list(df_raw.columns),
        "min_invoice_date": min_date,
        "max_invoice_date": max_date,
    }

    with open(provenance, "w", encoding="utf-8") as f:
        json.dump(provenance_data, f, indent=2)

    return provenance_data


def canonicalize_customer_id(val: Any) -> Optional[str]:
    """Canonicalize customer ID: string without .0, None if null/empty."""
    if pd.isna(val) or val is None or val == "":
        return None
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    if not s or s.lower() == "nan" or s.lower() == "none":
        return None
    return s


def clean_transactions(
    df_raw: pd.DataFrame,
    merchandise_regex: str = DEFAULT_MERCHANDISE_REGEX,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Clean raw retail transactions according to the 8 ordered rules in docs/05_DATA_SPEC.md.

    Returns:
        (df_cleaned, audit_dict)
    """
    total_raw_rows = len(df_raw)
    merch_pattern = re.compile(merchandise_regex)

    # Step 1: Canonicalize columns & parse types
    df = df_raw.copy()
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    df["InvoiceNo"] = df["InvoiceNo"].astype(str).str.strip().str.upper()
    df["StockCode"] = df["StockCode"].astype(str).str.strip().str.upper()
    df["Description"] = df["Description"].apply(
        lambda x: str(x).strip() if pd.notna(x) and str(x).strip() != "" else None
    )
    df["Country"] = df["Country"].apply(
        lambda x: str(x).strip() if pd.notna(x) and str(x).strip() != "" else "Unknown"
    )
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce")
    df["CustomerID"] = df["CustomerID"].apply(canonicalize_customer_id)

    audit: Dict[str, Any] = {
        "total_raw_rows": total_raw_rows,
        "disjoint_removals": {},
        "retained_rows": 0,
        "retained_purchase_value_gbp": 0.0,
        "anonymous_transactions": {
            "row_count": 0,
            "estimated_value_gbp": 0.0,
        },
        "excluded_merchandise_codes": {},
    }

    # Step 2: Quarantine invalid core values (missing/malformed date, invoice, stockcode, non-finite quantity/price, invalid customer id)
    # CustomerID validity check: if present, must be numeric digits
    invalid_customer = df["CustomerID"].apply(
        lambda c: c is not None and not bool(re.match(r"^[0-9]+$", c))
    )
    invalid_core = (
        df["InvoiceDate"].isna()
        | df["InvoiceNo"].isna()
        | (df["InvoiceNo"] == "")
        | df["StockCode"].isna()
        | (df["StockCode"] == "")
        | df["Quantity"].isna()
        | df["UnitPrice"].isna()
        | invalid_customer
    )
    r2_count = int(invalid_core.sum())
    audit["disjoint_removals"]["rule2_invalid_core_values"] = r2_count
    df = df[~invalid_core].copy()

    # Step 3: Remove exact duplicates across all 8 fields, retaining first
    dup_mask = df.duplicated(subset=REQUIRED_COLUMNS, keep="first")
    r3_count = int(dup_mask.sum())
    audit["disjoint_removals"]["rule3_exact_duplicates"] = r3_count
    df = df[~dup_mask].copy()

    # Step 4: Exclude missing CustomerID (keep track of count & value)
    missing_customer = df["CustomerID"].isna()
    r4_count = int(missing_customer.sum())
    anon_val = float((df.loc[missing_customer, "Quantity"] * df.loc[missing_customer, "UnitPrice"]).sum())
    audit["disjoint_removals"]["rule4_missing_customer_id"] = r4_count
    audit["anonymous_transactions"]["row_count"] = r4_count
    audit["anonymous_transactions"]["estimated_value_gbp"] = round(anon_val, 2)
    df = df[~missing_customer].copy()

    # Step 5: Exclude cancellation invoices (starts with 'C') and nonpositive quantity (Quantity <= 0)
    cancellation_or_nonpos_qty = df["InvoiceNo"].str.startswith("C") | (df["Quantity"] <= 0)
    r5_count = int(cancellation_or_nonpos_qty.sum())
    audit["disjoint_removals"]["rule5_cancellations_and_nonpositive_qty"] = r5_count
    df = df[~cancellation_or_nonpos_qty].copy()

    # Step 6: Exclude nonpositive UnitPrice (UnitPrice <= 0)
    nonpos_price = df["UnitPrice"] <= 0
    r6_count = int(nonpos_price.sum())
    audit["disjoint_removals"]["rule6_nonpositive_price"] = r6_count
    df = df[~nonpos_price].copy()

    # Step 7: Keep merchandise codes matching regex ^[0-9]{5}[A-Z]?$
    valid_merch = df["StockCode"].apply(lambda code: bool(merch_pattern.match(code)))
    excluded_merch = df[~valid_merch]
    r7_count = int((~valid_merch).sum())
    audit["disjoint_removals"]["rule7_excluded_merchandise_codes"] = r7_count

    # Track excluded code patterns and frequencies
    excluded_counts = excluded_merch["StockCode"].value_counts().to_dict()
    audit["excluded_merchandise_codes"] = {
        str(k): int(v) for k, v in list(excluded_counts.items())[:50]
    }
    df = df[valid_merch].copy()

    # Step 8: Calculate purchase_value_gbp = Quantity * UnitPrice
    df["Quantity"] = df["Quantity"].astype(int)
    df["UnitPrice"] = df["UnitPrice"].astype(float)
    df["purchase_value_gbp"] = (df["Quantity"] * df["UnitPrice"]).round(4)
    valid_purchase_val = (df["purchase_value_gbp"] > 0) & np.isfinite(df["purchase_value_gbp"])
    r8_count = int((~valid_purchase_val).sum())
    audit["disjoint_removals"]["rule8_non_positive_purchase_value"] = r8_count
    df = df[valid_purchase_val].copy()

    # Sort deterministically
    df = df.sort_values(
        by=["InvoiceDate", "InvoiceNo", "StockCode"], ascending=[True, True, True]
    ).reset_index(drop=True)

    retained_rows = len(df)
    retained_val = float(df["purchase_value_gbp"].sum())
    audit["retained_rows"] = retained_rows
    audit["retained_purchase_value_gbp"] = round(retained_val, 2)

    total_disjoint_removals = sum(audit["disjoint_removals"].values())
    assert (
        total_raw_rows == total_disjoint_removals + retained_rows
    ), f"Row reconciliation failed: {total_raw_rows} != {total_disjoint_removals} + {retained_rows}"

    return df, audit
