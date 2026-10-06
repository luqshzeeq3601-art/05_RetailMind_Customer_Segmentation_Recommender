# RetailMind Model Card

## 1. Measured Implementation Identity

| Field | Measured Value |
|---|---|
| Artifact/model version | `0.1.0-release` (Stage: `test` / `release`) |
| Segmentation model | **K-Means ($K=3$, Seed=42)** (Mean Silhouette: `0.3317`, Median Pairwise ARI: `0.9992`; MO1 target 0.35 missed) |
| Recommendation model | **Item-Item Collaborative Filtering ($N=50$ neighbors, cosine similarity)** |
| Dataset source hash (SHA-256) | `43465A06F2CCF7C8B5BD2892BC7DEFB52F97487934FE93B16AE4C3936424676D` |
| Config hash (SHA-256) | `E80370C58F7D1499FE8288668719DE716CD6B2E603F5DAA42544E63094FFC652` |
| Dependency lock hash (SHA-256) | `E5F4A06797B034CD6F6C02787A831BD4241DD91DC68A371D8F842DF44BEEADF9` |
| Selection manifest hash (SHA-256) | `1766C365617812FE6973BBDC77AE858281DE19ECA340932E2EBB5F944636E63E` |
| Final test primary cohort NDCG@10 | **0.1698** (Recall@10: `0.0788`, Hit Rate@10: `58.54%`, Coverage: `32.00%`) |
| Frozen validation baseline NDCG@10 | **0.1211** (Segment Popularity, Recall@10: `0.0489`, Hit Rate@10: `55.69%`) |
| Global popularity baseline NDCG@10 | **0.1253** (Global Popularity, Recall@10: `0.0510`, Hit Rate@10: `56.62%`) |
| 95% Paired bootstrap difference CI vs Frozen Baseline | `[0.0368, 0.0606]` (Strictly $> 0$, relative gain +40.29%) |
| Measured warm p95 latency | **3.450 ms** (200 requests, single process, target $\le 200\text{ ms}$: **PASSED**) |

---

## 2. Intended Use

RetailMind is an analyst-facing decision support tool for exploring customer segmentation and generating ranked product recommendation shortlists from historical implicit purchase transactions.

It is **not** an automated transaction/campaign agent, payment system, credit scoring engine, or live warehouse inventory controller.

---

## 3. Dataset and Cleaning Evidence

- **Official Source:** UCI Online Retail (541,909 raw transaction lines from 2010-12-01 to 2011-12-09).
- **Disjoint Removals:**
  - Missing/invalid core timestamps/invoices/quantities: 0 rows
  - Exact duplicates across all 8 fields: 5,268 rows
  - Missing Customer ID: 135,037 rows (anonymous purchase value tracked separately: £1,447,487.53)
  - Cancellations (`C` prefix) and nonpositive quantities: 8,872 rows
  - Nonpositive unit price: 40 rows
  - Non-merchandise product codes (e.g. POST, D, BANK CHARGES): 1,833 rows
- **Retained Purchases:** 390,859 transactions (GBP £8,722,008.97 total purchase value; 100% exact reconciliation).
- **Wholesale Concentration:** Top 1% of customers account for 30.6% of training spend; top 10% account for 60.2%.

---

## 4. Segment Profiles & Campaign Hypotheses

| Segment ID | Label | Share | Median R | Median F | Median M | Campaign Hypothesis |
|---|---|---|---|---|---|---|
| **SG01** | High-Value Frequent VIPs | 24.31% | 16.0 d | 5.0 orders | £1,871.42 | Loyalty perks, early product access, and premium bundles to maximize retention |
| **SG02** | Recent New / Occasional Buyers | 29.33% | 15.0 d | 2.0 orders | £509.00 | Nurture sequence and introductory category recommendations to foster repeat purchase |
| **SG03** | Dormant / Low Engagement | 46.37% | 93.0 d | 1.0 order | £313.44 | Low-cost seasonal email reminders and highlight of top global bestsellers |

---

## 5. Frozen Evaluation & Model Evidence

Evaluated on the locked 28-day final holdout (`2011-11-12` to `2011-12-10`) against un-sampled full catalog ($|C| = 2,753$ items):

| Model / Cohort | Cohort Size | NDCG@10 | Recall@10 | Precision@10 | Hit Rate@10 | Catalog Coverage |
|---|---|---|---|---|---|---|
| **ItemItemCF_N50 (Primary Returners)** | **1,300** | **0.1698** | **0.0788** | **0.1539** | **58.54%** | **32.00%** |
| SegmentPopularity (Frozen Baseline) | 1,300 | 0.1211 | 0.0489 | 0.1052 | 55.69% | 0.65% |
| GlobalPopularity (Baseline) | 1,300 | 0.1253 | 0.0510 | 0.1065 | 56.62% | 0.36% |
| **Cold-Start (Global Popularity)** | **226** | **0.0853** | **0.0360** | **0.0726** | **44.69%** | **0.36%** |
| **ItemItemCF_N50_NewItemsOnly** | **1,188** | **0.0666** | **0.0446** | **0.0539** | **32.91%** | **28.66%** |
| GlobalPopularity_NewItemsOnly | 1,188 | 0.0591 | 0.0323 | 0.0471 | 31.65% | 2.00% |
| SegmentPopularity_NewItemsOnly | 1,188 | 0.0584 | 0.0330 | 0.0481 | 32.66% | 2.83% |

---

## 6. Known Limitations

1. **Implicit Feedback:** Recommendation scores derive from item co-purchase cosine similarity and do not represent calibrated purchase probabilities.
2. **Offline vs Causal:** Offline NDCG improvements demonstrate superior ranking alignment with historical purchases, but live conversion uplift requires an online randomized A/B trial.
3. **UK Retail Context:** The dataset reflects UK online giftware transactions from 2010–2011; generalization to other markets or product categories must be verified.
4. **Historical Catalog Proxy:** Active catalog eligibility requires $\ge 5$ distinct buyers in history and $\ge 1$ purchase in the preceding 90 days; real-time warehouse inventory availability is not modeled.
