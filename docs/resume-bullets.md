# Resume Bullets — Meridian

- Built Meridian, a portfolio-scale fraud detection demo that scores **synthetic** card-like transactions with a FastAPI backend and React frontend.
- Implemented a reproducible offline ML workflow: generated synthetic labeled data, extracted risk features, and trained/evaluated a logistic regression baseline with ROC-AUC and confusion-matrix reporting.
- Engineered scoring features from transaction attributes (amount, merchant category patterns, country risk patterns) to mirror practical fraud-signal design choices.
- Combined model probability and rule-based indicators into decision bands used to route higher-risk events into an analyst review queue.
- Added transaction-level explanation outputs (SHAP contribution values + top factors) to support interpretable scoring discussions during demos.
- Documented architecture, API behavior, and synthetic-data limitations to keep technical claims accurate and recruiter-friendly.
