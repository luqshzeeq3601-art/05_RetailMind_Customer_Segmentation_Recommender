"""Shared recommendation and segmentation service for CLI, Dashboard, and Benchmarking."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import pandas as pd

from retailmind.contracts import (
    BundleManifest,
    CustomerProfile,
    RecommendationRequest,
    RecommendationResponse,
    SegmentSummary,
)


def escape_csv_formula(val: Any) -> Any:
    """Protect cells against spreadsheet formula injection."""
    if isinstance(val, str) and val and val[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{val}"
    return val


class RetailMindService:
    """Loads and serves trusted RetailMind artifact bundles."""

    def __init__(self, bundle_dir: str | Path) -> None:
        self.bundle_dir = Path(bundle_dir)
        if not self.bundle_dir.exists():
            raise FileNotFoundError(f"Bundle directory does not exist: {self.bundle_dir}")

        manifest_path = self.bundle_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"manifest.json missing in bundle: {self.bundle_dir}")

        with open(manifest_path, "r", encoding="utf-8") as f:
            self.manifest = BundleManifest.model_validate_json(f.read())

        # Load tables
        self.df_profiles = pd.read_parquet(self.bundle_dir / "customer_profiles.parquet")
        self.df_segment_summaries = pd.read_parquet(self.bundle_dir / "segment_summaries.parquet")

        # Map profiles for fast lookup
        self.profile_lookup: Dict[str, Dict[str, Any]] = {}
        for _, row in self.df_profiles.iterrows():
            self.profile_lookup[str(row["customer_id"])] = row.to_dict()

        # Load catalog
        with open(self.bundle_dir / "catalog.json", "r", encoding="utf-8") as f:
            catalog_data = json.load(f)
            self.catalog_items: List[str] = catalog_data["catalog_items"]
            self.item_descriptions: Dict[str, str] = catalog_data["item_descriptions"]

        # Load customer purchase history
        with open(self.bundle_dir / "customer_history.json", "r", encoding="utf-8") as f:
            self.customer_history: Dict[str, List[str]] = json.load(f)

        # Load models
        models_data = joblib.load(self.bundle_dir / "models.joblib")
        self.segmenter = models_data["segmenter"]
        self.scaler = models_data["scaler"]
        self.global_pop = models_data["global_pop"]
        self.seg_pop = models_data["seg_pop"]
        self.cf_model = models_data["cf_model"]

    def get_customer_profile(self, customer_id: str) -> Optional[CustomerProfile]:
        """Lookup customer profile if known."""
        cid = customer_id.strip()
        if cid in self.profile_lookup:
            row = self.profile_lookup[cid]
            return CustomerProfile(
                customer_id=cid,
                recency_days=float(row["recency_days"]),
                frequency_invoices=int(row["frequency_invoices"]),
                monetary_gbp=float(row["monetary_gbp"]),
                status=row["status"],
                segment_id=row.get("segment_id"),
                segment_label=row.get("segment_label"),
            )
        return None

    def get_segment_summaries(self) -> List[SegmentSummary]:
        """Return all segment summary profiles."""
        summaries = []
        for _, row in self.df_segment_summaries.iterrows():
            summaries.append(
                SegmentSummary(
                    segment_id=row["segment_id"],
                    segment_label=row["segment_label"],
                    customer_count=int(row["customer_count"]),
                    customer_share=float(row["customer_share"]),
                    median_recency=float(row["median_recency"]),
                    median_frequency=float(row["median_frequency"]),
                    median_monetary=float(row["median_monetary"]),
                    campaign_hypothesis=row["campaign_hypothesis"],
                    snapshot_cutoff=self.manifest.snapshot_cutoff,
                    version=self.manifest.bundle_version,
                )
            )
        return summaries

    def recommend(self, request: RecommendationRequest) -> RecommendationResponse:
        """Produce deterministic recommendations for a customer under requested mode and K."""
        cid = request.customer_id.strip()
        top_k = request.top_k
        mode = request.mode

        profile = self.get_customer_profile(cid)
        if profile is not None:
            cust_status = profile.status
            seg_id = profile.segment_id
            seg_label = profile.segment_label
        else:
            cust_status = "unknown_customer"
            seg_id = None
            seg_label = None

        # Handle unknown customer: global popularity
        if cust_status == "unknown_customer":
            raw_items = self.global_pop.recommend(
                k=top_k,
                exclude_items=set(),
                item_descriptions=self.item_descriptions,
            )
        elif self.cf_model is not None:
            raw_items = self.cf_model.recommend_for_customer(
                customer_id=cid,
                k=top_k,
                segment_id=seg_id,
                seg_pop=self.seg_pop,
                global_pop=self.global_pop,
                mode=mode,
                item_descriptions=self.item_descriptions,
            )
        else:
            # Fallback to segment popularity if CF is not in bundle
            exclude = set(self.customer_history.get(cid, [])) if mode == "new_items_only" else set()
            raw_items = self.seg_pop.recommend(
                segment_id=seg_id,
                k=top_k,
                global_pop=self.global_pop,
                exclude_items=exclude,
                item_descriptions=self.item_descriptions,
            )

        returned_k = len(raw_items)
        fallback_count = sum(1 for item in raw_items if item.is_fallback)

        # Determine status precedence
        if returned_k == 0:
            status = "empty_catalog"
        elif returned_k < top_k:
            status = "insufficient_catalog"
        elif fallback_count == returned_k:
            status = "fallback_only"
        else:
            status = "ok"

        return RecommendationResponse(
            customer_id=cid,
            customer_status=cust_status,
            segment_id=seg_id,
            segment_label=seg_label,
            snapshot_cutoff=self.manifest.snapshot_cutoff,
            recommendation_mode=mode,
            requested_k=top_k,
            returned_k=returned_k,
            status=status,
            fallback_count=fallback_count,
            model_version=self.manifest.bundle_version,
            items=raw_items,
        )

    def export_recommendations_csv(self, response: RecommendationResponse) -> str:
        """Export recommendation items table as safe CSV."""
        rows = []
        for item in response.items:
            rows.append(
                {
                    "rank": item.rank,
                    "stock_code": escape_csv_formula(item.stock_code),
                    "description": escape_csv_formula(item.description),
                    "score": item.score,
                    "method": item.method,
                    "reason_code": item.reason_code,
                    "reason_text": escape_csv_formula(item.reason_text),
                    "supporting_stock_codes": json.dumps(item.supporting_stock_codes),
                    "is_fallback": item.is_fallback,
                    "customer_id": escape_csv_formula(response.customer_id),
                    "customer_status": response.customer_status,
                    "snapshot_cutoff": response.snapshot_cutoff,
                    "recommendation_mode": response.recommendation_mode,
                    "model_version": response.model_version,
                    "fallback_count": response.fallback_count,
                }
            )
        df = pd.DataFrame(rows)
        return df.to_csv(index=False)

    def export_segments_csv(self) -> str:
        """Export segment summaries table as safe CSV."""
        df = self.df_segment_summaries.copy()
        for col in ["segment_label", "campaign_hypothesis"]:
            if col in df.columns:
                df[col] = df[col].apply(escape_csv_formula)
        return df.to_csv(index=False)
