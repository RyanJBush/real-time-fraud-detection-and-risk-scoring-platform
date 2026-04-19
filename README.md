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
- `viewer@meridian.ai` (Viewer)
