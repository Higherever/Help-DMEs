"""
Help DMEs — Scrape Master (Orquestrador Unificado Inteligente)
==============================================================
Script principal e ÚNICO de coleta de jogadores do catálogo EA FC 26.
Substitui todos os scripts antigos:
  - scrape_players_v2.py
  - scrape_all_players.py
  - update_missing_substats.py
  - scrape_ea_ratings.py
  - scrape_full_db.py
  - maintain_players_db.py

Funcionalidades:
  ✅ Skip inteligente em 3 camadas (estado JSON + banco SQLite + disco)
  ✅ Detecção de novidades (compara IDs do Futbin vs banco)
  ✅ Pipeline completo de 5 fases (listagem, detalhes, FutGG HD, download, pós-processamento)
  ✅ Resiliência (Ctrl+C salva estado, retoma de onde parou)
  ✅ Estado atômico via tmpfile (sem corrupção de queda)
  ✅ Anti-bot premium (User-Agents, delays gaussianos, back-off exponencial)

Modo de uso:
    cd "/home/gambeta/Projetos/Socorro DMEs/Socorro DMEs"
    source backend/.venv/bin/activate
    python backend/scripts/scrape_master.py                    # Raspa tudo, pula o já feito
    python backend/scripts/scrape_master.py --pages 1-50       # Só páginas 1 a 50
    python backend/scripts/scrape_master.py --pages 1-2 --test # Modo teste: 5 jogadores/página
    python backend/scripts/scrape_master.py --force             # Ignora skip, reprocessa tudo
"""

import sys
import os
import json
import logging
import re
import argparse
import unicodedata
import asyncio
import random
import tempfile
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime, UTC
from typing import Optional, Dict, List, Tuple

import aiohttp
import aiofiles
from bs4 import BeautifulSoup

# ── Configurar paths (100% dinâmico) ─────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.anti_bot import fetch_html, fetch_binary, create_session

# ── Logging ──────────────────────────────────────────────────────────────────
LOG_FILE = SCRIPT_DIR / "scrape_master.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ]
)
logger = logging.getLogger("scrape_master")

# ── Constantes ───────────────────────────────────────────────────────────────
FUTBIN_BASE    = "https://www.futbin.com"
FUTGG_BASE     = "https://www.fut.gg"
DATABASE_FILE  = PROJECT_ROOT / "database" / "help_dmes.db"
IMAGES_DIR     = PROJECT_ROOT / "images"
STATE_FILE     = SCRIPT_DIR / "scrape_master_state.json"
SCRAPER_VERSION = "v3.0-master"

# Semáforos (simula usuário humano)
FUTBIN_SEM = asyncio.Semaphore(2)
FUTGG_SEM  = asyncio.Semaphore(2)
IMG_SEM    = asyncio.Semaphore(4)

# Tipos de card base (Gold/Silver/Bronze)
BASE_CARD_TYPES = {
    "gold", "gold rare", "gold non-rare",
    "silver", "silver rare", "silver non-rare",
    "bronze", "bronze rare", "bronze non-rare",
}


# ═══════════════════════════════════════════════════════════════════════════════
# STATE MANAGEMENT (Atômico e Resiliente)
# ═══════════════════════════════════════════════════════════════════════════════

