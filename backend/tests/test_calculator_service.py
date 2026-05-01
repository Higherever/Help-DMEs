"""Testes do calculator_service."""

import pytest
from backend.models.models import (
    AppSetting, SBCSet, SBCChallenge, ChallengeRequirement, UserSquadPlayer
)
from backend.services import calculator_service


@pytest.mark.asyncio
async def test_analyze_sbc_not_found(test_session):
    """SBC inexistente deve levantar ValueError."""
    with pytest.raises(ValueError, match="não encontrado"):
        await calculator_service.analyze_sbc(test_session, 999)


@pytest.mark.asyncio
async def test_analyze_sbc_empty_squad(test_session):
    """Análise com elenco vazio."""
    # Criar setting necessária
    test_session.add(AppSetting(key="allow_active_11_in_sbc", value="false", description="t"))
    
    # Criar SBC mínimo
    sbc = SBCSet(futgg_id="test-1", name="Teste SBC", category="players", source="fut.gg")
    test_session.add(sbc)
    await test_session.flush()
    
    challenge = SBCChallenge(sbc_set_id=sbc.id, name="Desafio 1", order_index=0)
    test_session.add(challenge)
    await test_session.flush()
    
    result = await calculator_service.analyze_sbc(test_session, sbc.id)
    assert result["available_players"] == 0


@pytest.mark.asyncio
async def test_calculate_path_basic(test_session):
    """Cálculo com SBC simples."""
    test_session.add(AppSetting(key="allow_active_11_in_sbc", value="false", description="t"))
    
    sbc = SBCSet(futgg_id="test-2", name="Teste", category="upgrades", source="fut.gg")
    test_session.add(sbc)
    await test_session.flush()
    
    ch = SBCChallenge(sbc_set_id=sbc.id, name="Squad", order_index=0)
    test_session.add(ch)
    await test_session.flush()
    
    result = await calculator_service.calculate_optimal_path(test_session, sbc.id)
    assert "steps" in result
    assert "feasible" in result
