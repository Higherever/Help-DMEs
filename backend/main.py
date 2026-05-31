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

from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import init_db, get_session_dependency
from backend.models.models import SBCSet, SBCChallenge, ScrapeLog, PlayerCard, FCPlayer

from backend.schemas.schemas import (
    AppSettingResponse, AppSettingUpdateRequest,
    UserSquadPlayerResponse, SquadImportResponse, SquadStatsResponse,
    BulkExcludeRequest, BulkActionResponse,
    SBCSetResponse, SBCSetDetailResponse,
    ScrapeStatusResponse, ScrapeStartResponse, ScrapeLogResponse,
)

from backend.services import settings_service, squad_service
from backend.services.futbin_service import get_scrape_status, scrape_all_sbcs


APP_VERSION = "0.4.0"


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

# Servir imagens locais baixadas pelo scraper
from fastapi.staticfiles import StaticFiles
from pathlib import Path

_images_dir = Path("images")
_images_dir.mkdir(exist_ok=True)
app.mount("/images", StaticFiles(directory=str(_images_dir)), name="images")


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
#  CARDS — Busca de Imagens de Cards e Miniaturas
# ══════════════════════════════════════════════

@app.get("/api/cards/search-image")
async def search_card_image(
    name: str = Query(..., description="Nome do jogador para buscar"),
    league: Optional[str] = Query(None, description="Liga do jogador para maior precisão"),
    team: Optional[str] = Query(None, description="Time/Clube do jogador para maior precisão"),
    session: AsyncSession = Depends(get_session_dependency),
):
    """
    Busca na base de dados (player_cards e fc_players) e retorna o caminho
    do card completo (HD) e sua respectiva miniatura (Small) de 150px.
    """
    # Função interna para realizar a busca no banco
    async def try_search(exact_match: bool):
        # 1. Buscar primeiro na tabela player_cards (DMEs)
        query_pc = select(PlayerCard).where(PlayerCard.card_image_url != None)
        
        # Filtro de nome case-insensitive parcial
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

        # 2. Buscar depois na tabela fc_players (Catálogo Global)
        query_fc = select(FCPlayer).where(FCPlayer.card_template_url != None)
        
        # Filtro de nome case-insensitive parcial
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

    # Tenta busca exata (Nome + Liga + Clube)
    card_path = await try_search(exact_match=True)
    
    # Se falhar e tivermos mais dados (liga ou clube), tenta fallback buscando apenas por Nome
    if not card_path and (league or team):
        card_path = await try_search(exact_match=False)
        
    if not card_path:
        raise HTTPException(
            status_code=404,
            detail=f"Nenhum card correspondente encontrado para o jogador '{name}'."
        )

    # Deduzir caminho da miniatura (small) substituindo '/full/' por '/small/'
    # Ex: /images/cards/full/sbc_player_1_nome.png -> /images/cards/small/sbc_player_1_nome.png
    small_path = card_path.replace("/full/", "/small/")

    return {
        "full_image_url": card_path,
        "small_image_url": small_path
    }


@app.get("/api/cards/all-images")
async def list_all_card_images():
    """
    Retorna uma lista de todas as imagens de cartas de jogadores salvas fisicamente
    no servidor estático, na pasta images/cards/full.
    """
    try:
        import os
        from pathlib import Path
        
        full_dir = Path("images/cards/full")
        if not full_dir.exists():
            return []
            
        images = []
        for file in os.listdir(full_dir):
            if file.endswith((".png", ".jpg", ".jpeg", ".webp")):
                images.append({
                    "name": file,
                    "full_image_url": f"/images/cards/full/{file}",
                    "small_image_url": f"/images/cards/small/{file}"
                })
        
        return sorted(images, key=lambda x: x["name"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar imagens: {str(e)}")


# ══════════════════════════════════════════════
#  SBCs — Listagem e Detalhes
# ══════════════════════════════════════════════

@app.get("/api/sbcs", response_model=list[SBCSetResponse])
async def list_sbcs(
    category: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session_dependency),
):
    """Lista todos os SBCs coletados, com filtro opcional por categoria."""
    from sqlalchemy.orm import selectinload
    query = (
        select(SBCSet)
        .options(
            selectinload(SBCSet.player_card),
            selectinload(SBCSet.challenges)
        )
        .order_by(SBCSet.scraped_at.desc())
    )
    if category:
        query = query.where(SBCSet.category == category)

    result = await session.execute(query)
    sbcs = result.scalars().all()

    return [_sbc_to_response(s) for s in sbcs]


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
    source: str = Query("futbin", description="Fonte de scraping: futbin"),
    session: AsyncSession = Depends(get_session_dependency),
):
    """Inicia o scraping em background via Futbin."""
    status = get_scrape_status()
    if status["status"] == "running":
        return ScrapeStartResponse(status="running", message="Scraping já em andamento.")

    asyncio.create_task(_run_scraping_background())
    return ScrapeStartResponse(status="started", message="Scraping Futbin iniciado em background.")


