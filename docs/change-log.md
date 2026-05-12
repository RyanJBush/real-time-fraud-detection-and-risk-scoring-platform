# Meridian Change Log

## 2026-05-12 — Portfolio honesty and documentation refresh

- Rewrote the root README to explicitly position Meridian as a **portfolio-scale fraud detection demo** using synthetic/sample transaction data only.
- Clarified student identity statement and removed hype-oriented phrasing (for example "production-ready" style claims).
- Added practical local developer commands in `Makefile` for dependency install, synthetic data generation, offline training demo, and quick evaluation.
- Added `scripts/generate_synthetic_transactions.py` as a synthetic-only data generation entry point aligned to model expectations.
- Refined Portfolio Preview page language and visuals to emphasize demo architecture, synthetic-data disclaimer, and concrete ML workflow steps.
- Updated resume bullets to focus on implemented technical work: feature engineering, logistic baseline training, rule+model decisioning, and SHAP explanations.
- Refreshed screenshots documentation wording and checklist to reinforce synthetic-data-only usage.

## Claims softened/corrected

- "Live Preview" style wording standardized to portfolio/design preview context.
- Real-world banking implications removed; no claims of real customer accounts, institution integrations, or deployment readiness.
- Model claims constrained to what is implemented in-repo (rules + logistic regression + SHAP-backed explanation outputs).
