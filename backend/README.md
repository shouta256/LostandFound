# Backend

FastAPI serves the item list from PostgreSQL using SQLAlchemy ORM. Run `make setup` from the repository root to apply migrations and insert five sample items without duplication or overwriting existing rows. `make up` starts both app servers.

```text
app/
├── main.py          # FastAPI entry point
└── api/
    └── router.py    # Item list routes under /api/v1
```

After the repository [setup](../README.md), activate `.venv` and run from the repository root:

```bash
python -m uvicorn app.main:app --app-dir backend --reload
```

The server starts at `http://127.0.0.1:8000`. `GET /api/v1/items` currently requires no authentication; authentication will be added with Google login. Stop with `Ctrl+C`.

Add feature route modules under `app/api/` and register them in `router.py`. Follow [openapi.yaml](../openapi.yaml) and [API_CONTRACT.md](../API_CONTRACT.md). Generated API docs are disabled to keep the checked-in OpenAPI file as the sole interface specification.

Run `make test` from the repository root with PostgreSQL running. The two tests check repeatable seeding and API listing in isolated database schemas.
