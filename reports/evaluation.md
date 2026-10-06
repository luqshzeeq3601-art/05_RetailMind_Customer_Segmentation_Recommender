# RetailMind: Model Evaluation and Performance Report

**Date:** 06 October 2026  
**Artifact Version:** `0.1.0-release`  
**Dataset:** UCI Online Retail (541,909 raw records, 390,859 cleaned eligible purchases)  
**Source SHA-256:** `43465A06F2CCF7C8B5BD2892BC7DEFB52F97487934FE93B16AE4C3936424676D`  
**Lock SHA-256:** `E5F4A06797B034CD6F6C02787A831BD4241DD91DC68A371D8F842DF44BEEADF9`  

---

## 1. Executive Summary

RetailMind implements an end-to-end customer intelligence system combining **time-safe RFM customer segmentation** and **sparse item-item collaborative filtering with popularity fallback hierarchy**.

All data processing, clustering, item similarity scoring, and evaluations strictly obey **chronological boundaries**, completely eliminating future information leakage. Under frozen test holdout evaluation over 28 calendar days:

- **Customer Segmentation:** K-Means ($K=3$) was selected under the documented 0.01 silhouette tolerance rule, achieving a median pairwise Adjusted Rand Index (ARI) of **0.9992** across multiple seed initializations, a mean silhouette score of **0.3317**, and balanced segments (smallest cluster holding 24.31% of active customers). *(Note: MO1 target of silhouette $\ge 0.35$ is honestly reported as missed).*
- **Product Recommendations:** Sparse Item-Item Collaborative Filtering ($N=50$ neighbors) achieved an **NDCG@10 of 0.1698**, **Recall@10 of 0.0788**, and a **Hit Rate@10 of 58.54%** on returning customers, significantly outperforming the frozen validation baseline `SegmentPopularity` (**+40.29% NDCG uplift**, 95% paired bootstrap difference CI: `[0.0368, 0.0606]`, strictly positive) and `GlobalPopularity` (**+35.50% NDCG uplift**).
- **New Product Recommendations:** In new-items-only mode on 1,188 returners, Item-Item CF achieved **NDCG@10 of 0.0666** and **Recall@10 of 0.0446**, beating the new-product popularity baselines (`GlobalPopularity_NewItemsOnly` at 0.0591 NDCG and `SegmentPopularity_NewItemsOnly` at 0.0584 NDCG).
- **Latency & Parity:** Warm recommendation inference p95 latency is **3.45 ms** (far below the 200 ms target), with 100% ranking parity between CLI and Streamlit interfaces.

---

## 2. Customer Segmentation Performance

### 2.1 Candidate Comparison (Validation Prefix $< 2011-10-15$)

Directly generated from `reports/cluster_comparison.csv`:

| Model Family | Configuration | Mean Silhouette | Median Pairwise ARI | Davies-Bouldin | Min Cluster Share | Eligible? |
|---|---|---|---|---|---|---|
| **K-Means** | **K = 3** (Selected) | **0.3317** | **0.9992** | **1.1034** | **23.51%** | **Yes** |
| K-Means | K = 4 | 0.3402 | 0.9880 | 1.0181 | 14.00% | Yes |
| K-Means | K = 5 | 0.3398 | 0.9955 | 0.9529 | 9.28% | Yes |
| K-Means | K = 6 | 0.3166 | 0.9888 | 0.9779 | 5.48% | Yes |
| RFM Rules | 4 Quantile Bins | 0.2311 | 1.0000 | 1.1985 | 16.28% | No (Baseline) |
| GMM | K = 3, diag | 0.2244 | 0.9992 | 1.4986 | 21.50% | No (Sil < 0.30) |
| GMM | K = 6, full | 0.1780 | 0.9284 | 1.9571 | 7.83% | No (Sil < 0.30) |
| GMM | K = 6, diag | 0.1767 | 0.9938 | 1.9096 | 5.32% | No (Sil < 0.30) |
| GMM | K = 3, full | 0.1699 | 1.0000 | 1.7468 | 22.09% | No (Sil < 0.30) |
| GMM | K = 4, diag | 0.1658 | 1.0000 | 1.7719 | 10.96% | No (Sil < 0.30) |
| GMM | K = 4, full | 0.1583 | 1.0000 | 1.7851 | 14.80% | No (Sil < 0.30) |
| GMM | K = 5, diag | 0.1434 | 1.0000 | 2.0670 | 5.58% | No (Sil < 0.30) |
| GMM | K = 5, full | 0.1391 | 0.9997 | 2.0549 | 5.09% | No (Sil < 0.30) |

