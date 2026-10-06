# 00. Start Here

## 1. Project identity

| Field | Value |
|---|---|
| Project | 05 — RetailMind |
| Purpose | Customer segmentation and product recommendations from retail purchases |
| Owner | ZeeqRyz |
| Date | 06 October 2026, Asia/Kuala_Lumpur |
| Status | **Implementation & Validation Complete** |
| Release Version | `0.1.0-release` |
| Primary Dataset | UCI Online Retail (541,909 raw rows, 390,859 cleaned eligible purchases) |

## 2. Working assumptions

1. This is a solo portfolio project with a local, analyst-facing dashboard and production CLI.
2. Official UCI Online Retail data source is downloaded, verified (`43465A06F2CCF7C8B5BD2892BC7DEFB52F97487934FE93B16AE4C3936424676D`), cleaned, and audited locally.
3. Local CPU execution is default and optimal. All latency targets are verified on local CPU (p95 warm latency: 3.45 ms).
4. Targets are evaluated against rigorous temporal holdouts with paired bootstrap confidence intervals.
5. All 14 tasks (T01–T14) and checkpoints are fully implemented, tested, and verified.

## 3. Reading order

1. This file, [AGENTS.md](../AGENTS.md), [progress](09_PROGRESS_LOG.md), [decisions](08_DECISIONS_LOG.md) and [tasks](../tasks/todo.md).
2. [Problem & Objectives](01_PROBLEM_AND_OBJECTIVES.md) and [PRD](02_PRD.md).
3. [Data rules](05_DATA_SPEC.md) and [experiment rules](06_EXPERIMENT_PLAN.md).
4. [Technical design](04_TECHNICAL_DESIGN.md), [validation](10_VALIDATION_AND_DELIVERY.md), [Model Card](MODEL_CARD.md), and [Evaluation Report](../reports/evaluation.md).

## 4. Verified Run Commands

The complete pipeline is operational and tested via the local virtual environment:

```powershell
Set-Location 'C:\Users\ZeeqRyz\Desktop\Ai-ML\Machine Learning Projects\05_RetailMind_Customer_Segmentation_Recommender'

# 1. Environment & dependencies
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .

# 2. Data acquisition & cleaning
.\.venv\Scripts\python.exe -m retailmind.cli download --config configs/default.yaml
.\.venv\Scripts\python.exe -m retailmind.cli prepare --config configs/default.yaml

# 3. Validation & selection freeze
.\.venv\Scripts\python.exe -m retailmind.cli train --stage validation --config configs/default.yaml
.\.venv\Scripts\python.exe -m retailmind.cli freeze --config configs/default.yaml

# 4. Final test refit & evaluation
.\.venv\Scripts\python.exe -m retailmind.cli train --stage test --config configs/default.yaml

# 5. Production inference & monitoring
.\.venv\Scripts\python.exe -m retailmind.cli recommend --customer-id 17850 --top-k 10 --bundle artifacts/release
.\.venv\Scripts\python.exe -m retailmind.cli benchmark --bundle artifacts/release --calls 200
.\.venv\Scripts\python.exe -m retailmind.cli monitor --reference reports/reference.json --current reports/current.json

# 6. Analyst Dashboard
.\.venv\Scripts\python.exe -m streamlit run app/dashboard.py

# 7. Quality Gates
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
```

## 5. Document ownership

Requirements belong in the PRD; data rules in the data specification; model rules in the experiment plan. The task checklist owns task status. The progress log owns evidence. Update the owner document when a decision changes, then record why in the decision log.
