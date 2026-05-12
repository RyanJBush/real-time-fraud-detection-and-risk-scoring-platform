# Meridian — Real-Time Fraud Detection Platform

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?style=flat&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat&logo=typescript&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)
![SHAP](https://img.shields.io/badge/SHAP-Explainability-blueviolet?style=flat)

**Portfolio project:** full-stack fraud-risk scoring workflow using **synthetic/sample transaction data only**.

> ⚠️ Responsible use: Meridian is a learning and portfolio system, not a production fraud-prevention product. It does not process real banking data, cardholder data, or live payment traffic.

## Why this project (recruiter-friendly)

Meridian showcases capabilities aligned with FinTech, ML, backend, and data-science roles:

- **FinTech workflows:** transaction intake, risk scoring, analyst review queue, and audit-friendly reasoning.
- **Applied ML in product context:** shared feature extraction between live scoring and offline evaluation.
- **Backend engineering:** FastAPI routers, auth/RBAC, persistence, job orchestration, and test coverage.
- **Data science communication:** transparent metrics, limitations, and explainability outputs.

## Fraud scoring workflow

1. **Ingest transaction** via `POST /api/transactions`.
2. **Extract features** (`amount`, high-amount flag, risky-country flag, merchant-risk flag).
3. **Run hybrid score**:
   - Rule signals
   - Logistic regression baseline probability
4. **Assign decision band** (`approve`, `review`, `decline`) with reason codes.
5. **Persist score trace** for investigation and reporting.
6. **Fetch explainability** from `GET /api/explanations/{transaction_id}` for top contributing factors.

See implementation notes in `backend/app/ml.py`, `backend/app/routers/scores.py`, and `backend/app/routers/explanations.py`.

## Review queue workflow

Human-in-the-loop operations are centered in the review endpoints:

- `GET /api/reviews/queue` for pending/resolved cases
- `POST /api/reviews/{transaction_id}/assign` to assign ownership
- `POST /api/reviews/{transaction_id}/decision` to record analyst outcome
- `GET /api/reviews/{transaction_id}/history` for audit timeline

This models analyst triage behavior and decision governance in a portfolio-safe environment.

## Explainability view

Explainability claims are intentionally scoped to what is implemented:

- SHAP-based feature contributions are exposed for transaction explanations.
- API returns top factors and directional impact for analyst interpretation.
- Narrative output supports decision review, not regulatory-grade documentation.

No claims are made beyond the implemented explainability endpoints/UI.

## Model evaluation

Meridian includes offline and API-visible evaluation paths for **illustrative** performance analysis:

- Precision, recall, F1, ROC-AUC, Brier score
- Confusion matrix views
- Cost-sensitive framing for false negatives vs false positives

All evaluation results are derived from synthetic labels and must not be interpreted as production performance.

## Local demo setup

### Prerequisites
- Docker + Docker Compose
- (Optional for local dev) Python 3.11+, Node.js 20+

### Run with Docker

```bash
docker compose up --build
```

- Frontend: `http://localhost:5173`
- Backend docs: `http://localhost:8000/docs`

### Seed demo transactions

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@meridian.ai","password":"password123"}' | jq -r .access_token)

curl -X POST "http://localhost:8000/api/simulations/run-demo?seed=42" \
  -H "Authorization: Bearer $TOKEN"
```

### Helpful docs
- Architecture: `docs/architecture.md`
- API reference: `docs/api.md`
- Demo walkthrough: `docs/demo-runbook.md`
- Resume bullets: `docs/resume-bullets.md`
- Screenshot guide: `docs/screenshots/README.md`

## Limitations and future work

### Current limitations
- Synthetic/sample transactions only; no real banking integrations.
- Baseline model architecture intended for demonstration, not production hardening.
- Limited feature set and constrained scenario realism.
- Explainability centered on implemented SHAP flow only.

### Future work
- Add richer synthetic behavior simulation (device, velocity, graph features).
- Expand model registry/versioning and drift monitoring.
- Add calibration dashboards and threshold policy simulation.
- Add role-specific case-management UX for ops leadership views.

## Responsible-use statement

- This repository must only be used with synthetic/demo data.
- Do not present this system as a deployed fraud-prevention platform.
- Do not claim real loss prevention, customer protection outcomes, or compliance certification.
- Keep evaluation claims bounded to reproducible synthetic experiments.
