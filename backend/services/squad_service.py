"""
Help DMEs — Squad Service
===========================
Gerenciamento do elenco do usuário: importação CSV, filtros, exclusão e
disponibilidade para SBCs.

O CSV exportado pelo EA FC contém 17 colunas:
  Name, Rating, Rarity, Preferred Position, Nation, League, Team,
  Price Limits, Last Sale Price, Discard Value, Untradeable, Loans,
  DefinitionId, IsDuplicate, IsInActive11, Alternate Positions, ExternalPrice

Regras de disponibilidade para SBC (ver Regras de Negócio):
  🚫 BLOQUEIO ABSOLUTO: is_loan=True, is_excluded=True
  🛡️ PROTEÇÃO CONDICIONAL: is_in_active_11=True (controlado por setting)
  📊 PRIORIDADE: duplicatas > intransferíveis > menor rating > menor preço
"""

import csv
import io
import re
import logging
from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import select, delete, func, case, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.models import UserSquadPlayer
from backend.services.settings_service import get_setting_bool

logger = logging.getLogger("help_dmes." + __name__.split(".")[-1])


# ──────────────────────────────────────────────
# Helpers de parsing do CSV
# ──────────────────────────────────────────────

def _parse_bool(value: str) -> bool:
    """Converte 'true'/'false' do CSV para bool Python."""
    return value.strip().lower() == "true"


def _parse_int(value: str, default: int = 0) -> int:
    """Converte string numérica para int, com fallback."""
    try:
        return int(value.strip())
    except (ValueError, TypeError):
        return default


def _parse_price_limits(value: str) -> tuple[Optional[int], Optional[int]]:
    """
    Parseia o campo 'Price Limits' do CSV.
    Formato: 'Mín.:750 Máx.:14000' → (750, 14000)
    Se '--NA--' → (None, None)
    """
    if not value or value.strip() == "--NA--":
        return None, None
    match = re.findall(r'(\d+)', value)
    if len(match) >= 2:
        return int(match[0]), int(match[1])
    return None, None


def _parse_external_price(value: str) -> Optional[int]:
    """
    Parseia o campo 'ExternalPrice' do CSV.
    '31000' → 31000
    '-- NA --' → None
    """
    cleaned = value.strip()
    if not cleaned or cleaned == "-- NA --":
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


# ──────────────────────────────────────────────
# Funções do serviço
# ──────────────────────────────────────────────

async def import_csv(session: AsyncSession, file_content: bytes) -> dict:
    """
    Importa o CSV do elenco para o banco de dados.
    Deleta todos os registros anteriores (reimportação completa).

    Retorna: {"total_imported": int, "total_skipped": int, "message": str}
    """
    # Decodificar conteúdo (pode ter BOM UTF-8)
    text = file_content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    # Limpar elenco anterior
    await session.execute(delete(UserSquadPlayer))

    # Carregar mapeamento de posições PT -> EN para cruzamento robusto
    from backend.models.models import PositionMapping, FCPlayer, PlayerCard
    pos_mapping_res = await session.execute(select(PositionMapping))
    pos_map = {row.pt.upper(): row.en.upper() for row in pos_mapping_res.scalars().all()}

    imported = 0
    skipped = 0

    for row in reader:
        try:
            price_min, price_max = _parse_price_limits(row.get("Price Limits", ""))
            rating_val = _parse_int(row["Rating"])
            pref_pos_pt = row["Preferred Position"].strip().upper()
            pref_pos_en = pos_map.get(pref_pos_pt, pref_pos_pt)
            cleaned_name = row["Name"].strip()

            # Buscar playstyles no catálogo global (fc_players) ou player_cards (fallback)
            playstyles_json = None

            # 1. Tentar busca por nome exato e rating exato e posição compatível em fc_players
            fc_q = select(FCPlayer.playstyles_json).where(
                FCPlayer.overall == rating_val,
                FCPlayer.position.ilike(f"%{pref_pos_en}%"),
                func.lower(FCPlayer.name) == cleaned_name.lower()
            )
            fc_res = await session.execute(fc_q)
            playstyles_json = fc_res.scalars().first()

            # 2. Tentar busca em player_cards por nome exato e rating exato e posição compatível (fallback 1)
            if not playstyles_json:
                pc_q = select(PlayerCard.playstyles_json).where(
                    PlayerCard.overall == rating_val,
                    PlayerCard.position.ilike(f"%{pref_pos_en}%"),
                    func.lower(PlayerCard.name) == cleaned_name.lower()
                )
                pc_res = await session.execute(pc_q)
                playstyles_json = pc_res.scalars().first()

            # 3. Tentar busca flexível (contendo nome) e posição compatível em fc_players (fallback 2)
            if not playstyles_json:
                fc_q_flex = select(FCPlayer.playstyles_json).where(
                    FCPlayer.overall == rating_val,
                    FCPlayer.position.ilike(f"%{pref_pos_en}%"),
                    (FCPlayer.name.ilike(f"%{cleaned_name}%")) | 
                    (func.lower(cleaned_name).like(func.concat('%', func.lower(FCPlayer.name), '%')))
                )
                fc_res_flex = await session.execute(fc_q_flex)
                playstyles_json = fc_res_flex.scalars().first()

            # 4. Fallback absoluto: Buscar apenas por Nome + Rating (ignorando posição, caso haja divergência de escalação no CSV)
            if not playstyles_json:
                fc_q_abs = select(FCPlayer.playstyles_json).where(
                    FCPlayer.overall == rating_val,
                    (func.lower(FCPlayer.name) == cleaned_name.lower()) |
                    (FCPlayer.name.ilike(f"%{cleaned_name}%")) |
                    (func.lower(cleaned_name).like(func.concat('%', func.lower(FCPlayer.name), '%')))
                )
                fc_res_abs = await session.execute(fc_q_abs)
                playstyles_json = fc_res_abs.scalars().first()

            player = UserSquadPlayer(
                name=cleaned_name,
                rating=rating_val,
                rarity=row["Rarity"].strip(),
                preferred_position=row["Preferred Position"].strip(),
                nation=row["Nation"].strip(),
                league=row["League"].strip(),
                team=row["Team"].strip(),
                price_min=price_min,
                price_max=price_max,
                last_sale_price=_parse_int(row.get("Last Sale Price", "0")),
                discard_value=_parse_int(row.get("Discard Value", "0")),
                is_untradeable=_parse_bool(row.get("Untradeable", "false")),
                is_loan=_parse_bool(row.get("Loans", "false")),
                definition_id=row["DefinitionId"].strip(),
                is_duplicate=_parse_bool(row.get("IsDuplicate", "false")),
                is_in_active_11=_parse_bool(row.get("IsInActive11", "false")),
                alternate_positions=row.get("Alternate Positions", "").strip() or None,
                external_price=_parse_external_price(row.get("ExternalPrice", "")),
                playstyles_json=playstyles_json,
                is_excluded=False,
                imported_at=datetime.now(UTC),
            )
            session.add(player)
            imported += 1

        except Exception as e:
            logger.error(f"Erro ao importar jogador {row.get('Name')}: {e}")
            skipped += 1
            continue

    await session.flush()
    return {
        "total_imported": imported,
        "total_skipped": skipped,
        "message": f"Elenco importado: {imported} jogadores. {skipped} ignorados.",
    }


