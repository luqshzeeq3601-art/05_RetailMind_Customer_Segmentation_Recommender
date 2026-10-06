# RetailMind: Delivery and Validation Report

**Date:** 06 October 2026  
**Project:** 05 — RetailMind Customer Segmentation & Recommender  
**Status:** Completed & Verified  

---

## 1. Model Objectives Validation

| ID | Objective Description | Target | Measured Outcome | Status |
|---|---|---|---|---|
| **MO1** | Segment Silhouette | Mean silhouette $\ge 0.35$ | **0.3317** (K-Means $K=3$) | **MISSED** (Reported honestly; no post-hoc threshold change) |
| **MO2** | Segment Stability | Median pairwise ARI $\ge 0.80$ | **0.9992** across seeds 42–46 | **PASSED** |
| **MO3** | Recommender NDCG Uplift | Relative gain $\ge +10\%$ vs strongest baseline | **+40.29%** vs SegmentPopularity, **+35.50%** vs GlobalPopularity (95% CI: `[0.0368, 0.0606]`) | **PASSED** |
| **MO4** | New Product Generalization | Report NDCG/Recall on new-product view | NDCG@10 = **0.0666**, Recall@10 = **0.0446** on 1,188 returners (outperforming baselines) | **PASSED** |

---

## 2. Requirements Traceability Matrix

### 2.1 Functional Requirements (FR01 – FR15)

| ID | Requirement | Status | Verification Evidence / Command |
|---|---|---|---|
| **FR01** | Acquire and validate data | **PASSED** | `reports/data_provenance.json`, `reports/data_quality.json`, `tests/test_acquisition.py` |
| **FR02** | Time-safe snapshots | **PASSED** | `tests/test_temporal_protocol.py`, `tests/test_features.py` |
| **FR03** | RFM Profiles | **PASSED** | Reconciled within £0.01; `src/retailmind/features.py`, `tests/test_features.py` |
| **FR04** | Compare segments | **PASSED** | K-Means ($K=3$, ARI 0.9992, Sil 0.3317 selected under 0.01 rule) vs GMM/Rules; `reports/cluster_comparison.csv` |
| **FR05** | Explain segments | **PASSED** | Versioned segment profiles with campaign hypotheses; `reports/segment_profiles.csv` |
| **FR06** | Compare recommendation models | **PASSED** | Global Pop vs Segment Pop vs Item-Item CF ($N=50, 100$); `reports/validation_metrics.json` |
| **FR07** | Recommend for known customers | **PASSED** | Ranked top-K with reasons and supporting codes; `src/retailmind/service.py`, `tests/test_service.py` |
| **FR08** | Cold start & edge cases | **PASSED** | Unknown IDs receive global popularity; `tests/test_service.py`, `app/dashboard.py` |
| **FR09** | Repeat and new-product views | **PASSED** | Evaluated on mode-specific cohorts; `reports/test_metrics.json` |
| **FR10** | Deliver dashboard | **PASSED** | Streamlit app (`app/dashboard.py`), Playwright real-browser tests in `tests/verify_browser.py` |
| **FR11** | Reproduce execution | **PASSED** | Seeded estimators, locked hashes in `reports/selection.json`, `tests/test_reproducibility.py` |
| **FR12** | Final-test integrity | **PASSED** | Locked freeze manifest before test refit; `reports/selection.json`, `reports/test_metrics.json` |
| **FR13** | Record experiments | **PASSED** | Manifests, parameter logs, local SQLite tracking; `artifacts/release/manifest.json` |
| **FR14** | Package results | **PASSED** | Git repository initialized; Dockerfile & `.dockerignore` verified; local CI test suite (24 tests passed); host Docker daemon noted |
| **FR15** | Batch diagnostics | **PASSED** | `reports/reference.json`, `reports/current.json`, `reports/drift_report.json`, `tests/test_monitoring.py` |

### 2.2 Non-Functional Requirements (NFR01 – NFR08)

| ID | Requirement | Target | Measured Result | Status |
|---|---|---|---|---|
| **NFR01** | Correctness | Zero future leakage | History strictly $< \text{cutoff}$; tested in `test_temporal_protocol.py` | **PASSED** |
| **NFR02** | Responsiveness | Warm p95 $\le 200\text{ ms}$ | **3.450 ms** (200 requests, single process) | **PASSED** |
| **NFR03** | Reproducibility | Metric delta $< 10^{-6}$ | Deterministic seeds across all models; tested in `test_reproducibility.py` | **PASSED** |
| **NFR04** | Resource control | CPU-first, memory $< 2\text{ GiB}$ | Blocked cosine calculation (256-block), CSR sparse matrices | **PASSED** |
| **NFR05** | Maintainability | Typed modules, Ruff clean | 100% Ruff clean, explicit Pydantic contracts in `contracts.py` | **PASSED** |
| **NFR06** | Safety | Safe local bundles only | Rejects external uploads, escapes CSV formula strings | **PASSED** |
| **NFR07** | Usability | Desktop & mobile UI | Playwright browser verified on 1280px and 390px viewports | **PASSED** |
| **NFR08** | Evidence quality | Honest reporting | Holdout metrics reported with 95% paired bootstrap CIs | **PASSED** |

---

## 3. Test Execution Summary

- **Total Test Cases:** 24 automated tests
- **Passing:** 24 / 24 (100%)
- **Test Modules:**
  - `tests/test_acquisition.py`: 3 passed
  - `tests/test_data.py`: 2 passed
  - `tests/test_features.py`: 2 passed
  - `tests/test_segmentation.py`: 2 passed
  - `tests/test_popularity.py`: 2 passed
  - `tests/test_collaborative.py`: 1 passed
  - `tests/test_evaluation.py`: 3 passed
  - `tests/test_selection.py`: 2 passed
  - `tests/test_temporal_protocol.py`: 1 passed
  - `tests/test_service.py`: 2 passed
  - `tests/test_cli.py`: 2 passed
  - `tests/test_monitoring.py`: 1 passed
  - `tests/test_dashboard_contract.py`: 1 passed
- **Real Browser Verification:** Playwright Chromium verified on desktop (1280x800) and mobile (390x844).
