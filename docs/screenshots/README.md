# Screenshots

This folder holds UI captures used in the project README and the demo runbook.
Add PNGs here using the filenames below so the existing markdown links resolve
without further edits.

> **Reminder:** all screenshots must come from a local run against synthetic
> data. Never commit screenshots that contain real customer information.

## Suggested capture list

Capture at roughly **1280 px wide** (1× density) — readable at thumbnail size
without bloating the repo. PNG is preferred; keep each file under ~500 KB by
running it through `pngquant` or `oxipng` if needed.

| File | What to capture | How to get there |
|---|---|---|
| `dashboard-kpis.png` | KPI cards + fraud trend chart + alert feed | Log in as `analyst@meridian.ai`, open **Dashboard** after running the demo seeding endpoint |
| `review-queue.png` | Review queue with mixed pending / resolved cases | Open **Reviews** after seeding; show at least one assigned case |
| `transaction-detail.png` | A single transaction with risk score, decision band, and reason codes | Click a flagged transaction from **Transactions** |
| `shap-explanation.png` | SHAP top-factor panel with bar contributions | On the transaction detail page, expand the explainability section |
| `model-evaluation.png` | Model evaluation table (precision / recall / F1 / ROC-AUC / Brier / cost-sensitive) | **Fraud Lab → Evaluation** after a simulation run |
| `swagger-docs.png` | FastAPI Swagger UI showing the router groups | `http://localhost:8000/docs` |

## Optional extras

| File | What to capture |
|---|---|
| `case-clusters.png` | Suspicious-activity clusters with auto-generated summaries |
| `audit-trail.png` | Audit log filtered to a single transaction id |
| `rules-admin.png` | Admin rules-management view (Admin role only) |
| `login-page.png` | Login screen with the seeded demo credentials hint |

## Capture checklist

Before committing any screenshot:

- [ ] You are logged in as a demo user (no real email addresses visible).
- [ ] No real card numbers, names, or merchant identifiers appear on screen.
- [ ] Browser dev tools / extensions are closed so the chrome is clean.
- [ ] The viewport is sized to ~1280×800 (or the closest preset in your browser).
- [ ] The file is named exactly as listed above so the README links resolve.

## Updating the README

If you rename a file or add a new one, update the **Screenshots / Demo** table
in [`../../README.md`](../../README.md) to match.