def load_state() -> dict:
    """Carrega progresso de raspagem do arquivo JSON."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
                state.setdefault("completed_pages", [])
                state.setdefault("failed_players", [])
                state.setdefault("last_page_processed", 0)
                return state
        except Exception as e:
            logger.warning(f"Erro ao carregar estado ({e}). Inicializando novo.")
    return {
        "completed_pages": [],
        "last_page_processed": 0,
        "failed_players": [],
        "version": SCRAPER_VERSION,
        "started_at": datetime.now(UTC).isoformat(),
    }


def save_state(state: dict):
    """Salva progresso de forma atômica via tmpfile."""
    try:
        fd, temp_path = tempfile.mkstemp(dir=str(SCRIPT_DIR), suffix=".tmp")
        os.close(fd)
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        shutil.move(temp_path, str(STATE_FILE))
    except Exception as e:
        logger.error(f"Erro ao salvar estado: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def sanitize(text: str) -> str:
    """Converte texto para slug seguro para nome de arquivo."""
    if not text:
        return "unknown"
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ASCII", "ignore").decode("ASCII")
    clean = re.sub(r"[^a-zA-Z0-9\s_-]", "", ascii_text)
    clean = re.sub(r"[\s_-]+", "_", clean)
    return clean.strip("_").lower()[:50]


def safe_int(val) -> Optional[int]:
    """Converte para int com segurança."""
    try:
        if val is None:
            return None
        return int(str(val).strip())
    except (ValueError, TypeError):
        return None


def playstyle_slug(name: str) -> str:
    """Normaliza nome de PlayStyle para slug estável."""
    return sanitize(name)


def detect_playstyle_plus(name: str = "", icon_url: str = "", classes: List[str] | Tuple[str, ...] = ()) -> bool:
    """Detecta PlayStyle+ por classe, URL ou texto."""
    text = " ".join([name or "", icon_url or "", " ".join(classes or [])]).lower()
    return any(
        marker in text
        for marker in (
            "/plus/",
            "-plus",
            "_plus",
            "psplus",
            "playstyle-plus",
            "playstyle_plus",
            "playstyle+",
            " plus ",
            "gold",
        )
    )


def normalize_playstyle(raw, source: str = "unknown") -> Optional[dict]:
    """Converte PlayStyle bruto para contrato canônico salvo no banco."""
    if not raw:
        return None
    item = {"name": raw} if isinstance(raw, str) else dict(raw) if isinstance(raw, dict) else None
    if not item:
        return None

    name = item.get("name") or item.get("title") or item.get("label") or item.get("alt") or ""
    icon_url = item.get("icon_url") or item.get("icon_path") or item.get("src") or ""
    classes = item.get("classes") or []
    tier = str(item.get("tier") or "").lower()
    is_plus_raw = item.get("is_plus")
    is_plus = (
        is_plus_raw is True or
        str(is_plus_raw).strip().lower() in {"1", "true", "yes", "plus", "playstyle+", "psplus"} or
        tier == "plus" or
        detect_playstyle_plus(str(name), str(icon_url), classes)
    )

    clean_name = re.sub(r"\s*(playstyle\+|\+)$", "", str(name), flags=re.I).strip()
    slug = item.get("slug") or playstyle_slug(clean_name)
    if not clean_name and slug == "unknown":
        return None

    item_source = item.get("source") or source
    verified = item.get("verified_by_futgg")
    if verified is None:
        verified = item_source in {"futgg", "futgg_fallback"}

    return {
        "name": clean_name or slug.replace("_", " ").title(),
        "slug": slug,
        "icon_url": icon_url,
        "is_plus": bool(is_plus),
        "tier": "plus" if is_plus else "base",
        "source": item_source,
        "verified_by_futgg": bool(verified),
    }


def normalize_playstyles(raw_playstyles, source: str = "unknown") -> List[dict]:
    """Normaliza lista/JSON de PlayStyles e deduplica por slug, preferindo Plus."""
    if isinstance(raw_playstyles, str):
        try:
            raw_playstyles = json.loads(raw_playstyles)
        except json.JSONDecodeError:
            raw_playstyles = []
    if not isinstance(raw_playstyles, list):
        return []

    by_slug = {}
    for raw in raw_playstyles:
        normalized = normalize_playstyle(raw, source=source)
        if not normalized:
            continue
        existing = by_slug.get(normalized["slug"])
        if not existing or (normalized["is_plus"] and not existing.get("is_plus")):
            by_slug[normalized["slug"]] = normalized
    return list(by_slug.values())


def merge_playstyle_sources(futbin_playstyles, futgg_playstyles) -> List[dict]:
    """Futbin vence quando apresenta PlayStyles; FutGG só cobre ausência total."""
    futbin = normalize_playstyles(futbin_playstyles, source="futbin")
    if futbin:
        for item in futbin:
            item["source"] = "futbin"
            item["verified_by_futgg"] = False
        return futbin

    fallback = normalize_playstyles(futgg_playstyles, source="futgg_fallback")
    for item in fallback:
        item["source"] = "futgg_fallback"
        item["verified_by_futgg"] = True
    return fallback


def filter_plus_playstyles(raw_playstyles) -> List[dict]:
    """Retorna só PlayStyles+ renderizáveis."""
    return [
        item for item in normalize_playstyles(raw_playstyles, source="unknown")
        if item.get("tier") == "plus" or item.get("is_plus") is True
    ]


def playstyles_are_current(raw_playstyles) -> bool:
    """Confere se PlayStyles existem e já usam schema canônico atual."""
    if isinstance(raw_playstyles, str):
        try:
            parsed = json.loads(raw_playstyles)
        except json.JSONDecodeError:
            return False
    else:
        parsed = raw_playstyles

    if not isinstance(parsed, list) or not parsed:
        return False

    required = {"name", "slug", "icon_url", "is_plus", "tier", "source", "verified_by_futgg"}
    for item in parsed:
        if not isinstance(item, dict) or not required.issubset(item.keys()):
            return False

    return bool(normalize_playstyles(parsed, source="db"))


def _playstyle_element_name(el) -> str:
    title = (
        el.get("title") or el.get("aria-label") or el.get("data-original-title") or
        el.get("data-tooltip") or el.get("alt") or ""
    )
    if title:
        return str(title).strip()

    img = el.select_one("img")
    if img:
        img_title = img.get("title") or img.get("alt") or img.get("aria-label") or ""
        if img_title:
            return str(img_title).strip()

    label = el.select_one(".slim-font, [class*='name'], [class*='label'], span, div")
    return label.get_text(" ", strip=True) if label else el.get_text(" ", strip=True)


def _playstyle_element_icon_url(el) -> str:
    img = el if el.name == "img" else el.select_one("img")
    if not img:
        return ""
    return img.get("src") or img.get("data-src") or img.get("data-original") or ""


def extract_futbin_playstyles(soup: BeautifulSoup) -> List[dict]:
    """Extrai PlayStyles ativos do Futbin."""
    playstyles = []
    wrappers = soup.select(".player-abilities-wrapper:not(.hidden)")
    candidates = []
    for wrapper in wrappers:
        candidates.extend(wrapper.select("a[href*='/playstyles/']"))
    if not candidates:
        candidates = soup.select("a[href*='/playstyles/'], .playstyle-icon")

    for el in candidates:
        classes = el.get("class", [])
        if "active" not in classes and el.name != "img" and not el.select_one("img"):
            continue
        normalized = normalize_playstyle({
            "name": _playstyle_element_name(el),
            "icon_url": _playstyle_element_icon_url(el),
            "classes": classes,
            "is_plus": "psplus" in classes,
        }, source="futbin")
        if normalized:
            playstyles.append(normalized)
    return normalize_playstyles(playstyles, source="futbin")


def extract_futgg_playstyles(soup: BeautifulSoup) -> List[dict]:
    """Extrai PlayStyles do FutGG para fallback quando Futbin não retorna nenhum."""
    selectors = [
        "a[href*='playstyle']",
        "[class*='playstyle']",
        "img[src*='playstyle']",
        "img[src*='playstyles']",
    ]
    seen_nodes = []
    for selector in selectors:
        for el in soup.select(selector):
            if el not in seen_nodes:
                seen_nodes.append(el)

    playstyles = []
    for el in seen_nodes:
        classes = el.get("class", [])
        normalized = normalize_playstyle({
            "name": _playstyle_element_name(el),
            "icon_url": _playstyle_element_icon_url(el),
            "classes": classes,
            "is_plus": detect_playstyle_plus(_playstyle_element_name(el), _playstyle_element_icon_url(el), classes),
        }, source="futgg")
        if normalized:
            playstyles.append(normalized)
    return normalize_playstyles(playstyles, source="futgg")


# ═══════════════════════════════════════════════════════════════════════════════
# BANCO DE DADOS — Verificação, Migração e Skip
# ═══════════════════════════════════════════════════════════════════════════════

def verify_and_migrate_db():
    """Garante que a tabela fc_players exista com todas as colunas necessárias."""
    if not DATABASE_FILE.parent.exists():
        DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DATABASE_FILE))
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS fc_players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            futbin_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            overall INTEGER NOT NULL,
            position TEXT,
            nation TEXT,
            club TEXT,
            league TEXT,
            card_type TEXT,
            face_url TEXT,
            bg_url_raw TEXT,
            card_template_url TEXT,
            scraped_at TEXT
        )
    """)

    extended_columns = [
        ("pace",            "INTEGER"), ("shooting",        "INTEGER"),
        ("passing",         "INTEGER"), ("dribbling_stat",  "INTEGER"),
        ("defending",       "INTEGER"), ("physic",          "INTEGER"),
        ("acceleration",    "INTEGER"), ("sprint_speed",    "INTEGER"),
        ("finishing",       "INTEGER"), ("shot_power",      "INTEGER"),
        ("long_shots",      "INTEGER"), ("volleys",         "INTEGER"),
        ("positioning_att", "INTEGER"), ("penalties",       "INTEGER"),
        ("short_passing",   "INTEGER"), ("long_passing",    "INTEGER"),
        ("crossing",        "INTEGER"), ("curve",           "INTEGER"),
        ("free_kick",       "INTEGER"), ("vision",          "INTEGER"),
        ("agility",         "INTEGER"), ("balance",         "INTEGER"),
        ("reactions",       "INTEGER"), ("ball_control",    "INTEGER"),
        ("composure",       "INTEGER"), ("skill_dribbling", "INTEGER"),
        ("interceptions",   "INTEGER"), ("heading",         "INTEGER"),
        ("marking",         "INTEGER"), ("standing_tackle", "INTEGER"),
        ("sliding_tackle",  "INTEGER"), ("jumping",         "INTEGER"),
        ("stamina",         "INTEGER"), ("strength",        "INTEGER"),
        ("aggression",      "INTEGER"),
        ("gk_diving",       "INTEGER"), ("gk_handling",     "INTEGER"),
        ("gk_kicking",      "INTEGER"), ("gk_positioning",  "INTEGER"),
        ("gk_reflexes",     "INTEGER"),
        ("skill_moves",     "INTEGER"), ("weak_foot",       "INTEGER"),
        ("foot",            "TEXT"),    ("height",          "INTEGER"),
        ("weight",          "INTEGER"), ("age",             "INTEGER"),
        ("alt_positions",   "TEXT"),    ("workrates",       "TEXT"),
        ("accelerate_type", "TEXT"),    ("futgg_player_id", "TEXT"),
        ("render_url",      "TEXT"),    ("bg_url_hd",       "TEXT"),
        ("nation_flag_url", "TEXT"),    ("club_logo_url",   "TEXT"),
        ("league_logo_url", "TEXT"),    ("playstyles_json",  "TEXT"),
        ("portrait_url",    "TEXT"),
        ("scraped_version", "TEXT"),    ("detail_scraped_at", "TEXT"),
    ]

    cur.execute("PRAGMA table_info(fc_players)")
    existing_cols = {row[1] for row in cur.fetchall()}

    added = 0
    for col_name, col_type in extended_columns:
        if col_name not in existing_cols:
            try:
                cur.execute(f'ALTER TABLE fc_players ADD COLUMN "{col_name}" {col_type}')
                added += 1
            except Exception as e:
                logger.error(f"Erro ao adicionar coluna {col_name}: {e}")

    conn.commit()
    conn.close()

    if added > 0:
        logger.info(f"Banco verificado. {added} colunas adicionadas.")
    else:
        logger.info("Banco verificado. Schema 100% atualizado.")


