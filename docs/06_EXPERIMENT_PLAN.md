# 06. Experiment and Evaluation Plan

## 1. Questions to test

1. Do learned RFM clusters provide stable, understandable groups compared with RFM rules?
2. Does item-based collaborative filtering rank future purchases better than global or segment popularity?
3. How much of the eligible population receives personalized recommendations, and where do fallback and catalog limits matter?

No classification accuracy target is used for segmentation. Customer purchases provide implicit binary relevance, not explicit product ratings.

## 2. Fixed evaluation protocol

Use the cutoffs and windows in [the data specification](05_DATA_SPEC.md), seed 42, K = 10, the full eligible catalog and no sampled negatives.

1. Fit validation candidates on the history prefix before 15 October 2011.
2. Select segmentation using only prefix diagnostics. Evaluate recommendation settings on the following 28 days.
3. Freeze algorithm, features, preprocessing, catalog rules, parameters, mode, tie-breaking and selection evidence in `reports/selection.json`.
4. Refit the frozen algorithms and settings on history before 12 November 2011.
5. Evaluate that bundle on the final 28-day interval and report results. Do not select another model based on test results.

A refit learns new centroids and similarities from the longer permitted history; it does not change the selected algorithm or hyperparameters. Segment IDs are interpreted within their versioned bundle.

## 3. Segmentation candidates and selection

| Model | Candidate settings | Purpose |
|---|---|---|
| RFM rules | Fixed rules from the data spec | Simple operational baseline and fallback |
| K-Means | K in {3, 4, 5, 6}; `n_init=20` | Hard customer groups |
| Gaussian Mixture | Components in {3, 4, 5, 6}; covariance in {full, diag}; `n_init=5`; regularization recorded | Alternative geometry and soft membership diagnostics |

Use log1p + the training-fitted scaler for both learned methods. Use seeds **42, 43, 44, 45, 46**. Record convergence failures instead of dropping them silently.

For each setting, report:

- Silhouette on all active customers if there are at most 2,000; otherwise use a fixed seed-42 sample of 2,000 customer IDs. Check that every cluster in every compared fit is represented. If needed, replace sampled IDs deterministically with omitted-cluster representatives, then reuse the resulting shared sample for all fits.
- Cluster counts, shares and median raw R/F/M.
- Median pairwise adjusted Rand index (ARI) across the ten pairs of seed runs on the same customer population.
- Davies–Bouldin score, and GMM BIC within the GMM family only. BIC is not a K-Means comparison metric.

**Eligibility:** every seed run converges, every cluster in every run has >= 3% of active customers, median pairwise ARI >= 0.80 and mean sampled silhouette >= 0.30. The aspirational silhouette target is 0.35.

**Selection:** among eligible settings, maximize mean silhouette. If within 0.01, prefer higher median ARI, then fewer clusters, then K-Means. Persist the selected setting's seed-42 fit. If none qualifies, select the RFM-rule baseline and report the failed criteria.

Use descriptive labels derived from median R/F/M and document one campaign hypothesis per group. Never name clusters solely from their number or use a churn interpretation without evidence. Assign learned segment IDs by median monetary descending, frequency descending and recency ascending, with cluster number as the final tie-break; this mapping is version-specific.

The RFM baseline may contain small groups. Report its sizes and any valid silhouette, but do not pretend it passed the learned-model eligibility gate.

## 4. Recommendation candidates

### 4.1 Baselines

1. **Global popularity:** 90-day distinct buyer count, with deterministic StockCode tie-breaks.
2. **Segment popularity:** same count within the customer's selected segment; fill with global popularity when its list is short. Inactive and unknown customers use global popularity.

Both follow the same catalog and repeat-mode rules as collaborative filtering. The strongest baseline is the one with higher validation macro NDCG@10 on the primary cohort; ties within 1e-6 prefer global popularity.

### 4.2 Item-item collaborative filtering

- Binary customer-item CSR matrix from prefix purchases of eligible catalog items.
- Item cosine similarity; zero diagonal; discard an edge if fewer than 2 distinct customers bought both items.
- For each seed item retain top N positive neighbors; compare N in {50, 100}.
- Customer score for item i: sum of retained similarities from the customer's distinct historical catalog items to i, divided by the number of those seed items. Zero-seed customers use popularity.
- Primary candidates are items with positive CF score. Order descending, then StockCode ascending. Fill remaining positions with segment popularity, then global popularity, removing duplicates at each step.
- No blending of incomparable raw popularity and cosine scores in the MVP.
- A CF list may include previously bought items because the primary task allows repeat purchase. A seed item's diagonal similarity is zero, so self-similarity cannot create its score.

Compare the two N settings on the same validation cohort. Highest NDCG@10 wins; ties within 1e-6 prefer N=50.

## 5. Evaluation populations

For a cutoff, define catalog `C`, each customer's prior purchase set `H_u` and unique eligible future-purchase set `P_u` after deterministic cleaning.

