# API Surface

## Transactions
- `POST /api/v1/transactions/ingest`: ingest transaction, engineer features, score fraud risk, apply rules, and persist decision.
- `GET /api/v1/transactions?limit=50`: list recent transactions.

## Scoring
- `POST /api/v1/scoring`: re-score existing transaction by `transaction_id` using stored feature vector.

## Explanations
- `GET /api/v1/explanations/{transaction_id}`: retrieve stored SHAP top-feature contributions for a scored transaction.

Use `/docs` on the backend server for Swagger UI.