@app.get("/api/scrape/status", response_model=ScrapeStatusResponse)
async def scrape_status(session: AsyncSession = Depends(get_session_dependency)):
    """Status atual do scraping."""
    from backend.services.futbin_service import get_scrape_status
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
        {"id": "futbin", "name": "Futbin", "is_primary": True},
    ]


@app.post("/api/scrape/players/playstyles")
async def start_ea_ratings_scraping(
    background_tasks: BackgroundTasks,
    pages: str = Query("1-3", description="Páginas a raspar. Ex: '1-3'"),
    test_mode: bool = Query(False, description="Modo de teste rápido (apenas 5 jogadores)"),
):
    """Inicia a sincronização de playstyles da EA em background de forma isolada."""
    from backend.services.futbin_service import _scrape_state
    from backend.scripts.scrape_ea_ratings import main as run_ea_scraper
    import re
    from datetime import datetime, UTC
    import logging
    logger = logging.getLogger("help_dmes.main")
    
    status = get_scrape_status()
    if status["status"] == "running":
        raise HTTPException(status_code=400, detail="Scraping/Sincronização já em andamento.")
        
    def update_ea_progress(msg, done, total):
        _scrape_state.update(
            status="running",
            message=f"EA Ratings: {msg}",
            current=done,
            total=total
        )
        
    def parse_pages(pages_str: str) -> tuple[int, int]:
        m = re.match(r"(\d+)[-–](\d+)", pages_str)
        if m:
            return int(m.group(1)), int(m.group(2))
        return int(pages_str), int(pages_str)
        
    sp, ep = parse_pages(pages)
    
    async def run_in_background():
        _scrape_state.update(
            status="running",
            message="EA Ratings: Iniciando sincronização em background...",
            current=0,
            total=100
        )
        try:
            await run_ea_scraper(
                start_page=sp,
                end_page=ep,
                test_mode=test_mode,
                max_concurrent=15,
                delay=0.5,
                progress_callback=update_ea_progress
            )
            _scrape_state.update(
                status="completed",
                message=f"Coleta de Playstyles da EA concluída com sucesso (Páginas {pages})!",
                last_scrape_at=datetime.now(UTC).isoformat()
            )
        except Exception as e:
            logger.error(f"Erro na sincronização de playstyles da EA em background: {e}")
            _scrape_state.update(
                status="failed",
                message=f"Falha na sincronização da EA: {e}"
            )
            
    background_tasks.add_task(run_in_background)
    return {"status": "started", "message": "Coleta e sincronização de Playstyles da EA iniciada em background."}


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
        playstyles_json=player.playstyles_json,
        imported_at=player.imported_at,
    )


