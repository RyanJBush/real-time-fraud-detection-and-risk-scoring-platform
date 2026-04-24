# Meridian AI

Production-style monorepo for a real-time fraud detection MVP.

## Structure
- `backend/` FastAPI + ML scoring + SHAP explanations
- `frontend/` React + Vite + Tailwind dashboard
- `docs/` architecture and product docs

## Quick start
```bash
docker compose up --build
```

App URLs:
- Frontend: http://localhost:5173
- Backend: http://localhost:8000/docs

## Local development
```bash
make check
```

Seed users (password: `password123`):
- `admin@meridian.ai` (Admin)
- `analyst@meridian.ai` (Analyst)
- `reviewer@meridian.ai` (Reviewer)
- `viewer@meridian.ai` (Viewer)

## Phase 1 fraud platform upgrades
- Hybrid rules + ML scoring with adaptive signal weighting and approve/review/decline thresholds
- Reason codes, decision traces, and richer SHAP explanation summaries
- Manual review queue with override decisions and review event history
- KPI summary metrics extended with fraud/review/false-positive rates and blocked fraud value
- Seeded fraud scenario generator: `POST /api/simulations/seed-scenarios`
