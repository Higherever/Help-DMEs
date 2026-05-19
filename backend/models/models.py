"""
Help DMEs — Modelos ORM SQLAlchemy
===================================
Todas as tabelas do banco de dados help_dmes.db.

Tabelas:
  - sbc_sets:               Cada DME/SBC como um todo
  - sbc_challenges:         Cada desafio individual dentro de um set
  - challenge_requirements:  Requisitos de cada desafio
  - sbc_rewards:            Recompensas de desafios e sets
  - player_cards:           Carta de jogador (reward principal)
  - user_squad:             Elenco do usuário importado do CSV
  - position_mapping:       Mapeamento de posições PT↔EN
  - rarity_mapping:         Mapeamento de raridades PT↔EN
  - app_settings:           Configurações globais do sistema
  - scrape_logs:            Log de sincronizações com fontes externas
"""

from datetime import datetime, UTC
from typing import Optional, List

from sqlalchemy import (
    String, Integer, Float, Boolean, Text, DateTime,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship
)


# ──────────────────────────────────────────────
# Base declarativa para todos os modelos
# ──────────────────────────────────────────────

class Base(DeclarativeBase):
    """Base class para todos os modelos ORM."""
    pass


# ══════════════════════════════════════════════
#  SBC SETS — Cada DME/SBC como um todo
# ══════════════════════════════════════════════

class SBCSet(Base):
    """
    Representa um SBC completo (ex: 'Moisés Caicedo', 'Gold Upgrade').
    Cada set contém N challenges que devem ser completados.
    """
    __tablename__ = "sbc_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    futgg_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="ID do Fut.gg ex: 26-841")
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, comment="players/upgrades/challenges/icons/foundations/swaps")
    total_cost: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="Custo estimado em FC Coins")
    challenges_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_repeatable: Mapped[bool] = mapped_column(Boolean, default=False)
    repeat_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="null = infinito")
    refresh_interval: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="Ex: '1 day'")
    expires_text: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    repeatable_text: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    refresh_text: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    raw_card_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="JSON com bg, face, etc.")
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completion_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="% de quem completou")
    is_new: Mapped[bool] = mapped_column(Boolean, default=False)
    scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="fut.gg", comment="fut.gg ou futnext")

    # Relacionamentos
    challenges: Mapped[List["SBCChallenge"]] = relationship(
        back_populates="sbc_set", cascade="all, delete-orphan", order_by="SBCChallenge.order_index"
    )
    rewards: Mapped[List["SBCReward"]] = relationship(
        back_populates="sbc_set", cascade="all, delete-orphan",
        primaryjoin="SBCSet.id == SBCReward.sbc_set_id"
    )
    player_card: Mapped[Optional["PlayerCard"]] = relationship(
        back_populates="sbc_set", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<SBCSet(id={self.id}, name='{self.name}', category='{self.category}')>"


# ══════════════════════════════════════════════
#  SBC CHALLENGES — Cada desafio dentro de um set
# ══════════════════════════════════════════════

class SBCChallenge(Base):
    """
    Desafio individual dentro de um SBC set.
    Ex: '90-Rated Squad', 'Premier League', 'Top Form'.
    """
    __tablename__ = "sbc_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sbc_set_id: Mapped[int] = mapped_column(Integer, ForeignKey("sbc_sets.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estimated_cost: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="Custo em FC Coins")
    challenge_image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    formation: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="Ex: 4-3-3, 4-4-2")
    order_index: Mapped[int] = mapped_column(Integer, default=0, comment="Ordem dentro do set")
    solution_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relacionamentos
    sbc_set: Mapped["SBCSet"] = relationship(back_populates="challenges")
    requirements: Mapped[List["ChallengeRequirement"]] = relationship(
        back_populates="challenge", cascade="all, delete-orphan"
    )
    rewards: Mapped[List["SBCReward"]] = relationship(
        back_populates="challenge", cascade="all, delete-orphan",
        primaryjoin="SBCChallenge.id == SBCReward.challenge_id"
    )

    def __repr__(self) -> str:
        return f"<SBCChallenge(id={self.id}, name='{self.name}', set_id={self.sbc_set_id})>"


# ══════════════════════════════════════════════
#  CHALLENGE REQUIREMENTS — Requisitos de cada desafio
# ══════════════════════════════════════════════

