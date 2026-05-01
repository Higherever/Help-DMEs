"""
Help DMEs — Settings Service
==============================
CRUD de configurações globais do sistema (tabela app_settings).

Configurações disponíveis:
  - allow_active_11_in_sbc (bool): Permite usar time titular em SBCs
  - auto_exclude_loans (bool): Exclui empréstimos automaticamente
  - default_source (str): Fonte primária de scraping
  - scrape_on_startup (bool): Scraping automático ao iniciar
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.models import AppSetting


async def get_all_settings(session: AsyncSession) -> list[AppSetting]:
    """Retorna todas as configurações do sistema."""
    result = await session.execute(
        select(AppSetting).order_by(AppSetting.key)
    )
    return list(result.scalars().all())


async def get_setting(session: AsyncSession, key: str) -> AppSetting | None:
    """Busca uma configuração pela chave. Retorna None se não existir."""
    return await session.get(AppSetting, key)


async def update_setting(session: AsyncSession, key: str, value: str) -> AppSetting:
    """
    Atualiza o valor de uma configuração existente.
    Levanta ValueError se a chave não existir.
    """
    setting = await session.get(AppSetting, key)
    if not setting:
        raise ValueError(f"Configuração '{key}' não encontrada.")
    setting.value = value
    await session.flush()
    return setting


async def get_setting_bool(session: AsyncSession, key: str, default: bool = False) -> bool:
    """
    Atalho: busca uma configuração e retorna como bool.
    Usa a property .as_bool do modelo AppSetting.
    Retorna o valor default se a chave não existir.
    """
    setting = await session.get(AppSetting, key)
    if not setting:
        return default
    return setting.as_bool
