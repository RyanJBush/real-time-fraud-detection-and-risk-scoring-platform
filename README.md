# Meridian — Portfolio-Scale Fraud Detection Demo

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Open%20App-22c55e?style=for-the-badge)](https://fraud-detection.onrender.com)

> **Synthetic/sample transaction data only — not real banking data.**

Meridian is a portfolio project built by a **University of Maryland student studying Information Science and Electrical Engineering with a Business minor**. It demonstrates a realistic, student-scale fraud scoring workflow using synthetic transaction events, a baseline machine learning model, and analyst review tooling.

## Summary
Meridian simulates how card-like transactions can be scored for fraud risk and routed for manual review through a batch processing pipeline with streaming simulation using generator patterns. The project is intended for technical interviews and portfolio review, not production financial operations.

## What this demonstrates
- Building a full-stack fraud operations demo (FastAPI + React + PostgreSQL).
- Engineering fraud features from transaction fields such as amount, merchant type, and country.
- Training and evaluating a baseline logistic regression classifier on synthetic labels.
- Combining model output with rule-based signals for clearer triage decisions.
- Returning SHAP-based feature contributions for per-transaction explanation views.

## Model behavior at a high level
The training/scoring pipeline uses synthetic transaction records with fields like:
- `amount`
- `merchant`
- `country`
- derived risk indicators (for example high-amount and risky-merchant patterns)

The label is binary:
- `is_fraud = 1` for synthetic fraud-pattern transactions
- `is_fraud = 0` for synthetic legitimate-pattern transactions

The backend extracts numeric features and scores with a logistic regression baseline, then combines model signals with rules to produce decision bands used by the review queue.


## How it Works
Meridian uses an offline-trained logistic regression model and deterministic fraud rules in a staged scoring flow. Transaction records are generated and ingested in mini-batches, then replayed in order to simulate stream-like behavior with Python generators. For each scored transaction, the API returns SHAP feature attributions so reviewers can see which inputs (for example amount, merchant risk, and country risk) pushed the score up or down, improving explainability during triage.

## Model Performance
The table below is an example placeholder for demo reporting metrics (values are illustrative):

| Metric    | Example Value |
|-----------|---------------|
| Precision | 0.89          |
| Recall    | 0.84          |
| F1        | 0.86          |
| AUC-ROC   | 0.92          |

## Tech stack
- **Backend:** Python, FastAPI, SQLAlchemy, PostgreSQL
- **Frontend:** React, TypeScript, Vite
- **ML/Data:** scikit-learn, pandas, NumPy, SHAP
- **Dev tooling:** Docker Compose, pytest, Makefile

## Architecture
- System architecture: [`docs/architecture.md`](docs/architecture.md)
- API behavior and endpoints: [`docs/api.md`](docs/api.md)

High-level flow:
1. Ingest synthetic transaction event.
2. Generate fraud-related features.
3. Score using rules + logistic regression baseline.
4. Persist score, decision context, and explanation metadata.
5. Route higher-risk items to analyst review workflows.

## Running locally
### Prerequisites
- Python 3.11+
- Node.js 20+
- (Optional) Docker + Docker Compose

### Quick start commands
```bash
make install
make synthetic-data
make train-demo
make eval-demo
```

What these do:
- `make install`: installs backend and frontend dependencies.
- `make synthetic-data`: generates a small synthetic CSV dataset.
- `make train-demo`: trains/evaluates the offline logistic baseline.
- `make eval-demo`: runs backend tests for scoring and pipeline checks.

### Optional full app run
```bash
docker compose up --build
```
- Frontend: `http://localhost:5173`
- API docs (Swagger): `http://localhost:8000/docs`

## Demo workflow
1. Generate synthetic data and run the offline model demo.
2. Start the app (`docker compose up --build`).
3. Log in with seeded demo credentials.
4. Trigger seeded simulation data through `POST /api/simulations/run-demo?seed=42`.
5. Review dashboard KPIs, flagged transactions, and explanation output.

## Screenshots
- Add UI or workflow screenshots under [`docs/images/`](docs/images/) for README embedding and release notes.
- Existing screenshot inventory and capture checklist: [`docs/screenshots/README.md`](docs/screenshots/README.md)
- Portfolio Preview page: [`docs/preview/index.html`](docs/preview/index.html)

## Limitations and future work
### Current limitations
- Synthetic/sample data only; no real customer accounts or banking integrations.
- Portfolio-scale feature set and fraud patterns (not institution-tuned).
- Baseline model scope and calibration are designed for demonstration.

### Future work
- Add richer synthetic behavior simulation (velocity, device, graph link analysis).
- Expand model comparison beyond logistic regression.
- Add threshold calibration and drift monitoring views.
- Improve analyst tooling for case prioritization experiments.

## Resume bullets
- Project resume bullets: [`docs/resume-bullets.md`](docs/resume-bullets.md)

## License
See [`LICENSE`](LICENSE).


## Running the Demo
1. Generate synthetic transactions:
```bash
python scripts/generate_synthetic_data.py
```
2. Load generated CSV from `data/synthetic_transactions.csv` into your analysis/training workflow.
3. Start services with Docker Compose and run seeded simulation API calls for live scoring.