### 5.1 Primary known-customer cohort

- Customer appears in prefix history, including inactive known customers.
- `G_u = P_u intersect C` is nonempty.
- Evaluate each model on exactly the same users and full catalog. Repeat purchases are allowed.
- A known customer whose history contains no catalog seed gets fallback recommendations and **remains in the cohort**.

### 5.2 Cold-start cohort

- Customer is absent from prefix history and `P_u intersect C` is nonempty.
- Report global-popularity metrics separately. Do not mix new customers into a headline personalization gain.

### 5.3 New-product view

- Filter all models to candidates `C minus H_u`.
- Ground truth is `G_new_u = (P_u intersect C) minus H_u`.
- Evaluate only customers with nonempty `G_new_u` and report the new cohort size. Do not reuse repeat-allowed denominators.

### 5.4 Required coverage accounting

Report known / new customers, returners / non-returners, active / inactive, users with empty in-catalog ground truth, out-of-catalog future products, empty candidate sets and CF fallback frequency.

Ranking metrics on returners with in-catalog positives describe that population. They do not establish purchase propensity for non-returners or quality on future unseen products.

## 6. Metrics

For a unique ordered top-K list `L_u` and nonempty binary relevant set `G_u`:

- **Recall@K:** `|L_u intersect G_u| / |G_u|`.
- **Precision@K:** `|L_u intersect G_u| / K`. A short list is padded with misses through rank K, so it is not rewarded for returning fewer items.
- **HitRate@K:** 1 if any recommendation is relevant, else 0.
- **DCG@K:** sum of `1[item at rank r is in G_u] / log2(r + 1)` for r = 1..K; missing ranks contribute zero.
- **IDCG@K:** sum of `1 / log2(r + 1)` for r = 1..min(K, |G_u|).
- **NDCG@K:** DCG / IDCG.

Macro-average equally across the defined customers; do not overweight large buyers. Also report median and cohort counts. For users without in-catalog positives, report an exclusion count rather than an undefined metric silently replaced with zero.

- **Catalog coverage@K:** unique recommended items / catalog size over the primary cohort. Empty catalog makes coverage unavailable, not zero success.
- **Future item coverage:** future unique customer-item pairs whose items are in C / all eligible future customer-item pairs, including cold-start customers.
- **Fallback item share:** popularity-filled items / all returned items in the primary cohort.
- **Personalized customer share:** primary-cohort customers with at least one nonfallback item / primary-cohort customers.
- Repeat/new-product splits use their own cohorts and denominators.

Verify a custom sparse-friendly metric implementation against hand-calculated rankings. The sklearn NDCG reference is useful, but its default score-tie averaging differs from this project's deterministic StockCode ranking; do not compare tied scores without aligning the convention.

## 7. Uncertainty and promotion

1. Use 1,000 paired customer bootstrap resamples, seed 42, to compute 95% percentile intervals for mean NDCG@10 and candidate-minus-baseline NDCG@10. Use identical customer draws for both models.
2. Promote CF on validation only if relative NDCG gain is >= 10%, mean Recall@10 is not below the strongest baseline and the lower endpoint of the paired difference interval is > 0.
3. If the strongest baseline NDCG is zero, relative uplift is unavailable; promotion requires positive CF NDCG, nondecreasing Recall and a positive lower difference interval. Explicitly report this exceptional rule.
4. If CF does not qualify, freeze the strongest popularity baseline as the serving choice. Keep CF experiment results in the report.
5. If the chosen model underperforms on final test, retain the frozen evaluated model and disclose the result. A later model change requires a new experiment and an independent future holdout; it cannot be presented as the original locked test.

Catalog coverage >= 10% is a **diagnostic aspiration**, not a reason to switch models after test inspection.

## 8. Tracking and outputs

Record dataset/config/lock hashes, cutoffs, model family, params, seeds, code revision when available, cohort definitions, runtime, memory and all metrics in local MLflow.

Required reports:

1. `reports/cluster_comparison.csv` and `reports/segment_profiles.csv`.
2. `reports/validation_metrics.json` and recommendation comparison table.
3. `reports/selection.json`, frozen before final-test fitting and evaluation.
4. `reports/test_metrics.json`, cohort counts, per-customer metrics and bootstrap intervals.
5. `reports/evaluation.md`: method, actual results, baselines, missed targets, coverage and limitations.
6. Updated [model card](MODEL_CARD.md).

## 9. Prohibited shortcuts

- Random transaction-row splits or a single full-data customer profile reused across cutoffs.
- Calculating the catalog, item support, popularity, product descriptions or scaler using future purchases.
- Hiding fallback users or excluding hard-to-recommend customers from only one model.
- Evaluating with sampled negatives while claiming full-catalog ranking quality.
- Comparing repeat and new-product metrics using different unstated denominators.
- Selecting clusters or models using final-test performance.
- Treating no purchase as a confirmed negative exposure, or offline gains as campaign impact.

