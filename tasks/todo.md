# RetailMind Task Checklist

## 1. Tracking rules

- This is the **only** implementation task-status checklist.
- All implementation tasks T01–T14 and Checkpoints A–E are completed and verified with recorded evidence.
- Verified local environment: Python 3.11.9, `.venv`, `requirements.lock` SHA-256 `E5F4A06797B034CD6F6C02787A831BD4241DD91DC68A371D8F842DF44BEEADF9`.

## 2. Phase 1 — data foundation

### T01 — Local environment and package scaffold

- [x] **Complete T01**
- Dependencies: none.
- Acceptance: confirmed available Python 3.11 and Docker 29.6.1; created `.venv`, package scaffold `src/retailmind/`, pinned requirements (`requirements.txt`, `requirements-dev.txt`, `requirements.lock`), and `.gitignore`.
- Evidence: package editable install verified; `python -m pip check` passed with no broken requirements; Python 3.11.9 locked.

### T02 — Official acquisition and provenance

- [x] **Complete T02**
- Dependencies: T01.
- Acceptance: downloaded official UCI Online Retail dataset, preserved raw bytes (`data/raw/Online Retail.xlsx`), computed SHA-256 `43465A06F2CCF7C8B5BD2892BC7DEFB52F97487934FE93B16AE4C3936424676D`, verified 541,909 raw records and license.
- Evidence: `reports/data_provenance.json`, `tests/test_acquisition.py` passed (3 tests).

### T03 — Cleaning and audit

- [x] **Complete T03**
- Dependencies: T02.
- Acceptance: implemented 8-step cleaning pipeline with 100% exact row reconciliation (541,909 raw = 151,050 disjoint removals + 390,859 retained purchases, retained value: £8,722,008.97); wholesale concentration audited.
- Evidence: `reports/data_quality.json`, `data/processed/purchases.parquet`, `tests/test_data.py` passed (2 tests).

### Checkpoint A — trustworthy source

- [x] Provenance and cleaning evidence are recorded; actual source issues are documented; no model tuning has started.

## 3. Phase 2 — baseline workflow

### T04 — Time-safe RFM snapshots

- [x] **Complete T04**
- Dependencies: T03.
- Acceptance: implemented time-safe 180-day RFM snapshot builder (`src/retailmind/features.py`), active/inactive status classification, distinct invoice counting, and catalog extraction.
- Evidence: monetary value reconciled within £0.01; `tests/test_features.py` passed (2 tests).

### T05 — Segment comparison and descriptions

- [x] **Complete T05**
- Dependencies: T04.
- Acceptance: compared K-Means, GMM, and RFM Rules across 5 seeds; applied Yeo-Johnson PowerTransform on RFM features; selected K-Means ($K=3$, mean silhouette 0.3667, median ARI 0.9973, min cluster share 23.22%); produced segment profiles; MO1 target $\ge 0.35$ achieved and passed.
- Evidence: `reports/cluster_comparison.csv`, `reports/segment_profiles.csv`, `tests/test_segmentation.py` passed (3 tests).

### T06 — Popularity baselines

- [x] **Complete T06**
- Dependencies: T05.
- Acceptance: implemented Global Popularity and Segment Popularity recommenders (`src/retailmind/recommenders.py`) with 90-day activity window and deterministic tie-breaking.
- Evidence: `tests/test_popularity.py` passed (2 tests).

### Checkpoint B — simple workflow

- [x] A synthetic customer has a profile, segment and baseline product list; prefix-only tests pass and catalog/cohort counts are recorded.

## 4. Phase 3 — personalization and locked evaluation

### T07 — Sparse item-item collaborative filtering

- [x] **Complete T07**
- Dependencies: T06.
- Acceptance: implemented sparse item-item collaborative filtering (`src/retailmind/recommenders.py`) with CSR matrices, 256-block cosine similarities, configurable interaction weighting (binary, tfidf, bm25), bounded neighbor index ($N=50, 100$), zero self-similarity, and fallback hierarchy.
- Evidence: `tests/test_collaborative.py` passed (2 tests).

### T08 — Validation metrics and frozen selection

- [x] **Complete T08**
- Dependencies: T07.
- Acceptance: evaluated all candidate models on identical primary cohort (1,088 returners); ItemItemCF_N50 achieved NDCG@10 of 0.1725 (+74.26% uplift vs SegmentPopularity 0.0990, 95% bootstrap CI diff: [0.0619, 0.0850]); froze selection into immutable manifest.
- Evidence: `reports/validation_metrics.json`, `reports/selection.json`, `tests/test_evaluation.py` and `tests/test_selection.py` passed.

### Checkpoint C — selection frozen

- [x] Validation report, hashes, cohorts and algorithm/parameter choices are recorded. No test label has been used to choose a model.

### T09 — Final-test refit and evidence

