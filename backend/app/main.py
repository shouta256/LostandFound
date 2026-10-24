from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import router
from app.errors import APIError

# The API contract lives in the repository's openapi.yaml.
app = FastAPI(title="Lost & Found Tracker", openapi_url=None)
app.include_router(router)


@app.exception_handler(APIError)
async def api_error(request: Request, error: APIError):
    return JSONResponse(status_code=error.status_code, headers={"Cache-Control": "no-store", **error.headers},
                        content={"error": {"code": error.code, "message": error.message, "details": []}})


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, error: RequestValidationError):
    invalid_json = any(detail["type"] == "json_invalid" for detail in error.errors())
    return JSONResponse(status_code=400 if invalid_json else 422, headers={"Cache-Control": "no-store"}, content={"error": {
        "code": "INVALID_JSON" if invalid_json else "VALIDATION_ERROR",
        "message": "Invalid JSON body." if invalid_json else "Invalid request parameters.",
        "details": [
            {"field": ".".join(map(str, detail["loc"])), "message": "Invalid value."}
            for detail in error.errors() if not invalid_json
        ],
    }})


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, error: SQLAlchemyError):
    return JSONResponse(status_code=500, headers={"Cache-Control": "no-store"}, content={"error": {
        "code": "INTERNAL_ERROR", "message": "Unable to complete the request.", "details": [],
    }})
