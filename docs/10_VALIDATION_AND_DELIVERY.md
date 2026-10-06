# 10. Validation and Delivery

## 1. Verification strategy

Use small synthetic fixtures for correctness and official historical data for model assessment. Tests must cover behavior that could change a customer profile, recommendation or evaluation result. Avoid tests that only reproduce implementation internals.

| Area | Meaningful checks | Requirements |
|---|---|---|
| Acquisition / schema | Invalid download, missing columns, nonfinite values and canonical IDs | FR01, NFR06 |
| Cleaning | Cancellations, nonpositive quantities/prices, missing IDs, exact duplicate handling and count/value reconciliation | FR01, FR03 |
| Time safety | Exact cutoff, future-row invariance and no future product description/catalog/support | FR02, FR12, NFR01 |
| RFM | Multiple product lines in one order, 180-day boundary, active/inactive/unknown states | FR03 |
| Segments | Quantile ties, stored scaler/cutpoints, deterministic mapping, size/stability gates and rule fallback | FR04, FR05 |
| Popularity / CF | Hand-calculated binary matrix, support filtering, zero diagonal, unique lists, score ties and fallback | FR06–FR08 |
| Evaluation | Hand-ranked NDCG/Recall/Precision, short lists, full candidate catalog and mode-specific cohorts | FR06, FR09, FR12, NFR08 |
| Freeze protocol | Missing/mismatched config/data manifest, validation-only selection and immutable evaluated artifact | FR11–FR13, NFR03 |
| Service | Invalid ID/K/mode, missing/corrupt bundle, unknown customer and CLI/dashboard parity | FR07–FR11, NFR01, NFR06 |
| Exports | Display/export row parity, reason fields, Unicode and formula-like string protection | FR10, NFR07 |
| Packaging | Locked dependency consistency, local CI-equivalent checks and Docker smoke test | FR14, NFR05 |
| Performance | Warm local p95, startup measured separately and memory dimensions recorded | NFR02, NFR04 |
| Diagnostics | Unchanged, shifted and empty snapshots with explained heuristic flags | FR15, Should |

## 2. Model evidence

The final evaluation report must include:

1. Source hash, cleaned inclusion/removal counts and exact temporal cutoffs.
2. Segmentation comparison, stable labels, customer shares and median R/F/M.
3. Two popularity baselines, CF results and the frozen serving choice.
4. Known-customer and cold-start cohorts with counts, exclusions and full-catalog definitions.
5. Repeat-allowed and new-product-only metrics, each with its own cohort.
6. NDCG@10, Recall@10, Precision@10, HitRate@10, paired confidence interval, coverage and fallback share.
7. Comparison of actual results with targets, including failed criteria.
8. A clear statement that no live conversion, retention or revenue experiment was performed.

A trained model, notebook screenshot or configuration file alone does not prove the dashboard or container works.

## 3. Dashboard browser checks

Inspect the real running page at desktop width and a narrow approximately 390-pixel viewport. Record the tested browser, screen sizes and app/bundle versions. Use the applicable Streamlit and browser-testing skills when implementation reaches this task.

1. With no bundle, the page gives a readable setup message and does not expose an exception traceback to the analyst.
2. Overview shows the historical date, customer population and GBP units. Segment totals reconcile to the snapshot population.
3. A known active demo customer displays the correct RFM values, segment and explanation.
4. A known inactive demo customer is labeled inactive and still follows the documented recommendation/fallback path.
5. An unknown customer gets popularity with an explicit unknown/fallback status.
6. Switching to `new_items_only` removes every previously purchased item from both CF and fallback lists.
7. K = 1, 10 and 20 behave correctly, including a catalog with fewer items than K.
8. Segment and recommendation CSVs match the displayed rows, preserve Unicode and safely handle formula-like text.
9. Controls can be reached by keyboard, tables remain readable, and empty states explain the next action.
10. CLI and page ranks are identical for the same customer, mode, K and bundle.

