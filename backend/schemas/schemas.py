"""
Help DMEs — Schemas Pydantic (Request/Response)
=================================================
Modelos de validação para todos os endpoints REST da API.
Usa Pydantic v2 com BaseModel.

Organização:
  - SBC:        Schemas de SBC sets, challenges, requirements, rewards
  - Player:     Schemas de cartas de jogador
  - Squad:      Schemas de elenco (import, filtros, estatísticas)
  - Settings:   Schemas de configurações do sistema
  - Scrape:     Schemas de scraping (status, logs)
  - Calculator: Schemas do motor de cálculo
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════
#  SBC — Sets, Challenges, Requirements, Rewards
# ══════════════════════════════════════════════

class ChallengeRequirementResponse(BaseModel):
    """Requisito individual de um desafio."""
    id: int
    requirement_type: str
    operator: str
    value: str
    detail: Optional[str] = None


class SBCRewardResponse(BaseModel):
    """Recompensa de um SBC set ou challenge."""
    id: int
    reward_type: str
    name: str
    is_untradeable: bool = False
    image_url: Optional[str] = None


class PlayerCardResponse(BaseModel):
    """Carta de jogador — reward principal de SBC player (dados completos)."""
    id: int
    name: str
    overall: int
    position: Optional[str] = None
    alt_positions: Optional[str] = None
    card_type: Optional[str] = None

    # Face stats (6)
    pace: Optional[int] = None
    shooting: Optional[int] = None
    passing: Optional[int] = None
    dribbling_stat: Optional[int] = None
    defending: Optional[int] = None
    physic: Optional[int] = None

    # Sub-atributos detalhados (30)
    acceleration: Optional[int] = None
    sprint_speed: Optional[int] = None
    finishing: Optional[int] = None
    shot_power: Optional[int] = None
    long_shots: Optional[int] = None
    volleys: Optional[int] = None
    positioning_att: Optional[int] = None
    short_passing: Optional[int] = None
    long_passing: Optional[int] = None
    crossing: Optional[int] = None
    curve: Optional[int] = None
    free_kick: Optional[int] = None
    vision: Optional[int] = None
    agility: Optional[int] = None
    balance: Optional[int] = None
    reactions: Optional[int] = None
    ball_control: Optional[int] = None
    composure: Optional[int] = None
    skill_dribbling: Optional[int] = None
    interceptions: Optional[int] = None
    heading: Optional[int] = None
    marking: Optional[int] = None
    standing_tackle: Optional[int] = None
    sliding_tackle: Optional[int] = None
    jumping: Optional[int] = None
    stamina: Optional[int] = None
    strength: Optional[int] = None
    aggression: Optional[int] = None
    penalties: Optional[int] = None

    # GK stats
    gk_diving: Optional[int] = None
    gk_handling: Optional[int] = None
    gk_kicking: Optional[int] = None
    gk_positioning: Optional[int] = None
    gk_reflexes: Optional[int] = None

    # Metadados
    skill_moves: Optional[int] = None
    weak_foot: Optional[int] = None
    foot: Optional[str] = None
    height: Optional[int] = None
    weight: Optional[int] = None
    age: Optional[int] = None
    country: Optional[str] = None
    club_name: Optional[str] = None
    league_name: Optional[str] = None
    workrates: Optional[str] = None
    accelerate_type: Optional[str] = None

    # URLs de CDN
    card_image_url: Optional[str] = None
    face_url: Optional[str] = None
    render_url: Optional[str] = None
    club_logo_url: Optional[str] = None
    nation_flag_url: Optional[str] = None
    league_logo_url: Optional[str] = None

    # Meta
    meta_rating: Optional[float] = None
    meta_tier: Optional[str] = None
    playstyles_json: Optional[str] = None

    # IDs cruzados
    sofifa_id: Optional[int] = None
    futbin_id: Optional[str] = None


class SBCChallengeResponse(BaseModel):
    """Desafio individual dentro de um SBC set."""
    id: int
    name: str
    description: Optional[str] = None
    estimated_cost: Optional[int] = None
    formation: Optional[str] = None
    order_index: int = 0
    requirements: List[ChallengeRequirementResponse] = []
    rewards: List[SBCRewardResponse] = []


class PlayerCardCompactResponse(BaseModel):
    """Subset compacto do PlayerCard para exibição no card visual da listagem.
    Contém apenas os dados necessários para renderizar o card sem precisar 
    de raw_card_data JSON. Os 30 sub-atributos ficam no PlayerCardResponse completo.
    """
    id: int
    name: str
    overall: int
    position: Optional[str] = None
    alt_positions: Optional[str] = None
    card_type: Optional[str] = None

    # Face stats (6)
    pace: Optional[int] = None
    shooting: Optional[int] = None
    passing: Optional[int] = None
    dribbling_stat: Optional[int] = None
    defending: Optional[int] = None
    physic: Optional[int] = None

    # Metadados do jogador
    skill_moves: Optional[int] = None
    weak_foot: Optional[int] = None
    workrates: Optional[str] = None
    accelerate_type: Optional[str] = None

    # URLs visuais
    card_image_url: Optional[str] = None   # bg do card (HD preferido)
    face_url: Optional[str] = None         # face low-res fallback
    render_url: Optional[str] = None       # face HD (CDN Futbin)
    club_logo_url: Optional[str] = None
    nation_flag_url: Optional[str] = None
    league_logo_url: Optional[str] = None

    # Meta rating
    meta_rating: Optional[float] = None
    meta_tier: Optional[str] = None
    playstyles_json: Optional[str] = None


class SBCSetResponse(BaseModel):
    """SBC/DME completo — visão resumida para listagem."""
    id: int
    futgg_id: str
    name: str
    description: Optional[str] = None
    category: str
    total_cost: Optional[int] = None
    challenges_count: int = 0
    expires_at: Optional[datetime] = None
    expires_text: Optional[str] = None
    is_repeatable: bool = False
    repeatable_text: Optional[str] = None
    refresh_text: Optional[str] = None
    image_url: Optional[str] = None
    completion_pct: Optional[float] = None
    is_new: bool = False
    source: str = "futbin"
    scraped_at: Optional[datetime] = None
    raw_card_data: Optional[str] = None  # DEPRECATED — usar player_card
    player_card: Optional[PlayerCardCompactResponse] = None  # ← Fonte única de verdade


class SBCSetDetailResponse(SBCSetResponse):
    """SBC/DME completo — visão detalhada com challenges e rewards."""
    challenges: List[SBCChallengeResponse] = []
    rewards: List[SBCRewardResponse] = []
    player_card_full: Optional[PlayerCardResponse] = None  # Dados completos (30 sub-stats)



# ══════════════════════════════════════════════
#  SQUAD — Elenco do Usuário
# ══════════════════════════════════════════════

class UserSquadPlayerResponse(BaseModel):
    """Jogador do elenco do usuário (todas as colunas do CSV)."""
    id: int
    name: str
    rating: int
    rarity: str
    preferred_position: str
    nation: str
    league: str
    team: str
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    last_sale_price: int = 0
    discard_value: int = 0
    external_price: Optional[int] = None
    is_untradeable: bool = False
    is_loan: bool = False
    is_duplicate: bool = False
    is_in_active_11: bool = False
    is_excluded: bool = False
    definition_id: str
    alternate_positions: Optional[str] = None
    playstyles_json: Optional[str] = None
    imported_at: Optional[datetime] = None


class SquadImportResponse(BaseModel):
    """Resultado da importação de CSV."""
    total_imported: int
    total_skipped: int
    message: str


class SquadStatsResponse(BaseModel):
    """Estatísticas do elenco."""
    total: int
    by_position: dict
    by_league: dict
    by_rating_range: dict
    duplicates: int
    untradeables: int
    loans: int
    excluded: int
    available_for_sbc: int


class BulkExcludeRequest(BaseModel):
    """Request para exclusão em lote."""
    filter_type: str = Field(..., description="Tipo: rating_above, rating_below, position, league, rarity")
    filter_value: str = Field(..., description="Valor do filtro")


class BulkActionResponse(BaseModel):
    """Resposta para ações em lote."""
    affected: int
    message: str


# ══════════════════════════════════════════════
#  SETTINGS — Configurações do Sistema
# ══════════════════════════════════════════════

class AppSettingResponse(BaseModel):
    """Configuração do sistema."""
    key: str
    value: str
    description: Optional[str] = None


class AppSettingUpdateRequest(BaseModel):
    """Request para atualizar uma configuração."""
    value: str


# ══════════════════════════════════════════════
#  SCRAPE — Status e Logs de Sincronização
# ══════════════════════════════════════════════

class ScrapeStatusResponse(BaseModel):
    """Status atual do scraping."""
    status: str = Field(default="idle", description="running / idle / failed")
    message: Optional[str] = None
    last_scrape_at: Optional[datetime] = None
    sbcs_count: int = 0


class ScrapeStartResponse(BaseModel):
    """Resposta ao iniciar scraping."""
    status: str
    message: str


class ScrapeLogResponse(BaseModel):
    """Log de uma sincronização."""
    id: int
    source: str
    status: str
    sbcs_scraped: int
    started_at: datetime
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None


# ══════════════════════════════════════════════
#  CALCULATOR — Motor de Cálculo
# ══════════════════════════════════════════════

class SuggestedPlayerResponse(BaseModel):
    """Jogador sugerido para um challenge."""
    player: UserSquadPlayerResponse
    assigned_position: str
    reason: str = Field(description="Ex: 'Duplicata', 'Intransferível', 'Menor rating'")


class StepResponse(BaseModel):
    """Passo individual da rota ótima."""
    order: int
    action: str = Field(description="Ex: 'Completar DME X', 'Usar carta Y como forragem'")
    sbc_name: Optional[str] = None
    challenge_name: Optional[str] = None
    suggested_players: List[SuggestedPlayerResponse] = []
    estimated_cost: int = 0
    gaps: List[str] = Field(default=[], description="Requisitos que o elenco NÃO atende")


class CalculatePathResponse(BaseModel):
    """Resposta do cálculo de rota ótima."""
    target_sbc: SBCSetResponse
    feasible: bool = Field(description="Se é possível completar com o elenco atual")
    steps: List[StepResponse] = []
    total_estimated_cost: int = 0
    message: str = ""


class AnalysisResponse(BaseModel):
    """Análise de viabilidade de um SBC."""
    sbc: SBCSetResponse
    total_requirements: int
    met_requirements: int
    unmet_requirements: List[str] = []
    available_players: int
    estimated_cost: int = 0
    feasible: bool = False
