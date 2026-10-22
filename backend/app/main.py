from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import router

# The API contract lives in the repository's openapi.yaml.
app = FastAPI(title="Lost & Found Tracker", openapi_url=None)
app.include_router(router)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, error: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid request parameters.",
        "details": [
            {"field": ".".join(map(str, detail["loc"])), "message": "Invalid value."}
            for detail in error.errors()
        ],
    }})


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, error: SQLAlchemyError):
    return JSONResponse(status_code=500, content={"error": {
        "code": "INTERNAL_ERROR", "message": "Unable to load items.", "details": [],
    }})