If browser inspection cannot be performed, record the limitation. Do not describe screenshots, responsiveness or runtime behavior as verified without inspecting them.

## 4. Batch diagnostics

Use snapshot summaries produced by the same feature/service code:

- R/F/M: count, median, quartiles and missing/unknown share.
- Segment shares: absolute percentage-point changes. Compare IDs directly only within the same segment-model version; cross-version changes require profile alignment and an explicit warning.
- Catalog: counts of additions/removals and Jaccard overlap.
- Fallback: percentage-point change in fallback item share.

Initial review heuristics: a median R/F/M relative change > 25% where reference median is nonzero; a segment share change > 10 percentage points within the same version; catalog overlap < 0.70; fallback share increase > 10 percentage points. When a reference median is zero, report the absolute change and do not divide by zero.

These thresholds are assumptions for review, not statistical proof of drift or a trigger for automatic retraining. Record reference/current periods and known seasonal differences.

## 5. Performance protocol

1. Record CPU, RAM, OS, Python version, lock hash, model version and catalog/history sizes.
2. Load the trusted bundle once; record load time separately.
3. Run 10 untimed warm-up requests, then 200 timed single-customer requests across a deterministic mix of active, inactive and unknown customers.
4. Time only the service call with K=10 in repeat-allowed mode, excluding browser rendering, startup and filesystem export.
5. Save median, p95, maximum and raw durations in `reports/latency.json`; aim for p95 <= 200 ms.
6. Keep the benchmark out of CI's pass/fail tests because hardware varies. The local release report owns performance evidence.

The planned `benchmark` CLI subcommand is created with the service in T10 and executed during T14:

```powershell
.\.venv\Scripts\python.exe -m retailmind.cli benchmark --bundle artifacts/release --top-k 10 --warmup 10 --calls 200 --output reports/latency.json
```

The command must validate that the selected synthetic/known customer mix exists in the loaded bundle and record the actual IDs/status counts used. Do not benchmark an unavailable fixture ID and silently treat it as a known customer.

## 6. Local delivery gate

At T14, create `reports/validation.md` with one evidence row for every Must FR and NFR, including the test/report path, date and outcome.

1. All meaningful tests and Ruff pass in the locked environment.
2. A clean environment install and documented pipeline replay work with the official data source.
3. Frozen evaluation artifacts and actual results are traceable and reproducible.
4. Mandatory real-browser flows and export contents are inspected.
5. Docker builds and launches with the release bundle mounted read-only. Missing-bundle behavior is also checked.
6. CI configuration performs tests/Ruff using synthetic fixtures. Report hosted CI as unverified until it actually runs on an authorized remote repository.
7. README and model card contain measured results or explicitly unavailable fields; targets never masquerade as results.
8. Any Should deferral is recorded in `tasks/todo.md` and the progress log.

An unavailable mandatory check is an unresolved delivery item, not a passed requirement. The planning package itself does not require implementation checks to run.

## 7. Three-minute demo script

1. Explain the analyst's two decisions and show the historical date/context.
2. Compare segment size and median R/F/M; explain one campaign hypothesis.
3. Inspect a known customer's history and top-10 product list; identify a historical supporting product.
4. Show unknown-customer fallback and switch to the new-product view.
5. Export the displayed list.
6. Show the baseline comparison and describe either measured gain or why the baseline won.
7. State that a live campaign experiment would be needed to measure conversion or revenue effects.

## 8. Portfolio packaging

After local implementation, prepare source, tests, synthetic fixtures, run commands, an architecture diagram, the evaluated model card and useful aggregate results. Attribute the source dataset.

Keep raw customer-level transactions, machine-local paths, environments, caches, tracking databases and large generated artifacts out of the default source package. Provide the official acquisition workflow instead. Publishing to GitHub or a demo host is a later authorized action and is not part of this planning request.