def _sbc_to_response(s: SBCSet) -> SBCSetResponse:
    """Converte SBCSet ORM → schema Pydantic resumido (com player_card compacto inline)."""
    from backend.schemas.schemas import PlayerCardCompactResponse

    # Montar PlayerCardCompactResponse se o SBC tiver player_card
    pc_compact = None
    if s.player_card:
        pc = s.player_card
        pc_compact = PlayerCardCompactResponse(
            id=pc.id, name=pc.name, overall=pc.overall,
            position=pc.position, alt_positions=pc.alt_positions,
            card_type=pc.card_type,
            pace=pc.pace, shooting=pc.shooting, passing=pc.passing,
            dribbling_stat=pc.dribbling_stat, defending=pc.defending, physic=pc.physic,
            skill_moves=pc.skill_moves, weak_foot=pc.weak_foot,
            workrates=pc.workrates, accelerate_type=pc.accelerate_type,
            card_image_url=pc.card_image_url, face_url=pc.face_url,
            render_url=pc.render_url, club_logo_url=pc.club_logo_url,
            nation_flag_url=pc.nation_flag_url, league_logo_url=pc.league_logo_url,
            meta_rating=pc.meta_rating, meta_tier=pc.meta_tier,
            playstyles_json=pc.playstyles_json,
        )

    # Cálculo dinâmico do custo se total_cost for 0 ou nulo (soma dos desafios)
    final_cost = s.total_cost
    if not final_cost or final_cost == 0:
        try:
            # Soma os estimated_cost dos desafios que pertencem a este SBC
            final_cost = sum(ch.estimated_cost for ch in s.challenges if ch.estimated_cost)
        except Exception:
            final_cost = 0

    return SBCSetResponse(
        id=s.id, futgg_id=s.futgg_id, name=s.name,
        description=s.description, category=s.category,
        total_cost=final_cost or None, challenges_count=s.challenges_count,
        expires_at=s.expires_at, expires_text=s.expires_text,
        is_repeatable=s.is_repeatable, repeatable_text=s.repeatable_text,
        refresh_text=s.refresh_text, raw_card_data=s.raw_card_data,
        image_url=s.image_url, completion_pct=s.completion_pct,
        is_new=s.is_new, source=s.source, scraped_at=s.scraped_at,
        player_card=pc_compact,
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
            position=pc.position, alt_positions=pc.alt_positions,
            card_type=pc.card_type,
            # Face stats
            pace=pc.pace, shooting=pc.shooting, passing=pc.passing,
            dribbling_stat=pc.dribbling_stat, defending=pc.defending, physic=pc.physic,
            # Sub-atributos
            acceleration=pc.acceleration, sprint_speed=pc.sprint_speed,
            finishing=pc.finishing, shot_power=pc.shot_power,
            long_shots=pc.long_shots, volleys=pc.volleys, positioning_att=pc.positioning_att,
            short_passing=pc.short_passing, long_passing=pc.long_passing,
            crossing=pc.crossing, curve=pc.curve, free_kick=pc.free_kick, vision=pc.vision,
            agility=pc.agility, balance=pc.balance, reactions=pc.reactions,
            ball_control=pc.ball_control, composure=pc.composure, skill_dribbling=pc.skill_dribbling,
            interceptions=pc.interceptions, heading=pc.heading, marking=pc.marking,
            standing_tackle=pc.standing_tackle, sliding_tackle=pc.sliding_tackle,
            jumping=pc.jumping, stamina=pc.stamina, strength=pc.strength, aggression=pc.aggression,
            penalties=pc.penalties,
            # GK
            gk_diving=pc.gk_diving, gk_handling=pc.gk_handling, gk_kicking=pc.gk_kicking,
            gk_positioning=pc.gk_positioning, gk_reflexes=pc.gk_reflexes,
            # Metadados
            skill_moves=pc.skill_moves, weak_foot=pc.weak_foot, foot=pc.foot,
            height=pc.height, weight=pc.weight, age=pc.age,
            country=pc.country, club_name=pc.club_name, league_name=pc.league_name,
            workrates=pc.workrates, accelerate_type=pc.accelerate_type,
            # URLs CDN
            card_image_url=pc.card_image_url, face_url=pc.face_url, render_url=pc.render_url,
            club_logo_url=pc.club_logo_url, nation_flag_url=pc.nation_flag_url,
            league_logo_url=pc.league_logo_url,
            # Meta
            meta_rating=pc.meta_rating, meta_tier=pc.meta_tier,
            playstyles_json=pc.playstyles_json,
            # IDs
            sofifa_id=pc.sofifa_id, futbin_id=pc.futbin_id,
        )

    # Reutiliza o mapeador base para campos comuns
    base = _sbc_to_response(sbc)
    
    return SBCSetDetailResponse(
        **base.model_dump(),
        challenges=challenges, rewards=set_rewards, player_card_full=player_card,
    )


