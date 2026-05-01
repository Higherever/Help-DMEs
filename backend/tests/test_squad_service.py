"""Testes do squad_service."""

import pytest
from backend.models.models import AppSetting, UserSquadPlayer
from backend.services import squad_service


CSV_EXEMPLO = (
    "Name,Rating,Rarity,Preferred Position,Nation,League,Team,"
    "Price Limits,Last Sale Price,Discard Value,Untradeable,Loans,"
    "DefinitionId,IsDuplicate,IsInActive11,Alternate Positions,ExternalPrice\n"
    "Jogador A,80,Raro,VOL,Brasil,Premier League,Chelsea,"
    "Mín.:750 Máx.:5000,1000,650,false,false,11111,false,false,VOL,1000\n"
    "Jogador B,75,Comum,ZAG,Argentina,La Liga,Real Madrid,"
    "Mín.:500 Máx.:2000,500,400,true,false,22222,true,false,ZAG,-- NA --\n"
    "Jogador C,70,Raro,ATA,França,Ligue 1,PSG,"
    "Mín.:300 Máx.:1000,300,200,false,true,33333,false,false,ATA,500\n"
).encode("utf-8")


@pytest.mark.asyncio
async def test_import_csv(test_session):
    result = await squad_service.import_csv(test_session, CSV_EXEMPLO)
    assert result["total_imported"] == 3
    assert result["total_skipped"] == 0


@pytest.mark.asyncio
async def test_get_squad_filters(test_session):
    await squad_service.import_csv(test_session, CSV_EXEMPLO)
    
    # Filtro por rating mínimo
    players = await squad_service.get_squad(test_session, rating_min=80)
    assert len(players) == 1
    assert players[0].name == "Jogador A"
    
    # Filtro excluindo empréstimos
    players_no_loans = await squad_service.get_squad(test_session, exclude_loans=True)
    assert len(players_no_loans) == 2  # Jogador C é empréstimo


@pytest.mark.asyncio
async def test_exclude_player(test_session):
    await squad_service.import_csv(test_session, CSV_EXEMPLO)
    players = await squad_service.get_squad(test_session)
    
    player = await squad_service.exclude_player(test_session, players[0].id)
    assert player.is_excluded is True
    
    # Toggle de volta
    player = await squad_service.exclude_player(test_session, players[0].id)
    assert player.is_excluded is False


@pytest.mark.asyncio
async def test_get_available_for_sbc(test_session):
    # Precisa da setting para o teste funcionar
    setting = AppSetting(key="allow_active_11_in_sbc", value="false", description="test")
    test_session.add(setting)
    await test_session.flush()
    
    await squad_service.import_csv(test_session, CSV_EXEMPLO)
    available = await squad_service.get_available_for_sbc(test_session)
    
    # Jogador C é empréstimo, deve ser excluído
    assert all(p.is_loan is False for p in available)
    assert all(p.is_excluded is False for p in available)
