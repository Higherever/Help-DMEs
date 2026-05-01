"""Testes do settings_service."""

import pytest
from backend.models.models import AppSetting
from backend.services.settings_service import (
    get_all_settings, get_setting, update_setting, get_setting_bool
)


@pytest.mark.asyncio
async def test_get_all_settings_empty(test_session):
    """Lista vazia quando banco não tem settings."""
    result = await get_all_settings(test_session)
    assert result == []


@pytest.mark.asyncio
async def test_create_and_get_setting(test_session):
    """Inserir e buscar setting."""
    setting = AppSetting(key="test_key", value="test_value", description="Teste")
    test_session.add(setting)
    await test_session.flush()
    
    found = await get_setting(test_session, "test_key")
    assert found is not None
    assert found.value == "test_value"


@pytest.mark.asyncio
async def test_update_setting(test_session):
    """Atualizar valor de uma setting."""
    setting = AppSetting(key="my_key", value="old", description="Teste")
    test_session.add(setting)
    await test_session.flush()
    
    updated = await update_setting(test_session, "my_key", "new")
    assert updated.value == "new"


@pytest.mark.asyncio
async def test_get_setting_bool(test_session):
    """Conversão para bool."""
    setting = AppSetting(key="flag", value="true", description="Flag")
    test_session.add(setting)
    await test_session.flush()
    
    result = await get_setting_bool(test_session, "flag", default=False)
    assert result is True
    
    result_missing = await get_setting_bool(test_session, "inexistente", default=False)
    assert result_missing is False