class ChallengeRequirement(Base):
    """
    Requisito específico de um desafio.
    Ex: 'Min. Team Rating: 90', 'Min. 1 Players from: Premier League'.

    Tipos de requisito (requirement_type):
      - team_rating:          Rating mínimo/máximo do time
      - players_from_league:  Jogadores de uma liga específica
      - players_from_nation:  Jogadores de uma nacionalidade
      - players_from_club:    Jogadores de um clube
      - players_same_nation:  Jogadores da mesma nacionalidade
      - players_same_league:  Jogadores da mesma liga
      - players_same_club:    Jogadores do mesmo clube
      - leagues_in_squad:     Ligas no elenco
      - nations_in_squad:     Nacionalidades no elenco
      - clubs_in_squad:       Clubes no elenco
      - player_quality:       Qualidade (Gold, Silver, Bronze)
      - player_rarity:        Raridade (Rare, Common)
      - player_type:          Tipo especial (TOTW, TOTS, etc.)
      - squad_chemistry:      Química total do time
      - player_count:         Número exato de jogadores
    """
    __tablename__ = "challenge_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    challenge_id: Mapped[int] = mapped_column(Integer, ForeignKey("sbc_challenges.id", ondelete="CASCADE"), nullable=False)
    requirement_type: Mapped[str] = mapped_column(String(50), nullable=False)
    operator: Mapped[str] = mapped_column(String(10), nullable=False, comment="min / max / exact")
    value: Mapped[str] = mapped_column(String(100), nullable=False)
    detail: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="Ex: 'Premier League', 'Any TOTW or TOTS'")

    # Relacionamento
    challenge: Mapped["SBCChallenge"] = relationship(back_populates="requirements")

    def __repr__(self) -> str:
        return f"<ChallengeRequirement({self.operator} {self.requirement_type}: {self.value} {self.detail or ''})>"


# ══════════════════════════════════════════════
#  SBC REWARDS — Recompensas
# ══════════════════════════════════════════════

class SBCReward(Base):
    """
    Recompensa de um SBC set ou de um challenge individual.
    Pode ser um pack, player pick, ou jogador específico.
    """
    __tablename__ = "sbc_rewards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sbc_set_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("sbc_sets.id", ondelete="CASCADE"), nullable=True)
    challenge_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("sbc_challenges.id", ondelete="CASCADE"), nullable=True)
    reward_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="pack / player / pick")
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_untradeable: Mapped[bool] = mapped_column(Boolean, default=False)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relacionamentos
    sbc_set: Mapped[Optional["SBCSet"]] = relationship(
        back_populates="rewards",
        primaryjoin="SBCReward.sbc_set_id == SBCSet.id"
    )
    challenge: Mapped[Optional["SBCChallenge"]] = relationship(
        back_populates="rewards",
        primaryjoin="SBCReward.challenge_id == SBCChallenge.id"
    )

    def __repr__(self) -> str:
        return f"<SBCReward(type='{self.reward_type}', name='{self.name}')>"


# ══════════════════════════════════════════════
#  PLAYER CARDS — Carta de jogador (reward principal do SBC)
# ══════════════════════════════════════════════

class PlayerCard(Base):
    """
    Carta de jogador que é a recompensa principal de um SBC player.
    Ex: Caicedo 93 TOTS HM, Schweinsteiger 96 Trophy Titans ICON.
    """
    __tablename__ = "player_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    futgg_player_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="ID no Fut.gg")
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    overall: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, comment="CM, ST, etc.")
    card_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="TOTS HM, Trophy Titans ICON, etc.")
    meta_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="Meta rating ex: 90.2")
    card_image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    player_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sbc_set_id: Mapped[int] = mapped_column(Integer, ForeignKey("sbc_sets.id", ondelete="CASCADE"), nullable=False)

    # Relacionamento
    sbc_set: Mapped["SBCSet"] = relationship(back_populates="player_card")

    def __repr__(self) -> str:
        return f"<PlayerCard(name='{self.name}', overall={self.overall}, type='{self.card_type}')>"


# ══════════════════════════════════════════════
#  USER SQUAD — Elenco do Usuário (importado do CSV)
# ══════════════════════════════════════════════

class UserSquadPlayer(Base):
    """
    Jogador do elenco do usuário, importado do CSV exportado pelo EA FC.

    Regras de filtragem para SBCs:
      🚫 BLOQUEIO ABSOLUTO:
        - is_loan=True → NUNCA entra em SBC
        - is_excluded=True → NUNCA entra (exclusão manual do usuário)
      🛡️ PROTEÇÃO CONDICIONAL:
        - is_in_active_11=True → BLOQUEADO por padrão
          Só libera se app_settings.allow_active_11_in_sbc = true
      📊 PRIORIDADE DE USO (forragem):
        1º is_duplicate=True (descartáveis)
        2º is_untradeable=True (sem valor de revenda)
        3º Menor rating primeiro
        4º Menor external_price primeiro
    """
    __tablename__ = "user_squad"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Dados do jogador (direto do CSV) ──
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False, comment="Overall da carta")
    rarity: Mapped[str] = mapped_column(String(100), nullable=False, comment="Em PT-BR: Raro, Comum, Seleção da Temporada, etc.")
    preferred_position: Mapped[str] = mapped_column(String(10), nullable=False, comment="Em PT-BR: VOL, ZAG, ATA, etc.")
    nation: Mapped[str] = mapped_column(String(100), nullable=False, comment="Em PT-BR: Brasil, Argentina, etc.")
    league: Mapped[str] = mapped_column(String(255), nullable=False, comment="Liga do jogador")
    team: Mapped[str] = mapped_column(String(255), nullable=False, comment="Clube do jogador")

    # ── Dados financeiros ──
    price_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="Preço mínimo de mercado")
    price_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="Preço máximo de mercado")
    last_sale_price: Mapped[int] = mapped_column(Integer, default=0)
    discard_value: Mapped[int] = mapped_column(Integer, default=0)
    external_price: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="Preço de mercado externo")

    # ── Flags booleanas ──
    is_untradeable: Mapped[bool] = mapped_column(Boolean, default=False, comment="Intransferível")
    is_loan: Mapped[bool] = mapped_column(Boolean, default=False, comment="Empréstimo — BLOQUEADO de SBCs")
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, comment="Carta duplicada")
    is_in_active_11: Mapped[bool] = mapped_column(Boolean, default=False, comment="Está no time titular")
    is_excluded: Mapped[bool] = mapped_column(Boolean, default=False, comment="Excluído pelo usuário da somatória")

    # ── Metadados ──
    definition_id: Mapped[str] = mapped_column(String(50), nullable=False, comment="ID único da carta no EA FC")
    alternate_positions: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="CSV de posições alternativas em PT: 'VOL,MC'")
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    def __repr__(self) -> str:
        return f"<UserSquadPlayer(name='{self.name}', rating={self.rating}, pos='{self.preferred_position}')>"

    @property
    def all_positions(self) -> list[str]:
        """Retorna lista com posição principal + alternativas."""
        positions = [self.preferred_position]
        if self.alternate_positions:
            positions.extend(self.alternate_positions.split(","))
        return list(set(positions))

    @property
    def is_available_for_sbc(self) -> bool:
        """
        Verifica disponibilidade básica (sem considerar setting do time titular).
        A verificação completa do time titular é feita no service.
        """
        return not self.is_loan and not self.is_excluded


