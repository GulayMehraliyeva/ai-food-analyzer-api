import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.routing import Match

logger = logging.getLogger("food_analyzer")


class ErrorCode:
    """Fixed error codes. The frontend switches on these values."""

    VALIDATION_ERROR = "VALIDATION_ERROR"          # 400
    INVALID_JSON = "INVALID_JSON"                  # 400
    UNAUTHORIZED = "UNAUTHORIZED"                  # 401 - token missing
    INVALID_TOKEN = "INVALID_TOKEN"                # 401 - token wrong / malformed header
    FORBIDDEN = "FORBIDDEN"                        # 403
    NOT_FOUND = "NOT_FOUND"                        # 404 - resource does not exist (or is not yours)
    ENDPOINT_NOT_FOUND = "ENDPOINT_NOT_FOUND"      # 404 - URL does not exist
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"      # 405
    CONFLICT = "CONFLICT"                          # 409
    INTERNAL_ERROR = "INTERNAL_ERROR"              # 500


class ApiError(Exception):
    """Raise anywhere in a request to return a structured error response."""

    def __init__(self, status_code, code, message, details=None, headers=None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        self.headers = headers


def success_response(message, data=None, status_code=200, meta=None, headers=None):
    body = {"success": True, "message": message, "data": data}
    if meta is not None:
        body["meta"] = meta
    return JSONResponse(status_code=status_code, content=body, headers=headers)


def error_response(status_code, code, message, details=None, headers=None):
    error = {"code": code, "message": message}
    if details:
        error["details"] = details
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "error": error},
        headers=headers,
    )


def validation_error(details, message="The request contains invalid or missing fields."):
    return ApiError(400, ErrorCode.VALIDATION_ERROR, message, details=details)


def _allowed_methods(request: Request):
    """Collect every method registered for the requested path (for the Allow header)."""
    methods = set()
    for route in request.app.routes:
        match, _ = route.matches(request.scope)
        if match in (Match.FULL, Match.PARTIAL) and getattr(route, "methods", None):
            methods.update(route.methods)
    methods.discard("HEAD")
    return sorted(methods)


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError):
        return error_response(exc.status_code, exc.code, exc.message, exc.details, exc.headers)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            return error_response(
                404,
                ErrorCode.ENDPOINT_NOT_FOUND,
                f"The endpoint {request.url.path} does not exist. "
                "See GET /api/v1/greeting for the list of endpoints.",
            )
        if exc.status_code == 405:
            allowed = _allowed_methods(request)
            return error_response(
                405,
                ErrorCode.METHOD_NOT_ALLOWED,
                f"Method {request.method} is not allowed for {request.url.path}. "
                f"Allowed methods: {', '.join(allowed)}.",
                headers={"Allow": ", ".join(allowed)},
            )
        return error_response(exc.status_code, "HTTP_ERROR", str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(request: Request, exc: RequestValidationError):
        details = []
        for err in exc.errors():
            loc = [str(p) for p in err.get("loc", []) if p not in ("query", "path", "body", "header")]
            details.append({"field": ".".join(loc) or "request", "message": err.get("msg", "Invalid value.")})
        return error_response(
            400, ErrorCode.VALIDATION_ERROR, "The request contains invalid or missing fields.", details
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return error_response(500, ErrorCode.INTERNAL_ERROR, "An unexpected error occurred. Please try again later.")
