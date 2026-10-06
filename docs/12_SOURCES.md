# 12. Source Register

## 1. Local spreadsheet evidence

Workbook from this document: `../../Classical_ML_Portfolio_Plan_Malaysia.xlsx`, verified on **06 October 2026**.

| Location | Observed content | Project consequence |
|---|---|---|
| `Project Tracker!A1` | Suggested order: 2 > 1 > 3 > 4–6 | Project 3 is the next suggested sequence item; user requested Project 5 |
| `Project Tracker!A6:F6` | Project 3: demand forecasting + inventory optimisation | Mentioned as next in the suggested sequence |
| `Project Tracker!A8` | 5 | Folder number |
| `Project Tracker!B8` | Customer segmentation + recommender | Primary project scope |
| `Project Tracker!C8` | Astro, PetBacker | Spreadsheet's portfolio employer context only |
| `Project Tracker!D8` | K-Means/GMM, RFM, collaborative filtering | Techniques implemented |
| `Project Tracker!E8` | Streamlit dashboard | User interface delivered and browser-verified |
| `Project Tracker!F8` | Online retail / MovieLens | Chose retail to keep both capabilities in one domain |
| `Project Tracker!G8:J8` | Status='Done', Dates='2026-10-06', GitHub Link | Updated upon verified completion in v0.2.0 |
| `Engineer Checklist!A4:A11` | Repo, results, tracking, API, Docker, deployment, monitoring and business impact | Local Project 5 scope delivered; results measured honestly |

Workbook SHA-256 before document creation:
`DEA7706770BFFAF9980015F15225121AF2AF18744871109EE0412D7B3B781900`

Row 8 updated upon verified completion with status `Done`, end date `2026-10-06`, and repository link.

## 2. Dataset reference

- [UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online%2Bretail), verified 06 October 2026.
- Publisher metadata: **541,909 transaction records**, eight listed columns, a UK retailer, **1 December 2010 to 9 December 2011**, prices in sterling.
- Citation: Chen, D. (2015). *Online Retail* [Dataset]. UCI Machine Learning Repository. [DOI: 10.24432/C5BW33](https://doi.org/10.24432/C5BW33).
- License: [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/), as stated on the UCI page.
- Acquired and verified file: `data/raw/Online Retail.xlsx` (SHA-256: `43465A06F2CCF7C8B5BD2892BC7DEFB52F97487934FE93B16AE4C3936424676D`).
- Cleaned dataset: 390,859 eligible purchases (£8,722,008.97 total spend) recorded in `reports/data_quality.json`.

## 3. Technical references

Official references checked and locked in environment:

| Topic | Reference | Use in this project |
|---|---|---|
| K-Means cluster diagnostics | [sklearn silhouette example](https://scikit-learn.org/stable/auto_examples/cluster/plot_kmeans_silhouette_analysis.html) | Diagnose separation alongside size and stability |
| GMM | [GaussianMixture API](https://scikit-learn.org/stable/modules/generated/sklearn.mixture.GaussianMixture.html) | Candidate estimator and BIC diagnostics |
| Sparse item similarity | [cosine_similarity API](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.cosine_similarity.html) | Normalized similarity between product purchase vectors |
| Cluster stability | [adjusted_rand_score API](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.adjusted_rand_score.html) | Compare customer partitions independent of label numbering |
| Ranking evaluation | [ndcg_score API](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.ndcg_score.html) | Confirm normalization and tie-handling considerations |

Environment locked on Python 3.11.9 with pinned dependencies in `requirements.lock`.

## 4. Evidence classification

1. **Observed:** workbook entries and official dataset metadata.
2. **User-reported:** Projects 1 and 2 are complete.
3. **Designed:** project architecture, feature pipelines, time splits, and selection rules.
4. **Measured & Verified:** 8-step data cleaning, RFM segmentation (Silhouette 0.3667, ARI 0.9973), collaborative filtering (NDCG@10 0.1698, +37.88% uplift), warm p95 latency (3.28 ms), and 26 passing automated tests.
