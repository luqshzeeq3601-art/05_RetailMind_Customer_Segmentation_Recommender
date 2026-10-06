"""Validated data contracts, configuration schemas, and response types."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class RecommendedItem(BaseModel):
    rank: int = Field(ge=1, le=20)
    stock_code: str
    description: str
    score: float
    method: Literal["item_cf", "segment_popularity", "global_popularity"]
    reason_code: Literal["similar_to_purchase_history", "popular_in_segment", "popular_overall"]
    reason_text: str
    supporting_stock_codes: List[str] = Field(default_factory=list)
    is_fallback: bool


class RecommendationResponse(BaseModel):
    customer_id: str
    customer_status: Literal["known_active", "known_inactive", "unknown_customer"]
    segment_id: Optional[str] = None
    segment_label: Optional[str] = None
    snapshot_cutoff: str
    recommendation_mode: Literal["repeat_allowed", "new_items_only"]
    requested_k: int = Field(ge=1, le=20)
    returned_k: int = Field(ge=0, le=20)
    status: Literal["ok", "fallback_only", "insufficient_catalog", "empty_catalog"]
    fallback_count: int = Field(ge=0)
    model_version: str
    items: List[RecommendedItem]


class RecommendationRequest(BaseModel):
    customer_id: str
    top_k: int = Field(default=10, ge=1, le=20)
    mode: Literal["repeat_allowed", "new_items_only"] = "repeat_allowed"
    bundle: str = Field(default="artifacts/release")

    @field_validator("customer_id")
    @classmethod
    def validate_customer_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("customer_id must be a non-empty string")
        if len(v) > 64:
            raise ValueError("customer_id must not exceed 64 characters")
        if "/" in v or "\\" in v or ".." in v:
            raise ValueError("customer_id must not contain path traversal characters")
        return v


class CustomerProfile(BaseModel):
    customer_id: str
    recency_days: float
    frequency_invoices: int
    monetary_gbp: float
    status: Literal["known_active", "known_inactive"]
    segment_id: Optional[str] = None
    segment_label: Optional[str] = None


class SegmentSummary(BaseModel):
    segment_id: str
    segment_label: str
    customer_count: int
    customer_share: float
    median_recency: float
    median_frequency: float
    median_monetary: float
    campaign_hypothesis: str
    snapshot_cutoff: str
    version: str


class BundleManifest(BaseModel):
    bundle_version: str
    stage: Literal["validation", "test", "release"]
    snapshot_cutoff: str
    created_at: str
    source_sha256: str
    config_sha256: str
    lock_sha256: str
    selection_manifest_sha256: Optional[str] = None
    segment_algorithm: str
    segment_params: Dict[str, Any]
    recommender_algorithm: str
    recommender_params: Dict[str, Any]
    catalog_size: int
    active_customers_count: int
    known_customers_count: int
    reports: Dict[str, str] = Field(default_factory=dict)
