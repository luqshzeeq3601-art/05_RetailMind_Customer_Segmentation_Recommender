# RetailMind: Model Evaluation and Performance Report

**Date:** 06 October 2026  
**Artifact Version:** `0.2.0-release`  
**Dataset:** UCI Online Retail (541,909 raw records, 390,859 cleaned eligible purchases)  
**Source SHA-256:** `43465A06F2CCF7C8B5BD2892BC7DEFB52F97487934FE93B16AE4C3936424676D`  
**Lock SHA-256:** `E5F4A06797B034CD6F6C02787A831BD4241DD91DC68A371D8F842DF44BEEADF9`  

---

## 1. Executive Summary

RetailMind implements an end-to-end customer intelligence system combining **time-safe RFM customer segmentation** (enhanced with Yeo-Johnson PowerTransformation) and **sparse item-item collaborative filtering with popularity fallback hierarchy**.

All data processing, clustering, item similarity scoring, and evaluations strictly obey **chronological boundaries**, completely eliminating future information leakage. Under frozen test holdout evaluation over 28 calendar days:

- **Customer Segmentation:** K-Means ($K=3$) with Yeo-Johnson power-transformed RFM features achieved a mean silhouette score of **0.3667** (exceeding the target $\ge 0.35$, **MO1 PASSED**), a median pairwise Adjusted Rand Index (ARI) of **0.9973** across multiple seed initializations, and well-balanced segments (smallest cluster holding 23.22% of active customers).
- **Product Recommendations:** Sparse Item-Item Collaborative Filtering ($N=50$ neighbors) achieved an **NDCG@10 of 0.1698**, **Recall@10 of 0.0788**, and a **Hit Rate@10 of 58.54%** on returning customers, significantly outperforming the frozen validation baseline `SegmentPopularity` (**+37.88% NDCG uplift**, 95% paired bootstrap difference CI: `[0.0349, 0.0585]`, strictly positive) and `GlobalPopularity` (**+35.50% NDCG uplift**).
- **New Product Recommendations:** In new-items-only mode on 1,188 returners, Item-Item CF achieved **NDCG@10 of 0.0666** and **Recall@10 of 0.0446**, beating the new-product popularity baselines (`GlobalPopularity_NewItemsOnly` at 0.0591 NDCG and `SegmentPopularity_NewItemsOnly` at 0.0596 NDCG).
- **Latency & Parity:** Warm recommendation inference p95 latency is **3.28 ms** (far below the 200 ms target), with 100% ranking parity between CLI, FastAPI, and Streamlit interfaces.
- **Commercial Impact:** The +37.88% NDCG uplift and +54.2% Recall lift translate into delivering **1.54 relevant suggestions per customer** (vs 1.09 with popularity), increasing product discovery by **+41.3%** while expanding active catalog surface area **46x** (recommending 881 distinct products vs 19) in the offline recommendation lists; margin and revenue effects were not measured.

---

## 2. Customer Segmentation Performance

### 2.1 Candidate Comparison (Validation Prefix $< 2011-10-15$)

Directly generated from `reports/cluster_comparison.csv`:

| Model Family | Configuration | Mean Silhouette | Median Pairwise ARI | Davies-Bouldin | Min Cluster Share | Eligible? |
|---|---|---|---|---|---|---|
| **K-Means** | **K = 3** (Selected) | **0.3667** | **0.9973** | **1.0329** | **23.22%** | **Yes** |
| K-Means | K = 4 | 0.3595 | 0.9957 | 0.9809 | 21.07% | Yes |
| K-Means | K = 5 | 0.3501 | 0.9992 | 1.0044 | 15.72% | Yes |
| K-Means | K = 6 | 0.3232 | 0.9934 | 1.0203 | 13.77% | Yes |
| RFM Rules | 4 Quantile Bins | 0.2658 | 1.0000 | 1.2257 | 16.28% | No (Baseline) |
| GMM | K = 4, diag | 0.2998 | 0.9992 | 1.2549 | 22.09% | No (Sil < 0.30) |
| GMM | K = 4, full | 0.2985 | 0.9977 | 1.2609 | 21.80% | No (Sil < 0.30) |
| GMM | K = 3, full | 0.2440 | 1.0000 | 1.4592 | 22.09% | No (Sil < 0.30) |
| GMM | K = 3, diag | 0.2440 | 1.0000 | 1.4592 | 22.09% | No (Sil < 0.30) |
| GMM | K = 5, full | 0.2172 | 1.0000 | 1.7895 | 11.56% | No (Sil < 0.30) |
| GMM | K = 6, diag | 0.2154 | 0.9627 | 2.0657 | 6.47% | No (Sil < 0.30) |
| GMM | K = 6, full | 0.2026 | 0.9353 | 2.1840 | 0.10% | No (Sil < 0.30) |
| GMM | K = 5, diag | 0.1753 | 0.9786 | 1.8241 | 0.03% | No (Sil < 0.30) |

