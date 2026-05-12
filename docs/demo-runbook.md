# Meridian — Demo Runbook

A guided, ~10-minute walkthrough designed for interviews and portfolio
reviews. Pair this with [`docs/architecture.md`](architecture.md) and
[`docs/api.md`](api.md).

> **Reminder:** every transaction, score, and metric in this demo is generated
> from synthetic data. Nothing here represents real customers or real fraud.

## 0. Prerequisites

- Docker + Docker Compose installed
- Ports `5173` (frontend), `8000` (backend), `5432` (postgres) free
- Roughly 1–2 GB of free RAM for the three containers

## 1. Boot the stack (≈1 min)

```bash
docker compose up --build
```

Wait until you see the backend log line `Uvicorn running on http://0.0.0.0:8000`.
Then open:

- Frontend: <http://localhost:5173>
- Swagger UI: <http://localhost:8000/docs>

## 2. Log in (≈30 s)

Use one of the seeded demo accounts (passwords are seeded for demo use only —
not a real credential pattern):

| Email | Role | Best for |
|---|---|---|
| `admin@meridian.ai` | Admin | Rules management, simulations |
| `analyst@meridian.ai` | Analyst | Default walkthrough — review queue |
| `reviewer@meridian.ai` | Reviewer | Case ownership / approvals |
| `viewer@meridian.ai` | Viewer | Read-only KPIs |

Password for all: `password123`.

## 3. Seed a realistic dataset (≈30 s)

Easiest path — call the one-click endpoint from Swagger UI or `curl`:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@meridian.ai","password":"password123"}' | jq -r .access_token)

curl -X POST "http://localhost:8000/api/simulations/run-demo?seed=42" \
  -H "Authorization: Bearer $TOKEN"
```

This generates and scores a mix of: card testing bursts, a high-value geo
attack, merchant takeover, stolen-card spend, bot activity, and an account
takeover sequence. The `seed=42` makes the result reproducible.

## 4. Storyline (≈7 min)

### 4.1 Ingestion → Scoring (≈2 min)

1. Open **Transactions**.
2. Submit a transaction via the ingest form (e.g. `amount=4500`, `country=NK`, `merchant=gift-cards`).
3. Click **Score** on the new row.
4. Open the transaction detail page and call out:
   - The risk score and the approve / review / decline decision.
   - The threshold band.
   - SHAP top-3 contributions (`amount`, `is_risky_country`, `merchant_risk` should dominate for this example).
   - Rule reason codes alongside the model probability.

### 4.2 Analyst review workflow (≈2 min)

1. Open **Review Queue**.
2. Pick a pending case from the seeded set.
3. Show the AI suggestion + rationale (`GET /api/reviews/{txn}/suggestion`).
4. Assign the case to a reviewer.
5. Submit an analyst-override decision with notes.
6. Open the history tab to show the decision timeline + audit entries.

### 4.3 Fraud Lab + evaluation (≈2 min)

1. Open **Fraud Lab**.
2. Run the `high_value_geo_attack` simulation with a deterministic seed.
3. Wait for the seeded transactions to be scored.
4. Show:
   - The model evaluation table (precision / recall / F1 / ROC-AUC / Brier / cost-sensitive).
   - The suspicious-clusters view and the auto-generated cluster summaries.

### 4.4 Business impact view (≈1 min)

1. Open **Dashboard**.
2. Show fraud + review KPIs, blocked-fraud value, and the trend chart.
3. Explain that every number on the page is recomputed against synthetic data.

## 5. Suggested talking points

- **Hybrid scoring** — rules carry policy that's hard to defend statistically; the ML model handles the long tail. Combining them keeps both auditability and recall.
- **Explainability** — SHAP top-factors plus reason codes mean every decision can be defended to a customer, an analyst, or a regulator.
- **Training/serving symmetry** — the live API and the offline trainer share `app.ml.extract_features`, so what you train is what you score.
- **Human-in-the-loop** — RBAC, queue, assignment, override, and audit trail mirror how a real fraud ops team would operate.
- **Reproducibility** — deterministic seeds in the simulator make the demo land the same way every time, which matters in interviews.

## 6. Optional — offline training in a terminal (≈1 min)

```bash
python scripts/generate_synthetic_dataset.py --rows 5000 --out data/synthetic_transactions.csv
python scripts/train_offline_model.py --data data/synthetic_transactions.csv
```

Prints precision / recall / F1 / ROC-AUC, a confusion matrix, and ranked top
risk factors. Reinforces the point that the metrics are illustrative — see the
[Limitations table](../README.md#%EF%B8%8F-limitations--future-work).

## 7. Shutdown

```bash
docker compose down -v   # -v drops the seeded postgres volume so the next demo starts clean
```
