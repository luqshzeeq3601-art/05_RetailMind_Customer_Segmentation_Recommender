"""CLI entry point for RetailMind."""

import argparse
import json
from pathlib import Path

import yaml

from retailmind.data import clean_transactions, download_official_dataset


def load_yaml_config(config_path: str | Path) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def cmd_download(args: argparse.Namespace) -> None:
    config = load_yaml_config(args.config)
    ds = config["dataset"]
    print(f"Downloading official dataset from {ds['source_url']}...")
    provenance = download_official_dataset(
        source_url=ds["source_url"],
        raw_zip_path=ds["raw_zip_path"],
        raw_xlsx_path=ds["raw_xlsx_path"],
        provenance_path=ds["provenance_path"],
        dataset_name=ds.get("dataset_name", "UCI Online Retail"),
        license_str=ds.get("license", "Creative Commons Attribution 4.0"),
    )
    print("Dataset downloaded successfully.")
    print(f"Raw XLSX SHA-256: {provenance['raw_xlsx_sha256']}")
    print(f"Raw rows: {provenance['raw_row_count']}")
    print(f"Date range: {provenance['min_invoice_date']} to {provenance['max_invoice_date']}")


def cmd_prepare(args: argparse.Namespace) -> None:
    import pandas as pd

    config = load_yaml_config(args.config)
    ds = config["dataset"]
    cleaning_cfg = config.get("cleaning", {})
    raw_xlsx = Path(ds["raw_xlsx_path"])

    if not raw_xlsx.exists():
        print(f"Raw dataset not found at {raw_xlsx}. Running download first...")
        cmd_download(args)

    print(f"Loading raw transactions from {raw_xlsx}...")
    df_raw = pd.read_excel(raw_xlsx, engine="openpyxl")
    print(f"Loaded {len(df_raw)} raw rows. Cleaning according to 8-step specification...")

    merch_regex = cleaning_cfg.get("valid_stock_code_regex", r"^[0-9]{5}[A-Z]?$")
    df_clean, audit = clean_transactions(df_raw, merchandise_regex=merch_regex)

    processed_path = Path(ds["processed_parquet_path"])
    processed_path.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_parquet(processed_path, index=False)
    print(f"Saved {len(df_clean)} cleaned purchases to {processed_path}.")

    quality_path = Path(ds["quality_path"])
    quality_path.parent.mkdir(parents=True, exist_ok=True)
    with open(quality_path, "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2)
    print(f"Saved data quality report to {quality_path}.")
    print("Disjoint removals summary:")
    for rule, count in audit["disjoint_removals"].items():
        print(f"  - {rule}: {count:,} rows")
    print(f"Retained rows: {audit['retained_rows']:,}")
    print(f"Retained value: GBP {audit['retained_purchase_value_gbp']:,.2f}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="retailmind",
        description="RetailMind: Customer Segmentation and Product Recommender CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Download command
    p_dl = subparsers.add_parser("download", help="Download official UCI dataset")
    p_dl.add_argument("--config", default="configs/default.yaml", help="Path to config YAML")

    # Prepare command
    p_prep = subparsers.add_parser("prepare", help="Clean and prepare purchases table")
    p_prep.add_argument("--config", default="configs/default.yaml", help="Path to config YAML")

    # Train command
    p_train = subparsers.add_parser("train", help="Train models on validation or test stage")
    p_train.add_argument("--stage", choices=["validation", "test"], required=True)
    p_train.add_argument("--config", default="configs/default.yaml", help="Path to config YAML")

    # Evaluate command
    p_eval = subparsers.add_parser("evaluate", help="Evaluate models on validation or test stage")
    p_eval.add_argument("--stage", choices=["validation", "test"], required=True)
    p_eval.add_argument("--config", default="configs/default.yaml", help="Path to config YAML")

    # Freeze command
    p_freeze = subparsers.add_parser("freeze", help="Freeze selected models from validation")
    p_freeze.add_argument("--config", default="configs/default.yaml", help="Path to config YAML")

    # Recommend command
    p_rec = subparsers.add_parser("recommend", help="Get top-K recommendations for a customer")
    p_rec.add_argument("--customer-id", required=True, help="Customer ID")
    p_rec.add_argument("--top-k", type=int, default=10, help="Number of items to recommend (1-20)")
    p_rec.add_argument(
        "--mode",
        choices=["repeat_allowed", "new_items_only"],
        default="repeat_allowed",
        help="Recommendation mode",
    )
    p_rec.add_argument("--bundle", default="artifacts/release", help="Path to model bundle")

    # Monitor command
    p_mon = subparsers.add_parser("monitor", help="Run batch diagnostics between reference and current snapshots")
    p_mon.add_argument("--reference", required=True, help="Path to reference snapshot metrics JSON")
    p_mon.add_argument("--current", required=True, help="Path to current snapshot metrics JSON")
    p_mon.add_argument("--output", default="reports/drift_report.json", help="Path to output report JSON")

    # Benchmark command
    p_bm = subparsers.add_parser("benchmark", help="Measure warm recommendation latency")
    p_bm.add_argument("--bundle", default="artifacts/release", help="Path to model bundle")
    p_bm.add_argument("--top-k", type=int, default=10, help="Top K recommendations")
    p_bm.add_argument("--warmup", type=int, default=10, help="Warmup requests")
    p_bm.add_argument("--calls", type=int, default=200, help="Benchmark requests")
    p_bm.add_argument("--output", default="reports/latency.json", help="Output latency report path")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "download":
        cmd_download(args)
    elif args.command == "prepare":
        cmd_prepare(args)
    elif args.command in ("train", "evaluate", "freeze", "recommend", "monitor", "benchmark"):
        from retailmind.service_cli import dispatch_service_cli
        dispatch_service_cli(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
