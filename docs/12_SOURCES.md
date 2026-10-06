# 12. Source Register

## 1. Local spreadsheet evidence

Workbook from this document: `../../Classical_ML_Portfolio_Plan_Malaysia.xlsx`, inspected read-only on **06 October 2026**.

| Location | Observed content | Planning consequence |
|---|---|---|
| `Project Tracker!A1` | Suggested order: 2 > 1 > 3 > 4–6 | Project 3 is the next suggested sequence item; user requested Project 5 |
| `Project Tracker!A6:F6` | Project 3: demand forecasting + inventory optimisation | Mentioned as next in the suggested sequence, not prepared here |
| `Project Tracker!A8` | 5 | Folder number |
| `Project Tracker!B8` | Customer segmentation + recommender | Primary project scope |
| `Project Tracker!C8` | Astro, PetBacker | Spreadsheet's portfolio employer context only |
| `Project Tracker!D8` | K-Means/GMM, RFM, collaborative filtering | Planned techniques |
| `Project Tracker!E8` | Streamlit dashboard | Mandatory user interface |
| `Project Tracker!F8` | Online retail / MovieLens | Chose retail to keep both capabilities in one domain |
| `Project Tracker!G4:G9` | All projects show Not started | Stale relative to the user's completion report for Projects 1 and 2 |
| `Engineer Checklist!A4:A11` | Repo, results, tracking, API, Docker, deployment, monitoring and business impact | Adapt to local Project 5 scope; API/cloud optional; impact must be measured honestly |

Workbook SHA-256 before document creation:

`DEA7706770BFFAF9980015F15225121AF2AF18744871109EE0412D7B3B781900`

No workbook status, date, formula, layout or link was edited.

## 2. Dataset reference

- [UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online%2Bretail), verified 06 October 2026.
- Publisher metadata: **541,909 transaction records**, eight listed columns, a UK retailer, **1 December 2010 to 9 December 2011**, prices in sterling.
- Cancellation invoices are indicated by a `C` prefix. The actual file's missingness and other quality issues require local audit.
- Citation: Chen, D. (2015). *Online Retail* [Dataset]. UCI Machine Learning Repository. [DOI: 10.24432/C5BW33](https://doi.org/10.24432/C5BW33).
- License: [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/), as stated on the UCI page. Attribute the dataset and document transformations.
- Acquisition must use the official page's download link. The binary download was not acquired or verified during planning; T02 records the actual URL and file hash.

Choosing this dataset is a project design decision. Its suitability is not proof of Malaysian market representativeness or expected recommendation gains.

## 3. Technical references

Official references checked during planning:

| Topic | Reference | Use in this project |
|---|---|---|
| K-Means cluster diagnostics | [sklearn silhouette example](https://scikit-learn.org/stable/auto_examples/cluster/plot_kmeans_silhouette_analysis.html) | Diagnose separation alongside size and stability |
| GMM | [GaussianMixture API](https://scikit-learn.org/stable/modules/generated/sklearn.mixture.GaussianMixture.html) | Candidate estimator and BIC diagnostics |
| Sparse item similarity | [cosine_similarity API](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.cosine_similarity.html) | Normalized similarity between product purchase vectors |
| Cluster stability | [adjusted_rand_score API](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.adjusted_rand_score.html) | Compare customer partitions independent of label numbering |
| Ranking evaluation | [ndcg_score API](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.ndcg_score.html) | Confirm normalization and tie-handling considerations |

The stable documentation URL may change over time. T01 must check the version actually installed and record matching documentation. These links do not pin a dependency version.

## 4. Evidence classification

1. **Observed:** workbook entries and official dataset metadata.
2. **User-reported:** Projects 1 and 2 are complete. Their runtime completion was not re-audited for this planning request.
3. **Designed:** project name, scope, features, time splits, promotion gates and work estimates.
4. **Unmeasured:** actual source quality, model results, latency, dashboard runtime, container behavior and business impact.

