# Meridian AI Architecture

## Monorepo layout

- `backend/`: FastAPI service with modular routers/services/schemas/models.
- `frontend/`: React + Vite dashboard shell.
- `docs/`: architecture and API docs.
- `.github/workflows/`: CI for backend and frontend checks.

## Backend fraud pipeline

1. `POST /api/v1/transactions/ingest` persists a transaction.
2. Feature engineering derives model-ready values (amount, channel risk, account velocity).
3. Random forest model generates a fraud probability.
4. Rule engine adds deterministic risk flags.
5. Decision engine maps score + rules to `approve|review|decline`.
6. SHAP explainer computes top feature contributions and stores them.

## Data model

- `transactions` table stores inbound payment events.
- `decisions` table stores score, decision, rule flags, feature vector, and SHAP explanation payload.
