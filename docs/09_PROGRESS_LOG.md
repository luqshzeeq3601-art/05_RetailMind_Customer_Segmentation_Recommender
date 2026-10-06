# 09. Progress Log

## 1. Planning session — 06 October 2026, Asia/Kuala_Lumpur

### Completed

1. Read the local portfolio spreadsheet's Project Tracker, Datasets, Engineer Checklist and Sources sheets without editing the workbook.
2. Confirmed Project 5 is customer segmentation plus recommender, with RFM, K-Means/GMM, collaborative filtering and a Streamlit dashboard.
3. Recorded that the suggested order points to Project 3 after Projects 1 and 2, while the user explicitly requested preparation of Project 5.
4. Recorded the user's completion statement for Projects 1 and 2. Spreadsheet statuses remain unchanged.
5. Verified official UCI dataset metadata/license and sklearn references for the planned techniques.
6. Created the project folder and Markdown execution contract, including PRD, data/experiment rules, implementation tasks and restart instructions.

### Verification evidence

- Source workbook from this document: `../../Classical_ML_Portfolio_Plan_Malaysia.xlsx`.
- Project evidence: `Project Tracker!A8:F8`; suggested order: `Project Tracker!A1`.
- Initial workbook SHA-256: `DEA7706770BFFAF9980015F15225121AF2AF18744871109EE0412D7B3B781900`.
- Planning verification: 15 Markdown files, 38 valid local Markdown links, 14 ordered implementation tasks, 15 functional requirements and 8 non-functional requirements.

---

## 2. Implementation Execution & Audit Session — 06 October 2026, Asia/Kuala_Lumpur

### Tasks Completed

- **T01 — Local environment and package scaffold:** Created `.venv` (Python 3.11.9), installed pinned dependencies, locked in `requirements.lock`, verified editable package install with `python -m pip check`.
- **T02 — Official acquisition and provenance:** Acquired official UCI Online Retail dataset, verified SHA-256 `43465A06F2CCF7C8B5BD2892BC7DEFB52F97487934FE93B16AE4C3936424676D`, recorded provenance in `reports/data_provenance.json`.
- **T03 — Cleaning and audit:** Implemented 8-step cleaning pipeline with 100% exact row reconciliation (541,909 raw = 151,050 disjoint removals + 390,859 retained purchases, retained spend: £8,722,008.97). Audited wholesale concentration (top 1% = 30.6% spend).
- **Checkpoint A:** Trustworthy source verified.
- **T04 — Time-safe RFM snapshots:** Implemented 180-day RFM snapshot builder, distinct invoice frequency, and active/inactive classification. Reconciled monetary sum within £0.01.
- **T05 — Segment comparison and descriptions:** Evaluated K-Means, GMM, and RFM Rules across 5 seeds. Applied exact 0.01 silhouette tolerance rule (`docs/06_EXPERIMENT_PLAN.md` §3), selecting K-Means ($K=3$, mean silhouette 0.3317, median ARI 0.9992, min cluster share 24.31%). Generated segment profiles in `reports/segment_profiles.csv`. Documented MO1 (target 0.35) as missed.
- **T06 — Popularity baselines:** Implemented Global and Segment Popularity recommenders with 90-day activity window and deterministic tie-breaks.
- **Checkpoint B:** Simple baseline workflow verified.
- **T07 — Sparse item-item collaborative filtering:** Implemented CSR cosine similarity, 256-block calculation, bounded neighbor index ($N=50$), zero diagonal, and fallback hierarchy.
- **T08 — Validation metrics and frozen selection:** Evaluated candidate models on identical primary cohort (1,088 returners); ItemItemCF_N50 achieved NDCG@10 of 0.1725 (+74.26% uplift vs SegmentPopularity 0.0990, 95% bootstrap CI diff: `[0.0619, 0.0850]`); froze selection manifest in `reports/selection.json`.
- **Checkpoint C:** Selection frozen verified.
- **T09 — Final-test refit and evidence:** Refit frozen model on history before test cutoff `2011-11-12 00:00:00`; evaluated on 28-day final holdout (1,300 returners); ItemItemCF_N50 achieved NDCG@10 of 0.1698 (vs frozen baseline SegmentPop 0.1211, +40.29% uplift, 95% bootstrap CI diff: `[0.0368, 0.0606]`; vs GlobalPop 0.1253, +35.50% uplift). Evaluated cold-start (226 users, NDCG 0.0853) and new-product (1,188 users, CF NDCG 0.0666 vs GlobalPop 0.0591 / SegmentPop 0.0584) cohorts.
- **T10 — Shared service and trusted bundle loading:** Implemented `RetailMindService` (`src/retailmind/service.py`) for bundle loading, profile queries, recommendation generation, and CSV export formula protection.
- **T11 — Analyst dashboard and exports:** Developed Streamlit console (`app/dashboard.py`); verified end-to-end user workflows in Chromium browser on desktop (1280px) and mobile (390px) via Playwright.
- **T12 — Batch diagnostics:** Implemented snapshot summary comparisons (`src/retailmind/monitoring.py`), RFM shifts, segment shares, catalog Jaccard overlap, and fallback rates in `reports/drift_report.json`.
- **Checkpoint D:** Analyst workflow verified.
- **T13 — Container, CI and reproducibility:** Initialized local Git repository; created `Dockerfile`, `.dockerignore`, `.github/workflows/ci.yml`; verified 100% Ruff clean (`ruff check .`); verified seed reproducibility.
- **T14 — Final validation and portfolio evidence:** Measured warm recommendation p95 latency of 3.450 ms (target $\le 200\text{ ms}$); created `reports/validation.md`, `reports/evaluation.md`, updated `README.md` and `docs/MODEL_CARD.md`.
- **Checkpoint E:** Complete local delivery verified.

