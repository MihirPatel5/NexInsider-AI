"""
tests/conftest.py — Shared test fixtures and configuration.
"""
import pytest
import asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from data.config import settings


# Create a separate test engine with NullPool to avoid connection pool issues
test_engine = create_async_engine(
    settings.database_url,
    poolclass=NullPool,  # No connection pooling for tests
    echo=False,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the entire test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session."""
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest.fixture
async def clean_test_tables(db_session: AsyncSession):
    """Clean test tables before each test."""
    from sqlalchemy import text
    
    # Clean tables in correct order (respecting foreign keys)
    tables = [
        "model_predictions",
        "performance_metrics_cache",
        "performance_alerts",
        "model_drift_log",
        "feature_drift_log",
    ]
    
    for table in tables:
        try:
            await db_session.execute(text(f"DELETE FROM {table}"))
            await db_session.commit()
        except Exception:
            # Table might not exist yet
            await db_session.rollback()
    
    yield
    
    # Cleanup after test
    for table in tables:
        try:
            await db_session.execute(text(f"DELETE FROM {table}"))
            await db_session.commit()
        except Exception:
            await db_session.rollback()
