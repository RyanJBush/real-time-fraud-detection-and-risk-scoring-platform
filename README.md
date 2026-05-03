# Meridian AI

Production-style monorepo for a real-time fraud detection platform demo.

## Stack
- **Backend:** FastAPI, SQLAlchemy, PostgreSQL/SQLite, hybrid rules + ML scoring, SHAP explainability.
- **Frontend:** React + Vite + TypeScript dashboard.
- **Infra:** Docker Compose, GitHub Actions CI.

## Repository Structure
- `backend/` API, fraud engine, review workflow, model evaluation services, tests.
- `frontend/` analyst console UI.
- `docs/` architecture/API/demo guides.

## Quick Start (Docker)
```bash
docker compose up --build
```

Endpoints:
- Frontend: http://localhost:5173
- Backend OpenAPI: http://localhost:8000/docs

## Local Development
### 1) Install dependencies
```bash
# backend
cd backend && pip install -e .[dev]

# frontend
cd ../frontend && npm ci
```

### 2) Environment
Copy examples as needed:
- `backend/.env.example`
- `frontend/.env.example`

### 3) Run services
```bash
# backend
cd backend && uvicorn app.main:app --reload --port 8000

# frontend
cd frontend && npm run dev
```

## Seed Users
Password for all: `password123`
- `admin@meridian.ai` (Admin)
- `analyst@meridian.ai` (Analyst)
- `reviewer@meridian.ai` (Reviewer)
- `viewer@meridian.ai` (Viewer)

## Quality Checks
```bash
make check
```

Includes:
- backend lint + tests
- frontend lint + typecheck + production build

## Demo Script (Portfolio Walkthrough)
See full guide in `docs/demo.md`.

High-level flow:
1. Login as `analyst@meridian.ai`.
2. Create a transaction in **Transactions**.
3. Score/rescore and inspect explanation in **Transaction Detail**.
4. Triage cases in **Review Queue** (assign + decision + history).
5. Run seeded simulation in **Fraud Lab** and review model evaluation + case clusters.
6. Return to **Dashboard** to show KPI/trend updates.

### One-click demo realism bootstrap (Phase 7)
Use this API to seed and score a realistic mixed dataset in one shot:

```bash
curl -X POST "http://localhost:8000/api/simulations/run-demo?seed=42" \
  -H "Authorization: Bearer <TOKEN>"
```

This generates + scores scenarios for:
- card testing burst
- high value geo attack
- merchant takeover
- stolen card
- bot activity
- account takeover

The response includes total generated/scored and example case IDs for quick UI walkthrough.

## Troubleshooting
- **401 Unauthorized:** token expired/invalid → logout/login.
- **No model metrics:** run seeded simulations first (Fraud Lab) to create labeled scored samples.
- **Frontend cannot reach backend:** set `VITE_API_BASE` (e.g. `http://localhost:8000/api`).
- **Backend tests fail due missing packages:** ensure backend dev deps installed (`pip install -e .[dev]`).