# ══════════════════════════════════════════════
#  POSITION MAPPING — Mapeamento de posições PT↔EN
# ══════════════════════════════════════════════

class PositionMapping(Base):
    """
    Tabela de mapeamento de posições entre PT-BR (CSV do elenco)
    e EN (dados do Fut.gg/Futbin).

    Usada internamente pelo motor de cálculo.
    O frontend SEMPRE exibe em PT-BR.
    """
    __tablename__ = "position_mapping"

    pt: Mapped[str] = mapped_column(String(10), primary_key=True, comment="Posição PT-BR: VOL, ZAG, ATA")
    en: Mapped[str] = mapped_column(String(10), nullable=False, comment="Posição EN: CDM, CB, ST")

    def __repr__(self) -> str:
        return f"<PositionMapping(pt='{self.pt}' → en='{self.en}')>"


# ══════════════════════════════════════════════
#  RARITY MAPPING — Mapeamento de raridades PT↔EN
# ══════════════════════════════════════════════

class RarityMapping(Base):
    """
    Tabela de mapeamento de raridades entre PT-BR (CSV do elenco)
    e EN (dados do Fut.gg/Futbin).

    Usada internamente pelo motor de cálculo para bater
    requisitos como 'Min. 3 Players: Rare' com raridade 'Raro' do CSV.
    """
    __tablename__ = "rarity_mapping"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pt: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, comment="Raridade PT-BR")
    en: Mapped[str] = mapped_column(String(100), nullable=False, comment="Raridade EN")
    is_gold: Mapped[bool] = mapped_column(Boolean, default=False, comment="Se conta como Gold")
    is_rare: Mapped[bool] = mapped_column(Boolean, default=False, comment="Se conta como Rare")
    is_special: Mapped[bool] = mapped_column(Boolean, default=False, comment="Se é carta especial")
    is_totw: Mapped[bool] = mapped_column(Boolean, default=False, comment="Se é TOTW")
    is_tots: Mapped[bool] = mapped_column(Boolean, default=False, comment="Se é TOTS ou TOTS-related")

    def __repr__(self) -> str:
        return f"<RarityMapping(pt='{self.pt}' → en='{self.en}')>"


# ══════════════════════════════════════════════
#  APP SETTINGS — Configurações Globais
# ══════════════════════════════════════════════

class AppSetting(Base):
    """
    Configurações globais do sistema.
    Persistidas em banco para sobreviver reinicializações.

    Configurações iniciais:
      - allow_active_11_in_sbc: false (🛡️ protege time titular)
      - auto_exclude_loans: true (🚫 empréstimos nunca entram)
      - default_source: "fut.gg"
      - scrape_on_startup: true
    """
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<AppSetting(key='{self.key}', value='{self.value}')>"

    @property
    def as_bool(self) -> bool:
        """Converte value para boolean."""
        return self.value.lower() in ("true", "1", "yes", "sim")


# ══════════════════════════════════════════════
#  SCRAPE LOGS — Histórico de sincronizações
# ══════════════════════════════════════════════

class ScrapeLog(Base):
    """
    Log de cada sincronização (scraping) realizada.
    Permite rastrear quando foi feita a última coleta,
    quantos SBCs foram coletados e se houve erros.
    """
    __tablename__ = "scrape_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, comment="fut.gg ou futnext")
    status: Mapped[str] = mapped_column(String(20), nullable=False, comment="success / partial / failed")
    sbcs_scraped: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<ScrapeLog(source='{self.source}', status='{self.status}', scraped={self.sbcs_scraped})>"
