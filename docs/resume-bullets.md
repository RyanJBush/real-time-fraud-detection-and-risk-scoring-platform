# Resume Bullets — Meridian Real-Time Fraud Detection Platform

ATS-friendly, one-line variants. Pick 3–4 that match the target role and drop
into the **Projects** section. Numbers reference behavior on the synthetic
dataset; reword honestly for any role-specific claims.

> **Honesty note:** Meridian is a portfolio project running on synthetic data.
> Do not phrase bullets in a way that implies real customers, real fraud loss
> prevented, or production deployment. The "Tips for tailoring" section at the
> bottom gives interview-safe wording.

## Short bullets (one line each)

- Built a real-time fraud-scoring FastAPI service with a hybrid rules + scikit-learn classifier, SHAP-based top-risk-factor explanations, and per-request decision auditing.
- Designed a synthetic transaction dataset and offline training pipeline producing precision, recall, F1, ROC-AUC, and confusion-matrix reports for model evaluation.
- Implemented a hybrid risk-scoring engine (rule layer + logistic regression) returning approve / review / decline decisions in <50 ms per transaction.
- Engineered SHAP-driven explainability that ranks the top three risk factors per transaction, making model decisions auditable for an analyst review workflow.
- Shipped a FinTech analytics platform with FastAPI, SQLAlchemy, scikit-learn, React/TypeScript, Docker Compose, and a GitHub Actions CI pipeline (lint + tests).
- Created a fraud-scenario simulator (card testing, geo attack, account takeover, bot activity) for reproducible model evaluation and demo data generation.
- Wrote pytest coverage across the scoring API, review workflow, and offline evaluator, with CI gating lint, type checks, and tests on every PR.
- Modeled fraud risk as a binary classification problem, comparing logistic regression and random forest baselines on precision / recall / F1 / ROC-AUC and calibration (Brier score).

## Skill-keyword variants

- **Machine learning / classification:** Built a binary fraud-classification model (logistic regression + random forest baselines) with class-balanced training, threshold tuning, and cost-sensitive scoring (FN:FP = 5:1).
- **Real-time APIs:** Exposed transaction scoring through a FastAPI endpoint with JWT auth, request-ID tracing, structured JSON logging, and Pydantic-validated payloads.
- **Risk scoring:** Combined rule-based signals (velocity, geo, merchant risk) with an ML probability to produce calibrated risk scores and reason codes per decision.
- **Predictive modeling:** Trained and evaluated fraud classifiers on a labeled synthetic dataset, reporting ROC-AUC, F1, false-positive rate, and confusion matrices.
- **FinTech analytics:** Surfaced fraud KPIs — block rate, false-positive rate, blocked fraud value, and trend charts — through a React/TypeScript analyst console.
- **Explainability / responsible ML:** Added SHAP feature attributions and a per-decision narrative summary so every approve / review / decline call is auditable.
- **Data engineering (light):** Wrote a deterministic synthetic-transaction generator (CSV) and a reusable offline training script that shares feature code with the live API.

## Tips for tailoring

- Lead with the verb the job description uses (Built / Designed / Shipped / Implemented).
- Keep one bullet that names the stack and one that names a measurable outcome.
- When asked about claims in interviews, be explicit that metrics come from a
  hand-crafted synthetic dataset — not production traffic — and that the project
  is a portfolio build, not a deployed product.
