from fastapi import FastAPI

from app.api.router import router

# The API contract lives in the repository's openapi.yaml.
app = FastAPI(title="Lost & Found Tracker", openapi_url=None)
app.include_router(router)
