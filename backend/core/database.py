"""
Help DMEs — Database Engine & Session
=======================================
SQLAlchemy Async com SQLite (aiosqlite).
Banco: database/help_dmes.db (portável para PyInstaller).
"""

import os
from pathlib import Path
from contextlib import asynccontextmanager
import logging

from sqlalchemy.ext.asyncio import (
    create_async_engine, AsyncSession, async_sessionmaker,
)
from backend.models.models import Base

logger = logging.getLogger("help_dmes." + __name__.split(".")[-1])

# Caminhos
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATABASE_DIR = PROJECT_ROOT / "database"
DATABASE_FILE = DATABASE_DIR / "help_dmes.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_FILE}"

# Engine Async
engine = create_async_engine(
    DATABASE_URL, echo=False,
    connect_args={"check_same_thread": False, "timeout": 30},
)

# Session Factory
async_session_factory = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False,
)


@asynccontextmanager
async def get_session():
    """Context manager para sessão async."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_session_dependency():
    """Dependency injection para FastAPI endpoints."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    Inicializa o banco:
      1. Cria diretório database/
      2. Cria tabelas (CREATE TABLE IF NOT EXISTS)
      3. Popula seed data (mapeamentos + settings)
    """
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from backend.core.seed import seed_initial_data
    await seed_initial_data()

    logger.info(f"✅ Banco de dados inicializado: {DATABASE_FILE}")


async def drop_db():
    """Remove todas as tabelas. ⚠️ DESTRUTIVO!"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("⚠️ Todas as tabelas foram removidas.")
