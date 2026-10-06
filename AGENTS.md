# RetailMind execution instructions

## 1. Communication

- Explain directly and briefly, using numbered points and useful bullets.
- Report what changed, the evidence, any limitation and the next ready task.
- Act as an ML engineer for correctness and a project manager for scope and delivery.

## 2. Begin each session

1. Read `docs/00_START_HERE.md`, `docs/09_PROGRESS_LOG.md`, `docs/08_DECISIONS_LOG.md` and `tasks/todo.md`.
2. Read the PRD and the technical, data or experiment sections relevant to the next ready task.
3. Inspect existing files and working changes. Preserve unrelated work and Projects 1 and 2.
4. A user instruction to start or continue authorizes the documented local implementation. Continue through ready tasks within the authorized session without repeated permission for routine steps.

## 3. Sources of truth

- Product scope and acceptance criteria: `docs/02_PRD.md`.
- Data, cleaning and temporal rules: `docs/05_DATA_SPEC.md`.
- Model selection and evaluation: `docs/06_EXPERIMENT_PLAN.md`.
- Architecture and interfaces: `docs/04_TECHNICAL_DESIGN.md`.
- Task status: **only** `tasks/todo.md`. Logs are evidence, not a second checklist.
- If documents conflict, resolve the conflict and record the decision before coding affected behavior. Direct user instructions take precedence.

## 4. Engineering rules

- Complete a bounded task, run its relevant checks, record evidence and select the next ready task.
- Put reusable logic in `src/retailmind/`. Keep notebooks exploratory and the dashboard thin.
- Use type hints, explicit configuration, seeded estimators and meaningful pytest tests.
- Check official documentation for installed versions. Pin a compatible environment in T01 and preserve its lock file.
- Use the same cleaning, feature and recommendation functions in training, CLI and dashboard.
- Split chronologically before fitting transformations, selecting catalog items, counting popularity or tuning models.
- Never use future transactions, future descriptions, test outcomes or CustomerID as model features.
- Never interpret cluster numbers as a natural ordering, similarities as probabilities or offline gains as revenue uplift.
- Never silently hide cohort exclusions, fallback recommendations, failed targets or short recommendation lists.
- Load only trusted project-generated model bundles. Never deserialize uploaded model files.
- Do not fabricate metrics, force clusters to look successful or retune after the final test result.

## 5. Scope and decisions

- Proceed with local setup, official data acquisition, analysis, training, tests, Docker and local dashboard work after implementation is requested.
- Resolve routine library and code organization choices within this plan autonomously.
- Changing the primary dataset, problem, temporal protocol or mandatory product scope needs user direction unless already authorized.
- External publication, cloud deployment, paid resources and contacting others need user authorization unless already provided.
- Deep learning, LLMs, live campaigns, real payments, inventory integration and automated retraining are outside the MVP.

## 6. End each session

1. Tick a task only when its acceptance criteria have evidence.
2. Append a dated progress entry with commands, results, changed files and unresolved issues.
3. Record material changes in the decision log and update the document that owns the rule.
4. Leave the next ready task ID and any remaining prerequisite.

