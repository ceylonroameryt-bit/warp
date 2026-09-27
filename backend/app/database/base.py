"""
Warp Ladger — Async SQLAlchemy Engine, Session Factory, and Redis Client
"""
from typing import AsyncGenerator

import structlog
from redis.asyncio import Redis, from_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

log = structlog.get_logger(__name__)

# ─── SQLAlchemy Async Engine ─────────────────────────────────
engine_kwargs = {
    "pool_recycle": settings.DB_POOL_RECYCLE,
    "pool_pre_ping": True,
    "echo": settings.is_development,
}
if not settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

AsyncSessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.compiler import compiles


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


# ─── SQLite Dialect Compatibility (for automated testing) ─────
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):
    return "VARCHAR(36)"


# ─── Redis ───────────────────────────────────────────────────
_redis_client: Redis | None = None


def get_redis() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


# ─── Lifecycle ───────────────────────────────────────────────
async def init_db() -> None:
    """Called at application startup."""
    try:
        import app.database.models  # noqa: F401 - ensure models are registered
        async with engine.begin() as conn:
            if settings.DATABASE_URL.startswith("sqlite"):
                await conn.run_sync(Base.metadata.create_all)
            else:
                await conn.run_sync(lambda _: None)  # verify connection
        log.info("database_connected", url=settings.DATABASE_URL.split("@")[-1])

        if settings.DATABASE_URL.startswith("sqlite"):
            from app.roles.service import seed_permissions_and_roles
            async with AsyncSessionFactory() as session:
                await seed_permissions_and_roles(session)
    except Exception as e:
        log.error("database_connection_failed", error=str(e))
        raise


async def close_db() -> None:
    """Called at application shutdown."""
    await engine.dispose()
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
    log.info("database_closed")


# ─── Session Dependency ───────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields a database session."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
