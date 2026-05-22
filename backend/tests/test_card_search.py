"""Testes de busca de cards de jogador (/api/cards/search-image)."""

import pytest
from sqlalchemy import select, func
from backend.models.models import PlayerCard, FCPlayer, SBCSet


async def execute_card_search(session, name: str, league: str = None, team: str = None):
    """
    Simula a lógica exata de busca de imagem implementada no endpoint do backend.
    """
    async def try_search(exact_match: bool):
        # 1. Buscar na tabela player_cards
        query_pc = select(PlayerCard).where(PlayerCard.card_image_url != None)
        query_pc = query_pc.where(
            func.lower(PlayerCard.name).like(f"%{name.lower()}%")
        )
        
        if exact_match:
            if league:
                query_pc = query_pc.where(
                    func.lower(PlayerCard.league_name).like(f"%{league.lower()}%")
                )
            if team:
                query_pc = query_pc.where(
                    func.lower(PlayerCard.club_name).like(f"%{team.lower()}%")
                )
                
        result_pc = await session.execute(query_pc)
        pc_player = result_pc.scalars().first()
        if pc_player:
            return pc_player.card_image_url

        # 2. Buscar na tabela fc_players
        query_fc = select(FCPlayer).where(FCPlayer.card_template_url != None)
        query_fc = query_fc.where(
            func.lower(FCPlayer.name).like(f"%{name.lower()}%")
        )
        
        if exact_match:
            if league:
                query_fc = query_fc.where(
                    func.lower(FCPlayer.league).like(f"%{league.lower()}%")
                )
            if team:
                query_fc = query_fc.where(
                    func.lower(FCPlayer.club).like(f"%{team.lower()}%")
                )
                
        result_fc = await session.execute(query_fc)
        fc_player = result_fc.scalars().first()
        if fc_player:
            return fc_player.card_template_url
            
        return None

    # Tenta busca exata
    card_path = await try_search(exact_match=True)
    
    # Fallback por nome se falhar
    if not card_path and (league or team):
        card_path = await try_search(exact_match=False)
        
    if not card_path:
        return None
        
    return {
        "full_image_url": card_path,
        "small_image_url": card_path.replace("/full/", "/small/")
    }


@pytest.mark.asyncio
async def test_search_exact_match_player_card(test_session):
    """Busca exata de PlayerCard por nome, liga e time."""
    # Criar um SBC set para vincular o player card (FK obrigatória)
    sbc = SBCSet(id=10, futgg_id="sbc-10", name="SBC Teste", category="players")
    test_session.add(sbc)
    await test_session.flush()

    card = PlayerCard(
        sbc_set_id=10,
        name="Kylian Mbappé",
        overall=94,
        country="França",
        club_name="Paris Saint-Germain",
        league_name="Ligue 1 McDonald's",
        card_image_url="/images/cards/full/sbc_player_10_kylian_mbappe_ligue_1_franca_psg.png"
    )
    test_session.add(card)
    await test_session.flush()

    # Busca com match exato
    result = await execute_card_search(
        test_session,
        name="Mbappé",
        league="Ligue 1",
        team="Paris"
    )
    assert result is not None
    assert result["full_image_url"] == "/images/cards/full/sbc_player_10_kylian_mbappe_ligue_1_franca_psg.png"
    assert result["small_image_url"] == "/images/cards/small/sbc_player_10_kylian_mbappe_ligue_1_franca_psg.png"


@pytest.mark.asyncio
async def test_search_exact_match_fc_player(test_session):
    """Busca exata de FCPlayer por nome, liga e clube."""
    player = FCPlayer(
        futbin_id="12345",
        name="Lionel Messi",
        overall=92,
        nation="Argentina",
        club="Inter Miami CF",
        league="Major League Soccer",
        card_template_url="/images/cards/full/fc_player_12345_lionel_messi_mls_argentina_inter_miami.png"
    )
    test_session.add(player)
    await test_session.flush()

    result = await execute_card_search(
        test_session,
        name="Messi",
        league="Soccer",
        team="Miami"
    )
    assert result is not None
    assert result["full_image_url"] == "/images/cards/full/fc_player_12345_lionel_messi_mls_argentina_inter_miami.png"
    assert result["small_image_url"] == "/images/cards/small/fc_player_12345_lionel_messi_mls_argentina_inter_miami.png"


@pytest.mark.asyncio
async def test_search_fallback_by_name(test_session):
    """Busca exata falha por time/liga divergente, mas fallback por nome encontra o jogador."""
    sbc = SBCSet(id=20, futgg_id="sbc-20", name="SBC Messi", category="players")
    test_session.add(sbc)
    await test_session.flush()

    card = PlayerCard(
        sbc_set_id=20,
        name="Lionel Messi",
        overall=92,
        country="Argentina",
        club_name="Inter Miami CF",
        league_name="Major League Soccer",
        card_image_url="/images/cards/full/sbc_player_20_lionel_messi.png"
    )
    test_session.add(card)
    await test_session.flush()

    # Liga divergente (ex. "La Liga" em vez de "Major League Soccer")
    result = await execute_card_search(
        test_session,
        name="Messi",
        league="La Liga",
        team="Inter Miami"
    )
    # A busca exata falha, mas o fallback por nome deve retornar com sucesso
    assert result is not None
    assert result["full_image_url"] == "/images/cards/full/sbc_player_20_lionel_messi.png"


@pytest.mark.asyncio
async def test_search_no_match(test_session):
    """Busca por nome que não existe retorna None."""
    result = await execute_card_search(
        test_session,
        name="Neymar Jr"
    )
    assert result is None
