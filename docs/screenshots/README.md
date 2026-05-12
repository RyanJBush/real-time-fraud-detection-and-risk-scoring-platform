# Screenshot Documentation — Meridian

This folder stores screenshots for README, architecture walkthroughs, and demo storytelling.

## Accuracy and privacy rules

- Capture only from local/demo runs seeded with synthetic/sample transactions.
- Never include real banking data, real customer data, or production environment artifacts.
- Ensure screenshots do not imply live fraud-prevention operations.

## Required screenshot set

| File | Purpose |
|---|---|
| `login-page.png` | Demonstrate role-based entry experience |
| `dashboard-kpis.png` | Show KPI summary and trend context |
| `review-queue.png` | Show analyst triage queue |
| `transaction-detail.png` | Show risk score + decision trace |
| `shap-explanation.png` | Show explainability factors for one score |
| `model-evaluation.png` | Show synthetic model evaluation metrics |
| `swagger-docs.png` | Show documented API surface in Swagger |

## Capture standard

- Resolution target: ~`1280x800`
- Format: PNG
- Keep image size optimized (<500 KB where practical)
- Use consistent theme/zoom for recruiter readability

## Suggested capture flow

1. Run `docker compose up --build`.
2. Log in with seeded demo account.
3. Execute `POST /api/simulations/run-demo?seed=42`.
4. Capture each screen in the table above.

## Alt-text / caption guidance for docs

When embedding screenshots in markdown, use captions that reinforce responsible claims:

- ✅ “Synthetic demo risk score with SHAP feature contributions.”
- ✅ “Analyst review queue in local portfolio environment.”
- ❌ “Live fraud prevention dashboard for banking customers.”

## Maintenance note

If UI changes significantly, refresh screenshots and update README references in the same PR/commit.
