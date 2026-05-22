# Changelog

## v1.0.0 — May 2026
- Hardened root `.gitignore` to exclude model artifacts, environment files, Node dependencies, OS cruft, and generated datasets across `data/` directories.
- Clarified README architecture language to describe a batch processing pipeline with streaming simulation via generator patterns.
- Added README sections for "How it Works", "Model Performance", Live Demo badge, and updated screenshot guidance under `docs/images/`.
- Added and standardized GitHub Actions CI workflow for Python 3.11, Ruff linting, and a pytest smoke test.

## 2026-05-14
- Added model drift detection service (PSI + KS test) and `/api/monitoring/drift` endpoint.
- Added A/B scoring endpoint `/api/score/ab` with model_a/model_b predictions and SHAP output.
- Added dashboard drift alert and side-by-side ModelComparison component.
- Added synthetic data generator script and demo instructions.
- Added GitHub Actions CI workflow and root `pyproject.toml`.
