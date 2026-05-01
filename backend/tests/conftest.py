"""
Help DMEs — Fixtures de Teste
================================
Banco SQLite em memória para testes isolados.
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from backend.models.models import Base


@pytest_asyncio.fixture
async def test_session():
    """Cria sessão de teste com banco SQLite em memória."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    
    await engine.dispose()
