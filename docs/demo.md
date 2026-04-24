# Meridian AI Demo Guide

This script is designed for interviews and portfolio walkthroughs.

## Setup
1. Start stack: `docker compose up --build`
2. Open frontend at `http://localhost:5173`
3. Login as `analyst@meridian.ai` / `password123`

## Storyline

### 1) Ingestion → Scoring
- Navigate to **Transactions**.
- Create a transaction using the ingest form.
- Click **Score** on the new row.
- Open transaction details and highlight:
  - decision
  - thresholds
  - SHAP contributions
  - reason codes.

### 2) Manual Review Workflow
- Navigate to **Review Queue**.
- Select a case.
- Show AI suggestion and confidence.
- Assign the case to a reviewer.
- Submit an analyst override decision with notes.
- Show history timeline update.

### 3) Fraud Realism + Evaluation
- Navigate to **Fraud Lab**.
- Run `high_value_geo_attack` simulation with deterministic seed.
- Wait for seeded transactions to be scored.
- Show:
  - model evaluation table (F1/AUC/Brier/cost)
  - suspicious clusters and generated summaries.

### 4) Business Impact
- Navigate to **Dashboard**.
- Show fraud and review KPIs, blocked fraud value, and trend updates.

## Suggested Talking Points
- Hybrid model + rules for explainable decisioning.
- Human-in-the-loop review with full action traceability.
- Scenario simulation for reproducible fraud testing.
- Evaluation metrics with calibration/cost perspectives.
