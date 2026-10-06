# 02. Product Requirements Document

| Field | Value |
|---|---|
| Product | RetailMind |
| Version | Implementation verified v2.0 |
| Owner | ZeeqRyz |
| Date | 06 October 2026 |
| Status | **Completed, Verified and Delivered (v0.2.0)** |
| Product goal | Help an analyst understand customer groups and inspect useful product recommendations |

## 1. Product summary

RetailMind converts historical retail transactions into RFM customer profiles, descriptive customer segments and ranked product recommendations. A local Streamlit dashboard lets an analyst review segments, inspect a customer and export the resulting tables. Python commands reproduce preparation, model comparison and final evaluation.

The MVP is a decision-support prototype. It does not send campaigns, estimate causal revenue uplift or integrate with a live store.

## 2. User stories

| ID | As a user, I want to... | So that... | Priority |
|---|---|---|---|
| US1 | Compare customer groups by recency, frequency and spending | I understand how their behavior differs | Must |
| US2 | See the evidence behind a segment label | I can assess whether the label makes sense | Must |
| US3 | Inspect a customer's top-10 recommendations | I can review a product shortlist | Must |
| US4 | See why each item was recommended and whether a fallback was used | I understand the recommendation's basis | Must |
| US5 | Get sensible results for a new customer | The workflow remains usable without purchase history | Must |
| US6 | Export segment and recommendation tables | I can use them in a later analysis | Must |
| US7 | Compare personalization with popularity using a future period | I can assess added value | Must |
| US8 | Review reference-versus-current diagnostics | I can identify a dataset or behavior change | Should |

## 3. Scope

### 3.1 Mandatory MVP

1. Official dataset acquisition, provenance and data-quality report.
2. Chronological snapshots and RFM profiles.
3. Rule-based RFM baseline, K-Means and GMM comparison.
4. Global popularity, segment popularity and item-item collaborative filtering comparison.
5. Known-customer and cold-start recommendation paths.
6. Locked temporal evaluation and a model card with actual results.
7. CLI, Streamlit dashboard, CSV exports and synthetic demo fixture.
8. Meaningful tests, experiment tracking, Docker support, CI configuration and run instructions.

### 3.2 Planned secondary capability

- A batch diagnostic report for RFM distributions, segment shares, catalog churn and fallback rate. It flags review needs, without automatically retraining or claiming that drift establishes model failure.

### 3.3 Outside MVP

- FastAPI service, cloud hosting, paid infrastructure and public deployment.
- ALS / neural recommenders, LLM explanations, feature stores and streaming.
- Real customer uploads, account login, campaign sending, payments and CRM integration.
- Inventory-aware recommendations, profit optimization, CLV prediction and causal A/B analysis.
- Movie recommendations or a second primary dataset.

The spreadsheet's generic engineer checklist includes API serving and cloud deployment. Project 5 specifically calls for a Streamlit dashboard. The MVP uses a shared local service plus CLI and dashboard; API and cloud work remain optional extensions.

## 4. Functional requirements

| ID | Requirement | Acceptance criteria | Owner document |
|---|---|---|---|
| FR01 | Acquire and validate data | Record official URL, retrieval date, SHA-256 and source license; reject missing columns and malformed core values; report exclusions by reason | Data spec |
| FR02 | Produce time-safe snapshots | Every feature, catalog entry and popularity count uses timestamps strictly before its cutoff; time-boundary tests pass | Data spec |
| FR03 | Compute RFM profiles | One profile per active customer; frequency counts distinct invoices; monetary uses eligible positive purchase value; inactive known customers are separately labeled | Data spec |
| FR04 | Compare segments | Evaluate rule-based RFM, K-Means and GMM; provide size, silhouette, stability and median RFM; apply declared fallback rules | Experiment plan |
| FR05 | Explain segments | Each segment has an evidence-based description and campaign hypothesis; labels are versioned and do not imply churn probability | Technical design |
| FR06 | Compare recommendation models | Evaluate two popularity baselines and collaborative filtering on identical cohorts and catalog rules | Experiment plan |
| FR07 | Recommend for known customers | Return up to K unique eligible items, ranked deterministically, with reason code, contribution information and fallback status | Technical design |
| FR08 | Handle cold start and edge cases | Unknown IDs use global popularity and `unknown_customer` status; empty / insufficient catalog returns a clear status, not an exception or fabricated products | Technical design |
| FR09 | Support repeat and new-product views | Primary evaluation allows repeats; secondary new-product view filters previously bought items and recomputes its evaluation cohort | Experiment plan |
| FR10 | Deliver dashboard | Analyst can view segment overview, choose a demo customer, inspect RFM and recommendations, switch view and download CSVs; missing bundle has a readable setup message | Validation |
| FR11 | Reproduce execution | Documented Windows commands reproduce preparation, training, evaluation and recommendation; artifacts identify their config, input hash and cutoff | Start guide |
| FR12 | Preserve final-test integrity | Freeze choices before test fitting and scoring; test labels never influence selections; failed targets and attempted reruns are disclosed | Experiment plan |
| FR13 | Record experiments | Each run records model, seed, params, split, dataset hash, metrics, cohort counts and artifact locations in local MLflow | Technical design |
| FR14 | Package results | Tests, Ruff, CI and Docker smoke checks have evidence; model card and README distinguish measured results from targets | Validation |
| FR15 | Provide batch diagnostics | Report reference/current distribution and catalog changes with thresholds labeled as review heuristics | Validation; Should |

