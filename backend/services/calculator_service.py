"""
Help DMEs — Calculator Service
=================================
Motor de otimização para completar DMEs/SBCs.
Analisa o elenco atual do usuário e sugere a rota ótima de forragem
respeitando prioridades e regras de negócio.
"""

from typing import List, Dict, Any, Tuple
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.models import SBCSet, SBCChallenge, ChallengeRequirement, UserSquadPlayer, PositionMapping, RarityMapping
from backend.services.squad_service import get_available_for_sbc
from backend.schemas.schemas import (
    AnalysisResponse, CalculatePathResponse, StepResponse, SuggestedPlayerResponse,
    SBCSetResponse, UserSquadPlayerResponse, ChallengeRequirementResponse
)

logger = logging.getLogger("help_dmes." + __name__.split(".")[-1])

FORMATIONS = {
    "4-4-2": ["GK","RB","CB","CB","LB","RM","CM","CM","LM","ST","ST"],
    "4-3-3": ["GK","RB","CB","CB","LB","CM","CM","CM","RW","ST","LW"],
    "4-3-3(4)": ["GK","RB","CB","CB","LB","CM","CM","CAM","RW","ST","LW"],
    "4-2-3-1": ["GK","RB","CB","CB","LB","CDM","CDM","CAM","CAM","CAM","ST"],
    "3-5-2": ["GK","CB","CB","CB","CDM","CM","CM","RM","LM","ST","ST"],
    "4-1-2-1-2": ["GK","RB","CB","CB","LB","CDM","CM","CM","CAM","ST","ST"],
    "4-1-2-1-2(2)": ["GK","RB","CB","CB","LB","CDM","CM","CM","CAM","ST","ST"],
    "4-5-1": ["GK","RB","CB","CB","LB","CM","CM","CM","RM","LM","ST"],
    "3-4-3": ["GK","CB","CB","CB","CM","CM","RM","LM","RW","LW","ST"],
}

_cached_rarity_map = None
_cached_position_map = None


async def _load_rarity_mappings(session: AsyncSession) -> Dict[str, RarityMapping]:
    """Carrega mapeamentos de raridade do banco com cache em memória."""
    global _cached_rarity_map
    if _cached_rarity_map is None:
        result = await session.execute(select(RarityMapping))
        _cached_rarity_map = {r.pt.lower(): r for r in result.scalars().all()}
    return _cached_rarity_map


async def _load_position_mappings(session: AsyncSession) -> Dict[str, str]:
    """Carrega mapeamentos de posições do banco com cache em memória."""
    global _cached_position_map
    if _cached_position_map is None:
        result = await session.execute(select(PositionMapping))
        _cached_position_map = {p.pt.upper(): p.en.upper() for p in result.scalars().all()}
    return _cached_position_map


def _estimate_card_cost(target_rating: int) -> int:
    """Estima o custo de uma carta individual baseado no rating alvo do desafio."""
    if target_rating >= 90: return 50000
    if target_rating >= 88: return 20000
    if target_rating >= 85: return 8000
    if target_rating >= 80: return 2000
    return 500


async def _get_sbc_with_relations(session: AsyncSession, sbc_id: int) -> SBCSet:
    """Busca o SBC com seus challenges e requirements pré-carregados."""
    result = await session.execute(
        select(SBCSet)
        .where(SBCSet.id == sbc_id)
        .options(
            selectinload(SBCSet.challenges).selectinload(SBCChallenge.requirements)
        )
    )
    sbc = result.scalar_one_or_none()
    if not sbc:
        raise ValueError(f"SBC com id {sbc_id} não encontrado.")
    return sbc