async def get_squad(
    session: AsyncSession,
    rating_min: Optional[int] = None,
    rating_max: Optional[int] = None,
    positions: Optional[list[str]] = None,
    nations: Optional[list[str]] = None,
    leagues: Optional[list[str]] = None,
    teams: Optional[list[str]] = None,
    rarities: Optional[list[str]] = None,
    untradeable_only: bool = False,
    duplicates_only: bool = False,
    exclude_loans: bool = True,
    search: Optional[str] = None,
) -> list[UserSquadPlayer]:
    """
    Retorna o elenco com filtros opcionais aplicados.
    Ordena por rating DESC, name ASC.
    """
    query = select(UserSquadPlayer)

    if rating_min is not None:
        query = query.where(UserSquadPlayer.rating >= rating_min)
    if rating_max is not None:
        query = query.where(UserSquadPlayer.rating <= rating_max)
    if positions:
        query = query.where(UserSquadPlayer.preferred_position.in_(positions))
    if nations:
        query = query.where(UserSquadPlayer.nation.in_(nations))
    if leagues:
        query = query.where(UserSquadPlayer.league.in_(leagues))
    if teams:
        query = query.where(UserSquadPlayer.team.in_(teams))
    if rarities:
        query = query.where(UserSquadPlayer.rarity.in_(rarities))
    if untradeable_only:
        query = query.where(UserSquadPlayer.is_untradeable == True)
    if duplicates_only:
        query = query.where(UserSquadPlayer.is_duplicate == True)
    if exclude_loans:
        query = query.where(UserSquadPlayer.is_loan == False)
    if search:
        query = query.where(UserSquadPlayer.name.ilike(f"%{search}%"))

    query = query.order_by(
        UserSquadPlayer.rating.desc(),
        UserSquadPlayer.name.asc()
    )

    result = await session.execute(query)
    return list(result.scalars().all())


async def exclude_player(session: AsyncSession, player_id: int) -> UserSquadPlayer:
    """
    Toggle de exclusão: inverte is_excluded do jogador.
    Levanta ValueError se o jogador não existir.
    """
    player = await session.get(UserSquadPlayer, player_id)
    if not player:
        raise ValueError(f"Jogador com id={player_id} não encontrado.")
    player.is_excluded = not player.is_excluded
    await session.flush()
    return player


