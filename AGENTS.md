# Project Instructions

## Project and Sources

Lost & Found Tracker is a small CM333 university MVP; favor straightforward, readable solutions over extra frameworks or abstractions.

- [openapi.yaml](openapi.yaml) is the sole API interface specification.
- [API_CONTRACT.md](API_CONTRACT.md) contains confirmed workflow decisions and the remaining R3 configuration question.
- [README.md](README.md) covers setup; [GITHUB_GUIDE.md](GITHUB_GUIDE.md) covers contribution and review.
- MVP scope is US1-US11, including Campus Item Pickup; US6 remains medium priority and US12-US15 remain future features.
- Follow the latest explicit user instructions; do not silently change confirmed D1-D8 or R1-R2 decisions or infer answers to R3.

## Working Style

- Write repository documentation and code identifiers in English; follow the user's language preference in conversation.
- Lead with the outcome and prioritize correctness, relevance, and necessary detail over arbitrary brevity.
- Keep documentation concise; define API schemas in OpenAPI and business workflow in API_CONTRACT.md, without copying them into other files.
- Stay within the requested task; a documentation task does not authorize application implementation.
- Inspect existing files before editing and preserve unrelated changes, including untracked files.
- Avoid new dependencies or configuration unless needed for the requested change.

## Technology

- Frontend: React, TypeScript, Vite; source in `frontend/src/`.
- Backend: Python, FastAPI, Pydantic; dependencies in `backend/requirements.txt`.
- Persistence: PostgreSQL, SQLAlchemy, Alembic; local database configured by `docker-compose.yml`.
- Use the existing project scripts rather than introducing a second setup workflow.

## Verification

Run checks relevant to the change; do not install or start the full application for a documentation-only edit.

| Change | Check |
| --- | --- |
| OpenAPI | `uv tool run --from openapi-spec-validator openapi-spec-validator --schema 3.1 openapi.yaml` if `uv` is available, or another OpenAPI 3.1 validator. |
| Frontend | `npm --prefix frontend run lint` and `npm --prefix frontend run build`. |
| Backend | `.venv/bin/python -m pytest` when backend tests exist. |
| Markdown | Check local links and consistency with the referenced files. |

- For behavior changes, add meaningful tests where appropriate and check affected permissions and workflow.
- For contract changes, verify methods, paths, schemas, status/error codes, and references; API validation is not proof of an implemented endpoint.
- Report changes, checks performed, checks not run, and remaining questions without claiming unverified results.

## Git and Local Data

- Work on a feature branch, not directly on `main`.
- Keep work local; do not push, open a pull request, or merge unless explicitly requested.
- Follow the repository's review requirements before merging.
- Never commit credentials or `.env`, overwrite unrelated work, or reset the worktree to discard changes.
- Do not delete database volumes or other user data as part of routine setup or verification.
