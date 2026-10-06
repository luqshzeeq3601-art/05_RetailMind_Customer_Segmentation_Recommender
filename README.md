# RetailMind: Customer Segmentation and Product Recommender

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3119/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)
[![MLflow](https://img.shields.io/badge/MLflow-Tracking-0194E2.svg)](https://mlflow.org/)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://retailmind-recommender.streamlit.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

RetailMind is an end-to-end customer intelligence system that transforms retail transaction history into **time-safe RFM customer segments** and **personalized product recommendations** with a Streamlit decision-support console and FastAPI microservice.

---

## 1. Key Measured Results

| Capability | Model | Primary Metric | Baseline Comparison | Statistical Significance |
|---|---|---|---|---|
| **Segmentation** | **K-Means ($K=3$, Yeo-Johnson)** | Silhouette: **0.3667** *(Target $\ge 0.35$ PASSED)* | Median Pairwise ARI: **0.9973** | Converged across 5 seeds; min cluster share 23.22% |
| **Personalized Recommender** | **Item-Item CF ($N=50$)** | NDCG@10: **0.1698** | Segment Pop: `0.1232` (+37.88%), Global Pop: `0.1253` (+35.50%) | 95% Bootstrap CI Diff vs Frozen Baseline: `[0.0349, 0.0585]` (paired bootstrap interval excludes zero) |
| **Recommender Hit Rate** | **Item-Item CF ($N=50$)** | Hit Rate@10: **58.54%** | Recall@10: **0.0788** (Precision@10: `0.1539`) | Full un-sampled catalog ($|C| = 2,753$, Coverage 32.0%) |
| **Inference Latency** | **Service API** | Warm p95: **3.279 ms** | Median: **0.764 ms** (200 requests) | Target $\le 200\text{ ms}$: **PASSED** |

---

## 2. Business & Commercial Impact

Translating statistical ranking metrics into tangible retail operations:

* **+41.3% Higher Product Discovery:** Personalized Item-Item CF delivers an average of **1.54 relevant suggestions per customer top-10 list** compared to **1.09** from popularity baselines (Recall@10 increased from 0.0511 to 0.0788, +54.2% relative uplift).
* **46x Greater Catalog Exposure (Offline Catalog Coverage):** Recommends **881 distinct active items** (32.0% catalog coverage) compared to only **19 items** (0.69% coverage) for segment popularity. This measures offline catalog exposure; item margins and cannibalization were not measured.
* **58.5% Purchase Prediction Hit Rate:** Nearly 6 in 10 returning shoppers receive at least one item in their top 10 that they purchase during the subsequent 28-day window.
* **Measured warm CPU latency:** Warm p95 latency of **3.28 ms** enables real-time recommendation serving on standard CPU cloud instances without requiring GPU infrastructure.

---

## 3. Customer Segments Overview

| Segment ID | Segment Label | Customer Share | Median Recency | Median Frequency | Median Monetary | Target Campaign Strategy |
|---|---|---|---|---|---|---|
| **SG01** | **Steady Active Buyers** | 39.50% | 18.0 days | 4.0 orders | £1,322.90 | Category cross-sell recommendations and volume discounts to boost basket size |
| **SG02** | **Recent New / Occasional Buyers** | 23.28% | 17.0 days | 1.0 order | £338.71 | Nurture sequence, category discovery recommendations |
| **SG03** | **Dormant / Low Engagement** | 37.22% | 108.0 days | 1.0 order | £301.03 | Re-engagement win-back discounts, seasonal bestsellers |

---

## 4. Quickstart & Execution Commands

### 4.1 Local Environment Setup

```powershell
Set-Location 'C:\Users\ZeeqRyz\Desktop\Ai-ML\Machine Learning Projects\05_RetailMind_Customer_Segmentation_Recommender'
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
```

### 4.2 Pipeline Workflow & MLflow Tracking

```powershell
# 1. Download official UCI dataset & record SHA-256 provenance
.\.venv\Scripts\python.exe -m retailmind.cli download --config configs/default.yaml

# 2. Clean transactions & generate data quality audit
.\.venv\Scripts\python.exe -m retailmind.cli prepare --config configs/default.yaml

# 3. Train validation candidates & log metrics to SQLite MLflow
.\.venv\Scripts\python.exe -m retailmind.cli train --stage validation --config configs/default.yaml

# 4. Freeze validation selection into immutable manifest
.\.venv\Scripts\python.exe -m retailmind.cli freeze --config configs/default.yaml

# 5. Refit frozen algorithms on test cutoff & evaluate 28-day holdout
.\.venv\Scripts\python.exe -m retailmind.cli train --stage test --config configs/default.yaml

# 6. Launch MLflow UI to inspect logged parameters, metrics & artifacts
.\.venv\Scripts\python.exe -m mlflow ui --backend-store-uri sqlite:///mlflow.db
```

### 4.3 Serving Interfaces (FastAPI & Streamlit)

```powershell
# Launch FastAPI REST microservice (Swagger UI: http://localhost:8000/docs)
.\.venv\Scripts\python.exe -m uvicorn retailmind.api:app --reload --port 8000

# Generate single-customer recommendation via CLI
.\.venv\Scripts\python.exe -m retailmind.cli recommend --customer-id 17850 --top-k 10 --bundle artifacts/release

# Launch Streamlit analyst dashboard
.\.venv\Scripts\python.exe -m streamlit run app/dashboard.py
```

### 4.4 Verification & Quality Gates

```powershell
# Run full pytest test suite (31 tests passing)
.\.venv\Scripts\python.exe -m pytest -q

# Run Ruff linter
.\.venv\Scripts\python.exe -m ruff check .

# Run real-browser Playwright verification
.\.venv\Scripts\python.exe tests/verify_browser.py
```

### 4.5 Streamlit Community Cloud Deployment

1. Fork or push this repository to your GitHub account (`luqshzeeq3601-art/05_RetailMind_Customer_Segmentation_Recommender`).
2. Navigate to [share.streamlit.io](https://share.streamlit.io/) and click **New app**.
3. Select repository: `luqshzeeq3601-art/05_RetailMind_Customer_Segmentation_Recommender`, Branch: `master`, Main file path: `app/dashboard.py`.
4. Click **Deploy!** The release bundle (`artifacts/release/`) is committed in Git and loads instantly without running training in the cloud.

### 4.6 Docker Container Execution

```powershell
# Build container image
docker build -t retailmind:local .

# Run container with release bundle mounted read-only
docker run --rm -p 8501:8501 --mount "type=bind,source=$((Get-Location).Path)\artifacts\release,target=/app/artifacts/release,readonly" retailmind:local
```

---

## 5. Architecture & Technical Design

```
RetailMind Architecture:
├── Raw UCI Excel Data (541,909 rows)
├── 8-Step Data Cleaning Pipeline (390,859 eligible purchases retained)
├── Chronological Time Splitting (Validation: <2011-10-15, Test: <2011-11-12)
├── Time-Safe RFM Snapshot Engine (180-day active window, distinct invoices)
├── Segment Estimator (K-Means K=3, Yeo-Johnson PowerTransform + StandardScaler)
├── Sparse Recommender Engine:
│   ├── Item-Item Cosine Similarity (CSR sparse matrices, 256-block cosine)
│   ├── Bounded Neighbor Index (Top 50 neighbors, min 2 co-buyers)
│   ├── Segment Popularity Fallback (90-day buyer activity in segment)
│   └── Global Popularity Fallback (90-day buyer activity across catalog)
├── Shared Service Layer (Request validation, status precedence, safe CSV export)
├── Experiment Tracking (SQLite-backed MLflow with run params, metrics & artifacts)
└── Production Interfaces:
    ├── FastAPI REST Microservice (retailmind.api, Swagger UI /docs)
    ├── Command Line Interface (retailmind.cli)
    ├── Streamlit Intelligence Dashboard (app/dashboard.py)
    └── Automated Batch Monitoring (retailmind.monitoring)
```

---

## 6. Documentation Map

- [Start Here Guide](docs/00_START_HERE.md) — Reading order, execution contract, and verification rules.
- [Product Requirements Document (PRD)](docs/02_PRD.md) — Functional and non-functional requirements.
- [Technical Design](docs/04_TECHNICAL_DESIGN.md) — System architecture, module interfaces, and artifact structure.
- [Data Specification](docs/05_DATA_SPEC.md) — 8-step cleaning rules, temporal split protocol, and RFM definitions.
- [Experiment & Evaluation Plan](docs/06_EXPERIMENT_PLAN.md) — Candidate models, selection rules, and ranking metrics.
- [Validation & Delivery Report](reports/validation.md) — Full requirements verification matrix and benchmark results.
- [Evaluation Report](reports/evaluation.md) — Comprehensive model performance analysis and bootstrap CIs.
- [Model Card](docs/MODEL_CARD.md) — Measured model metadata, performance metrics, and analytical limitations.
- [Decisions Log](docs/08_DECISIONS_LOG.md) — Chronological architecture and design decision records.
- [Progress Log](docs/09_PROGRESS_LOG.md) — Dated implementation entries and verification logs.
- [License](LICENSE) — MIT Software License & CC BY 4.0 Dataset Attribution.