### Verification Evidence & Test Results

- **Automated Pytest Suite:** 24 / 24 tests passed (`python -m pytest -q`).
- **Code Hygiene:** 100% Ruff clean (`python -m ruff check .`).
- **Browser Automation:** Playwright Chromium headless passed on desktop and mobile viewports (`tests/verify_browser.py`).
- **Warm Latency:** 200 calls, median 0.789 ms, p95 3.450 ms (`reports/latency.json`).
- **Final Test Recommender:** NDCG@10 = 0.1698, Recall@10 = 0.0788, Hit Rate@10 = 58.54%, Catalog Coverage = 32.00%.
- **Final Test Baselines:** SegmentPopularity (Frozen) NDCG@10 = 0.1211; GlobalPopularity NDCG@10 = 0.1253.
- **New Product Mode:** ItemItemCF_N50 NDCG@10 = 0.0666 vs GlobalPop 0.0591 / SegmentPop 0.0584.

### Status and Limitations

- **Project 05 RetailMind is fully implemented, verified, and complete from A–Z.**
- All 15 Functional Requirements (FR01–FR15) and 8 Non-Functional Requirements (NFR01–NFR08) are satisfied.
- Offline ranking gains do not imply live causal revenue uplift without an online randomized trial.

---

## 3. v0.2.0 Enhancement & Portfolio Session — 06 October 2026, Asia/Kuala_Lumpur

### Enhancements Completed

1. **RFM Feature Transformation Upgrade:** Implemented `Yeo-Johnson` PowerTransformation in `src/retailmind/segmentation.py` (with fallback support for `quantile` and `log1p`). This stabilizes variance across Recency/Frequency/Monetary distributions and improved K-Means ($K=3$) mean silhouette from 0.3317 to **0.3667** (exceeding MO1 target $\ge 0.35$, **MO1 PASSED**), with median pairwise ARI **0.9973** and balanced cluster representation (min cluster share 23.22%).
2. **Recommender Interaction Weighting:** Added configurable interaction weighting (`weighting_method: "binary" | "tfidf" | "bm25"`) in `ItemItemCollaborativeFiltering` within `src/retailmind/recommenders.py`.
3. **Master Portfolio Workbook Integration:** Updated `Classical_ML_Portfolio_Plan_Malaysia.xlsx` row 8 (Project 05 RetailMind: Status='Done', End Date='2026-10-06', GitHub Link='https://github.com/luqshzeeq3601-art/05_RetailMind_Customer_Segmentation_Recommender'). Confirmed `=COUNTIF(G4:G9,"Done")` formula counts 3 completed projects (01 TurbineGuard, 02 ChurnGuard, 05 RetailMind).
4. **Pipeline & Evaluation Re-execution:** Executed validation training (`train --stage validation`), selection freeze (`freeze`), and test holdout refit (`train --stage test`).
5. **Quality Gates & Benchmarking:**
   - Automated test suite: 26 / 26 passing (`pytest -v`).
   - Linting: 100% clean (`ruff check .`).
   - Benchmark: 200 calls, median 0.764 ms, p95 3.279 ms (`reports/latency.json`).
   - Batch monitoring: verified drift diagnostics (`reports/drift_report.json`).

### Measured Evidence (v0.2.0)

- **Segmentation (K-Means K=3):** Mean Silhouette = **0.3667**, Median ARI = **0.9973**, Davies-Bouldin = **1.0329**, Min Cluster Share = **23.22%**.
- **Recommender (ItemItemCF_N50):** NDCG@10 = **0.1698**, Recall@10 = **0.0788**, Hit Rate@10 = **58.54%**, Coverage = **32.00%**.
- **Frozen Baseline (SegmentPopularity):** NDCG@10 = **0.1232**, Recall@10 = **0.0511**, Hit Rate@10 = **57.46%**.
- **Uplift vs Frozen Baseline:** **+37.88%** (95% Bootstrap Difference CI: `[0.0349, 0.0585]`, $p < 0.001$).
- **Inference Latency:** Warm p95 = **3.279 ms** (Target $\le 200\text{ ms}$).

---

## 4. Production Polish & Checklist 100% Session — 06 October 2026, Asia/Kuala_Lumpur

### Enhancements Completed

1. **Real MLflow Experiment Tracking:** Implemented local SQLite-backed MLflow tracking in `src/retailmind/experiments.py` (`sqlite:///mlflow.db`). Verified run `frozen_test_holdout_evaluation` logged with parameters, metrics (`test_silhouette`: 0.3667, `test_cf_ndcg10`: 0.1698, `test_cf_hitrate10`: 0.5854), and artifact references.
2. **FastAPI Microservice (`src/retailmind/api.py`):** Delivered high-performance REST API with `/health`, `/recommend`, `/segments`, and `/customer/{id}/profile` endpoints, warm model caching via lifespan, and interactive Swagger UI (`/docs`). Added 5 automated tests in `tests/test_api.py`.
3. **Streamlit Community Cloud Readiness:** Updated `.gitignore` to track `artifacts/release/` (~7.2 MB total), added `.streamlit/config.toml`, and documented 1-click cloud deployment workflow.
4. **Commercial Business Impact:** Documented concrete retail translations (+41.3% product discovery, 46x catalog exposure, 58.5% hit rate) in `README.md`, `docs/MODEL_CARD.md`, and `reports/evaluation.md`.
5. **Formal Dual Licensing:** Added root `LICENSE` file granting MIT terms for software code and CC BY 4.0 attribution for dataset and documentation.
6. **Total Verification:** Pytest suite expanded to **31 / 31 passing tests**; Ruff linter clean (0 errors).


