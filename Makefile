.PHONY: backend-test backend-lint frontend-lint frontend-build check

backend-test:
	cd backend && python -m pytest -q

backend-lint:
	cd backend && python -m ruff check .

frontend-lint:
	cd frontend && npm run lint

frontend-build:
	cd frontend && npm run build

check: backend-lint backend-test frontend-lint frontend-build
