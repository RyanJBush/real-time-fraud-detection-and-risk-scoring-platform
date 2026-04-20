# Meridian AI Platform Architecture

- Ingestion: `POST /api/transactions`
- Hybrid fraud decisioning: ML probability + rule/signal layer (velocity, geo, merchant, duplicate, anomaly proxy)
- Thresholding: approve/review/decline with reason codes and persisted decision traces
- Explainability: SHAP contributions persisted with ranked factors and decision summaries
- Manual review workflow: queue, analyst override, review history events
- KPI metrics: fraud/review rates, false-positive rate, blocked fraud value
- Seeded simulation: deterministic fraud scenario generation for demos and evaluation
- RBAC: Admin, Analyst, Reviewer, Viewer via JWT
