# Screenshot Documentation — Meridian

This directory contains screenshots captured from local demo runs.

> **Data disclaimer:** Uses synthetic transaction data — not real banking data.

## Current screenshot inventory

The following files currently exist in this folder:

- `login-page.png` — Login screen for local portfolio demo access
- `dashboard-kpis.png` — KPI dashboard after demo simulation seed
- `review-queue.png` — Analyst queue for pending and resolved reviews
- `transaction-detail.png` — Transaction detail with score context and reason trace
- `shap-explanation.png` — SHAP contribution visualization from explanation endpoint
- `model-evaluation.png` — Offline evaluation view based on synthetic labels
- `swagger-docs.png` — Backend API reference in Swagger UI

## Capture checklist for future refreshes

- [ ] Re-capture screenshots after major UI layout changes
- [ ] Verify seeded synthetic data is loaded before capturing
- [ ] Confirm no real customer or banking data appears in any image
- [ ] Keep consistent viewport and zoom for recruiter readability

## Suggested capture workflow

1. Run `docker compose up --build`.
2. Log in with demo credentials.
3. Trigger `POST /api/simulations/run-demo?seed=42`.
4. Capture each screen listed in the inventory.