def _player_to_response(player: UserSquadPlayer) -> UserSquadPlayerResponse:
    """Converte o model para o schema."""
    return UserSquadPlayerResponse(
        id=player.id, name=player.name, rating=player.rating,
        rarity=player.rarity, preferred_position=player.preferred_position,
        nation=player.nation, league=player.league, team=player.team,
        price_min=player.price_min, price_max=player.price_max,
        last_sale_price=player.last_sale_price, discard_value=player.discard_value,
        external_price=player.external_price, is_untradeable=player.is_untradeable,
        is_loan=player.is_loan, is_duplicate=player.is_duplicate,
        is_in_active_11=player.is_in_active_11, is_excluded=player.is_excluded,
        definition_id=player.definition_id,
        alternate_positions=player.alternate_positions,
        imported_at=player.imported_at,
    )


def _sbc_to_response(sbc: SBCSet) -> SBCSetResponse:
    """Converte o model para o schema resumido."""
    return SBCSetResponse(
        id=sbc.id, futgg_id=sbc.futgg_id, name=sbc.name,
        description=sbc.description, category=sbc.category,
        total_cost=sbc.total_cost, challenges_count=sbc.challenges_count,
        expires_at=sbc.expires_at, is_repeatable=sbc.is_repeatable,
        image_url=sbc.image_url, completion_pct=sbc.completion_pct,
        is_new=sbc.is_new, source=sbc.source, scraped_at=sbc.scraped_at,
    )


def _meets_requirement(player: UserSquadPlayer, req: ChallengeRequirement, rarity_map: Dict[str, RarityMapping] = None) -> bool:
    """Verifica se um jogador atende a um requisito específico (avaliação individual)."""
    # Requisitos como 'min_team_rating' ou 'min_leagues_in_squad' são validados no grupo, não no jogador.
    
    if req.requirement_type == "player_quality":
        quality = req.detail.lower() if req.detail else ""
        rm = rarity_map.get(player.rarity.lower()) if rarity_map else None
        
        if rm:
            if "gold" in quality: return rm.is_gold
            if "silver" in quality: return not rm.is_gold and player.rating >= 65
            if "bronze" in quality: return player.rating < 65
        
        # Fallback se não encontrar no mapa ou mapa não provido
        if "gold" in quality: return player.rating >= 75
        if "silver" in quality: return 65 <= player.rating < 75
        if "bronze" in quality: return player.rating < 65
        return False
    
    if req.requirement_type == "player_rarity":
        rarity_detail = req.detail.lower() if req.detail else ""
        rm = rarity_map.get(player.rarity.lower()) if rarity_map else None
        
        if rm:
            if "rare" in rarity_detail: return rm.is_rare
            if "common" in rarity_detail: return not rm.is_rare
            
        # Fallback ou match direto por string
        return rarity_detail in player.rarity.lower()

    if req.requirement_type == "player_type":
        type_detail = req.detail.upper() if req.detail else ""
        rm = rarity_map.get(player.rarity.lower()) if rarity_map else None
        
        if rm:
            if "TOTW" in type_detail: return rm.is_totw
            if "TOTS" in type_detail: return rm.is_tots
            
        return type_detail in player.rarity.upper()
        
    if req.requirement_type == "players_from_league":
        return (req.detail and req.detail.lower() in player.league.lower())
        
    if req.requirement_type == "players_from_nation":
        return (req.detail and req.detail.lower() in player.nation.lower())
        
    if req.requirement_type == "players_from_club":
        return (req.detail and req.detail.lower() in player.team.lower())

    return True # Se for um requisito de grupo ou desconhecido, ignoramos na checagem individual