## 5. Non-functional requirements

| ID | Requirement | Acceptance criteria |
|---|---|---|
| NFR01 | Correctness | No future information enters fitted artifacts; CLI and dashboard rank parity tests pass |
| NFR02 | Responsiveness | Warm recommendation p95 <= 200 ms, 200 calls, single process, hardware recorded; startup measured separately |
| NFR03 | Reproducibility | Seed and data/config hashes recorded; same locked environment reproduces metrics within 1e-6 |
| NFR04 | Resource control | CPU-first; sparse interactions; item similarities computed in blocks and retained as bounded neighbors; no full customer-item dense matrix |
| NFR05 | Maintainability | Reusable typed modules, minimal UI logic, meaningful test fixtures, Ruff clean |
| NFR06 | Input and artifact safety | Validate IDs and K; load only a trusted local bundle; no uploaded pickle/joblib models; no secrets or raw records in logs |
| NFR07 | Usability | Visible data date, GBP units, recommendation mode, empty states and fallback labels; readable tables and keyboard-accessible controls |
| NFR08 | Evidence quality | No claim of real conversion / revenue impact; all cohort denominators and unserved cases reported |

## 6. Dashboard workflow

1. **Overview:** display the snapshot date, active / inactive customer counts, segment table and median RFM comparison.
2. **Customer:** select a synthetic demo or local historical customer; show status, RFM values and the segment description.
3. **Recommendations:** select K in 1–20 and mode `repeat_allowed` or `new_items_only`; display product, rank, reason and fallback tag.
4. **Exports:** download the displayed segment summary or selected customer's recommendations. Raw transaction export is outside the dashboard.
5. **Evidence:** link to the evaluation summary, model card and limitations. A metric target must never appear as a measured result.

## 7. Output contract

The Python service and CLI response contain:

```json
{
  "customer_id": "DEMO-001",
  "customer_status": "known_active",
  "segment_id": "SG01",
  "segment_label": "derived from measured RFM profile",
  "snapshot_cutoff": "2011-11-12T00:00:00",
  "recommendation_mode": "repeat_allowed",
  "requested_k": 10,
  "returned_k": 1,
  "status": "insufficient_catalog",
  "model_version": "example-only",
  "items": [
    {
      "rank": 1,
      "stock_code": "90001",
      "description": "Synthetic fixture product",
      "score": 0.25,
      "reason_code": "similar_to_purchase_history",
      "reason_text": "Similar purchase pattern to a product in your history",
      "supporting_stock_codes": ["90002"],
      "is_fallback": false
    }
  ]
}
```

This is a synthetic contract example, **not a prediction or source-data row**. Exact types, statuses and CSV fields are specified in [the technical design](04_TECHNICAL_DESIGN.md). `score` values are internal ranking values; do not compare scores across different algorithms.

## 8. Acceptance and release

1. All Must requirements pass with recorded evidence in `reports/validation.md` and the progress log.
2. Model selection follows the frozen protocol. A baseline release is acceptable if complex models do not qualify.
3. The temporal evaluation reports cohort sizes, baseline results, uncertainty, coverage and missed targets.
4. The dashboard's required flows are inspected in a real browser.
5. A clean local setup and Docker smoke check are demonstrated, or the exact unresolved dependency is recorded and delivery remains incomplete for that requirement.
6. Publication is a separate authorized action; local completion does not imply a public launch.

## 9. Verified checks and release criteria

- Source-data schema, counts (541,909 raw rows, 390,859 eligible purchases), missingness, and cancellations were fully audited in T02–T03.
- Eligible customer and item cohorts were verified for both validation prefix (<2011-10-15) and final test prefix (<2011-11-12).
- Local Python 3.11.9 environment and Docker configuration were verified in T01 and T13.
- All 15 Functional Requirements and 8 Non-Functional Requirements have passed with evidence in `reports/validation.md`.


