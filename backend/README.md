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

The server starts at `http://127.0.0.1:8000`. `GET /api/v1/items` remains temporarily unauthenticated as specified in the contract. Stop with `Ctrl+C`.

Add feature route modules under `app/api/` and register them in `router.py`. Follow [openapi.yaml](../openapi.yaml) and [API_CONTRACT.md](../API_CONTRACT.md). Generated API docs are disabled to keep the checked-in OpenAPI file as the sole interface specification.

Run `make test` from the repository root with PostgreSQL running. Tests use isolated database schemas; authentication tests mock Google verification and require no Google credentials.

## Google Authentication

Run `make setup`, then `make up`. Open `http://localhost:5173` and sign in with Google. Keep Docker Desktop running; PostgreSQL is needed for login.

Setup copies the shared `GOOGLE_CLIENT_ID` from `.env.example` and creates a private `AUTH_SECRET_KEY` in `.env`. It fills empty values and keeps existing settings. Never share or commit `.env`. Only the public client ID is sent to the browser.

To use another Google web client, set `GOOGLE_CLIENT_ID` in `.env`. Allow `http://localhost` and `http://localhost:5173` in its JavaScript origins. Restart the servers after changing settings.

The backend checks the Google ID token and returns a one-hour application token. The frontend keeps it in memory and clears it on sign-out, expiry, or reload. Sign-out does not revoke the token or sign out of Google. There is no refresh token.

New users are students. Repeat logins keep the user ID and assigned role. For protected routes, import `get_current_user` from `app.auth` and use `Depends(get_current_user)`. It returns the database User with the current role. Send `Authorization: Bearer <access_token>` with requests. Use `Depends(require_team_member)` from `app.auth` for team-member-only routes; students receive 403 and unauthenticated requests receive 401. In tests, override the database and authentication settings dependencies.

For local/dev role assignment, activate `.venv`, change to `backend/`, and run `python -m app.set_role student@example.com team_member` (or use `student` to demote). The user must sign in once first, then sign in again to get the new role in the frontend. Email matching is case-insensitive.

For deployment, use a separate Google client and allow the production frontend origin. Set `GOOGLE_CLIENT_ID` for both the frontend build and backend. Store a random `AUTH_SECRET_KEY` of at least 32 bytes in the hosting service's secrets. Use the same key for all backend instances; do not reuse local keys. Confirm deployment settings under R3 in [API_CONTRACT.md](../API_CONTRACT.md).
