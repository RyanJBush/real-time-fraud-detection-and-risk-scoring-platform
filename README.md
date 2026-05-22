# Real-Time Fraud Detection & Risk Scoring Platform

> **Portfolio project for data science, fintech, machine learning, and risk analytics roles.**
> Uses synthetic/sample transaction data only (no real customer or banking data).

## Executive Summary
This project demonstrates an end-to-end fraud detection and risk scoring platform built with a FastAPI backend, React frontend, PostgreSQL persistence, and a baseline machine learning model. It combines deterministic fraud rules with logistic-regression probability scoring, then routes higher-risk transactions into an analyst review workflow with audit history and explainability support. The repository is designed to showcase production-style architecture patterns and practical ML/risk operations workflows in a recruiter-friendly format while remaining explicitly demo-safe.

## Business Problem and Fintech Use Case
Digital payments and card-like transaction systems need fast risk decisions to reduce fraud exposure while minimizing false positives that disrupt legitimate users. This platform simulates that fintech use case by scoring incoming transactions, assigning decision bands (approve/review/decline), and supporting human-in-the-loop review for escalated items. It is intended to demonstrate how data science and software engineering components connect in a risk operations context using synthetic data.

## Key Features
- Real-time-style transaction intake and scoring via API endpoints.
- Hybrid risk engine combining:
  - rule-based fraud signals, and
  - ML-based fraud probability (logistic regression baseline).
- Transaction-level explainability endpoint for SHAP-style feature contributions.
- Review queue operations: assignment, decisioning, suggestion support, and history.
- Metrics and model-evaluation endpoints for classification reporting on synthetic labels.
- Simulation endpoints for seeded scenarios and stream-like demo runs.
- Role-based auth flow with JWT and route-level access control.
- Audit and job/status endpoints for operational visibility.

## Tech Stack
- **Backend:** Python, FastAPI, SQLAlchemy, PostgreSQL.
- **Frontend:** React, TypeScript, Vite.
- **ML/Data:** scikit-learn, pandas, NumPy, SHAP.
- **Quality/Dev Tooling:** pytest, Ruff, Docker Compose, Makefile workflows.

## Machine Learning / Risk Scoring Workflow
1. Synthetic transaction data is generated and/or ingested.
2. Feature extraction builds model inputs and risk indicators.
3. Deterministic fraud rules compute explicit signal flags.
4. Logistic regression baseline outputs fraud probability.
5. Rules + model outputs are combined into decision bands.
6. Score context is stored and exposed through scoring/explanation/review APIs.
7. Offline evaluation reports classification metrics for synthetic-data benchmarking.

## Data Pipeline / Processing Flow
- **Data creation:** scripts generate synthetic transaction records with controllable fraud-rate and seed settings.
- **Offline modeling:** training script fits and evaluates the baseline model from CSV data.
- **Online/demo scoring path:** transaction payload -> feature extraction -> scoring -> persistence -> review queue -> metrics/explanations.
- **Simulation utilities:** scenario seeding and stream/demo endpoints support reproducible walkthroughs.

## Architecture Overview
High-level system flow:
1. **Frontend (React/TypeScript)** sends authenticated REST requests.
2. **Backend (FastAPI)** orchestrates transactions, scoring, explainability, reviews, metrics, rules, cases, simulations, and jobs.
3. **Services layer** performs fraud scoring, feature generation, model evaluation, drift checks, analytics, and workflow/audit logic.
4. **Database layer (PostgreSQL + SQLAlchemy)** stores transactions, scores, rule state, and review history.

Supporting documentation:
- Architecture details: `docs/architecture.md`
- API endpoint reference: `docs/api.md`

## Setup and Installation
### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker + Docker Compose (optional, for full stack run)

### Quick Start
```bash
make install
make synthetic-data
make train-demo
make eval-demo
```

### Run Full Application (Optional)
```bash
docker compose up --build
```
- Frontend: `http://localhost:5173`
- Backend API docs: `http://localhost:8000/docs`

## Example Use Cases
- Demonstrate a **fraud scoring API** in technical interviews.
- Show a **classification + rule-engine hybrid** risk decisioning approach.
- Walk through **analyst review operations** (queue, assignment, decision history).
- Discuss **model evaluation and threshold trade-offs** on synthetic data.
- Explain **transaction-level risk reasoning** through explanation endpoints.

## Skills Demonstrated
- End-to-end ML application development (data generation, model training, inference integration).
- Fraud/risk feature engineering and binary classification workflow design.
- API design for scoring, explanations, metrics, and review operations.
- Data pipeline thinking for batch/offline and near-real-time/demo paths.
- Full-stack integration (FastAPI + React + PostgreSQL).
- Testing and maintainability practices with pytest, linting, and modular services.
- Security fundamentals (JWT authentication, role-based route access).

## Resume-Ready Project Description
Built a full-stack **Real-Time Fraud Detection & Risk Scoring Platform** using Python (FastAPI), React, PostgreSQL, and scikit-learn. Implemented a hybrid risk engine that combines logistic-regression fraud probability with rule-based signals, exposed scoring/explanation/review APIs, and added synthetic-data simulation workflows for reproducible demos. Developed analyst-focused review queue and metrics endpoints to demonstrate practical machine learning operations, risk triage, and auditable decision workflows.

## Future Improvements
- Add richer synthetic behavior patterns (velocity/device/graph-style relationships).
- Expand model registry and side-by-side model comparison experiments.
- Enhance threshold calibration and drift-monitoring UX.
- Strengthen case-management workflows and prioritization logic.
- Add deeper observability around model/feature freshness and job reliability.

## License
See `LICENSE`.
