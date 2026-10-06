# 05. Data Specification

## 1. Source and provenance

Primary dataset: **UCI Online Retail**. Verified source metadata, license, citation and acquisition page are in [the source register](12_SOURCES.md). The file has not been downloaded during planning.

On acquisition, preserve the original XLSX in `data/raw/`, record its SHA-256, retrieval time and official source URL, and never overwrite it with cleaned data. Read the XLSX with openpyxl via pandas; this is data ingestion, not spreadsheet authoring.

The official metadata's missing-value flag is not sufficient for this project. Audit the actual file. Do not copy commonly reported missingness counts from tutorials as measured results.

## 2. Raw schema

| Field | Parsing rule | Use |
|---|---|---|
| `InvoiceNo` | Trimmed uppercase string; preserve identifier semantics | Order grouping and cancellation detection |
| `StockCode` | Trimmed uppercase string | Product identity, never ordinal input |
| `Description` | Trimmed nullable text | Historical display label only |
| `Quantity` | Finite integer | Purchase eligibility and value calculation |
| `InvoiceDate` | Parsed timestamp | History / holdout partition |
| `UnitPrice` | Finite numeric value, GBP | Purchase value |
| `CustomerID` | Nullable canonical string; normalize integral numeric forms without `.0`; reject fractional numeric IDs | Customer grouping, never a feature |
| `Country` | Trimmed nullable text | Descriptive slicing only |

- Require the listed columns; record unexpected columns rather than treating them as features.
- Interpret source timestamps in their recorded clock without converting them to UTC. The source timezone is not asserted here. Cutoffs use the same naive clock.
- Missing descriptions may use StockCode for display. Missing country may use `Unknown` for descriptive summaries.
- Validate malformed numeric and timestamp values. Quarantine affected rows with a reason; a missing required column is a hard failure.

## 3. Cleaning contract

Apply rules in this order and record disjoint removal counts. Preserve an audit of raw and retained rows so counts reconcile.

1. Canonicalize identifiers and parse types.
2. Quarantine rows with invalid/missing core timestamp, invoice, stock code, quantity or price, and malformed nonmissing CustomerID. Missing CustomerID follows rule 4.
3. Remove exact duplicates across all eight canonical raw fields, retaining the first. Record this as an explicit deduplication assumption; do not deduplicate merely by invoice/product pair.
4. Exclude missing CustomerID from customer modeling; report their count and purchase value separately as anonymous data.
5. Exclude cancellation invoices whose InvoiceNo begins with `C` and nonpositive Quantity rows. Record both cancellation and quantity attributes even though the primary removal reason is exclusive.
6. Exclude nonpositive UnitPrice rows.
7. Keep merchandise codes matching `^[0-9]{5}[A-Z]?$` for the initial MVP. Record all excluded code patterns and examples from the training prefix. T03 must check this policy against observed merchandise descriptions before model selection and document any correction.
8. Calculate `purchase_value_gbp = Quantity * UnitPrice`; require finite positive values.

RFM monetary value is **retained positive purchase value**, not net revenue or profit. Returns and cancellation handling is an explicit simplification. Do not later subtract returns inconsistently in one path.

Do not clip or remove large positive orders automatically. Inspect their effect using training history; report wholesale concentration and optional sensitivity analysis. Any winsorization choice must be fixed using training history before validation outcomes are inspected.

## 4. Time protocol

| Stage | History available to fitting | Future purchase label interval |
|---|---|---|
| Validation | Timestamp < `2011-10-15 00:00:00` | `[2011-10-15, 2011-11-12)` — 28 days |
| Final test | Timestamp < `2011-11-12 00:00:00` | `[2011-11-12, 2011-12-10)` — 28 days |

Use half-open intervals: include start, exclude end. A purchase exactly at cutoff belongs to the future period. The test-end boundary follows the published source period; the last recorded day may be incomplete and must be disclosed.

1. Prepare deterministic partitions before fitting any learned transformation or popularity count.
2. T03 exploratory analysis uses the validation-training prefix only. Whole-file schema, timestamp range, hash and structural counts may be inspected for integrity; future item preferences and outcomes remain unavailable for tuning.
3. Validation selects the model settings. Freeze them, then refit using all history before the final-test cutoff.
4. The final test is for assessment, not parameter selection.
5. If dates or eligible cohorts are unsuitable, document the issue before modeling and request direction for a material protocol change. Never shift a split after inspecting test performance.