async def bulk_exclude(session: AsyncSession, filter_type: str, filter_value: str) -> int:
    """
    Marca is_excluded=True em lote por critério.

    filter_type aceita:
      - 'rating_above': todos com rating > valor
      - 'rating_below': todos com rating < valor
      - 'position': todos com preferred_position == valor
      - 'league': todos com league == valor
      - 'rarity': todos com rarity == valor
    """
    query = sa_update(UserSquadPlayer).values(is_excluded=True)

    if filter_type == "rating_above":
        query = query.where(UserSquadPlayer.rating > int(filter_value))
    elif filter_type == "rating_below":
        query = query.where(UserSquadPlayer.rating < int(filter_value))
    elif filter_type == "position":
        query = query.where(UserSquadPlayer.preferred_position == filter_value)
    elif filter_type == "league":
        query = query.where(UserSquadPlayer.league == filter_value)
    elif filter_type == "rarity":
        query = query.where(UserSquadPlayer.rarity == filter_value)
    else:
        raise ValueError(f"Tipo de filtro inválido: '{filter_type}'")

    result = await session.execute(query)
    await session.flush()
    return result.rowcount


async def bulk_include(session: AsyncSession) -> int:
    """Desmarca is_excluded=False em TODOS os jogadores."""
    result = await session.execute(
        sa_update(UserSquadPlayer).values(is_excluded=False)
    )
    await session.flush()
    return result.rowcount


async def get_available_for_sbc(session: AsyncSession) -> list[UserSquadPlayer]:
    """
    Retorna APENAS jogadores disponíveis para SBC, aplicando todas as regras:

    🚫 BLOQUEIO ABSOLUTO:
      - is_loan=True → NUNCA
      - is_excluded=True → NUNCA

    🛡️ PROTEÇÃO CONDICIONAL:
      - is_in_active_11=True → bloqueado SE allow_active_11_in_sbc=false

    📊 PRIORIDADE DE USO (ordem da query):
      1º is_duplicate=True (descartáveis)
      2º is_untradeable=True (sem valor de revenda)
      3º Menor rating
      4º Menor external_price (nulls por último)
    """
    # Verificar setting de proteção do time titular
    allow_active = await get_setting_bool(session, "allow_active_11_in_sbc", default=False)

    query = select(UserSquadPlayer).where(
        UserSquadPlayer.is_loan == False,
        UserSquadPlayer.is_excluded == False,
    )

    # Se NÃO permite time titular, filtrar
    if not allow_active:
        query = query.where(UserSquadPlayer.is_in_active_11 == False)

    # Ordenar por prioridade de uso (melhor para forragem primeiro)
    query = query.order_by(
        UserSquadPlayer.is_duplicate.desc(),       # Duplicatas primeiro
        UserSquadPlayer.is_untradeable.desc(),     # Intransferíveis segundo
        UserSquadPlayer.rating.asc(),              # Menor rating terceiro
        case(
            (UserSquadPlayer.external_price.is_(None), 999999),
            else_=UserSquadPlayer.external_price
        ).asc(),                                    # Menor preço (nulls por último)
    )

    result = await session.execute(query)
    return list(result.scalars().all())


async def get_squad_stats(session: AsyncSession) -> dict:
    """
    Retorna estatísticas do elenco:
      - total, by_position, by_league, by_rating_range
      - duplicates, untradeables, loans, excluded, available_for_sbc
    """
    all_players = await session.execute(select(UserSquadPlayer))
    players = list(all_players.scalars().all())

    if not players:
        return {
            "total": 0, "by_position": {}, "by_league": {},
            "by_rating_range": {}, "duplicates": 0, "untradeables": 0,
            "loans": 0, "excluded": 0, "available_for_sbc": 0,
        }

    # Contadores
    by_position: dict[str, int] = {}
    by_league: dict[str, int] = {}
    ranges = {"90+": 0, "85-89": 0, "80-84": 0, "75-79": 0, "70-74": 0, "<70": 0}
    duplicates = 0
    untradeables = 0
    loans = 0
    excluded = 0

    for p in players:
        # Por posição
        by_position[p.preferred_position] = by_position.get(p.preferred_position, 0) + 1
        # Por liga
        by_league[p.league] = by_league.get(p.league, 0) + 1
        # Por range de rating
        if p.rating >= 90:
            ranges["90+"] += 1
        elif p.rating >= 85:
            ranges["85-89"] += 1
        elif p.rating >= 80:
            ranges["80-84"] += 1
        elif p.rating >= 75:
            ranges["75-79"] += 1
        elif p.rating >= 70:
            ranges["70-74"] += 1
        else:
            ranges["<70"] += 1
        # Flags
        if p.is_duplicate:
            duplicates += 1
        if p.is_untradeable:
            untradeables += 1
        if p.is_loan:
            loans += 1
        if p.is_excluded:
            excluded += 1

    # Disponíveis para SBC (contagem rápida)
    available = await get_available_for_sbc(session)

    return {
        "total": len(players),
        "by_position": dict(sorted(by_position.items(), key=lambda x: -x[1])),
        "by_league": dict(sorted(by_league.items(), key=lambda x: -x[1])[:15]),  # Top 15
        "by_rating_range": ranges,
        "duplicates": duplicates,
        "untradeables": untradeables,
        "loans": loans,
        "excluded": excluded,
        "available_for_sbc": len(available),
    }