def is_player_complete(futbin_id: str, name: str) -> bool:
    """
    Verifica em 3 camadas se o jogador já está completamente processado:
      1. Banco SQLite — detail_scraped_at e card_template_url preenchidos
      2. Disco — imagem full e small existem com tamanho aceitável
    Retorna True = pode ser pulado.
    """
    name_slug = sanitize(name)
    card_filename = f"fc_player_{futbin_id}_{name_slug}.png"

    # Camada 3: Disco
    card_full = IMAGES_DIR / "cards" / "full" / card_filename
    card_small = IMAGES_DIR / "cards" / "small" / card_filename

    if not card_full.exists() or card_full.stat().st_size < 1000:
        return False
    if not card_small.exists() or card_small.stat().st_size < 100:
        return False

    # Camada 2: Banco SQLite
    conn = sqlite3.connect(str(DATABASE_FILE))
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT detail_scraped_at, card_template_url, acceleration, nation_flag_url, club_logo_url, league_logo_url, league, playstyles_json FROM fc_players WHERE futbin_id = ?",
            (str(futbin_id),)
        )
        row = cur.fetchone()
        if not row:
            return False

        detail_scraped, card_url, accel, nation_flag, club_logo, league_logo, league, playstyles_json = row
        # Jogador completo = detalhes raspados + card salvo + sub-atributos preenchidos
        if not detail_scraped or not card_url or accel is None:
            return False

        # PlayStyles fazem parte da completude. Se faltar, reprocessa só para atualizar metadados.
        if not playstyles_are_current(playstyles_json):
            return False

        # Verificar se as bandeiras/logos obrigatórios existem e são caminhos locais (/images/)
        # Se for Icons, a liga é "Icons" e não possui league_logo_url no card
        if not nation_flag or nation_flag.startswith("http"):
            return False
        if not club_logo or club_logo.startswith("http"):
            return False
        if league and str(league).lower() != "icons" and (not league_logo or league_logo.startswith("http")):
            return False

        return True
    except Exception:
        return False
    finally:
        conn.close()


def get_existing_ids_for_page(futbin_ids: List[str]) -> set:
    """Consulta quais futbin_ids já existem no banco. Retorna set de IDs existentes."""
    if not futbin_ids:
        return set()

    conn = sqlite3.connect(str(DATABASE_FILE))
    cur = conn.cursor()
    try:
        placeholders = ",".join("?" for _ in futbin_ids)
        cur.execute(
            f"SELECT futbin_id FROM fc_players WHERE futbin_id IN ({placeholders})",
            futbin_ids
        )
        return {row[0] for row in cur.fetchall()}
    except Exception:
        return set()
    finally:
        conn.close()


def upsert_player_sqlite(player_data: dict) -> bool:
    """INSERT ou UPDATE direto no SQLite (sem ORM, máxima performance)."""
    conn = sqlite3.connect(str(DATABASE_FILE))
    cur = conn.cursor()
    try:
        futbin_id = str(player_data["futbin_id"])

        cur.execute("SELECT id FROM fc_players WHERE futbin_id = ?", (futbin_id,))
        row = cur.fetchone()

        cur.execute("PRAGMA table_info(fc_players)")
        valid_cols = {r[1] for r in cur.fetchall()}

        fields = {
            "futbin_id":        futbin_id,
            "name":             player_data.get("name", "Unknown"),
            "overall":          player_data.get("overall", 0),
            "position":         player_data.get("position"),
            "nation":           player_data.get("nation"),
            "club":             player_data.get("club"),
            "league":           player_data.get("league"),
            "card_type":        player_data.get("card_type"),
            # FIX: For special cards the listing-page face_url_raw is always the BASE gold
            # face of the player (e.g. /players/p{id}.png), NOT the special card render.
            # The correct face is always the locally-downloaded render_url.
            # Priority: render_url (local, correct) > face_url (if already local path) > face_url_raw (remote fallback)
            "face_url":         (
                player_data.get("render_url") or          # locally-downloaded render (always correct)
                (player_data.get("face_url") if (player_data.get("face_url") or "").startswith("/images/") else None) or  # local path already stored
                player_data.get("face_url_raw")            # raw remote URL (fallback only)
            ),
            "bg_url_raw":       player_data.get("bg_url_raw"),
            "card_template_url": player_data.get("card_template_url"),
            "render_url":       player_data.get("render_url"),
            "portrait_url":     player_data.get("portrait_url"),
            "bg_url_hd":        player_data.get("card_template_url") or player_data.get("bg_url_hd") or player_data.get("futgg_card_image_url"),
            "nation_flag_url":  player_data.get("nation_flag_url"),
            "club_logo_url":    player_data.get("club_logo_url"),
            "league_logo_url":  player_data.get("league_logo_url"),
            "futgg_player_id":  player_data.get("futgg_player_id"),
            "playstyles_json":  player_data.get("playstyles_json"),
            "alt_positions":    player_data.get("alt_positions"),
            "workrates":        player_data.get("workrates"),
            "accelerate_type":  player_data.get("accelerate_type"),
            "foot":             player_data.get("foot"),
            "skill_moves":      player_data.get("skill_moves"),
            "weak_foot":        player_data.get("weak_foot"),
            "height":           player_data.get("height"),
            "weight":           player_data.get("weight"),
            "age":              player_data.get("age"),
            # Face stats
            "pace":             player_data.get("pace"),
            "shooting":         player_data.get("shooting"),
            "passing":          player_data.get("passing"),
            "dribbling_stat":   player_data.get("dribbling_stat"),
            "defending":        player_data.get("defending"),
            "physic":           player_data.get("physic"),
            # Sub-atributos
            "acceleration":     player_data.get("acceleration"),
            "sprint_speed":     player_data.get("sprint_speed"),
            "finishing":        player_data.get("finishing"),
            "shot_power":       player_data.get("shot_power"),
            "long_shots":       player_data.get("long_shots"),
            "volleys":          player_data.get("volleys"),
            "positioning_att":  player_data.get("positioning_att"),
            "penalties":        player_data.get("penalties"),
            "short_passing":    player_data.get("short_passing"),
            "long_passing":     player_data.get("long_passing"),
            "crossing":         player_data.get("crossing"),
            "curve":            player_data.get("curve"),
            "free_kick":        player_data.get("free_kick"),
            "vision":           player_data.get("vision"),
            "agility":          player_data.get("agility"),
            "balance":          player_data.get("balance"),
            "reactions":        player_data.get("reactions"),
            "ball_control":     player_data.get("ball_control"),
            "composure":        player_data.get("composure"),
            "skill_dribbling":  player_data.get("skill_dribbling"),
            "interceptions":    player_data.get("interceptions"),
            "heading":          player_data.get("heading"),
            "marking":          player_data.get("marking"),
            "standing_tackle":  player_data.get("standing_tackle"),
            "sliding_tackle":   player_data.get("sliding_tackle"),
            "jumping":          player_data.get("jumping"),
            "stamina":          player_data.get("stamina"),
            "strength":         player_data.get("strength"),
            "aggression":       player_data.get("aggression"),
            "gk_diving":        player_data.get("gk_diving"),
            "gk_handling":      player_data.get("gk_handling"),
            "gk_kicking":       player_data.get("gk_kicking"),
            "gk_positioning":   player_data.get("gk_positioning"),
            "gk_reflexes":      player_data.get("gk_reflexes"),
            # Auditoria
            "scraped_version":  SCRAPER_VERSION,
            "detail_scraped_at": datetime.now(UTC).isoformat() if (player_data.get("pace") or player_data.get("gk_diving")) else None,
        }

        if not row:
            fields["scraped_at"] = datetime.now(UTC).isoformat()

        db_fields = {k: v for k, v in fields.items() if k in valid_cols and v is not None}

        if row:
            set_clause = ", ".join(f'"{k}" = ?' for k in db_fields if k != "futbin_id")
            values = [db_fields[k] for k in db_fields if k != "futbin_id"]
            values.append(futbin_id)
            cur.execute(f'UPDATE fc_players SET {set_clause} WHERE futbin_id = ?', values)
        else:
            cols = ", ".join(f'"{k}"' for k in db_fields)
            placeholders = ", ".join("?" for _ in db_fields)
            values = [db_fields[k] for k in db_fields]
            cur.execute(f'INSERT INTO fc_players ({cols}) VALUES ({placeholders})', values)

        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erro no upsert de {player_data.get('name')}: {e}")
        return False
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# FASE 1: LISTAGEM DO FUTBIN
# ═══════════════════════════════════════════════════════════════════════════════

