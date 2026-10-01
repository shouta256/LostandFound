# Shortcuts for local development. Run from the repository root.
#   make setup  - install everything (run once, and again when dependencies change)
#   make up     - start PostgreSQL and the React dev server
#   make down   - stop PostgreSQL

PYTHON ?= python3
VENV := .venv

.PHONY: setup up down

setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r backend/requirements.txt
	@if [ ! -f .env ]; then cp .env.example .env && echo "Created .env from .env.example"; else echo ".env already exists, leaving it unchanged"; fi
	cd frontend && npm install
	@echo "Setup complete. Run 'make up' to start the project."

up:
	docker compose up -d --wait
	@echo "PostgreSQL is running on localhost:5432. Starting React at http://localhost:5173 (Ctrl+C to stop)."
	cd frontend && npm run dev

down:
	docker compose down
