"""Main FastAPI application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
import structlog

from .core.config import settings
from .core.database import init_db
from .api.routes import cards, stores
from .scrapers import registry
from .models.schemas import HealthStatus


# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("starting collected company")
    await init_db()
    logger.info("database initialized")
    logger.info("registered scrapers", count=registry.count(), scrapers=registry.list_available())
    yield
    # Shutdown
    logger.info("shutting down collected company")


app = FastAPI(
    title="Collected Company",
    description="MTG singles price aggregator for local game stores",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(cards.router)
app.include_router(stores.router)

# Mount static files
app.mount("/static", StaticFiles(directory="collected_company/static"), name="static")

# Templates
templates = Jinja2Templates(directory="collected_company/templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health", response_model=HealthStatus)
async def health_check():
    """Health check endpoint."""
    from .core.database import engine
    from sqlalchemy import text

    # Test database connection
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        logger.error("database health check failed", error=str(e))
        db_status = f"error: {str(e)}"

    # Count active stores
    from .core.database import AsyncSessionLocal
    from .models.store import Store
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Store).where(Store.is_active == True))
        active_stores = len(list(result.scalars().all()))

    return HealthStatus(
        status="ok" if db_status == "ok" else "degraded",
        database=db_status,
        scrapers_available=registry.count(),
        active_stores=active_stores,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("collected_company.main:app", host="0.0.0.0", port=8000, reload=True)