async def scrape_futbin_page_list(
    session: aiohttp.ClientSession,
    page: int,
) -> List[Dict]:
    """Raspa a lista de jogadores de uma página do Futbin."""
    url = f"{FUTBIN_BASE}/players?page={page}"

    async with FUTBIN_SEM:
        html = await fetch_html(session, url)

    if not html:
        logger.error(f"Falha ao carregar listagem da página {page}.")
        return []

    soup = BeautifulSoup(html, "lxml")
    rows = soup.select(".player-row")

    if not rows:
        logger.warning(f"Nenhum jogador encontrado na página {page}.")
        debug_path = SCRIPT_DIR / f"debug_page_{page}.html"
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(html)
        return []

    players = []
    for row in rows:
        try:
            player = _parse_player_row(row, page)
            if player and player.get("futbin_id"):
                players.append(player)
        except Exception as e:
            logger.debug(f"Erro ao parsear row na página {page}: {e}")

    return players


def _parse_player_row(row, page: int) -> Optional[Dict]:
    """Extrai dados básicos de uma linha da listagem do Futbin."""
    # ID
    card_link = (
        row.select_one("a.player-row-playercard") or
        row.select_one("a[href*='/26/player/']") or
        row.select_one("a[href*='/player/']")
    )
    if not card_link:
        return None

    href = card_link.get("href", "")
    m = re.search(r"/player/(\d+)/", href)
    if not m:
        return None
    futbin_id = m.group(1)

    # Nome
    name_el = row.select_one("a.table-player-name") or row.select_one(".table-player-info a")
    name = name_el.get_text(strip=True) if name_el else "Unknown"

    # Overall
    rating_el = (
        row.select_one(".playercard-s-26-rating") or
        row.select_one(".table-rating") or
        row.select_one(".rating")
    )
    overall = safe_int(rating_el.get_text(strip=True)) or 0 if rating_el else 0

    # Posição
    pos_el = (
        row.select_one(".playercard-s-26-pos") or
        row.select_one(".table-pos") or
        row.select_one(".position")
    )
    position = pos_el.get_text(strip=True) if pos_el else ""

    # Tipo de Card
    bg_img = (
        row.select_one("img.playercard-s-26-bg") or
        row.select_one("img[src*='/cards/tiny/']") or
        row.select_one("img[src*='/cards/small/']")
    )
    bg_url = bg_img.get("src", "") if bg_img else ""

    card_type = ""
    if bg_url:
        m_ver = re.search(r"/cards/tiny/\d+_(.+?)\.png", bg_url)
        if m_ver:
            card_type = m_ver.group(1).replace("_", " ").title()
    if not card_type:
        version_el = row.select_one(".table-player-revision, .revision")
        card_type = version_el.get_text(strip=True) if version_el else ""

    # Biografia
    club_el = row.select_one(".table-player-club img")
    club = (club_el.get("data-original-title") or club_el.get("title") or club_el.get("alt") or "").strip() if club_el else ""

    nation_el = row.select_one(".table-player-nation img")
    nation = (nation_el.get("data-original-title") or nation_el.get("title") or nation_el.get("alt") or "").strip() if nation_el else ""

    league_el = row.select_one(".table-player-league img")
    league = (league_el.get("data-original-title") or league_el.get("title") or league_el.get("alt") or "").strip() if league_el else ""

    # URL do jogador
    player_url = f"{FUTBIN_BASE}{href}" if href and not href.startswith("http") else href

    # EA Item ID (a partir da face)
    is_base_card = card_type.lower() in BASE_CARD_TYPES
    if is_base_card:
        face_el = (
            row.select_one("img[src*='/players/p']") or
            row.select_one(".playercard-s-26-img-column img") or
            row.select_one("img.playercard-26-special-img")
        )
    else:
        face_el = (
            row.select_one("img.playercard-26-special-img") or
            row.select_one("img[src*='/players/p']") or
            row.select_one(".playercard-s-26-img-column img")
        )

    face_url = ""
    ea_item_id = ""
    if face_el:
        face_url = face_el.get("data-original") or face_el.get("data-src") or face_el.get("src") or ""
        if face_url:
            m_ea = re.search(r'/players/p?(\d+)\.png', face_url)
            if m_ea:
                ea_item_id = m_ea.group(1)

    return {
        "futbin_id": futbin_id,
        "ea_item_id": ea_item_id,
        "name": name,
        "overall": overall,
        "position": position,
        "card_type": card_type,
        "nation": nation,
        "club": club,
        "league": league,
        "player_url": player_url,
        "face_url_raw": face_url,
        "bg_url_raw": bg_url,
        "page": page,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# FASE 2: DETALHES DO JOGADOR NO FUTBIN
# ═══════════════════════════════════════════════════════════════════════════════

async def scrape_futbin_player_detail(
    session: aiohttp.ClientSession,
    player_url: str,
    futbin_id: str,
    card_type: str = "",
    position: str = "",
) -> Dict:
    """Raspa detalhes completos de um jogador no Futbin."""
    if not player_url:
        return {}

    async with FUTBIN_SEM:
        html = await fetch_html(session, player_url)

    if not html:
        return {}

    soup = BeautifulSoup(html, "lxml")
    data = {}

    # ── Imagens (BG HD + Face/Render) ──
    try:
        bg_img = soup.select_one("img.playercard-26-bg")
        if bg_img:
            srcset = bg_img.get("srcset", "")
            if srcset:
                urls = [u.strip().split(" ")[0] for u in srcset.split(",")]
                data["bg_url_hd"] = urls[-1]
            else:
                data["bg_url_hd"] = bg_img.get("src", "")

        card_type_lower = (card_type or "").lower()
        is_base = card_type_lower in BASE_CARD_TYPES

        if is_base:
            face_img = (
                soup.select_one("img[src*='/players/p']") or
                soup.select_one("img.playercard-26-special-img")
            )
            portrait_img = soup.select_one("img[src*='/players/']:not([src*='/players/p'])")
            if portrait_img:
                portrait_src = portrait_img.get("data-original") or portrait_img.get("data-src") or portrait_img.get("src") or ""
                if portrait_src and "/players/" in portrait_src:
                    data["portrait_url"] = portrait_src
        else:
            face_img = (
                soup.select_one("img.playercard-26-special-img") or
                soup.select_one("img[src*='/players/p']")
            )

        if face_img:
            data["render_url"] = face_img.get("src", "")
    except Exception:
        pass

    # ── 6 Face Stats ──
    try:
        is_gk = "GK" in str(position).upper()
        if is_gk:
            stat_map = {
                "DIV": "gk_diving", "HAN": "gk_handling", "KIC": "gk_kicking",
                "REF": "gk_reflexes", "SPD": "pace", "POS": "gk_positioning"
            }
        else:
            stat_map = {
                "PAC": "pace", "SHO": "shooting", "PAS": "passing",
                "DRI": "dribbling_stat", "DEF": "defending", "PHY": "physic"
            }
        for stat_div in soup.select(".playercard-26-stats, .playercard-s-26-stats, .playercard-stats"):
            val_el = stat_div.select_one(".playercard-26-stat-number, .playercard-s-26-stat-value, .playercard-stat-number")
            lbl_el = stat_div.select_one(".playercard-26-stat-value, .playercard-s-26-stat-label, .playercard-stat-value")
            if val_el and lbl_el:
                lbl = lbl_el.get_text(strip=True).upper()
                col = stat_map.get(lbl)
                if col and col not in data:
                    val = safe_int(val_el.get_text(strip=True))
                    if val and 1 <= val <= 99:
                        data[col] = val
    except Exception:
        pass

    # ── Sub-atributos ──
    try:
        is_gk = "GK" in str(position).upper()
        sub_map = {
            "Acceleration": "acceleration", "Accel": "acceleration",
            "Sprint Speed": "sprint_speed", "Sprint Spd": "sprint_speed",
            "Finishing": "finishing", "Shot Power": "shot_power", "Shot Pwr": "shot_power",
            "Long Shots": "long_shots", "Long Shot": "long_shots",
            "Volleys": "volleys",
            "Positioning": "gk_positioning" if is_gk else "positioning_att",
            "Att. Position": "positioning_att",
            "Att Position": "positioning_att", "Att.Position": "positioning_att",
            "Penalties": "penalties", "Penalty": "penalties",
            "Short Passing": "short_passing", "Short Pass": "short_passing",
            "Long Passing": "long_passing", "Long Pass": "long_passing",
            "Crossing": "crossing", "Curve": "curve",
            "FK Accuracy": "free_kick", "Free Kick Accuracy": "free_kick",
            "FK Acc.": "free_kick", "FK Acc": "free_kick", "Free Kick": "free_kick",
            "Vision": "vision",
            "Agility": "agility", "Balance": "balance",
            "Reactions": "reactions", "Ball Control": "ball_control", "Ball Ctrl": "ball_control",
            "Composure": "composure", "Dribbling": "skill_dribbling",
            "Interceptions": "interceptions",
            "Heading Accuracy": "heading", "Heading Acc.": "heading",
            "Heading Acc": "heading", "Heading": "heading", "Head. Acc.": "heading",
            "Def Awareness": "marking", "Def. Awareness": "marking",
            "Defensive Awareness": "marking", "Marking": "marking",
            "Def Aware": "marking", "Def. Aware": "marking",
            "Standing Tackle": "standing_tackle", "Stand Tackle": "standing_tackle",
            "Stand. Tackle": "standing_tackle",
            "Sliding Tackle": "sliding_tackle", "Slide Tackle": "sliding_tackle",
            "Slide. Tackle": "sliding_tackle",
            "Jumping": "jumping", "Stamina": "stamina",
            "Strength": "strength", "Aggression": "aggression",
            "GK Diving": "gk_diving", "GK Handling": "gk_handling",
            "GK Kicking": "gk_kicking", "GK Positioning": "gk_positioning",
            "GK Reflexes": "gk_reflexes",
            "Diving": "gk_diving", "Handling": "gk_handling",
            "Kicking": "gk_kicking", "Reflexes": "gk_reflexes",
            "Speed": "pace",
        }
        for stat_row in soup.select(".player-stat-row"):
            name_el = stat_row.select_one(".player-stat-name")
            val_el = stat_row.select_one(".player-stat-value")
            if name_el and val_el:
                label = name_el.get_text(strip=True)
                col = sub_map.get(label)
                if col and col not in data:
                    val = safe_int(val_el.get_text(strip=True))
                    if val and 1 <= val <= 99:
                        data[col] = val

        # Fallback
        if not data.get("short_passing"):
            for row_el in soup.select("tr, .stat-row, .sub-stat-row, div[class*='stat']"):
                cells = row_el.find_all(["td", "span", "div"])
                if len(cells) >= 2:
                    label_text = cells[0].get_text(strip=True)
                    col = sub_map.get(label_text)
                    if col and col not in data:
                        val = safe_int(cells[-1].get_text(strip=True))
                        if val and 1 <= val <= 99:
                            data[col] = val
    except Exception:
        pass

    # ── Perfil biográfico ──
    try:
        profile_map = {
            "Weak Foot": "weak_foot", "WF": "weak_foot",
            "Skill Moves": "skill_moves", "Skills": "skill_moves", "SM": "skill_moves",
            "Foot": "foot", "Preferred Foot": "foot",
            "Height": "height", "Age": "age", "Weight": "weight",
            "Work Rates": "workrates", "Work Rate": "workrates", "WR": "workrates",
            "AcceleRATE": "accelerate_type", "Accelerate": "accelerate_type",
            "AccelType": "accelerate_type",
            "Alt Pos": "alt_positions", "Alt. Pos": "alt_positions",
            "Alternative Positions": "alt_positions",
        }
        for profile_div in soup.select(".align-center, .xs-font"):
            label_el = profile_div.select_one(".text-faded")
            if label_el:
                label = label_el.get_text(strip=True)
                col = profile_map.get(label)
                if col and col not in data:
                    value_els = [el for el in profile_div.children if el != label_el and hasattr(el, "get_text")]
                    if value_els:
                        val_text = " ".join(el.get_text(strip=True) for el in value_els).strip()
                        if col in ["weak_foot", "skill_moves"]:
                            val_text = re.sub(r"[^\d]", "", val_text)
                            data[col] = safe_int(val_text)
                        elif col == "height":
                            cm = re.search(r"(\d+)\s*cm", val_text, re.I)
                            data[col] = safe_int(cm.group(1)) if cm else val_text
                        elif col == "weight":
                            kg = re.search(r"(\d+)\s*kg", val_text, re.I)
                            data[col] = safe_int(kg.group(1)) if kg else val_text
                        elif col == "age":
                            am = re.search(r"(\d+)", val_text)
                            data[col] = safe_int(am.group(1)) if am else val_text
                        else:
                            data[col] = val_text
    except Exception:
        pass

    # ── Player Roles ──
    try:
        roles = []
        for role_div in soup.select(".xxs-row.align-center"):
            pos_el = role_div.select_one(".xs-font.uppercase.text-faded")
            role_el = role_div.select_one("a[href*='/roles']")
            if pos_el and role_el:
                pos = pos_el.get_text(strip=True)
                role_text = role_el.get_text(" ", strip=True)
                role_text = re.sub(r"\s+", " ", role_text).strip()
                roles.append(f"{pos}: {role_text}")
        if roles:
            data["workrates"] = " | ".join(roles)
    except Exception:
        pass

    # ── Playstyles ──
    try:
        playstyles = extract_futbin_playstyles(soup)
        if playstyles:
            data["playstyles_json"] = json.dumps(playstyles, ensure_ascii=False)
    except Exception:
        pass

    # ── Emblemas (URLs) ──
    try:
        nation_img = (
            soup.select_one("img.nation") or
            soup.select_one("img[src*='/nation/'], img[src*='nations/'], img[src*='nation_flags/'], img[src*='/flags/']")
        )
        if nation_img:
            data["nation_flag_url"] = nation_img.get("src", "")

        club_img = (
            soup.select_one("img.playercard-26-club") or
            soup.select_one("img[src*='/clubs/'], img[src*='/club/']")
        )
        if club_img:
            data["club_logo_url"] = club_img.get("src", "")

        league_img = (
            soup.select_one("img.playercard-26-league") or
            soup.select_one("img[src*='/leagues/'], img[src*='/league/']")
        )
        if league_img:
            data["league_logo_url"] = league_img.get("src", "")
    except Exception:
        pass

    return data


# ═══════════════════════════════════════════════════════════════════════════════
# FASE 3: IMAGEM HD DO CARD (FUTGG)
# ═══════════════════════════════════════════════════════════════════════════════

async def scrape_futgg_card_image(
    session: aiohttp.ClientSession,
    player_name: str,
    ea_item_id: str,
) -> Dict:
    """Busca imagem HD do card no FutGG."""
    result = {}
    if not ea_item_id:
        return result

    url = f"{FUTGG_BASE}/players/{ea_item_id}/"

    async with FUTGG_SEM:
        html = await fetch_html(session, url)

    if not html:
        return result

    soup = BeautifulSoup(html, "lxml")
    card_img = None
    target_pattern = f"26-{ea_item_id}"

    for img in soup.select("img[src*='futgg-player-item-card']"):
        src = img.get("src", "")
        if target_pattern in src:
            card_img = img
            break

    if not card_img:
        for img in soup.select("img[src*='futgg-player-item-card']"):
            src = img.get("src", "")
            if f"-{ea_item_id}" in src:
                card_img = img
                break

    if not card_img:
        card_img = soup.select_one("img[src*='/2026/futgg-player-item-card/']")

    if card_img:
        img_url = card_img.get("src", "")
        if img_url:
            if "cdn-cgi/image" in img_url:
                img_url = re.sub(r"cdn-cgi/image/[^/]*/", "", img_url)
            result["futgg_card_image_url"] = img_url

    render_img = (
        soup.select_one("img[src*='/players/p']") or
        soup.select_one("img[src*='/player-renders/']") or
        soup.select_one("img[src*='/renders/']")
    )
    if render_img:
        r_url = render_img.get("src", "")
        if "cdn-cgi/image" in r_url:
            r_url = re.sub(r"cdn-cgi/image/[^/]*/", "", r_url)
        result["futgg_render_url"] = r_url

    try:
        playstyles = extract_futgg_playstyles(soup)
        if playstyles:
            result["futgg_playstyles_json"] = json.dumps(playstyles, ensure_ascii=False)
    except Exception:
        pass

    result["futgg_player_id"] = ea_item_id
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# FASE 4: DOWNLOAD DE IMAGENS
# ═══════════════════════════════════════════════════════════════════════════════

async def download_binary_file(
    session: aiohttp.ClientSession,
    url: str,
    dest_path: Path,
) -> bool:
    """Baixa arquivo binário respeitando semáforos."""
    if not url:
        return False

    if dest_path.exists() and dest_path.stat().st_size > 100:
        return True

    clean_url = url if "futbin.com" in url else (url.split("?")[0] if "?" in url else url)
    if clean_url.startswith("//"):
        clean_url = "https:" + clean_url

    async with IMG_SEM:
        data = await fetch_binary(session, clean_url)

    if data and len(data) > 100:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(dest_path, "wb") as f:
            await f.write(data)
        return True

    return False


async def download_and_process_images(
    session: aiohttp.ClientSession,
    player_data: Dict,
    futbin_id: str,
) -> Dict:
    """Pipeline de download e pós-processamento de todas as imagens do jogador."""
    paths = {}
    name_slug = sanitize(player_data.get("name", "unknown"))

    # 1. Card Completo HD
    card_url = (
        player_data.get("futgg_card_image_url") or
        player_data.get("bg_url_hd") or
        player_data.get("bg_url_raw")
    )
    if card_url:
        card_filename = f"fc_player_{futbin_id}_{name_slug}.png"
        card_path = IMAGES_DIR / "cards" / "full" / card_filename

        if await download_binary_file(session, card_url, card_path):
            # FASE 5: Pós-processamento — remover fundo branco
            await remove_white_background(card_path)

            paths["card_template_url"] = f"/images/cards/full/{card_filename}"
            paths["bg_url_hd"] = f"/images/cards/full/{card_filename}"

            # Gerar miniatura cropada premium
            small_path = IMAGES_DIR / "cards" / "small" / card_filename
            create_premium_thumbnail(str(card_path), str(small_path))

    # 2. Render/Face
    render_url = (
        player_data.get("futgg_render_url") or
        player_data.get("render_url") or
        player_data.get("face_url_raw")
    )
    if render_url:
        render_filename = f"render_{futbin_id}_{name_slug}.png"
        render_path = IMAGES_DIR / "cards" / "renders" / render_filename
        if await download_binary_file(session, render_url, render_path):
            paths["render_url"] = f"/images/cards/renders/{render_filename}"
            paths["face_url"] = f"/images/cards/renders/{render_filename}"

    # 3. Escudo do Clube
    club_url = player_data.get("club_logo_url")
    if club_url:
        club_slug = sanitize(player_data.get("club", "unknown"))
        club_filename = f"club_{club_slug}.png"
        club_path = IMAGES_DIR / "cards" / "clubs" / club_filename
        if await download_binary_file(session, club_url, club_path):
            paths["club_logo_url"] = f"/images/cards/clubs/{club_filename}"

    # 4. Bandeira da Nação
    nation_url = player_data.get("nation_flag_url")
    if nation_url:
        if "nation_unknown" in str(nation_url):
            nation_url = None
            
    if nation_url:
        nation_slug = sanitize(player_data.get("nation", "unknown"))
        nation_filename = f"nation_{nation_slug}.png"
        nation_path = IMAGES_DIR / "cards" / "nations" / nation_filename
        if await download_binary_file(session, nation_url, nation_path):
            paths["nation_flag_url"] = f"/images/cards/nations/{nation_filename}"

    # 5. Logo da Liga
    league_url = player_data.get("league_logo_url")
    if league_url:
        league_slug = sanitize(player_data.get("league", "unknown"))
        league_filename = f"league_{league_slug}.png"
        league_path = IMAGES_DIR / "cards" / "leagues" / league_filename
        if await download_binary_file(session, league_url, league_path):
            paths["league_logo_url"] = f"/images/cards/leagues/{league_filename}"

    return paths


# ═══════════════════════════════════════════════════════════════════════════════
# FASE 5: PÓS-PROCESSAMENTO (ImageMagick + Pillow)
# ═══════════════════════════════════════════════════════════════════════════════

async def remove_white_background(image_path: Path) -> bool:
    """Remove fundo branco dos cantos via ImageMagick (floodfill 4 cantos)."""
    if not image_path.exists():
        return False

    fd_out, temp_out = tempfile.mkstemp(suffix=".png")
    os.close(fd_out)

    try:
        cmd = [
            "magick",
            str(image_path),
            "-fuzz", "10%",
            "-fill", "none",
            "-draw", "color 0,0 floodfill",
            "-gravity", "NorthEast", "-draw", "color 0,0 floodfill",
            "-gravity", "SouthWest", "-draw", "color 0,0 floodfill",
            "-gravity", "SouthEast", "-draw", "color 0,0 floodfill",
            temp_out
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await process.communicate()

        if process.returncode != 0:
            logger.debug(f"ImageMagick falhou em {image_path.name}: {stderr.decode()[:100]}")
            if os.path.exists(temp_out):
                os.remove(temp_out)
            return False

        shutil.move(temp_out, str(image_path))
        return True
    except FileNotFoundError:
        logger.warning("ImageMagick ('magick') não encontrado. Pulando remoção de fundo branco.")
        if os.path.exists(temp_out):
            os.remove(temp_out)
        return False
    except Exception as e:
        logger.error(f"Erro ao remover fundo: {e}")
        if os.path.exists(temp_out):
            try: os.remove(temp_out)
            except: pass
        return False


def create_premium_thumbnail(input_path: str, output_path: str) -> bool:
    """Gera miniatura cropada premium 150x169px a partir do card HD."""
    try:
        from PIL import Image
        dest = Path(output_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        with Image.open(input_path) as img:
            img_temp = img.resize((504, 698), Image.Resampling.LANCZOS)
            topo = img_temp.crop((0, 0, 504, 422))
            base = img_temp.crop((0, 558, 504, 698))

            small_canvas = Image.new("RGBA", (504, 562), (0, 0, 0, 0))
            small_canvas.paste(topo, (0, 0))
            small_canvas.paste(base, (0, 422))

            resized = small_canvas.resize((150, 169), Image.Resampling.LANCZOS)
            resized.save(dest, "PNG")
            return True
    except Exception as e:
        logger.error(f"Erro ao criar miniatura: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# ORQUESTRADOR: PROCESSAMENTO DE UM JOGADOR
# ═══════════════════════════════════════════════════════════════════════════════

async def process_single_player(
    session_futbin: aiohttp.ClientSession,
    session_futgg: aiohttp.ClientSession,
    player_basic: Dict,
) -> bool:
    """
    Pipeline completo de um jogador:
    F2: Detalhes Futbin + F3: Imagem FutGG (paralelo)
    F4: Download de imagens
    F5: Pós-processamento
    Persistência no banco
    """
    # Recuperar dados básicos faltantes do banco de dados (evita perdas em buscas de colunas parciais)
    db_path = PROJECT_ROOT / "database" / "help_dmes.db"
    if not db_path.exists():
        db_path = PROJECT_ROOT / "help_dmes.db"
        
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT nation, club, league, position, ea_id FROM fc_players WHERE futbin_id = ?", (str(player_basic["futbin_id"]),))
            db_row = cursor.fetchone()
            if db_row:
                for col in ["nation", "club", "league", "position"]:
                    if not player_basic.get(col) and db_row[col]:
                        player_basic[col] = db_row[col]
                if not player_basic.get("ea_item_id") and db_row["ea_id"]:
                    player_basic["ea_item_id"] = db_row["ea_id"]
            conn.close()
        except Exception as e:
            logger.debug(f"Erro ao recuperar dados básicos adicionais do banco: {e}")

    futbin_id = player_basic["futbin_id"]
    name = player_basic["name"]
    overall = player_basic["overall"]
    player_url = player_basic.get("player_url", "")
    ea_item_id = player_basic.get("ea_item_id", "")

    logger.info(f"  ➤ Processando: {name} (OVR:{overall}, ID:{futbin_id})")

    # F2 + F3 em paralelo
    tasks = [
        scrape_futbin_player_detail(session_futbin, player_url, futbin_id, card_type=player_basic.get("card_type", ""), position=player_basic.get("position", "")),
        scrape_futgg_card_image(session_futgg, name, ea_item_id),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    futbin_detail = results[0] if not isinstance(results[0], Exception) else {}
    futgg_data = results[1] if not isinstance(results[1], Exception) else {}

    if isinstance(results[0], Exception):
        logger.debug(f"Futbin detalhe falhou para {name}: {results[0]}")
    if isinstance(results[1], Exception):
        logger.debug(f"FutGG falhou para {name}: {results[1]}")

    merged_playstyles = merge_playstyle_sources(
        futbin_detail.get("playstyles_json"),
        futgg_data.get("futgg_playstyles_json"),
    )

    # Mesclar dados
    player_combined = {**player_basic, **futbin_detail, **futgg_data}
    if merged_playstyles:
        player_combined["playstyles_json"] = json.dumps(merged_playstyles, ensure_ascii=False)

    # F4 + F5: Download e pós-processamento
    image_paths = await download_and_process_images(session_futbin, player_combined, futbin_id)
    player_combined.update(image_paths)

    # Persistir no banco
    success = upsert_player_sqlite(player_combined)
    if success:
        has_card = bool(player_combined.get("card_template_url"))
        has_stats = bool(player_combined.get("pace"))
        has_subs = bool(player_combined.get("acceleration"))
        logger.info(
            f"  ✅ {name} salvo | "
            f"Card: {'✓' if has_card else '✗'} | "
            f"Stats: {'✓' if has_stats else '✗'} | "
            f"Subs: {'✓' if has_subs else '✗'}"
        )
        return True
    else:
        logger.error(f"  ❌ Erro ao salvar {name}.")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    parser = argparse.ArgumentParser(
        description="Help DMEs — Scrape Master (Orquestrador Unificado de Coleta de Jogadores EA FC 26)"
    )
    parser.add_argument("--pages", default="1-750",
                        help="Intervalo de páginas. Ex: '1-100', '50-200'. Default: 1-750")
    parser.add_argument("--test", action="store_true",
                        help="Modo teste: apenas 5 jogadores por página.")
    parser.add_argument("--force", action="store_true",
                        help="Ignora skip, reprocessa todos os jogadores.")
    parser.add_argument("--delay-mult", type=float, default=1.0,
                        help="Multiplicador de delay anti-bot (default: 1.0).")
    args = parser.parse_args()

    # Parsear intervalo de páginas
    try:
        m = re.match(r"(\d+)[-–](\d+)", args.pages)
        if m:
            start_page, end_page = int(m.group(1)), int(m.group(2))
        else:
            n = int(args.pages)
            start_page, end_page = n, n
    except Exception:
        logger.error(f"Formato inválido: '{args.pages}'. Use '1-750' ou '12'.")
        sys.exit(1)

    print("\n" + "═"*80)
    print("   🚀 HELP DMEs — SCRAPE MASTER v3.0 (Orquestrador Unificado)")
    print(f"   Páginas: {start_page} a {end_page} | Modo: {'TESTE (5/pág)' if args.test else 'COMPLETO'}")
    print(f"   Force: {'SIM' if args.force else 'NÃO (skip inteligente ativo)'}")
    print(f"   Banco: {DATABASE_FILE}")
    print("═"*80 + "\n")

    # Verificar e migrar banco
    verify_and_migrate_db()

    # Carregar progresso
    state = load_state()
    completed_pages = set(state.get("completed_pages", []))

    # Sessões HTTP
    session_futbin = create_session()
    session_futgg  = create_session()

    total_saved = 0
    total_skipped = 0
    total_failed = 0
    total_new_detected = 0

    try:
        for page in range(start_page, end_page + 1):

            print(f"\n{'─'*70}")
            print(f"  📄 PÁGINA {page}/{end_page}")
            print(f"{'─'*70}")

            # ── F1: Raspar listagem (sempre — é 1 request, rápido) ──
            players_basic = await scrape_futbin_page_list(session_futbin, page)
            if not players_basic:
                logger.warning(f"Página {page} vazia.")
                if page > 100:
                    logger.info("Provavelmente fim do catálogo. Encerrando.")
                    break
                continue

            if args.test:
                players_basic = players_basic[:5]
                logger.info(f"[TESTE] Limitado a 5 jogadores na página {page}")

            # ── Detecção de novidades: comparar IDs vs banco ──
            page_futbin_ids = [p["futbin_id"] for p in players_basic]
            existing_ids = get_existing_ids_for_page(page_futbin_ids)

            new_ids = set(page_futbin_ids) - existing_ids
            if new_ids:
                total_new_detected += len(new_ids)
                logger.info(f"  🆕 {len(new_ids)} jogador(es) novo(s) detectado(s) nesta página!")

            # ── Filtrar jogadores que precisam ser processados ──
            to_process = []
            page_skipped = 0

            for player in players_basic:
                fid = player["futbin_id"]

                if args.force:
                    to_process.append(player)
                    continue

                # Jogador novo (não existe no banco)
                if fid in new_ids:
                    to_process.append(player)
                    continue

                # Jogador existe — verificar se está completo (3 camadas)
                if is_player_complete(fid, player["name"]):
                    page_skipped += 1
                    total_skipped += 1
                else:
                    # Existe mas incompleto (falta sub-atributos, imagens, etc.)
                    to_process.append(player)

            if not to_process:
                print(f"  ✅ Página {page} — todos os {len(players_basic)} jogadores já completos. [PULADA]")
                if page not in completed_pages:
                    completed_pages.add(page)
                    state["completed_pages"] = sorted(list(completed_pages))
                    save_state(state)
                continue

            print(f"  👥 {len(players_basic)} na listagem | {page_skipped} pulados | {len(to_process)} a processar")

            # ── Processar jogadores pendentes ──
            page_saved = 0
            page_failed = 0

            for i, player in enumerate(to_process, 1):
                print(f"\n  [{i}/{len(to_process)}] ", end="", flush=True)

                try:
                    success = await process_single_player(session_futbin, session_futgg, player)
                    if success:
                        page_saved += 1
                        total_saved += 1
                    else:
                        page_failed += 1
                        total_failed += 1
                        state["failed_players"].append({
                            "futbin_id": player["futbin_id"],
                            "name": player["name"],
                            "page": page,
                            "reason": "db_save_failure",
                            "at": datetime.now(UTC).isoformat(),
                        })
                except Exception as e:
                    logger.error(f"Erro crítico em {player['name']}: {e}")
                    page_failed += 1
                    total_failed += 1
                    state["failed_players"].append({
                        "futbin_id": player["futbin_id"],
                        "name": player["name"],
                        "page": page,
                        "reason": str(e)[:200],
                        "at": datetime.now(UTC).isoformat(),
                    })

                # Delay anti-bot entre jogadores
                base_delay = 3.0 * args.delay_mult
                delay = max(1.5, min(8.0, random.gauss(base_delay, 0.8)))
                await asyncio.sleep(delay)

            # Registrar página como concluída
            if page_failed == 0:
                completed_pages.add(page)
                state["completed_pages"] = sorted(list(completed_pages))
                logger.info(f"✅ Página {page}: {page_saved} salvos, {page_skipped} pulados.")
            else:
                logger.warning(f"⚠ Página {page}: {page_failed} falhas. Será tentada novamente.")

            state["last_page_processed"] = page
            save_state(state)

            # Delay entre páginas
            if page < end_page:
                page_delay = (8.0 + random.uniform(2, 6)) * args.delay_mult
                logger.info(f"Aguardando {page_delay:.1f}s antes da próxima página...")
                await asyncio.sleep(page_delay)

    finally:
        await session_futbin.close()
        await session_futgg.close()

    print("\n" + "═"*80)
    print("   🏁 SCRAPE MASTER — CONCLUÍDO!")
    print(f"   Salvos/Atualizados: {total_saved}")
    print(f"   Pulados (já completos): {total_skipped}")
    print(f"   Novos detectados: {total_new_detected}")
    print(f"   Falhas: {total_failed}")
    print(f"   Banco: {DATABASE_FILE}")
    print("═"*80 + "\n")


# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrompido pelo usuário (Ctrl+C).")
        print("O progresso foi salvo em scrape_master_state.json.")
        print("Ao iniciar novamente, o sistema retomará de onde parou.\n")
        sys.exit(130)
