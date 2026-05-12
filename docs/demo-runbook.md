# Meridian Demo Runbook (Interview-Friendly)

> Audience: recruiters, hiring managers, engineers, data scientists.
> 
> Constraint: run only against synthetic/sample data.

## 1) Start the demo stack

```bash
docker compose up --build
```

Open:
- Frontend: `http://localhost:5173`
- Swagger: `http://localhost:8000/docs`

## 2) Log in as demo user

Use seeded credentials:
- `admin@meridian.ai`
- `analyst@meridian.ai`
- `reviewer@meridian.ai`
- `viewer@meridian.ai`

Password: `password123`

## 3) Seed deterministic transaction scenarios

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@meridian.ai","password":"password123"}' | jq -r .access_token)

curl -X POST "http://localhost:8000/api/simulations/run-demo?seed=42" \
  -H "Authorization: Bearer $TOKEN"
```

## 4) 8-minute guided story

### A) Fraud scoring workflow (2 min)
- Ingest a transaction.
- Score it.
- Show risk band + reason codes.

### B) Review queue (2 min)
- Open pending cases.
- Assign a case.
- Submit decision with notes.
- Show decision history.

### C) Explainability view (2 min)
- Open transaction detail.
- Show SHAP top factors.
- Explain “why this score” in plain language.

### D) Model evaluation + metrics (2 min)
- Open evaluation view/API response.
- Call out precision/recall/F1/ROC-AUC/Brier.
- Explain synthetic-data caveat clearly.

## 5) Recruiter-facing talk track

- “This project demonstrates end-to-end fraud-risk workflow design, not production deployment.”
- “Scores and metrics are generated from synthetic data for reproducible evaluation.”
- “The system includes explainability and human review to support accountable decision workflows.”

## 6) Responsible-use script (say this explicitly)

“Meridian is a portfolio platform. It does not process real banking data, does not claim real-world fraud prevention efficacy, and should not be used as a production control.”

## 7) Shutdown

```bash
docker compose down -v
```
