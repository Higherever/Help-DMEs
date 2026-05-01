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
    """Carta de jogador — reward principal de SBC player."""
    id: int
    name: str
    overall: int
    position: Optional[str] = None
    card_type: Optional[str] = None
    meta_rating: Optional[float] = None
    card_image_url: Optional[str] = None


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
    is_repeatable: bool = False
    image_url: Optional[str] = None
    completion_pct: Optional[float] = None
    is_new: bool = False
    source: str = "fut.gg"
    scraped_at: Optional[datetime] = None


class SBCSetDetailResponse(SBCSetResponse):
    """SBC/DME completo — visão detalhada com challenges e rewards."""
    challenges: List[SBCChallengeResponse] = []
    rewards: List[SBCRewardResponse] = []
    player_card: Optional[PlayerCardResponse] = None


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
