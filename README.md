# Meridian — Real-Time Fraud Detection Platform

A portfolio demo of a fraud-scoring workflow built with synthetic transaction streams.

## Recruiter-facing summary
Meridian is a full-stack fraud-operations simulation that shows how a transaction can move from intake to risk scoring to analyst review. The project is designed for portfolio review and technical interviews, with clear documentation and reproducible local setup. University of Maryland student studying Information Science and Electrical Engineering with a Business minor.

> **Data disclaimer:** Uses synthetic transaction data — not real banking data. The model is trained and evaluated on synthetic/sample datasets and is not connected to production financial systems.

## What this project demonstrates
- Designing a fraud-risk decision pipeline for demo-scale FinTech workflows
- Combining rule-based signals with ML probability outputs for case triage
- Exposing explainability outputs for analyst review using implemented SHAP calls
- Building a local full-stack app with API docs, seeded scenarios, and review queue flows

## Tech stack
- **Backend:** Python, FastAPI, SQLAlchemy, PostgreSQL
- **Frontend:** React, TypeScript, Vite
- **ML/Data:** scikit-learn, pandas, NumPy, SHAP
- **Dev tooling:** Docker, Docker Compose, pytest, Makefile

## Architecture overview
- Architecture docs: [`docs/architecture.md`](docs/architecture.md)
- API docs and endpoint behavior: [`docs/api.md`](docs/api.md)

High-level flow:
1. Ingest synthetic transaction event
2. Engineer risk features
3. Score with rules + logistic regression baseline
4. Return fraud score, decision band, and explanation metadata
5. Route high-risk items to analyst review queue

## How to run locally
### Prerequisites
- Docker + Docker Compose
- Optional local development tools: Python 3.11+, Node.js 20+

### Start the app
```bash
docker compose up --build
```

- Frontend: `http://localhost:5173`
- Backend Swagger UI: `http://localhost:8000/docs`

## Demo workflow
1. Launch services with Docker Compose.
2. Authenticate with the seeded admin account.
3. Trigger deterministic simulation data:
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@meridian.ai","password":"password123"}' | jq -r .access_token)

curl -X POST "http://localhost:8000/api/simulations/run-demo?seed=42" \
  -H "Authorization: Bearer $TOKEN"
```
4. Review dashboard KPIs, queue operations, transaction detail view, and explanation output.

## Screenshots / demo
See screenshot inventory and capture guidance in [`docs/screenshots/README.md`](docs/screenshots/README.md).

For a recruiter-friendly UI walkthrough, open the Portfolio Preview page:
- [`docs/preview/index.html`](docs/preview/index.html) (Portfolio Preview)

## Limitations and future work
### Current limitations
- Uses synthetic/sample transaction data only; no real institution integrations
- Demo-scale modeling and scenario realism; not validated for operational deployment
- Limited feature space compared with production anti-fraud stacks

### Future work
- Expand synthetic behavior modeling (velocity, device, graph/network signals)
- Add threshold simulation and calibration views for policy tuning
- Improve model registry/versioning and drift-monitoring workflow
- Extend case-management UX for role-specific operations

## Resume bullets
- Project-specific resume bullets: [`docs/resume-bullets.md`](docs/resume-bullets.md)

## License
This project is licensed under the terms in [`LICENSE`](LICENSE).
