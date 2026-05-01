"""
Help DMEs — FastAPI Application
==================================
Ponto de entrada da API REST. Define todos os endpoints organizados por área:
  - /api/settings   → Configurações do sistema
  - /api/squad      → Gerenciamento do elenco (CSV, filtros, exclusão)
  - /api/sbcs       → Listagem e detalhes de SBCs/DMEs
  - /api/scrape     → Controle de scraping (start, status, logs)
  - /api/calculate  → Motor de cálculo (stub — Fase 4)

Startup:
  - Inicializa o banco de dados (create tables + seed)
  - Scraping automático ao iniciar (se habilitado em settings)
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import init_db, get_session_dependency
from backend.models.models import SBCSet, SBCChallenge, ScrapeLog

from backend.schemas.schemas import (
    AppSettingResponse, AppSettingUpdateRequest,
    UserSquadPlayerResponse, SquadImportResponse, SquadStatsResponse,
    BulkExcludeRequest, BulkActionResponse,
    SBCSetResponse, SBCSetDetailResponse,
    ScrapeStatusResponse, ScrapeStartResponse, ScrapeLogResponse,
)

from backend.services import settings_service, squad_service
from backend.services.fut_gg_service import get_scrape_status, scrape_all_sbcs


APP_VERSION = "0.3.0"


# ──────────────────────────────────────────────
# Lifespan (startup/shutdown)
# ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa o banco de dados ao iniciar a aplicação."""
    await init_db()
    yield


# ──────────────────────────────────────────────
# App FastAPI
# ──────────────────────────────────────────────

app = FastAPI(
    title="Help DMEs API",
    description="Motor inteligente de otimização de DMEs/SBCs para EA FC 26",
    version=APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════
#  ROOT
# ══════════════════════════════════════════════

@app.get("/")
async def root():
    """Status da API."""
    return {"status": "ok", "message": "Help DMEs Engine rodando", "version": APP_VERSION}


# ══════════════════════════════════════════════
#  SETTINGS — Configurações do Sistema
# ══════════════════════════════════════════════

@app.get("/api/settings", response_model=list[AppSettingResponse])
async def list_settings(session: AsyncSession = Depends(get_session_dependency)):
    """Retorna todas as configurações do sistema."""
    settings = await settings_service.get_all_settings(session)
    return [AppSettingResponse(key=s.key, value=s.value, description=s.description) for s in settings]


@app.patch("/api/settings/{key}", response_model=AppSettingResponse)
async def update_setting(
    key: str,
    body: AppSettingUpdateRequest,
    session: AsyncSession = Depends(get_session_dependency),
):
    """Atualiza uma configuração (ex: toggle do time titular)."""
    try:
        setting = await settings_service.update_setting(session, key, body.value)
        return AppSettingResponse(key=setting.key, value=setting.value, description=setting.description)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ══════════════════════════════════════════════
#  SQUAD — Gerenciamento do Elenco
# ══════════════════════════════════════════════

@app.post("/api/squad/import", response_model=SquadImportResponse)
async def import_squad(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session_dependency),
):
    """Importa o CSV do elenco (reimportação completa — apaga dados anteriores)."""
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Arquivo deve ser .csv")

    content = await file.read()
    result = await squad_service.import_csv(session, content)
    return SquadImportResponse(**result)


@app.get("/api/squad", response_model=list[UserSquadPlayerResponse])
async def list_squad(
    rating_min: Optional[int] = Query(None),
    rating_max: Optional[int] = Query(None),
    position: Optional[str] = Query(None, description="Posições separadas por vírgula: VOL,MC"),
    nation: Optional[str] = Query(None, description="Nações separadas por vírgula"),
    league: Optional[str] = Query(None, description="Ligas separadas por vírgula"),
    team: Optional[str] = Query(None, description="Clubes separados por vírgula"),
    rarity: Optional[str] = Query(None, description="Raridades separadas por vírgula"),
    untradeable_only: bool = Query(False),
    duplicates_only: bool = Query(False),
    exclude_loans: bool = Query(True),
    search: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session_dependency),
):
    """Lista o elenco com filtros opcionais."""
    players = await squad_service.get_squad(
        session,
        rating_min=rating_min,
        rating_max=rating_max,
        positions=position.split(",") if position else None,
        nations=nation.split(",") if nation else None,
        leagues=league.split(",") if league else None,
        teams=team.split(",") if team else None,
        rarities=rarity.split(",") if rarity else None,
        untradeable_only=untradeable_only,
        duplicates_only=duplicates_only,
        exclude_loans=exclude_loans,
        search=search,
    )
    return [_player_to_response(p) for p in players]


@app.get("/api/squad/stats", response_model=SquadStatsResponse)
async def squad_stats(session: AsyncSession = Depends(get_session_dependency)):
    """Estatísticas do elenco (total, por posição, por liga, etc.)."""
    stats = await squad_service.get_squad_stats(session)
    return SquadStatsResponse(**stats)


