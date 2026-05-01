"""
Help DMEs — Seed Data
======================
Dados iniciais populados automaticamente na primeira execução:
  - Mapeamento de posições PT↔EN
  - Mapeamento de raridades PT↔EN (com flags is_gold, is_rare, is_special, etc.)
  - Configurações padrão do sistema (app_settings)
"""

from sqlalchemy import select
import logging
from backend.core.database import async_session_factory
from backend.models.models import PositionMapping, RarityMapping, AppSetting

logger = logging.getLogger("help_dmes." + __name__.split(".")[-1])


# ──────────────────────────────────────────────
# Dados de seed
# ──────────────────────────────────────────────

POSITION_MAPPINGS = [
    # PT-BR → EN (padrão EA FC)
    {"pt": "GL",  "en": "GK"},
    {"pt": "ZAG", "en": "CB"},
    {"pt": "LD",  "en": "RB"},
    {"pt": "LE",  "en": "LB"},
    {"pt": "VOL", "en": "CDM"},
    {"pt": "MC",  "en": "CM"},
    {"pt": "MEI", "en": "CAM"},
    {"pt": "MD",  "en": "RM"},
    {"pt": "ME",  "en": "LM"},
    {"pt": "PD",  "en": "RW"},
    {"pt": "PE",  "en": "LW"},
    {"pt": "ATA", "en": "ST"},
]

RARITY_MAPPINGS = [
    # Gold Common
    {"pt": "Comum", "en": "Common", "is_gold": True, "is_rare": False, "is_special": False, "is_totw": False, "is_tots": False},
    # Gold Rare
    {"pt": "Raro", "en": "Rare", "is_gold": True, "is_rare": True, "is_special": False, "is_totw": False, "is_tots": False},
    # Especiais
    {"pt": "Seleção da Temporada", "en": "Team of the Season", "is_gold": True, "is_rare": True, "is_special": True, "is_totw": False, "is_tots": True},
    {"pt": "Menções Honrosas do TOTS", "en": "TOTS Honourable Mentions", "is_gold": True, "is_rare": True, "is_special": True, "is_totw": False, "is_tots": True},
    {"pt": "Revelação do TOTS", "en": "TOTS Breakthrough", "is_gold": True, "is_rare": True, "is_special": True, "is_totw": False, "is_tots": True},
    {"pt": "Revelação do TOTS ", "en": "TOTS Breakthrough", "is_gold": True, "is_rare": True, "is_special": True, "is_totw": False, "is_tots": True},  # variante com espaço
    {"pt": "Seleção da Semana (TOTW)", "en": "Team of the Week", "is_gold": True, "is_rare": True, "is_special": True, "is_totw": True, "is_tots": False},
    {"pt": "Ídolo", "en": "Icon", "is_gold": True, "is_rare": True, "is_special": True, "is_totw": False, "is_tots": False},
    {"pt": "ÍDOLO Multicampeões", "en": "Trophy Titans Icon", "is_gold": True, "is_rare": True, "is_special": True, "is_totw": False, "is_tots": False},
    {"pt": "Herói/Heroína Multicampeões", "en": "Trophy Titans Hero", "is_gold": True, "is_rare": True, "is_special": True, "is_totw": False, "is_tots": False},
    {"pt": "Aniversário do FUT", "en": "FUT Birthday", "is_gold": True, "is_rare": True, "is_special": True, "is_totw": False, "is_tots": False},
    {"pt": "Turnê Mundial Premium", "en": "Premium World Tour", "is_gold": True, "is_rare": True, "is_special": True, "is_totw": False, "is_tots": False},
    {"pt": "Tour mundial", "en": "World Tour", "is_gold": True, "is_rare": False, "is_special": True, "is_totw": False, "is_tots": False},
    {"pt": "Confronto", "en": "Showdown", "is_gold": True, "is_rare": True, "is_special": True, "is_totw": False, "is_tots": False},
    {"pt": "Melhoria de Confronto", "en": "Showdown Upgrade", "is_gold": True, "is_rare": True, "is_special": True, "is_totw": False, "is_tots": False},
    {"pt": "FC Pro ao Vivo", "en": "FC Pro Live", "is_gold": True, "is_rare": True, "is_special": True, "is_totw": False, "is_tots": False},
    {"pt": "Base de Elenco", "en": "Squad Foundations", "is_gold": True, "is_rare": False, "is_special": True, "is_totw": False, "is_tots": False},
]

DEFAULT_SETTINGS = [
    {
        "key": "allow_active_11_in_sbc",
        "value": "false",
        "description": "🛡️ Permite usar jogadores do time titular em SBCs. Desativado por padrão — protege o elenco ativo.",
    },
    {
        "key": "auto_exclude_loans",
        "value": "true",
        "description": "🚫 Exclui jogadores emprestados automaticamente de SBCs (sem exceção).",
    },
    {
        "key": "default_source",
        "value": "fut.gg",
        "description": "Fonte primária de scraping de SBCs.",
    },
    {
        "key": "scrape_on_startup",
        "value": "true",
        "description": "Executar scraping automático ao iniciar o programa.",
    },
]


# ──────────────────────────────────────────────
# Função de seed
# ──────────────────────────────────────────────

async def seed_initial_data():
    """
    Popula dados iniciais no banco (idempotente).
    Só insere registros que ainda não existem.
    """
    async with async_session_factory() as session:
        try:
            # Seed: Posições PT↔EN
            for mapping in POSITION_MAPPINGS:
                existing = await session.get(PositionMapping, mapping["pt"])
                if not existing:
                    session.add(PositionMapping(**mapping))

            # Seed: Raridades PT↔EN
            for mapping in RARITY_MAPPINGS:
                result = await session.execute(
                    select(RarityMapping).where(RarityMapping.pt == mapping["pt"])
                )
                if not result.scalar_one_or_none():
                    session.add(RarityMapping(**mapping))

            # Seed: Configurações padrão
            for setting in DEFAULT_SETTINGS:
                existing = await session.get(AppSetting, setting["key"])
                if not existing:
                    session.add(AppSetting(**setting))

            await session.commit()
            logger.info("✅ Dados de seed populados com sucesso.")

        except Exception as e:
            await session.rollback()
            logger.error(f"⚠️ Erro ao popular seed data: {e}")
            raise