*Selection Rule Application:* Under `docs/06_EXPERIMENT_PLAN.md` §3, candidates are ranked by mean silhouette score, with ties within 0.01 resolved by higher stability (ARI), fewer clusters, and K-Means preference. K-Means $K=3$ achieves the highest mean silhouette (**0.3667**) among all configurations, near-perfect stability (median ARI **0.9973**), and balanced representation.

*Target Status (MO1):* **Passed.** Mean silhouette score of 0.3667 exceeds the target threshold of 0.3500.

### 2.2 Segment Profiles and Campaign Hypotheses

Directly generated from `reports/segment_profiles.csv`:

| Segment ID | Segment Label | Customer Count | Share (%) | Median Recency | Median Frequency | Median Monetary | Recommended Campaign Strategy |
|---|---|---|---|---|---|---|---|
| **SG01** | **Steady Active Buyers** | 1,196 | 39.50% | 18.0 days | 4.0 orders | £1,322.90 | Category cross-sell recommendations and volume discounts to boost basket size. |
| **SG02** | **Recent New / Occasional Buyers** | 705 | 23.28% | 17.0 days | 1.0 order | £338.71 | Nurture sequence and introductory category recommendations to foster repeat purchase. |
| **SG03** | **Dormant / Low Engagement** | 1,127 | 37.22% | 108.0 days | 1.0 order | £301.03 | Low-cost seasonal email reminders and highlight of top global bestsellers. |

---

## 3. Product Recommendation Performance

### 3.1 Final Test Holdout Evaluation (28-Day Period: `2011-11-12` to `2011-12-10`)

Evaluated on the frozen, held-out purchase interval using the complete, un-sampled catalog ($|C| = 2,753$ items, future item coverage 98.31%):

| Model / Cohort | Cohort Size | NDCG@10 | Recall@10 | Precision@10 | Hit Rate@10 | Catalog Coverage | Fallback Item Share |
|---|---|---|---|---|---|---|---|
| **ItemItemCF_N50 (Selected, Returners)** | **1,300** | **0.1698** | **0.0788** | **0.1539** | **58.54%** | **32.00%** | **0.0%** |
| SegmentPopularity (Frozen Baseline, Returners) | 1,300 | 0.1232 | 0.0511 | 0.1090 | 57.46% | 0.69% | 100.0% |
| GlobalPopularity (Baseline, Returners) | 1,300 | 0.1253 | 0.0510 | 0.1065 | 56.62% | 0.36% | 100.0% |
| **ColdStart_GlobalPop (New Customers)** | **226** | **0.0853** | **0.0360** | **0.0726** | **44.69%** | **0.36%** | **100.0%** |
| **ItemItemCF_N50_NewItemsOnly** | **1,188** | **0.0666** | **0.0446** | **0.0539** | **32.91%** | **28.66%** | **0.0%** |
| GlobalPopularity_NewItemsOnly | 1,188 | 0.0591 | 0.0323 | 0.0471 | 31.65% | 2.00% | 100.0% |
| SegmentPopularity_NewItemsOnly | 1,188 | 0.0596 | 0.0320 | 0.0479 | 32.32% | 2.47% | 100.0% |

### 3.2 Statistical Significance (1,000 Paired Bootstrap Draws vs Frozen Baseline)

- **Item-Item CF NDCG@10 95% CI:** `[0.1592, 0.1807]`
- **Frozen Baseline (`SegmentPopularity`) NDCG@10 95% CI:** `[0.1150, 0.1313]`
- **Paired Difference ($\Delta \text{NDCG}$) 95% CI:** `[0.0349, 0.0585]` (Strictly $> 0$, relative gain +37.88%)
- **Relative Gain vs GlobalPopularity:** +35.50% ($0.1698$ vs $0.1253$)

---

## 4. Latency & Operational Performance

- **Warm Inference Latency (200 requests, K=10, `reports/latency.json`):**
  - Median: **0.764 ms**
  - P95: **3.279 ms** (Target $\le 200\text{ ms}$: **PASSED**)
  - P99: **6.919 ms**
  - Maximum: **49.365 ms**
- **Catalog Size:** 2,753 active items (98.31% future item coverage).
- **Parity Verification:** Direct model scoring, CLI output, and Streamlit dashboard output are 100% identical.

---

## 5. Scope Boundaries and Limitations

1. **Implicit Feedback:** Recommendation scores reflect co-purchase cosine affinity and historical frequency; they do not represent calibrated purchase probabilities.
2. **Causal Impact:** Offline ranking improvements demonstrate superior historical preference alignment, but do not guarantee incremental conversion or revenue uplift without online A/B testing.
3. **Wholesale Concentration:** Top 1% of customers account for 30.6% of historical spending. Segment-specific marketing should consider order volume constraints.
4. **Cold Start:** New customers with zero historical purchases receive non-personalized global bestsellers until initial transaction data is recorded.
