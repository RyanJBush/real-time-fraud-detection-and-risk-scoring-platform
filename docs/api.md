# API Surface

## Auth
- `POST /api/auth/login`
- `GET /api/auth/me`

## Transactions
- `POST /api/transactions`
- `GET /api/transactions`
- `GET /api/transactions/{transaction_id}`

## Scoring + Explainability
- `POST /api/scores`
- `GET /api/scores/{transaction_id}`
- `GET /api/explanations/{transaction_id}`

## Review Workflow
- `GET /api/reviews/queue?status=pending|resolved|all`
- `POST /api/reviews/{transaction_id}/decision`
- `GET /api/reviews/{transaction_id}/history`

## Metrics
- `GET /api/metrics/summary`

## Simulations
- `POST /api/simulations/seed-scenarios`

Use `/docs` on the backend server for Swagger UI.
