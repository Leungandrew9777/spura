import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.endpoints import router as v1_router
from app.db.init_db import init_database

logger = logging.getLogger("spura")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables and seed league data on startup. Idempotent, so it is safe to
    # run on every boot. If the database is not yet reachable, log and continue;
    # the API's own startup will not be blocked.
    try:
        init_database()
        logger.info("Database schema initialized")
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not initialize database: %s", exc)
    yield


app = FastAPI(
    title="Spura Engine",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# CORS: allow the deployed frontend origin (or all origins for a public API).
# The browser CORS spec forbids a wildcard origin combined with credentials,
# so only enable credentials when specific origins are configured.
cors_origins = settings.CORS_ORIGINS
allow_credentials = "*" not in cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