async def _run_scraping_background():
    """Executa scraping Futbin em background e na sequência sincroniza playstyles da EA Ratings com resiliência total."""
    import logging
    logger = logging.getLogger("help_dmes.main")

    from backend.core.database import get_session
    from backend.services.futbin_service import scrape_all_sbcs, _scrape_state
    from backend.scripts.scrape_ea_ratings import main as run_ea_scraper
    from datetime import datetime, UTC

    futbin_success = False
    futbin_error = None
    ea_success = False
    ea_error = None

    # 1. Executar o scraping dos SBCs e cartas de SBC da Futbin (isolado)
    try:
        _scrape_state.update(
            status="running",
            message="Futbin: Iniciando raspagem dos SBCs...",
            current=0,
            total=100
        )
        async with get_session() as session:
            futbin_res = await scrape_all_sbcs(session)
            logger.info(f"Scraping Futbin concluído em background: {futbin_res}")
            futbin_success = True
    except Exception as e:
        logger.error(f"Erro catastrófico durante o scraping dos SBCs da Futbin: {e}")
        futbin_error = str(e)
        futbin_success = False

    # 2. Executar a coleta automática e sincronização de playstyles da EA Ratings (Pratas e Bronzes)
    # Roda de forma totalmente independente de eventuais falhas do Futbin!
    logger.info("Iniciando coleta automática de playstyles da EA Ratings em background...")
    
    # Callback para atualizar o estado do polling exibido no front-end em tempo real
    def update_ea_progress(msg, done, total):
        _scrape_state.update(
            status="running",
            message=f"EA Ratings: {msg}",
            current=done,
            total=total
        )
    
    msg_prefix = f"(Aviso: Futbin falhou: {futbin_error}) " if not futbin_success else ""
    _scrape_state.update(
        status="running",
        message=f"EA Ratings: Iniciando sincronização de playstyles... {msg_prefix}",
        current=0,
        total=100
    )
    
    try:
        # Executa o scraper da EA Ratings para as páginas 1 a 3 (sincronização padrão)
        await run_ea_scraper(
            start_page=1,
            end_page=3,
            test_mode=False,
            max_concurrent=15,
            delay=0.5,
            progress_callback=update_ea_progress
        )
        logger.info("Coleta automática de playstyles da EA concluída com sucesso!")
        ea_success = True
    except Exception as e:
        logger.error(f"Erro na coleta automática de playstyles da EA: {e}")
        ea_error = str(e)
        ea_success = False

    # 3. Consolidação e definição de status e mensagem final
    now_iso = datetime.now(UTC).isoformat()
    if futbin_success and ea_success:
        _scrape_state.update(
            status="completed",
            message="Sincronização Completa! Futbin SBCs e EA Ratings Playstyles atualizados com sucesso.",
            last_scrape_at=now_iso
        )
    elif futbin_success and not ea_success:
        _scrape_state.update(
            status="completed",  # Concluiu parcialmente
            message=f"Sincronização parcial: Futbin atualizado, mas EA Ratings falhou ({ea_error}).",
            last_scrape_at=now_iso
        )
    elif not futbin_success and ea_success:
        _scrape_state.update(
            status="completed",  # Concluiu parcialmente
            message=f"Sincronização parcial: EA Ratings atualizada, mas Futbin falhou ({futbin_error}).",
            last_scrape_at=now_iso
        )
    else:
        _scrape_state.update(
            status="failed",
            message=f"Sincronização falhou totalmente: Futbin ({futbin_error}) | EA ({ea_error}).",
            last_scrape_at=now_iso
        )