@app.patch("/api/squad/{player_id}/exclude")
async def toggle_exclude_player(
    player_id: int,
    session: AsyncSession = Depends(get_session_dependency),
):
    """Toggle de exclusão individual de um jogador."""
    try:
        player = await squad_service.exclude_player(session, player_id)
        return {
            "id": player.id,
            "name": player.name,
            "is_excluded": player.is_excluded,
            "message": f"{'Excluído' if player.is_excluded else 'Incluído'}: {player.name}",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/squad/bulk-exclude", response_model=BulkActionResponse)
async def bulk_exclude_players(
    body: BulkExcludeRequest,
    session: AsyncSession = Depends(get_session_dependency),
):
    """Exclusão em lote por filtro."""
    try:
        affected = await squad_service.bulk_exclude(session, body.filter_type, body.filter_value)
        return BulkActionResponse(
            affected=affected,
            message=f"{affected} jogadores excluídos por filtro '{body.filter_type}={body.filter_value}'.",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/squad/bulk-include", response_model=BulkActionResponse)
async def bulk_include_players(session: AsyncSession = Depends(get_session_dependency)):
    """Remove exclusão de TODOS os jogadores."""
    affected = await squad_service.bulk_include(session)
    return BulkActionResponse(
        affected=affected,
        message=f"{affected} jogadores reincluídos.",
    )


# ══════════════════════════════════════════════
#  SBCs — Listagem e Detalhes
# ══════════════════════════════════════════════

@app.get("/api/sbcs", response_model=list[SBCSetResponse])
async def list_sbcs(
    category: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session_dependency),
):
    """Lista todos os SBCs coletados, com filtro opcional por categoria."""
    query = select(SBCSet).order_by(SBCSet.scraped_at.desc())
    if category:
        query = query.where(SBCSet.category == category)

    result = await session.execute(query)
    sbcs = result.scalars().all()

    return [
        SBCSetResponse(
            id=s.id, futgg_id=s.futgg_id, name=s.name,
            description=s.description, category=s.category,
            total_cost=s.total_cost, challenges_count=s.challenges_count,
            expires_at=s.expires_at, is_repeatable=s.is_repeatable,
            image_url=s.image_url, completion_pct=s.completion_pct,
            is_new=s.is_new, source=s.source, scraped_at=s.scraped_at,
        )
        for s in sbcs
    ]


@app.get("/api/sbcs/{sbc_id}", response_model=SBCSetDetailResponse)
async def get_sbc_detail(
    sbc_id: int,
    session: AsyncSession = Depends(get_session_dependency),
):
    """Detalhes completos de um SBC com challenges, requisitos e rewards."""
    sbc = await session.get(SBCSet, sbc_id)
    if not sbc:
        raise HTTPException(status_code=404, detail="SBC não encontrado")

    # Carregar challenges com requisitos e rewards (eager)
    from sqlalchemy.orm import selectinload
    result = await session.execute(
        select(SBCSet)
        .where(SBCSet.id == sbc_id)
        .options(
            selectinload(SBCSet.challenges).selectinload(SBCChallenge.requirements),
            selectinload(SBCSet.challenges).selectinload(SBCChallenge.rewards),
            selectinload(SBCSet.rewards),
            selectinload(SBCSet.player_card),
        )
    )
    sbc = result.scalar_one()

    return _sbc_to_detail_response(sbc)


# ══════════════════════════════════════════════
#  SCRAPE — Controle de Scraping
# ══════════════════════════════════════════════

@app.post("/api/scrape/start", response_model=ScrapeStartResponse)
async def start_scraping(
    source: str = Query("fut.gg", description="Fonte de scraping: fut.gg ou futnext"),
    session: AsyncSession = Depends(get_session_dependency),
):
    """Inicia o scraping em background. Fonte: fut.gg (padrão) ou futnext."""
    status = get_scrape_status()
    if status["status"] == "running":
        return ScrapeStartResponse(status="running", message="Scraping já em andamento.")

    if source == "futnext":
        asyncio.create_task(_run_futnext_background())
        return ScrapeStartResponse(status="started", message="Scraping FutNext iniciado em background.")
    
    asyncio.create_task(_run_scraping_background())
    return ScrapeStartResponse(status="started", message="Scraping Fut.gg iniciado em background.")


@app.get("/api/scrape/status", response_model=ScrapeStatusResponse)
async def scrape_status(session: AsyncSession = Depends(get_session_dependency)):
    """Status atual do scraping."""
    status = get_scrape_status()

    # Contar SBCs no banco se o status não tiver contagem
    if status["sbcs_count"] == 0:
        result = await session.execute(select(func.count(SBCSet.id)))
        status["sbcs_count"] = result.scalar() or 0

    return ScrapeStatusResponse(
        status=status["status"],
        message=status.get("message"),
        last_scrape_at=status["last_scrape_at"],
        sbcs_count=status["sbcs_count"],
    )


@app.get("/api/scrape/logs", response_model=list[ScrapeLogResponse])
async def scrape_logs(
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_session_dependency),
):
    """Histórico de sincronizações."""
    result = await session.execute(
        select(ScrapeLog).order_by(ScrapeLog.started_at.desc()).limit(limit)
    )
    logs = result.scalars().all()
    return [
        ScrapeLogResponse(
            id=l.id, source=l.source, status=l.status,
            sbcs_scraped=l.sbcs_scraped, started_at=l.started_at,
            finished_at=l.finished_at, error_message=l.error_message,
        )
        for l in logs
    ]


