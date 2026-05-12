# Meridian — Architecture

> **Reminder:** Meridian is a portfolio project. All data is synthetic. Nothing
> in this document should be read as a claim about production fraud-prevention
> performance.

## 1. System overview

```
┌─────────────────────┐    REST / JWT     ┌──────────────────────────────┐
│ React + TypeScript  │ ────────────────▶ │ FastAPI (app/main.py)        │
│ Analyst Console     │                   │ 11 routers under app/routers │
└─────────────────────┘                   └──────────────┬───────────────┘
                                                         │
                                          ┌──────────────┴───────────────┐
                                          │                              │
                                ┌─────────▼─────────┐         ┌──────────▼─────────┐
                                │ Scoring engine     │         │ Persistence        │
                                │ (app/ml.py)        │         │ SQLAlchemy + PG    │
                                │  • Rule layer      │         │  • transactions    │
                                │  • LogisticRegr.   │         │  • scores / rules  │
                                │  • SHAP explainer  │         │  • reviews / audit │
                                └────────────────────┘         │  • jobs / cases    │
                                                               └────────────────────┘
```

## 2. Layers

### 2.1 Client layer (`frontend/`)

- **Stack:** React + Vite + TypeScript.
- **Key pages** (`frontend/src/pages/`): `DashboardPage`, `TransactionsPage`, `TransactionDetailPage`, `ReviewsPage`, `AlertsPage`, `IntelligencePage`, `SettingsPage`, `LoginPage`.
- **Reusable components** (`frontend/src/components/`): `KpiCard`, `RiskBadge`, `RiskGauge`, `ScorePanel`, `TransactionsPanel`.
- Authentication via JWT obtained from `POST /api/auth/login` and held in client state.

### 2.2 API layer (`backend/app/`)

- **Framework:** FastAPI 0.111+, served by Uvicorn. App factory in `backend/app/main.py`.
- **Cross-cutting middleware:**
  - Request-ID + timing middleware adds `X-Request-ID` and logs structured JSON access lines.
  - CORS configured via `ALLOWED_ORIGINS` env var (defaults to Vite dev origins).
- **Routers** (all under `backend/app/routers/`):
  - `auth.py` — login, current user.
  - `transactions.py` — ingest + paginated list/detail with filters.
  - `scores.py` — synchronous scoring entry-point; calls rules + model.
  - `explanations.py` — SHAP factors + narrative summary per transaction.
  - `reviews.py` — analyst queue, assignment, decision, history, AI suggestion.
  - `simulations.py` — `/seed-scenarios`, `/stream`, `/run-demo` deterministic scenarios.
  - `metrics.py` — KPI summary + trend endpoints.
  - `audit.py` — audit log query.
  - `jobs.py` — background feature-refresh job list, detail, retry, summary.
  - `cases.py` — case-cluster summarization endpoints.
  - `rules.py` — admin CRUD for rule definitions.

### 2.3 Scoring engine (`backend/app/ml.py`)

- **Features extracted per transaction:**
  - `amount` (raw)
  - `is_high_amount` (= 1 when `amount > 3000`)
  - `is_risky_country` (= 1 when country in `{NK, IR}`)
  - `merchant_risk` (= 1 when merchant in `{luxury-goods, crypto-exchange, gift-cards}`)
- **Model:** `sklearn.linear_model.LogisticRegression` trained at import time on a small hand-crafted matrix (kept deliberately tiny so the package is fast to load and reproducible). Production-ready training happens offline via `scripts/train_offline_model.py`.
- **Explainability:** `shap.LinearExplainer` (falls back to `coef_ × features` if SHAP fails to load). Top-3 factors ranked by absolute contribution.
- **Decision policy:** approve / review / decline thresholds layered on top of the model probability, with rule signals contributing to the final reason codes.

### 2.4 Data layer

- **Postgres 16** (via `docker-compose.yml`).
- **ORM:** SQLAlchemy 2.x with `Base = declarative_base()`.
- **Core tables** (`backend/app/models.py`): transactions, scores, explanations, reviews, audit logs, jobs, cases, rules, users.

## 3. Request flow — scoring a transaction

1. Client `POST /api/transactions` with payload validated by Pydantic.
2. Transaction is persisted; row id returned.
3. Client `POST /api/scores` (or the UI triggers it automatically).
4. `scores.py` calls `extract_features` → `score_transaction` → builds rule signals.
5. Combined risk score + decision + reason codes persisted.
6. `GET /api/explanations/{id}` returns SHAP factors + narrative for the UI's risk panel.

The same `extract_features` function is imported by `scripts/train_offline_model.py`,
so the **offline training pipeline and the live scoring path use the exact
same feature code** — eliminating a common class of training/serving skew bugs.

## 4. Review workflow

- `GET /api/reviews/queue` — pending / resolved / all, paginated.
- `POST /api/reviews/{txn}/assign` — assign to reviewer.
- `GET /api/reviews/{txn}/suggestion` — AI-assisted recommendation + rationale.
- `POST /api/reviews/{txn}/decision` — analyst override; persists decision + notes.
- `GET /api/reviews/{txn}/history` — full timeline of state changes.
- All actions are written to the audit log (`/api/audit/logs`).

## 5. Background jobs

- Feature-refresh jobs are kicked off via `POST /api/features/refresh`.
- `GET /api/jobs` exposes the queue with status filtering; `/retry` re-runs failed jobs; `/summary` provides counts for dashboard health tiles.

## 6. RBAC

| Role | Capabilities |
|---|---|
| Admin | Manage rules, run simulations, full read |
| Analyst | Score transactions, work review queue, submit decisions |
| Reviewer | Take ownership of cases, approve / decline |
| Viewer | Read-only KPIs and transaction history |

Roles are encoded in the JWT issued by `/api/auth/login` and enforced inside each router.

## 7. CI / quality gates

`.github/workflows/ci.yml` runs two parallel jobs on every push and PR to `main`:

- **Backend:** `ruff check`, `mypy app`, `pytest`.
- **Frontend:** `eslint`, `tsc --noEmit`, `vite build`.

`make check` runs the same checks locally.

## 8. What's intentionally out of scope

See the "Limitations & Future Work" table in the [README](../README.md#%EF%B8%8F-limitations--future-work).
The short version: this is a teaching / portfolio system, not a production
fraud platform.
