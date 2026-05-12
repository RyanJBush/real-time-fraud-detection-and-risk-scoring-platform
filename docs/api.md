# Meridian API Documentation

> This API is for local demonstration with synthetic/sample transaction data only.

Base URL (local): `http://localhost:8000`

Auth model: Bearer JWT for non-auth routes.

## 1) Authentication

- `POST /api/auth/login`
- `GET /api/auth/me`

Use seeded demo identities (non-production credentials) from the runbook.

## 2) Transaction and scoring flow

### Step A: Ingest transaction
- `POST /api/transactions`

### Step B: Score transaction
- `POST /api/scores`
- `GET /api/scores/{transaction_id}`

### Step C: Explain score
- `GET /api/explanations/{transaction_id}`

Expected behavior:
- Returns synthetic risk score, decision band, and reason context.
- Explainability responses include implemented SHAP factor outputs.

## 3) Review queue endpoints

- `GET /api/reviews/queue?status=pending|resolved|all&page=1&page_size=25`
- `POST /api/reviews/{transaction_id}/assign`
- `POST /api/reviews/{transaction_id}/decision`
- `GET /api/reviews/{transaction_id}/history`
- `GET /api/reviews/{transaction_id}/suggestion`

Purpose:
- Demonstrate human-in-the-loop fraud operations and audit trail behavior.

## 4) Metrics and evaluation

- `GET /api/metrics/summary`
- `GET /api/metrics/trends`
- `GET /api/models/evaluation`

Metrics are generated from synthetic labels and are for comparative demonstration only.

## 5) Simulations and demo data

- `POST /api/simulations/seed-scenarios`
- `POST /api/simulations/stream`
- `POST /api/simulations/run-demo?seed=42`

Recommended for reproducible interview demos.

## 6) Platform and ops

- `GET /health`
- `GET /ready`
- `GET /api/audit/logs`
- `POST /api/features/refresh?window_hours=24`
- `GET /api/features/{transaction_id}`
- `GET /api/jobs`
- `GET /api/jobs/{job_id}`
- `POST /api/jobs/{job_id}/retry`
- `GET /api/jobs/summary`

## 7) Cases and rules

- `GET /api/cases/groups`
- `GET /api/cases/summary`
- `GET /api/rules`
- `POST /api/rules` (Admin)
- `PATCH /api/rules/{rule_id}` (Admin)

## 8) Responsible-use API disclaimer

- Do not connect this API to live financial systems.
- Do not represent outputs as production fraud decisions.
- Do not claim compliance or operational SLAs from this portfolio stack.