async def analyze_sbc(session: AsyncSession, sbc_id: int) -> dict:
    """
    Análise de viabilidade do SBC.
    Retorna um dict compatível com AnalysisResponse.
    """
    try:
        sbc = await _get_sbc_with_relations(session, sbc_id)
    except ValueError as e:
        raise ValueError(str(e))

    available_players = await get_available_for_sbc(session)
    total_available = len(available_players)
    
    # Carregar mapeamentos para verificação precisa
    rarity_map = await _load_rarity_mappings(session)

    total_requirements = 0
    met_requirements = 0
    unmet_list = []
    
    # Análise V1 simplificada: conta requisitos totais e faz uma estimativa básica
    for challenge in sbc.challenges:
        for req in challenge.requirements:
            total_requirements += 1
            
            # Se for rating de time, verifica se a média dos N melhores jogadores atinge
            if req.requirement_type == "team_rating":
                try:
                    target_rating = int(req.value)
                    # Pega os 11 melhores ratings
                    top_11 = sorted([p.rating for p in available_players], reverse=True)[:11]
                    avg_rating = sum(top_11) / 11 if len(top_11) == 11 else 0
                    if avg_rating >= target_rating:
                        met_requirements += 1
                    else:
                        unmet_list.append(f"{challenge.name}: {req.operator} {req.requirement_type} {req.value}")
                except Exception:
                    unmet_list.append(f"{challenge.name}: {req.requirement_type}")

            # Requisitos de tipo de jogador
            elif req.requirement_type in ["player_type", "players_from_league", "players_from_nation", "player_rarity", "player_quality"]:
                try:
                    needed_count = int(req.value)
                    # Conta quantos atendem
                    matching = sum(1 for p in available_players if _meets_requirement(p, req, rarity_map))
                    if matching >= needed_count:
                        met_requirements += 1
                    else:
                        unmet_list.append(f"{challenge.name}: Falta {needed_count - matching} de {req.detail}")
                except Exception:
                    unmet_list.append(f"{challenge.name}: {req.requirement_type}")
            else:
                # Para requisitos complexos (química, contagem de ligas), assumimos como unmet na análise superficial V1
                unmet_list.append(f"{challenge.name}: {req.requirement_type} (Verificação Complexa)")

    feasible = (met_requirements == total_requirements) if total_requirements > 0 else (total_available > 0)
    
    # Custo estimado do que falta (Placeholder: calcularemos precisamente no calculate_optimal_path)
    estimated_cost = len(unmet_list) * 5000 if not feasible else 0

    return {
        "sbc": _sbc_to_response(sbc).model_dump(),
        "total_requirements": total_requirements,
        "met_requirements": met_requirements,
        "unmet_requirements": unmet_list,
        "available_players": total_available,
        "estimated_cost": estimated_cost,
        "feasible": feasible
    }


async def estimate_cost(session: AsyncSession, sbc_id: int) -> int:
    """Estima o custo do SBC (utilitário)."""
    analysis = await analyze_sbc(session, sbc_id)
    return analysis["estimated_cost"]


