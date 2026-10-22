# Backend

Minimal FastAPI skeleton. Business endpoints and database access are not implemented yet.

```text
app/
├── main.py          # FastAPI entry point
└── api/
    └── router.py    # Register feature routers under /api/v1
```

After the repository [setup](../README.md), activate `.venv` and run from the repository root:

```bash
python -m uvicorn app.main:app --app-dir backend --reload
```

The server starts at `http://127.0.0.1:8000`. There are no routes yet, so requests return 404. Stop with `Ctrl+C`.

Add feature route modules under `app/api/` and register them in `router.py`. Follow [openapi.yaml](../openapi.yaml) and [API_CONTRACT.md](../API_CONTRACT.md). Generated API docs are disabled to keep the checked-in OpenAPI file as the sole interface specification.
