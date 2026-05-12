# API Surface

> Meridian is a portfolio project running against **synthetic data only**.
> Every endpoint below is for local / demo use — none of this is wired to a
> real payment network. Pair this reference with the live Swagger UI at
> `http://localhost:8000/docs`.

All non-auth endpoints expect a `Authorization: Bearer <JWT>` header. Obtain
the JWT from `POST /api/auth/login`. Sensitive routes (rules management,
simulation seeding) additionally check the role encoded in the JWT
(Admin / Analyst / Reviewer / Viewer).

## Auth
- `POST /api/auth/login`
- `GET /api/auth/me`

## Transactions
- `POST /api/transactions`
- `GET /api/transactions?page=1&page_size=25&status=&merchant=&country=&min_amount=&max_amount=`
- `GET /api/transactions/{transaction_id}`

## Scoring + Explainability
- `POST /api/scores`
- `GET /api/scores/{transaction_id}`
- `GET /api/explanations/{transaction_id}` (returns SHAP factors, contribution direction, narrative, and rule reason codes)

## Review Workflow
- `GET /api/reviews/queue?status=pending|resolved|all&page=1&page_size=25`
- `POST /api/reviews/{transaction_id}/assign`
- `POST /api/reviews/{transaction_id}/decision`
- `GET /api/reviews/{transaction_id}/history`
- `GET /api/reviews/{transaction_id}/suggestion` (AI-assisted decision recommendation + rationale)

## Metrics
- `GET /api/metrics/summary`
- `GET /api/metrics/trends` (fraud trend and top risky entities)

## Platform Ops
- `GET /health`
- `GET /ready`
- `GET /api/audit/logs?page=1&page_size=50&action=&entity_type=`
- `POST /api/features/refresh?window_hours=24` (background feature refresh job)
- `GET /api/features/{transaction_id}` (feature snapshot for decision traceability)
- `GET /api/jobs?page=1&page_size=50&job_type=&status=` (background job list/filter)
- `GET /api/jobs/{job_id}` (background job status/detail)
- `POST /api/jobs/{job_id}/retry` (retry supported failed/completed feature refresh jobs)
- `GET /api/jobs/summary` (queue health counters by status)

## Simulations
- `POST /api/simulations/seed-scenarios`
- `POST /api/simulations/stream`
- `POST /api/simulations/run-demo?seed=42` (one-click demo dataset — generates and scores card testing, geo attack, takeover, bot, and stolen-card scenarios)

## Offline Model Evaluation
- `GET /api/models/evaluation` (candidate model comparison with threshold tuning, class-imbalance-aware training, calibration via Brier score, and cost-sensitive scoring)

## Case Investigation
- `GET /api/cases/groups?status=all&limit=50` (grouped suspicious activity clusters)
- `GET /api/cases/summary?group_key=...` (AI-generated cluster summary)

## Rules Management
- `GET /api/rules`
- `POST /api/rules` (Admin)
- `PATCH /api/rules/{rule_id}` (Admin)

Use `/docs` on the backend server for Swagger UI, or `/redoc` for the ReDoc
variant.