async def calculate_optimal_path(session: AsyncSession, sbc_id: int) -> dict:
    """
    Calcula a rota ótima iterando sobre cada challenge.
    Retorna dict compatível com CalculatePathResponse.
    """
    try:
        sbc = await _get_sbc_with_relations(session, sbc_id)
    except ValueError as e:
        raise ValueError(str(e))

    available_players = await get_available_for_sbc(session)
    # available_players já vem ordenado pela melhor forragem (duplicate > untradeable > lowest rating > lowest price)
    
    # Carregar mapeamentos (para futuras expansões de filtros no loop de cálculo)
    rarity_map = await _load_rarity_mappings(session)
    position_map = await _load_position_mappings(session)
    
    used_player_ids = set()
    steps = []
    total_cost = 0
    all_feasible = True
    
    for idx, challenge in enumerate(sbc.challenges):
        suggested = []
        gaps = []
        challenge_cost = 0
        
        # Filtra requisitos
        rating_req = next((r for r in challenge.requirements if r.requirement_type == "team_rating"), None)
        target_rating = int(rating_req.value) if rating_req and rating_req.value.isdigit() else 0
        
        # Quantidade de cartas necessárias (Geralmente 11, mas pode variar. Assumindo 11 para V1 padrão)
        slots_needed = 11 
        
        # Algoritmo de Seleção Gulosa V1
        # Busca jogadores disponíveis que ainda não foram usados
        pool = [p for p in available_players if p.id not in used_player_ids]
        
        selected_for_challenge = []
        
        if challenge.formation and challenge.formation in FORMATIONS:
            needed_positions = FORMATIONS[challenge.formation].copy()
            pool_to_search = sorted(pool, key=lambda p: (p.rating, p.is_duplicate, p.is_untradeable), reverse=True) if target_rating > 0 else pool
            
            for pos_en in needed_positions:
                found_player = None
                for p in pool_to_search:
                    if p.id in [s.id for s in selected_for_challenge]: continue
                    p_en_positions = [position_map.get(pt.strip().upper(), pt.strip().upper()) for pt in p.all_positions]
                    if pos_en.upper() in p_en_positions:
                        found_player = p
                        break
                
                if found_player:
                    selected_for_challenge.append(found_player)
                else:
                    for p in pool_to_search:
                        if p.id not in [s.id for s in selected_for_challenge]:
                            selected_for_challenge.append(p)
                            gaps.append(f"Posição {pos_en} preenchida de forma improvisada com {p.name}")
                            break

            if target_rating > 0:
                avg = sum(c.rating for c in selected_for_challenge) / len(selected_for_challenge) if selected_for_challenge else 0
                if avg < target_rating:
                    gaps.append(f"Rating insuficiente. Média do elenco: {avg:.1f}, Exigido: {target_rating}")
                    all_feasible = False
        else:
            if target_rating > 0:
                # Selecionar cartas focando em atingir o rating. 
                # A pool está ordenada do menor rating para o maior (forragem). 
                # Se precisarmos de rating alto, precisamos pegar de trás para frente (maiores ratings)
                # Mas como é forragem, queremos usar as *piores* cartas que atingem a média.
                
                # Para V1: Vamos pegar as N cartas de menor rating que conseguem atingir o target
                # Se não atingir, pegamos as melhores possíveis.
                pool_high_to_low = sorted(pool, key=lambda p: (p.rating, p.is_duplicate, p.is_untradeable), reverse=True)
                
                # Pega as top 11
                candidates = pool_high_to_low[:slots_needed]
                if candidates:
                    avg = sum(c.rating for c in candidates) / len(candidates)
                    if avg < target_rating:
                        gaps.append(f"Rating insuficiente. Média do elenco: {avg:.1f}, Exigido: {target_rating}")
                        all_feasible = False
                    
                    selected_for_challenge = candidates
            else:
                # Sem requisito de rating de time, pega as piores possíveis primeiro
                selected_for_challenge = pool[:slots_needed]
            
        for player in selected_for_challenge:
            used_player_ids.add(player.id)
            
            # Define o motivo
            reason = "Menor rating"
            if player.is_duplicate: reason = "Duplicata"
            elif player.is_untradeable: reason = "Intransferível"
                
            suggested.append(SuggestedPlayerResponse(
                player=_player_to_response(player),
                assigned_position=player.preferred_position,
                reason=reason
            ))
            
            # Custo: se for untradeable ou duplicata, custo 0 de oportunidade (ou o discard_value)
            if not player.is_untradeable and not player.is_duplicate:
                challenge_cost += player.external_price or player.discard_value or 0

        # Verifica se faltam cartas para preencher os slots
        if len(selected_for_challenge) < slots_needed:
            missing = slots_needed - len(selected_for_challenge)
            gaps.append(f"Faltam {missing} jogadores no elenco para completar o desafio.")
            all_feasible = False
            # Penalidade de custo por carta faltando (estimativa baseada no rating alvo)
            challenge_cost += missing * _estimate_card_cost(target_rating)

        total_cost += challenge_cost
        
        steps.append(StepResponse(
            order=idx + 1,
            action=f"Completar '{challenge.name}'",
            sbc_name=sbc.name,
            challenge_name=challenge.name,
            suggested_players=suggested,
            estimated_cost=challenge_cost,
            gaps=gaps
        ))

    return {
        "target_sbc": _sbc_to_response(sbc).model_dump(),
        "feasible": all_feasible,
        "steps": [s.model_dump() for s in steps],
        "total_estimated_cost": total_cost,
        "message": "Rota calculada com sucesso." if all_feasible else "Elenco insuficiente para a rota ótima."
    }
