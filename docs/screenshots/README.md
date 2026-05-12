# Screenshot Documentation — Meridian

This directory stores screenshots from local demo runs.

> **Synthetic/sample transaction data only — not real banking data.**

## Current screenshot inventory

- `login-page.png` — Demo login screen.
- `dashboard-kpis.png` — KPI cards after seeded simulation run.
- `review-queue.png` — Analyst queue state for flagged synthetic transactions.
- `transaction-detail.png` — Transaction detail with score context and decision support signals.
- `shap-explanation.png` — SHAP contribution output for a synthetic transaction.
- `model-evaluation.png` — Offline model evaluation output snapshot.
- `swagger-docs.png` — FastAPI Swagger UI endpoint listing.

## Refresh checklist

- [ ] Re-capture screenshots after major UI changes.
- [ ] Verify seeded synthetic demo data is loaded before capture.
- [ ] Confirm no real customer/account identifiers appear in screenshots.
- [ ] Keep viewport and zoom consistent for portfolio readability.

## Suggested capture workflow

1. Run `docker compose up --build`.
2. Log in with demo credentials.
3. Trigger `POST /api/simulations/run-demo?seed=42`.
4. Capture each page listed above.
5. Replace old files in this directory with updated images.
