"""Task-scoped async database session for Celery workers.

Celery tasks are synchronous and run in prefork processes, so we create a fresh
async engine per task run (NullPool) and dispose it afterwards. This avoids
sharing an event-loop-bound connection pool across tasks.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


@asynccontextmanager
async def task_session() -> AsyncIterator[AsyncSession]:
    settings = get_settings()
    engine = create_async_engine(str(settings.database_url), poolclass=NullPool)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    finally:
        await engine.dispose()