@app.get("/api/scrape/sources")
async def list_scrape_sources():
    """Lista as fontes de scraping disponíveis."""
    return [
        {"id": "fut.gg", "name": "Fut.gg", "is_primary": True},
        {"id": "futnext", "name": "FutNext", "is_primary": False}
    ]


@app.get("/api/health")
async def health_check():
    """Verifica a saúde do sistema e conexão com banco."""
    return {
        "status": "healthy",
        "version": APP_VERSION,
        "database": "connected"
    }


# ══════════════════════════════════════════════
#  CALCULATE — Motor de Cálculo (Fase 4)
# ══════════════════════════════════════════════

from backend.services import calculator_service

@app.post("/api/calculate/{sbc_id}")
async def calculate_optimal_path(sbc_id: int, session: AsyncSession = Depends(get_session_dependency)):
    """[Fase 4] Calcula a rota ótima para completar um SBC."""
    try:
        return await calculator_service.calculate_optimal_path(session, sbc_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/calculate/{sbc_id}/analysis")
async def analyze_sbc(sbc_id: int, session: AsyncSession = Depends(get_session_dependency)):
    """[Fase 4] Análise de viabilidade de um SBC."""
    try:
        return await calculator_service.analyze_sbc(session, sbc_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ══════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════

def _player_to_response(player) -> UserSquadPlayerResponse:
    """Converte UserSquadPlayer ORM → schema Pydantic."""
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


def _sbc_to_detail_response(sbc) -> SBCSetDetailResponse:
    """Converte SBCSet ORM → schema Pydantic detalhado."""
    from backend.schemas.schemas import (
        SBCChallengeResponse, ChallengeRequirementResponse,
        SBCRewardResponse, PlayerCardResponse,
    )

    challenges = []
    for ch in sbc.challenges:
        reqs = [
            ChallengeRequirementResponse(
                id=r.id, requirement_type=r.requirement_type,
                operator=r.operator, value=r.value, detail=r.detail,
            )
            for r in ch.requirements
        ]
        rewards = [
            SBCRewardResponse(
                id=rw.id, reward_type=rw.reward_type, name=rw.name,
                is_untradeable=rw.is_untradeable, image_url=rw.image_url,
            )
            for rw in ch.rewards
        ]
        challenges.append(SBCChallengeResponse(
            id=ch.id, name=ch.name, description=ch.description,
            estimated_cost=ch.estimated_cost, formation=ch.formation,
            order_index=ch.order_index, requirements=reqs, rewards=rewards,
        ))

    set_rewards = [
        SBCRewardResponse(
            id=rw.id, reward_type=rw.reward_type, name=rw.name,
            is_untradeable=rw.is_untradeable, image_url=rw.image_url,
        )
        for rw in sbc.rewards
    ]

    player_card = None
    if sbc.player_card:
        pc = sbc.player_card
        player_card = PlayerCardResponse(
            id=pc.id, name=pc.name, overall=pc.overall,
            position=pc.position, card_type=pc.card_type,
            meta_rating=pc.meta_rating, card_image_url=pc.card_image_url,
        )

    return SBCSetDetailResponse(
        id=sbc.id, futgg_id=sbc.futgg_id, name=sbc.name,
        description=sbc.description, category=sbc.category,
        total_cost=sbc.total_cost, challenges_count=sbc.challenges_count,
        expires_at=sbc.expires_at, is_repeatable=sbc.is_repeatable,
        image_url=sbc.image_url, completion_pct=sbc.completion_pct,
        is_new=sbc.is_new, source=sbc.source, scraped_at=sbc.scraped_at,
        challenges=challenges, rewards=set_rewards, player_card=player_card,
    )


async def _run_scraping_background():
    """Executa scraping em background com fallback."""
    import logging
    logger = logging.getLogger("help_dmes.main")
    
    from backend.core.database import get_session
    async with get_session() as session:
        result = await scrape_all_sbcs(session)
        if result["status"] == "failed":
            logger.warning("Fut.gg falhou, tentando FutNext como fallback...")
            from backend.services.futnext_service import scrape_all_sbcs_futnext
            await scrape_all_sbcs_futnext(session)


async def _run_futnext_background():
    """Executa scraping FutNext em background."""
    from backend.core.database import get_session
    from backend.services.futnext_service import scrape_all_sbcs_futnext
    async with get_session() as session:
        await scrape_all_sbcs_futnext(session)
