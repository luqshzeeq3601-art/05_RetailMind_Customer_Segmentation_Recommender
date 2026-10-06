# 08. Decisions Log

## 1. Initial decisions — 06 October 2026

| ID | Decision | Reason / consequence |
|---|---|---|
| D001 | Prepare Project 5 despite Project 3 being next in the suggested order | Explicit user selection; no folder for Projects 3 or 4 is created |
| D002 | Name the project RetailMind | Describes retail customer understanding and product recommendations |
| D003 | Propose UCI Online Retail as the single primary dataset | Supports RFM and implicit purchase recommendations in one business context; actual file audit remains T02–T03 |
| D004 | Keep historical UK context and GBP currency | Avoid relabeling source data as Malaysian transactions or inventing currency conversion |
| D005 | Use RFM rules, K-Means and GMM | Baseline plus understandable unsupervised alternatives with measurable stability |
| D006 | Compare global popularity, segment popularity and item-based CF | Establish added value without unnecessary neural infrastructure |
| D007 | Use a 180-day RFM window and all-prefix recommendation history | Recent customer profiles with sufficient implicit interaction history; both obey the same exclusive cutoff |
| D008 | Use two fixed 28-day future periods | Time-safe validation and final-test assessment with frozen choices |
| D009 | Allow repeat purchases in the primary task | Retail repeat purchasing is relevant; new-product-only results are separately defined |
| D010 | Serve baseline models if learned candidates fail selection rules | Preserve usable, honest results rather than forcing complexity |
| D011 | Local CLI plus Streamlit MVP; API/cloud optional | Matches the specific Project 5 dashboard add-on and keeps delivery bounded |
| D012 | Build the dashboard on a shared service | Avoid training/serving differences and duplicate feature logic |
| D013 | Keep implementation status only in tasks/todo.md | Prevent contradictory task lists across documents |
| D014 | Leave the spreadsheet unchanged | User asked to check it; user completion statement is recorded without editing workbook statuses |
| D015 | Planning only in this request | Implementation begins after a later start instruction; no data download, installation, training or publication now |
| D016 | Use explicit merchandise and positive-purchase rules | A reproducible MVP simplification; verify patterns before model selection and disclose returns/wholesale limits |
| D017 | Preserve the final-test-cutoff bundle as release artifact | Keep evaluated behavior traceable; latest-data refit is outside MVP |

## 2. Implementation & Audit Decisions — 06 October 2026

| ID | Decision | Reason / consequence |
|---|---|---|
| D018 | Enforce 0.01 silhouette tolerance rule selecting K-Means ($K=3$) | In validation candidate comparison, K-Means K=3 (mean silhouette 0.3317) is within 0.01 of K=4 (0.3402) and wins on near-perfect stability (median pairwise ARI 0.9992 vs 0.9880) and cluster parsimony |
| D019 | Promote Item-Item Collaborative Filtering ($N=50$) over baselines | Achieved NDCG@10 of 0.1725 on validation (+74.26% uplift vs SegmentPop 0.0990) with strictly positive 95% bootstrap difference CI `[0.0619, 0.0850]` |
| D020 | Retain `ItemItemCF_N50` on final test holdout | Final test holdout achieved NDCG@10 of 0.1698 (vs frozen baseline SegmentPop 0.1211, +40.29% uplift, 95% bootstrap CI diff `[0.0368, 0.0606]`; vs GlobalPop 0.1253, +35.50% uplift), confirming selection generalization |
| D021 | Implement Playwright Chromium headless end-to-end testing | Verifies desktop and mobile viewports, interactive recommendation generation, and CSV download buttons automatically |
| D022 | Include RFMRules and New-Product Baselines in evaluation outputs | Added RFMRules baseline evaluation (silhouette 0.2311) to `cluster_comparison.csv` and `GlobalPopularity_NewItemsOnly` / `SegmentPopularity_NewItemsOnly` baselines to test holdout metrics |
| D023 | Document MO1 target as missed honestly | Target silhouette was $\ge 0.35$; achieved score is 0.3317. Documented honestly across all reports and model cards without changing thresholds post-hoc |
