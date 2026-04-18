# Meridian AI MVP Architecture

- Ingestion: `POST /api/transactions`
- Feature extraction + fraud scoring: `POST /api/scores`
- Explainability: SHAP contributions persisted per score
- Decisions: approve/review/decline from ML score + rule overrides
- RBAC: Admin, Analyst, Viewer via JWT
