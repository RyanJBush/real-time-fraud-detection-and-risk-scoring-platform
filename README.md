# Meridian AI Monorepo Scaffold

Production-oriented scaffold for a real-time fraud detection platform with FastAPI, React + Vite, PostgreSQL, SHAP explainability, Docker, and CI.

## Architecture

- **Backend (`backend/`)**: FastAPI app using a layered structure:
  - `routers/` for API endpoints
  - `schemas/` for request/response contracts
  - `models/` for SQLAlchemy entities
  - `services/` for ingestion, feature engineering, model scoring, rules, and decisions
  - `ml/` for model + SHAP explainability integration
- **Frontend (`frontend/`)**: React + Vite dashboard shell.
- **Docs (`docs/`)**: Architecture and API notes.
- **Infra**:
  - `docker-compose.yml` for full local stack (frontend, backend, postgres)
  - `.github/workflows/ci.yml` for CI checks

## Fraud pipeline implemented

- Transaction ingestion endpoint:
  - `POST /api/v1/transactions/ingest`
- Feature engineering:
  - `amount`, `is_ecommerce`, `channel_risk`, `account_tx_count_24h`
- Fraud scoring model:
  - in-memory `RandomForestClassifier`
- Rule-based detection:
  - `high_amount`, `wire_transfer`, `high_model_risk`
- Decision system:
  - maps to `approve`, `review`, or `decline`
- Explainability endpoint:
  - `GET /api/v1/explanations/{transaction_id}`

## Quick start

### 1) Local services (without Docker)

```bash
make backend-install
make frontend-install
make backend-run
make frontend-run
```

Backend docs: `http://localhost:8000/docs`  
Frontend: `http://localhost:5173`

### 2) Full stack with Docker

```bash
make up
```

Frontend: `http://localhost:3000`  
Backend: `http://localhost:8000`

## Development commands

```bash
make backend-test
make frontend-build
make down
```

## Demo API flow

```bash
curl -X POST http://localhost:8000/api/v1/transactions/ingest \
  -H 'Content-Type: application/json' \
  -d '{"account_id":"acct_1","merchant_id":"mrc_1","amount":3100,"currency":"USD","channel":"wire"}'

curl -X POST http://localhost:8000/api/v1/scoring \
  -H 'Content-Type: application/json' \
  -d '{"transaction_id":1}'

curl http://localhost:8000/api/v1/explanations/1
```