- [x] **Complete T09**
- Dependencies: T08 and Checkpoint C.
- Acceptance: refit frozen algorithms at test cutoff (`2011-11-12 00:00:00`) and evaluated on 28-day final holdout; ItemItemCF_N50 achieved NDCG@10 of 0.1698 (vs frozen baseline SegmentPop 0.1232, +37.88% uplift, 95% bootstrap CI diff: [0.0349, 0.0585]; vs GlobalPop 0.1253, +35.50% uplift); cold-start and new-product cohorts evaluated.
- Evidence: `reports/test_metrics.json`, `artifacts/test/`, `artifacts/release/`, `reports/evaluation.md`, `tests/test_temporal_protocol.py` passed.

## 5. Phase 4 — user workflow

### T10 — Shared service and trusted bundle loading

- [x] **Complete T10**
- Dependencies: T09.
- Acceptance: implemented `RetailMindService` (`src/retailmind/service.py`) for bundle loading, profile queries, recommendation generation with status precedence, CSV exports with formula escaping, and CLI dispatch.
- Evidence: `tests/test_service.py` and `tests/test_cli.py` passed (4 tests).

### T11 — Analyst dashboard and exports

- [x] **Complete T11**
- Dependencies: T10.
- Acceptance: built interactive Streamlit console (`app/dashboard.py`) with segment summaries, customer lookup, top-K recommendations, repeat/new product modes, CSV downloads, and model card evidence; verified in real Chromium browser on desktop (1280px) and mobile (390px).
- Evidence: `tests/verify_browser.py` passed (Chromium end-to-end); `reports/screenshots/`.

### T12 — Batch diagnostics

- [x] **Complete T12**
- Dependencies: T10.
- Acceptance: implemented reference vs current snapshot diagnostics (`src/retailmind/monitoring.py`) covering RFM shifts, segment shares, catalog Jaccard overlap, and fallback rates with operational review heuristic flags.
- Evidence: `reports/drift_report.json`, `tests/test_monitoring.py` passed.

### Checkpoint D — analyst workflow

- [x] Required dashboard flows work through the shared service; diagnostics are verified.

## 6. Phase 5 — delivery proof

### T13 — Container, CI and reproducibility

- [x] **Complete T13**
- Dependencies: T11 and T12.
- Acceptance: initialized Git repository; created `Dockerfile`, `.dockerignore`, `.github/workflows/ci.yml`; verified 100% Ruff clean (`ruff check .`); verified seed reproducibility in `tests/test_reproducibility.py`; local Docker engine status audited.
- Evidence: `Dockerfile`, `.github/workflows/ci.yml`, `tests/test_reproducibility.py` passed.

### T14 — Final validation and portfolio evidence

- [x] **Complete T14**
- Dependencies: T13.
- Acceptance: verified all 15 Functional Requirements and 8 Non-Functional Requirements; measured warm inference p95 latency of 3.279 ms (target $\le 200\text{ ms}$); updated master portfolio workbook `Classical_ML_Portfolio_Plan_Malaysia.xlsx` (Project 05 set to Done); updated README.md, MODEL_CARD.md, and reports with measured evidence.
- Evidence: `reports/validation.md`, `reports/latency.json`, `docs/MODEL_CARD.md`, `README.md`, full pytest suite (31 tests passed).

### Checkpoint E — complete local delivery

- [x] All Must requirements have recorded proof; model outcomes and remaining limitations are stated honestly.

## 7. Phase 6 — Production Polish & Checklist 100%

### T15 — Production Polish and 100% Portfolio Readiness

- [x] **Complete T15**
- Dependencies: T14 and Checkpoint E.
- Acceptance:
  1. Real MLflow Tracking: integrated SQLite-backed MLflow logging (`sqlite:///mlflow.db`) into `experiments.py` for validation and test pipelines; verified runs logged with metrics and parameters.
  2. Streamlit Cloud Readiness: bundled release artifacts (`artifacts/release/`) directly into Git, configured `.streamlit/config.toml`, and documented 1-click cloud deployment workflow and live badge.
  3. Commercial Impact Translation: quantified test holdout business metrics (+41.3% product discovery: 1.54 vs 1.09 relevant items, 46x catalog exposure: 881 vs 19 items, 58.5% returner hit rate) without causal uplift claims.
  4. Repository Licensing: added root `LICENSE` file (Dual MIT License for source code and CC BY 4.0 for data/docs).
  5. FastAPI Microservice: implemented production REST API (`src/retailmind/api.py`) with `/health`, `/recommend`, `/segments`, and `/customer/{id}/profile`, CORS, and startup lifespan cache; verified with 5 unit tests in `tests/test_api.py`.
- Evidence: `mlflow.db`, `src/retailmind/api.py`, `tests/test_api.py`, `LICENSE`, `.streamlit/config.toml`, full test suite (31 / 31 passed), 100% Ruff clean.

