.PHONY: backend-test backend-lint frontend-lint frontend-typecheck frontend-build check

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
