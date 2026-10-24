# Shortcuts for local development. Run from the repository root.
#   make setup  - install dependencies, start PostgreSQL, migrate and seed
#   make up     - start PostgreSQL, FastAPI, and the React dev server
#   make down   - stop PostgreSQL
#   make test   - run backend tests against an isolated PostgreSQL schema

PYTHON ?= python3
VENV := .venv

.PHONY: setup up down test

setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r backend/requirements.txt
	cd backend && ../$(VENV)/bin/python -m app.setup_env
	cd frontend && npm install
	docker compose up -d --wait
	$(VENV)/bin/python -m alembic -c backend/alembic.ini upgrade head
	cd backend && ../$(VENV)/bin/python -m app.seed
	@echo "Setup complete. Run 'make up' to start the project."

up:
	docker compose up -d --wait
	@echo "Starting FastAPI at http://127.0.0.1:8000 and React at http://localhost:5173 (Ctrl+C to stop both)."
	@trap 'kill "$$backend_pid" 2>/dev/null; wait "$$backend_pid" 2>/dev/null' EXIT; \
	$(VENV)/bin/python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000 & \
	backend_pid=$$!; \
	cd frontend && npm run dev -- --host 127.0.0.1 --port 5173 --strictPort

down:
	docker compose down

test:
	$(VENV)/bin/python -m pytest