## 5. RFM profiles

For a snapshot cutoff `t`, use eligible purchases in `[t - 180 days, t)`.

| Feature | Definition |
|---|---|
| Recency | Floor of `(t - latest eligible purchase timestamp)` in days |
| Frequency | Count of **distinct InvoiceNo**, not product lines |
| Monetary | Sum of eligible `purchase_value_gbp` in the window |

- Validation RFM window starts `2011-04-18`; test RFM window starts `2011-05-16`.
- Active customer: at least one eligible purchase inside the RFM window.
- Known inactive customer: prior eligible history exists but no purchase inside the window. Frequency and window monetary are zero; recency comes from the latest purchase in all prior history. Do not feed inactive profiles into the learned cluster model.
- Unknown customer: no eligible prior history. RFM values and segment are unavailable rather than fabricated zeros.
- Cluster predictors are R, F and M only. CustomerID, StockCode, Country and future purchases are not clustering predictors.
- For learned clusters use `log1p` on nonnegative R/F/M followed by StandardScaler. Fit the scaler on active training profiles only, persist it and reuse it during serving.

## 6. RFM-rule baseline

Learn the 25th, 50th and 75th percentile cutpoints per R/F/M feature from active training customers. Persist those cutpoints.

- Compute bin `1 + searchsorted(cutpoints, value, side='right')`, producing scores 1–4.
- Reverse the recency bin: `recency_score = 5 - bin`. Larger scores then mean more recent, more frequent or higher spending.
- Equal cutpoints may collapse score ranges. Do not rank tied customers arbitrarily to force equal-size bins.

In the rules below, R, F and M mean the **1–4 scores**, not the raw feature values. Apply these mutually exclusive rules in order:

1. R >= 3, F >= 3 and M >= 3: `recent_frequent_high_spend`.
2. R <= 2 and M >= 3: `less_recent_high_spend`.
3. R >= 3 and F <= 2: `recent_occasional`.
4. Otherwise: `other_active`.

Inactive and unknown statuses remain separate. Score cutpoints and labels are versioned per bundle.

## 7. Recommendation history and catalog

The recommender uses **all eligible history before cutoff**, while RFM uses the last 180 days. This distinction is intentional.

A product is eligible for a snapshot catalog only when:

1. It passes the merchandise and positive-purchase rules.
2. At least 5 distinct customers bought it before cutoff.
3. It has at least one eligible purchase in `[cutoff - 90 days, cutoff)`.

This is a historical activity rule, **not proof of current stock availability**. Report catalog size and the fraction of future purchases excluded by this rule.

- Create a binary sparse matrix: `interaction[customer, item] = 1` if the customer bought that catalog item before cutoff. Quantity and value do not create ratings.
- Item mappings, support counts and descriptions derive solely from the history prefix.
- Product description is the latest nonempty description before cutoff. Resolve timestamp ties deterministically using invoice ID and description text.
- Global popularity ranks items by distinct purchasing customers in the last 90 days, then StockCode ascending.
- Segment popularity uses the same window, restricted to current active customers in that segment. Inactive / unknown segments fall back to global popularity.
- Repeat purchase recommendations are allowed. The `new_items_only` view removes every previously purchased product from candidate and fallback lists.

## 8. Required data outputs

1. `reports/data_provenance.json`: source, hash, retrieval time, schema and source period.
2. `reports/data_quality.json`: split-specific inclusion/removal counts, missingness and purchase-value reconciliation.
3. `data/processed/purchases.parquet`: canonical eligible purchases with provenance columns.
4. Per-stage snapshot profiles, catalog and customer/item mappings with exclusive cutoff metadata.
5. Synthetic fixture with known cancellations, missing IDs, duplicate lines, same-order multiple products, inactive customers and boundary timestamps.

The full purchase file may contain future rows; snapshot builders must explicitly restrict by cutoff. Training tests must fail if future rows change any fitted output.

## 9. Required invariants

- `max(history_timestamp) < cutoff` for every fitted snapshot.
- Every active profile has Frequency >= 1 and Monetary > 0.
- A two-line invoice adds one order to Frequency.
- Sum of active customer monetary values equals eligible purchase value in the matching 180-day window within GBP 0.01.
- Every recommendation belongs to the snapshot catalog and is unique within its list.
- `new_items_only` lists contain no item in the customer's prior history.
- Adding future rows cannot change training RFM, scaler, catalog, descriptions, popularity or similarities.

