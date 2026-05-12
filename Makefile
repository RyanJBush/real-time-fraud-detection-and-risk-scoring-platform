.PHONY: install install-backend install-frontend synthetic-data train-demo eval-demo backend-test backend-lint frontend-lint frontend-typecheck frontend-build check

install: install-backend install-frontend

install-backend:
	python -m pip install -r backend/requirements.txt

install-frontend:
	cd frontend && npm ci

synthetic-data:
	python scripts/generate_synthetic_transactions.py --rows 1200 --fraud-rate 0.10 --seed 42 --out data/synthetic_transactions.csv

train-demo:
	python scripts/train_offline_model.py --data data/synthetic_transactions.csv --seed 42

eval-demo: backend-test

backend-test:
	cd backend && python -m pytest -q

backend-lint:
	cd backend && python -m ruff check .

frontend-lint:
	cd frontend && npm run lint

frontend-typecheck:
	cd frontend && npm run typecheck

frontend-build:
	cd frontend && npm run build

check: backend-lint backend-test frontend-lint frontend-typecheck frontend-build
