# Real-Time Fraud Detection & Risk Scoring Platform

> Recruiter-ready portfolio project for data science, fintech, machine learning, and risk analytics roles.  
> Uses synthetic/sample transaction data only.

## 1) Project title
Real-Time Fraud Detection & Risk Scoring Platform

## 2) Executive summary
This project is an end-to-end fraud analytics platform with a FastAPI backend, React frontend, SQL persistence, and ML-assisted risk scoring. It combines a baseline classifier with deterministic fraud rules to produce transaction decisions (`approve`, `review`, `decline`), then supports analyst workflows through review queues, audit logs, and explanations. The repository is designed for interview/demo use with synthetic data and reproducible simulation flows.

## 3) Business problem and fintech use case
Digital payments teams need fast transaction risk decisions while controlling false positives that can block legitimate users. This project simulates that fintech workflow by ingesting transactions, calculating risk, routing high-risk cases to manual review, and tracking outcomes. It demonstrates how fraud detection, risk scoring, and analyst operations connect in a practical risk platform.

## 4) Key features
- Transaction ingestion and scoring APIs for near-real-time decisioning.
- Hybrid scoring engine:
  - ML probability scoring (logistic regression baseline by default).
  - Rule-based behavioral signals (velocity, repeat attempts, geo risk, merchant risk, high amount, and related anomaly-style proxies).
- Decision trace persistence with reason codes and signal details.
- Explainability endpoint with SHAP-based attributions (plus fallback attribution logic) and narrative summaries.
- Review workflow: queue, assignment, comments, override decisions, fraud labeling, and case history.
- Metrics and trends endpoints for fraud/risk monitoring from labeled synthetic records.
- Candidate model evaluation endpoint (logistic regression, random forest, optional xgboost if available).
- Simulation endpoints for seeded scenarios, stream-style generation, and full demo runs.
- JWT authentication + role-based route protection (Admin/Analyst/Reviewer/Viewer).
- Background jobs for feature snapshot refresh and job status tracking.

## 5) Tech stack
- **Languages:** Python, TypeScript, JavaScript, SQL
- **Backend:** FastAPI, SQLAlchemy, Pydantic
- **Frontend:** React, Vite, Recharts
- **Database:** PostgreSQL (Docker) or SQLite (local `.env` default)
- **ML/Data:** scikit-learn, NumPy, SHAP
- **Quality/Tooling:** pytest, Ruff, ESLint, TypeScript typecheck, Docker Compose, Makefile

## 6) Machine learning / risk scoring workflow
1. Generate or ingest synthetic transaction records.
2. Extract model features (`amount`, high-amount flag, risky-country flag, merchant-risk flag).
3. Score fraud probability with the baseline classifier.
4. Compute rule-based risk signals (including velocity and anomaly-proxy behaviors).
5. Combine model score + rule score into a final risk score.
6. Map final score into decision bands (`approve`, `review`, `decline`) with stored reason codes.
7. Persist score, explanation artifacts, and decision trace for API/UI consumption.
8. Evaluate candidate models and threshold trade-offs on labeled synthetic data.

## 7) Data pipeline or processing flow
- **Synthetic data generation:** `scripts/generate_synthetic_transactions.py` and related generators create reproducible datasets.
- **Offline model workflow:** `scripts/train_offline_model.py` trains/evaluates a classifier from CSV and reports classification metrics.
- **Online scoring flow:** API transaction -> feature extraction -> hybrid scoring -> DB persistence -> review queue + explanations.
- **Simulation flow:** scenario seeding and demo-run endpoints populate and score realistic fraud patterns for walkthroughs.

## 8) Architecture overview
- **Frontend (React/TypeScript):** dashboard, transaction feed/detail, review queue, and intelligence/simulation pages.
- **API layer (FastAPI routers):** auth, transactions, scores, explanations, metrics, reviews, simulations, cases, rules, audit, and jobs.
- **Service layer:** fraud engine, model evaluation, trend analytics, drift detection, review workflow, feature snapshot jobs.
- **Persistence layer (SQLAlchemy):** transactions, risk scores, decision traces, explanations, labels, review cases/events, audit logs, background jobs.

Detailed references:
- `docs/architecture.md`
- `docs/api.md`

## 9) Setup and installation
### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker + Docker Compose (optional full-stack run)

### Quick start (local tooling)
```bash
make install
make synthetic-data
make train-demo
make eval-demo
```

### Run full stack (optional)
```bash
docker compose up --build
```
- Frontend: `http://localhost:5173`
- Backend docs: `http://localhost:8000/docs`

## 10) Example use cases
- Demo a fraud-scoring API workflow in interviews.
- Show a hybrid classification + rule-based decisioning approach for risk ops.
- Walk through analyst case management (assignment, override, fraud labeling, history).
- Compare model candidates and discuss threshold/cost trade-offs.
- Explain transaction-level risk drivers using contribution outputs and reason codes.

## 11) Skills demonstrated
- Fraud/risk analytics design and feature engineering.
- Binary classification modeling and model evaluation.
- Hybrid risk scoring (ML + rules) with explainability outputs.
- Real-time-style API development for scoring and review operations.
- Data pipeline design across synthetic generation, offline training, and online inference.
- Full-stack product implementation (FastAPI + React + SQL database).
- Security and governance fundamentals (JWT auth, RBAC, auditability).

## 12) Resume-ready project description
Built a full-stack **Real-Time Fraud Detection & Risk Scoring Platform** using **Python (FastAPI), React, SQLAlchemy/PostgreSQL, and scikit-learn**. Implemented a hybrid risk engine that combines ML classification scores with rule-based fraud signals, exposed scoring/review/explainability APIs, and delivered simulation-driven workflows for reproducible demos. Added analyst-facing dashboards, case triage operations, and model-evaluation endpoints to demonstrate practical fintech risk analytics and ML system design.

## 13) Future improvements
- Add richer synthetic fraud patterns (device/network/graph relationships).
- Expand drift monitoring and threshold calibration workflows.
- Add stricter model registry/versioning and experiment tracking.
- Improve case prioritization and SLA-style queue policies.
- Extend observability for feature freshness and background job reliability.

## License
See `LICENSE`.
