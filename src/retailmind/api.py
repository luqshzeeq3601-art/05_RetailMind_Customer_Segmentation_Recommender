"""FastAPI recommendation and customer segmentation microservice."""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from retailmind.contracts import RecommendationRequest, RecommendationResponse
from retailmind.service import RetailMindService

# Global service instance holder
_service: Optional[RetailMindService] = None


def get_service() -> RetailMindService:
    """Retrieve the initialized service instance."""
    global _service
    if _service is None:
        bundle_path = os.getenv("RETAILMIND_BUNDLE_DIR", "artifacts/release")
        if not Path(bundle_path).exists():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Model bundle not found at {bundle_path}. Run training pipelines first.",
            )
        _service = RetailMindService(bundle_path)
    return _service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm-load service on startup."""
    global _service
    bundle_path = os.getenv("RETAILMIND_BUNDLE_DIR", "artifacts/release")
    if Path(bundle_path).exists():
        try:
            _service = RetailMindService(bundle_path)
        except Exception:
            _service = None
    yield
    _service = None


app = FastAPI(
    title="RetailMind API",
    description="Customer Segmentation & Personalized Recommender Microservice",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.2.0"
    bundle_stage: str
    snapshot_cutoff: str
    catalog_size: int
    active_customers: int


class CustomerProfileResponse(BaseModel):
    customer_id: str
    status: str
    segment_id: Optional[str]
    segment_label: Optional[str]
    recency_days: Optional[float]
    frequency_invoices: Optional[int]
    monetary_gbp: Optional[float]


@app.get("/health", response_model=HealthResponse, tags=["Diagnostics"])
def health_check() -> HealthResponse:
    """Check service health and inspect loaded model bundle metadata."""
    srv = get_service()
    manifest = srv.manifest
    return HealthResponse(
        status="ok",
        version="0.2.0",
        bundle_stage=manifest.stage,
        snapshot_cutoff=manifest.snapshot_cutoff,
        catalog_size=manifest.catalog_size,
        active_customers=manifest.active_customers_count,
    )


@app.post("/recommend", response_model=RecommendationResponse, tags=["Recommender"])
def get_recommendations(request: RecommendationRequest) -> RecommendationResponse:
    """Generate top-K personalized product recommendations for a customer."""
    srv = get_service()
    try:
        return srv.recommend(request)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.get("/customer/{customer_id}/profile", response_model=CustomerProfileResponse, tags=["Segmentation"])
def get_customer_profile(customer_id: str) -> CustomerProfileResponse:
    """Lookup customer RFM profile and segment assignment."""
    srv = get_service()
    profile = srv.get_customer_profile(customer_id)
    if profile is None:
        return CustomerProfileResponse(
            customer_id=customer_id,
            status="unknown_customer",
            segment_id=None,
            segment_label=None,
            recency_days=None,
            frequency_invoices=None,
            monetary_gbp=None,
        )
    return CustomerProfileResponse(
        customer_id=profile.customer_id,
        status=profile.status,
        segment_id=profile.segment_id,
        segment_label=profile.segment_label,
        recency_days=profile.recency_days,
        frequency_invoices=profile.frequency_invoices,
        monetary_gbp=profile.monetary_gbp,
    )


@app.get("/segments", tags=["Segmentation"])
def get_segments() -> List[Dict[str, Any]]:
    """Retrieve all active customer segment profiles and campaign strategies."""
    srv = get_service()
    summaries = srv.get_segment_summaries()
    return [s.model_dump() for s in summaries]
