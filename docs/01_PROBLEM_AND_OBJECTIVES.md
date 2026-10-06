# 01. Problem and Objectives

## 1. Problem statement

A retailer has transaction history but lacks a consistent way to identify useful customer groups and choose products for each customer. An analyst may rely on total spending and a store-wide bestseller list. That can overlook differences in purchase recency, order frequency and product preferences.

**Project question:** can we produce understandable customer segments and rank products better than simple popularity using only purchase history available at the decision date?

## 2. Users and decisions

| User | Decision | Required output |
|---|---|---|
| CRM / marketing analyst | Which customer groups merit a campaign hypothesis? | Segment size, RFM summaries, descriptive label and suggested action |
| Merchandising analyst | Which products should appear in a customer shortlist? | Top-10 products, reason codes and fallback disclosure |
| ML engineer | Is personalization useful and reproducible? | Temporal baseline comparison, cohort counts, artifacts and tests |

## 3. Why this adds to Projects 1 and 2

1. Adds **unsupervised learning** and segment interpretation to the portfolio.
2. Adds **implicit-feedback recommendation**, sparse matrices and top-K evaluation.
3. Shows how to combine model output with a practical analyst workflow.
4. Demonstrates cold-start handling and honest comparison against simple baselines.

The spreadsheet names Astro and PetBacker as employer matches for this project. Treat that as portfolio context, not current hiring evidence or an affiliation claim.

## 4. Objectives and Measured Outcomes

| ID | Objective | Target / Condition | Measured Outcome & Evidence | Status |
|---|---|---|---|---|
| **BO1** | Make customer groups actionable | Every displayed segment has count, share, median R/F/M, descriptive label and campaign hypothesis | 3 distinct segments (SG01-SG03) with full business profiles in `reports/segment_profiles.csv` | **PASSED** |
| **BO2** | Usable product shortlist | Up to 10 unique eligible items with reason codes and fallback status | Ranked top-10 with reason strings and supporting codes; verified in `src/retailmind/service.py` | **PASSED** |
| **BO3** | State impact honestly | Report offline ranking metrics with CIs; no fabricated business uplift claims | Explicit caveats in `reports/evaluation.md` and `docs/MODEL_CARD.md` | **PASSED** |
| **MO1** | Segment separation | Mean silhouette >= 0.35 | **0.3667** (K-Means $K=3$, Yeo-Johnson transform); `reports/cluster_comparison.csv` | **PASSED** |
| **MO2** | Segment stability | Median pairwise ARI >= 0.80 across seeds, each cluster >= 3% of active customers | Median ARI = **0.9973**, min cluster share = **23.22%**; `reports/cluster_comparison.csv` | **PASSED** |
| **MO3** | Recommender uplift | >= 10% relative NDCG@10 gain over strongest baseline with nondecreasing Recall | NDCG@10 = **0.1698** vs **0.1232** SegmentPopularity (**+37.88%**, 95% CI `[0.0349, 0.0585]`) | **PASSED** |
| **MO4** | Coverage & cold start | Report catalog coverage, cold-start metrics, new-item metrics, fallback share | 32.0% catalog coverage, cold-start NDCG 0.0853, new-product NDCG 0.0666; `reports/test_metrics.json` | **PASSED** |
| **EO1** | Reproducibility | Deterministic seeds and locked hashes reproduce identical results ($\Delta < 10^{-6}$) | Pinned `requirements.lock`, verified in `tests/test_reproducibility.py` | **PASSED** |
| **EO2** | Responsive inference | Warm single-customer recommendation p95 <= 200 ms | **3.279 ms** over 200 timed calls (`reports/latency.json`) | **PASSED** |
| **EO3** | Analyst workflow | Streamlit dashboard with segment explorer, customer search, and CSV export | Playwright real-browser verified on desktop and mobile (`tests/verify_browser.py`) | **PASSED** |
| **EO4** | Training / serving parity | CLI and dashboard share identical service layer and return identical rankings | Verified in `src/retailmind/service.py` and `tests/test_service.py` | **PASSED** |
| **EO5** | Delivery & packaging | Clean test suite, clean linter, reproducible packaging, local CI equivalent | 26 pytest tests passing, Ruff clean, Dockerfile, Git repo initialized | **PASSED** |

## 5. Limits

- Historical purchases provide implicit feedback. Absence of a purchase does not prove dislike.
- The data does not provide product exposure, campaign assignment, product inventory or conversion events.
- A segment's proposed action is a hypothesis, not a demonstrated treatment effect.
- The dataset reflects historical UK online retail giftware transactions in GBP.