*Selection Rule Application:* Under `docs/06_EXPERIMENT_PLAN.md` §3, candidates within 0.01 mean silhouette of the highest eligible score (K=4 at 0.3402; tolerance threshold $\ge 0.3302$) are evaluated by higher median ARI, fewer clusters, and K-Means preference. K-Means $K=3$ (silhouette 0.3317) falls within the 0.01 band ($0.3402 - 0.3317 = 0.0085 \le 0.01$) and wins on near-perfect stability (median ARI **0.9992** vs 0.9880) and model parsimony.

*Target Status (MO1):* **Missed.** The achieved silhouette score of 0.3317 is below the aspirational target of 0.3500. This is documented transparently in all model logs.

### 2.2 Segment Profiles and Campaign Hypotheses

Directly generated from `reports/segment_profiles.csv`:

| Segment ID | Segment Label | Customer Count | Share (%) | Median Recency | Median Frequency | Median Monetary | Recommended Campaign Strategy |
|---|---|---|---|---|---|---|---|
| **SG01** | **High-Value Frequent VIPs** | 736 | 24.31% | 16.0 days | 5.0 orders | £1,871.42 | Loyalty perks, early product access, and premium bundles to maximize retention. |
| **SG02** | **Recent New / Occasional Buyers** | 888 | 29.33% | 15.0 days | 2.0 orders | £509.00 | Nurture sequence and introductory category recommendations to foster repeat purchase. |
| **SG03** | **Dormant / Low Engagement** | 1,404 | 46.37% | 93.0 days | 1.0 order | £313.44 | Low-cost seasonal email reminders and highlight of top global bestsellers. |

---

## 3. Product Recommendation Performance

### 3.1 Final Test Holdout Evaluation (28-Day Period: `2011-11-12` to `2011-12-10`)

Evaluated on the frozen, held-out purchase interval using the complete, un-sampled catalog ($|C| = 2,753$ items, future item coverage 98.31%):

| Model / Cohort | Cohort Size | NDCG@10 | Recall@10 | Precision@10 | Hit Rate@10 | Catalog Coverage | Fallback Item Share |
|---|---|---|---|---|---|---|---|
| **ItemItemCF_N50 (Selected, Returners)** | **1,300** | **0.1698** | **0.0788** | **0.1539** | **58.54%** | **32.00%** | **0.0%** |
| SegmentPopularity (Frozen Baseline, Returners) | 1,300 | 0.1211 | 0.0489 | 0.1052 | 55.69% | 0.65% | 100.0% |
| GlobalPopularity (Baseline, Returners) | 1,300 | 0.1253 | 0.0510 | 0.1065 | 56.62% | 0.36% | 100.0% |
| **ColdStart_GlobalPop (New Customers)** | **226** | **0.0853** | **0.0360** | **0.0726** | **44.69%** | **0.36%** | **100.0%** |
| **ItemItemCF_N50_NewItemsOnly** | **1,188** | **0.0666** | **0.0446** | **0.0539** | **32.91%** | **28.66%** | **0.0%** |
| GlobalPopularity_NewItemsOnly | 1,188 | 0.0591 | 0.0323 | 0.0471 | 31.65% | 2.00% | 100.0% |
| SegmentPopularity_NewItemsOnly | 1,188 | 0.0584 | 0.0330 | 0.0481 | 32.66% | 2.83% | 100.0% |

### 3.2 Statistical Significance (1,000 Paired Bootstrap Draws vs Frozen Baseline)

- **Item-Item CF NDCG@10 95% CI:** `[0.1592, 0.1807]`
- **Frozen Baseline (`SegmentPopularity`) NDCG@10 95% CI:** `[0.1132, 0.1293]`
- **Paired Difference ($\Delta \text{NDCG}$) 95% CI:** `[0.0368, 0.0606]` (Strictly $> 0$, relative gain +40.29%)
- **Relative Gain vs GlobalPopularity:** +35.50% ($0.1698$ vs $0.1253$)

---

## 4. Latency & Operational Performance

- **Warm Inference Latency (200 requests, K=10, `reports/latency.json`):**
  - Median: **0.789 ms**
  - P95: **3.450 ms** (Target $\le 200\text{ ms}$: **PASSED**)
  - P99: **7.367 ms**
  - Maximum: **54.221 ms**
- **Catalog Size:** 2,753 active items (98.31% future item coverage).
- **Parity Verification:** Direct model scoring, CLI output, and Streamlit dashboard output are 100% identical.

---

## 5. Scope Boundaries and Limitations

1. **Implicit Feedback:** Recommendation scores reflect co-purchase cosine affinity and historical frequency; they do not represent calibrated purchase probabilities.
2. **Causal Impact:** Offline ranking improvements demonstrate superior historical preference alignment, but do not guarantee incremental conversion or revenue uplift without online A/B testing.
3. **Wholesale Concentration:** Top 1% of customers account for 30.6% of historical spending. Segment-specific marketing should consider order volume constraints.
4. **Cold Start:** New customers with zero historical purchases receive non-personalized global bestsellers until initial transaction data is recorded.
