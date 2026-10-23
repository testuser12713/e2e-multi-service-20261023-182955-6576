"""FastAPI application of the job-processing API.

Start inside api/ with ``uvicorn main:app``. On startup the SQLite schema is created
at DATABASE_PATH (its parent directory included). CORS allows exactly the origins in
CORS_ORIGINS, never ``*`` and never with credentials.
"""

import logging
import os
import sqlite3
import traceback
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import db
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routers import jobs
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("api")

# The local Vite dev server: the only origin allowed when CORS_ORIGINS is not set.
DEFAULT_CORS_ORIGIN = "http://localhost:5173"

INTERNAL_ERROR_BODY = {"detail": "Internal Server Error"}


def get_cors_origins() -> list[str]:
    """Origins allowed by CORS, from the comma-separated CORS_ORIGINS variable.

    Only explicit http(s) origins are accepted. A wildcard or anything that is not an
    origin is dropped with a warning; when nothing valid remains, the local Vite dev
    origin is the only one allowed.
    """
    raw = os.environ.get("CORS_ORIGINS", "")
    origins: list[str] = []
    for entry in raw.split(","):
        origin = entry.strip().rstrip("/")
        if not origin:
            continue
        if "*" in origin or not origin.startswith(("http://", "https://")):
            logger.warning("CORS_ORIGINS: ignoring %r, only explicit origins are allowed", origin)
            continue
        if origin not in origins:
            origins.append(origin)
    return origins or [DEFAULT_CORS_ORIGIN]


def _log_unexpected_error(method: str, path: str, exc: BaseException) -> None:
    """Log an unhandled error with its stack, but without the exception message.

    The message of an arbitrary exception may quote request data such as a job's
    text, which must never reach the logs; type and stack locate the defect.
    """
    stack = "".join(traceback.format_list(traceback.extract_tb(exc.__traceback__)))
    logger.error("Unhandled %s on %s %s\n%s", type(exc).__name__, method, path, stack)


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Generic exception handler: 500 with a fixed body, no trace, no paths, no data."""
    _log_unexpected_error(request.method, request.url.path, exc)
    return JSONResponse(status_code=500, content=INTERNAL_ERROR_BODY)


class CatchUnexpectedErrors:
    """Turn any unhandled exception into the generic 500 INSIDE the CORS layer.

    Starlette runs a handler registered for ``Exception`` in its outermost
    middleware, outside CORSMiddleware, so that 500 would reach the browser without
    an Access-Control-Allow-Origin header and look like "API unreachable". This
    middleware sits inside CORS, so the generic 500 keeps its CORS headers.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def tracking_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, tracking_send)
        except Exception as exc:
            if response_started:
                # Too late for a clean 500; let the server close the connection.
                raise
            _log_unexpected_error(scope.get("method", "?"), scope.get("path", "?"), exc)
            response = JSONResponse(status_code=500, content=INTERNAL_ERROR_BODY)
            await response(scope, receive, send)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create the SQLite schema at DATABASE_PATH before the first request is served."""
    path = db.get_database_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = db.get_connection(path)
        try:
            db.init_schema(conn)
        finally:
            conn.close()
    except (OSError, sqlite3.Error) as exc:
        raise RuntimeError(
            f"Cannot create the SQLite database at DATABASE_PATH={path}: {exc}. "
            "Set DATABASE_PATH to a writable file path (see RUN.json and .env.example)."
        ) from exc
    app.state.database_path = path
    logger.info("SQLite schema ready")
    yield


health_router = APIRouter(tags=["health"])


@health_router.get("/health")
def health(conn: db.DbConnection) -> dict[str, str]:
    """Liveness and readiness: answers 200 only when the jobs table is reachable."""
    try:
        conn.execute("SELECT 1 FROM jobs LIMIT 1").fetchone()
    except sqlite3.Error as exc:
        logger.error("Health check: database unavailable (%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ok"}


def create_app() -> FastAPI:
    """Build the application; configuration is read here, never at import time."""
    application = FastAPI(title="Auftragsverarbeitung API", lifespan=lifespan)

    # Registered first, so CORSMiddleware (added next) wraps it.
    application.add_middleware(CatchUnexpectedErrors)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    # Backstop for an error raised outside the middleware above.
    application.add_exception_handler(Exception, handle_unexpected_error)

    application.include_router(health_router)
    application.include_router(jobs.router)
    return application


app = create_app()
