"""
Help DMEs — Scraper de Jogadores v2 (Anti-Bot + Futbin + FutGG)
================================================================
Scraper completo de cards de jogadores usando:
  - Futbin: listagem + stats detalhados por jogador
  - FutGG: imagem HD do card completo (template + render)

Técnicas anti-bot:
  - Pool de 25+ User-Agents reais (rotativo)
  - Headers completos sec-ch-ua, sec-fetch-*, Accept-Encoding
  - Delays gaussianos entre requests (µ=3.2s, σ=0.9s)
  - Cookie jar persistente por sessão
  - Back-off exponencial em 429/403/503
  - Rate limiting por domínio

Modo de uso:
    cd "/home/gambeta/Documentos/Socorro DMEs/Socorro DMEs"
    source backend/.venv/bin/activate
    python backend/scripts/scrape_players_v2.py --pages 1-3 [--test]

Flags:
    --pages   Intervalo de páginas (ex: "1-3" ou "5-10"). Default: 1-3
    --test    Modo debug: processa apenas 5 jogadores por página
    --reset   Limpa dados antes de iniciar (chama reset_scrape_data.py)
"""

import asyncio
import json
import logging
import re
import sys
import argparse
import unicodedata
from pathlib import Path
from datetime import datetime, UTC
from typing import Optional, Dict, List, Tuple

import aiohttp
import aiofiles
from bs4 import BeautifulSoup

# ── Configurar paths ──────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.database import async_session_factory, DATABASE_FILE
from backend.services.anti_bot import fetch_html, fetch_binary, create_session, reset_domain_state
from backend.services.card_renderer import CardRendererClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(BASE_DIR / "scripts" / "scrape_v2.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger("scraper_v2")

# ── Constantes ────────────────────────────────────────────────────────────────

FUTBIN_BASE    = "https://www.futbin.com"
FUTGG_BASE     = "https://www.fut.gg"
STATE_FILE     = BASE_DIR / "scripts" / "scraper_state.json"
IMAGES_DIR     = PROJECT_ROOT / "images"

# Semáforos de concorrência — baixo para simular usuário humano
FUTBIN_SEM = asyncio.Semaphore(2)
FUTGG_SEM  = asyncio.Semaphore(2)
IMG_SEM    = asyncio.Semaphore(4)

# Versão do scraper — para tracking de qualidade
SCRAPER_VERSION = "v2.0"


# ── State management ──────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_page": 0, "processed_bg_cache": {}, "version": SCRAPER_VERSION}


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ── Helpers ───────────────────────────────────────────────────────────────────

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
    """Converte para int, ignorando erros."""
    try:
        return int(str(val).strip())
    except Exception:
        return None


async def download_image(
    session: aiohttp.ClientSession,
    url: str,
    dest_path: Path,
) -> bool:
    """
    Baixa uma imagem e salva em dest_path.
    Retorna True se sucesso.
    """
    if not url:
        return False
    
    # Se já existe com tamanho razoável, pular
    if dest_path.exists() and dest_path.stat().st_size > 200:
        return True
    
    # Limpar URL (preservando query string/assinatura para o Futbin para evitar sig_invalid)
    if "futbin.com" in url:
        clean_url = url
    else:
        clean_url = url.split("?")[0] if "?" in url else url
    
    if clean_url.startswith("//"):
        clean_url = "https:" + clean_url
    
    async with IMG_SEM:
        data = await fetch_binary(session, clean_url)
    
    if data and len(data) > 200:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(dest_path, "wb") as f:
            await f.write(data)
        return True
    
    return False


# ── Fase 1: Listar jogadores da página do Futbin ──────────────────────────────

async def scrape_futbin_player_list(
    session: aiohttp.ClientSession,
    page: int,
) -> List[Dict]:
    """
    Raspa a página de listagem de jogadores do Futbin.
    Retorna lista de dicts com dados básicos de cada jogador.
    """
    url = f"{FUTBIN_BASE}/players?page={page}"
    logger.info(f"[Futbin] Raspando listagem — página {page}...")
    
    async with FUTBIN_SEM:
        html = await fetch_html(session, url)
    
    if not html:
        logger.error(f"[Futbin] Falha ao obter página {page}")
        return []
    
    soup = BeautifulSoup(html, "lxml")
    
    # Seletor verificado: .player-row retorna 30 jogadores por página
    rows = soup.select(".player-row")
    
    if not rows:
        logger.warning(f"[Futbin] Nenhum jogador encontrado na página {page}")
        # Salvar HTML para debug
        debug_path = BASE_DIR / "scripts" / f"debug_page_{page}.html"
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"[Futbin] HTML salvo em {debug_path} para debug")
        return []

    
    players = []
    for row in rows:
        try:
            player = _parse_player_row(row, page)
            if player and player.get("futbin_id"):
                players.append(player)
        except Exception as e:
            logger.debug(f"[Futbin] Erro ao parsear row: {e}")
    
    logger.info(f"[Futbin] Página {page}: {len(players)} jogadores encontrados")
    return players


def _parse_player_row(row, page: int) -> Optional[Dict]:
    """Extrai dados básicos de uma linha da listagem do Futbin."""
    
    # ── ID do Futbin ──
    futbin_id = None
    
    # Seletor principal: link do card do jogador
    card_link = (
        row.select_one("a.player-row-playercard") or
        row.select_one("a[href*='/26/player/']") or
        row.select_one("a[href*='/player/']")
    )
    if card_link:
        href = card_link.get("href", "")
        m = re.search(r"/player/(\d+)/", href)
        if m:
            futbin_id = m.group(1)
    
    if not futbin_id:
        return None
    
    # ── Nome ──
    name_el = (
        row.select_one("a.table-player-name") or
        row.select_one(".table-player-info a")
    )
    name = name_el.get_text(strip=True) if name_el else "Unknown"
    
    # ── Overall (rating está na mini card lateral) ──
    rating_el = (
        row.select_one(".playercard-s-26-rating") or
        row.select_one(".table-rating") or
        row.select_one(".rating")
    )
    overall = safe_int(rating_el.get_text(strip=True)) or 0 if rating_el else 0
    
    # ── Posição ──
    # Futbin exibe posição no card lateral
    pos_el = (
        row.select_one(".playercard-s-26-pos") or
        row.select_one(".table-pos") or
        row.select_one(".position")
    )
    position = pos_el.get_text(strip=True) if pos_el else ""
    
    # ── Versão/Tipo do Card ──
    # Nome da versão é extraído da URL do background do card
    bg_img = (
        row.select_one("img.playercard-s-26-bg") or
        row.select_one("img[src*='/cards/tiny/']") or
        row.select_one("img[src*='/cards/small/']")
    )
    bg_url = bg_img.get("src", "") if bg_img else ""
    
    # Extrair tipo do card da URL do background
    version = ""
    if bg_url:
        version_match = re.search(r"/cards/tiny/\d+_(.+?)\.png", bg_url)
        if version_match:
            version = version_match.group(1).replace("_", " ").title()
    
    # Fallback: coluna de versão direta
    if not version:
        version_el = row.select_one(".table-player-revision, .revision")
        version = version_el.get_text(strip=True) if version_el else ""
    
    # ── Clube, Nação, Liga ──
    club_el = row.select_one(".table-player-club img")
    club = ""
    if club_el:
        club = (
            club_el.get("data-original-title") or
            club_el.get("title") or
            club_el.get("alt") or ""
        ).strip()
    
    nation_el = row.select_one(".table-player-nation img")
    nation = ""
    if nation_el:
        nation = (
            nation_el.get("data-original-title") or
            nation_el.get("title") or
            nation_el.get("alt") or ""
        ).strip()
    
    league_el = row.select_one(".table-player-league img")
    league = ""
    if league_el:
        league = (
            league_el.get("data-original-title") or
            league_el.get("title") or
            league_el.get("alt") or ""
        ).strip()
    
    # ── URLs ──
    href = card_link.get("href", "") if card_link else ""
    player_url = f"{FUTBIN_BASE}{href}" if href and not href.startswith("http") else href
    
    # ── Face/Render do jogador (pequeno, da listagem) ──
    face_el = (
        row.select_one("img.playercard-26-special-img") or
        row.select_one("img[src*='/players/p']") or
        row.select_one(".playercard-s-26-img-column img")
    )
    face_url = ""
    ea_item_id = ""
    if face_el:
        face_url = (
            face_el.get("data-original") or
            face_el.get("data-src") or
            face_el.get("src") or ""
        )
        # Tentar upscale da URL para maior resolução
        if face_url:
            # Preservar assinatura para evitar sig_invalid
            # Extrair EA_ITEM_ID da face_url (ex: p100894739.png -> 100894739)
            m_ea = re.search(r'/players/p?(\d+)\.png', face_url)
            if m_ea:
                ea_item_id = m_ea.group(1)
    
    return {
        "futbin_id": futbin_id,
        "ea_item_id": ea_item_id,
        "name": name,
        "overall": overall,
        "position": position,
        "card_type": version,
        "nation": nation,
        "club": club,
        "league": league,
        "player_url": player_url,
        "face_url_raw": face_url,
        "bg_url_raw": bg_url,
        "page": page,
    }



# ── Fase 2: Detalhe completo do jogador no Futbin ────────────────────────────

async def scrape_futbin_player_detail(
    session: aiohttp.ClientSession,
    player_url: str,
    futbin_id: str,
) -> Dict:
    """
    Raspa a página de detalhe de um jogador no Futbin.
    Extrai stats completos, sub-atributos, playstyles, roles, perfil básico.
    """
    if not player_url:
        return {}
    
    logger.debug(f"[Futbin] Detalhes do jogador {futbin_id}: {player_url[:70]}")
    
    async with FUTBIN_SEM:
        html = await fetch_html(session, player_url)
    
    if not html:
        return {}
    
    soup = BeautifulSoup(html, "lxml")
    data = {}
    
    # ── BG do card e Face do jogador ─────────────────────────────────────────
    try:
        bg_img = soup.select_one("img.playercard-s-26-bg")
        if bg_img:
            bg_src = bg_img.get("src", "")
            # Preservar assinatura para evitar sig_invalid
            data["bg_url_hd"] = bg_src
        
        face_img = soup.select_one("img.playercard-26-special-img")
        if face_img:
            face_src = face_img.get("src", "")
            # Preservar assinatura para evitar sig_invalid
            data["render_url"] = face_src
    
    except Exception as e:
        logger.debug(f"[Futbin] Erro ao extrair imagens {futbin_id}: {e}")
    
    # ── 6 Face Stats (PAC, SHO, PAS, DRI, DEF, PHY) ──────────────────────────
    try:
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
                if col:
                    val = safe_int(val_el.get_text(strip=True))
                    if val and 1 <= val <= 99:
                        data[col] = val
    
    except Exception as e:
        logger.debug(f"[Futbin] Erro ao extrair face stats {futbin_id}: {e}")
    
    # ── Sub-atributos ──────────────────────────────────────────────────────────
    try:
        sub_map = {
            "Acceleration": "acceleration", "Sprint Speed": "sprint_speed",
            "Finishing": "finishing", "Shot Power": "shot_power",
            "Long Shots": "long_shots", "Volleys": "volleys",
            "Positioning": "positioning_att", "Penalties": "penalties",
            "Short Passing": "short_passing", "Long Passing": "long_passing",
            "Crossing": "crossing", "Curve": "curve",
            "FK Accuracy": "free_kick", "Free Kick Accuracy": "free_kick",
            "Vision": "vision",
            "Agility": "agility", "Balance": "balance",
            "Reactions": "reactions", "Ball Control": "ball_control",
            "Composure": "composure", "Dribbling": "skill_dribbling",
            "Interceptions": "interceptions", "Heading Accuracy": "heading",
            "Heading": "heading", "Def Awareness": "marking",
            "Defensive Awareness": "marking", "Marking": "marking",
            "Standing Tackle": "standing_tackle", "Sliding Tackle": "sliding_tackle",
            "Jumping": "jumping", "Stamina": "stamina",
            "Strength": "strength", "Aggression": "aggression",
            "GK Diving": "gk_diving", "GK Handling": "gk_handling",
            "GK Kicking": "gk_kicking", "GK Positioning": "gk_positioning",
            "GK Reflexes": "gk_reflexes",
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
    
    except Exception as e:
        logger.debug(f"[Futbin] Erro ao extrair sub-stats {futbin_id}: {e}")
    
    # ── Perfil básico (Altura, Peso, Idade, Pé, Pé Fraco, Fintas, AcceleRATE) ──
    try:
        profile_map = {
            "Weak Foot": "weak_foot",
            "Skill Moves": "skill_moves",
            "Foot": "foot",
            "Height": "height",
            "Age": "age",
            "Weight": "weight",
            "Work Rates": "workrates",
            "Work Rate": "workrates",
            "AcceleRATE": "accelerate_type",
            "Accelerate": "accelerate_type",
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
                            cm_match = re.search(r"(\d+)\s*cm", val_text, re.IGNORECASE)
                            if cm_match:
                                data[col] = safe_int(cm_match.group(1))
                            else:
                                data[col] = val_text
                        elif col == "weight":
                            kg_match = re.search(r"(\d+)\s*kg", val_text, re.IGNORECASE)
                            if kg_match:
                                data[col] = safe_int(kg_match.group(1))
                            else:
                                data[col] = val_text
                        elif col == "age":
                            age_match = re.search(r"(\d+)", val_text)
                            if age_match:
                                data[col] = safe_int(age_match.group(1))
                            else:
                                data[col] = val_text
                        else:
                            data[col] = val_text
                            
    except Exception as e:
        logger.debug(f"[Futbin] Erro ao extrair perfil básico {futbin_id}: {e}")
        
    # ── Player Roles (FC 26 - mapeado na coluna 'workrates') ──────────────────
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
            
    except Exception as e:
        logger.debug(f"[Futbin] Erro ao extrair player roles {futbin_id}: {e}")
        
    # ── Playstyles ───────────────────────────────────────────────────────────
    try:
        playstyles = []
        for anchor in soup.select("a[href*='/playstyles/']"):
            classes = anchor.get("class", [])
            if "active" in classes:
                name_el = anchor.select_one(".slim-font, div")
                if name_el:
                    name = name_el.get_text(strip=True)
                    is_plus = "psplus" in classes
                    img_el = anchor.select_one("img")
                    src = img_el.get("src", "") if img_el else ""
                    playstyles.append({"name": name, "is_plus": is_plus, "icon_url": src})
        
        if playstyles:
            data["playstyles_json"] = json.dumps(playstyles, ensure_ascii=False)
            
    except Exception as e:
        logger.debug(f"[Futbin] Erro ao extrair playstyles {futbin_id}: {e}")
        
    # ── URLs de Clube, Nação, Liga ────────────────────────────────────────────
    try:
        nation_img = soup.select_one(
            "img[src*='/nation/'], img[src*='nations/'], "
            "img[src*='nation_flags/'], img[src*='/flags/']"
        )
        if nation_img:
            # Preservar assinatura para evitar sig_invalid
            data["nation_flag_url"] = nation_img.get("src", "")
        
        club_img = soup.select_one("img[src*='/clubs/']")
        if club_img:
            # Preservar assinatura para evitar sig_invalid
            data["club_logo_url"] = club_img.get("src", "")
        
        league_img = soup.select_one("img[src*='/leagues/']")
        if league_img:
            # Preservar assinatura para evitar sig_invalid
            data["league_logo_url"] = league_img.get("src", "")
            
    except Exception as e:
        logger.debug(f"[Futbin] Erro ao extrair emblemas {futbin_id}: {e}")
        
    return data


async def scrape_futgg_card_image(
    session: aiohttp.ClientSession,
    player_name: str,
    overall: int,
    futbin_id: str,
    ea_item_id: str = "",
) -> Dict:
    """
    Busca a imagem HD consolidada do card de um jogador no FutGG usando ea_item_id.
    """
    result = {}
    if not ea_item_id:
        logger.warning(f"[FutGG] ea_item_id vazio para {player_name}. Não é possível buscar imagem direta no FutGG.")
        return result
        
    url = f"{FUTGG_BASE}/players/{ea_item_id}/"
    logger.info(f"[FutGG] Acessando página do jogador por EA ID: {url}")
    
    async with FUTGG_SEM:
        html = await fetch_html(session, url)
        
    if not html:
        logger.warning(f"[FutGG] Falha ao acessar página do jogador para {player_name} (EA ID: {ea_item_id})")
        return result
        
    soup = BeautifulSoup(html, "lxml")
    
    card_img = None
    target_pattern = f"26-{ea_item_id}"
    
    for img in soup.select("img[src*='futgg-player-item-card']"):
        src = img.get("src", "")
        if target_pattern in src:
            card_img = img
            break
            
    # Fallback 1: se não encontrar com ano 26, tentar com qualquer ano
    if not card_img:
        for img in soup.select("img[src*='futgg-player-item-card']"):
            src = img.get("src", "")
            if f"-{ea_item_id}" in src:
                card_img = img
                break
                
    # Fallback 2: se não encontrar por ID exato, pegar o primeiro do FC 26
    if not card_img:
        card_img = soup.select_one("img[src*='/2026/futgg-player-item-card/']")
        
    if card_img:
        img_url = card_img.get("src", "")
        if img_url:
            if "cdn-cgi/image" in img_url:
                img_url = re.sub(r"cdn-cgi/image/[^/]*/", "", img_url)
            
            result["futgg_card_image_url"] = img_url
            logger.info(f"[FutGG] Card HD encontrado para {player_name}: {img_url[:80]}")
    else:
        logger.warning(f"[FutGG] Card HD não encontrado no HTML para {player_name} (EA ID: {ea_item_id})")
        
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
        
    result["futgg_player_id"] = ea_item_id
    
    return result


# ── Fase 4: Salvar imagens localmente ────────────────────────────────────────

async def save_player_images(
    session: aiohttp.ClientSession,
    player_data: Dict,
    futbin_id: str,
) -> Dict:
    """
    Baixa e salva todas as imagens do jogador localmente.
    Retorna dict com caminhos locais.
    """
    image_paths = {}
    name_slug = sanitize(player_data.get("name", "unknown"))
    
    # ── Card completo HD (do FutGG) ──
    card_url = (
        player_data.get("futgg_card_image_url") or
        player_data.get("bg_url_hd") or
        player_data.get("bg_url_raw")
    )
    if card_url:
        card_filename = f"fc_player_{futbin_id}_{name_slug}.png"
        card_path = IMAGES_DIR / "cards" / "full" / card_filename
        success = await download_image(session, card_url, card_path)
        if success:
            image_paths["card_template_url"] = f"/images/cards/full/{card_filename}"
            
            # Criar miniatura 150px
            try:
                _create_thumbnail(str(card_path), str(IMAGES_DIR / "cards" / "small" / card_filename))
            except Exception as e:
                logger.debug(f"Erro ao criar miniatura: {e}")
    
    # ── Render/Foto do jogador ──
    render_url = (
        player_data.get("futgg_render_url") or
        player_data.get("render_url") or
        player_data.get("face_url_raw")
    )
    if render_url:
        render_filename = f"render_{futbin_id}_{name_slug}.png"
        render_path = IMAGES_DIR / "cards" / "renders" / render_filename
        success = await download_image(session, render_url, render_path)
        if success:
            image_paths["render_url"] = f"/images/cards/renders/{render_filename}"
    
    # ── Bandeira da nação ──
    nation_url = player_data.get("nation_flag_url")
    if nation_url:
        nation_slug = sanitize(player_data.get("nation", "unknown"))
        nation_filename = f"nation_{nation_slug}.png"
        nation_path = IMAGES_DIR / "cards" / "nations" / nation_filename
        success = await download_image(session, nation_url, nation_path)
        if success:
            image_paths["nation_flag_url"] = f"/images/cards/nations/{nation_filename}"
    
    # ── Logo do clube ──
    club_url = player_data.get("club_logo_url")
    if club_url:
        club_slug = sanitize(player_data.get("club", "unknown"))
        club_filename = f"club_{club_slug}.png"
        club_path = IMAGES_DIR / "cards" / "clubs" / club_filename
        success = await download_image(session, club_url, club_path)
        if success:
            image_paths["club_logo_url"] = f"/images/cards/clubs/{club_filename}"
    
    # ── Logo da liga ──
    league_url = player_data.get("league_logo_url")
    if league_url:
        league_slug = sanitize(player_data.get("league", "unknown"))
        league_filename = f"league_{league_slug}.png"
        league_path = IMAGES_DIR / "cards" / "leagues" / league_filename
        success = await download_image(session, league_url, league_path)
        if success:
            image_paths["league_logo_url"] = f"/images/cards/leagues/{league_filename}"
    
    return image_paths


def _create_thumbnail(input_path: str, output_path: str):
    """
    Gera a miniatura cropada premium (Small Card) de 150x169px a partir do card HD
    original, recortando o topo (queixo para cima) e a base curva, ocultando o centro.
    """
    try:
        from PIL import Image
        dest = Path(output_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        
        with Image.open(input_path) as img:
            # 1. Redimensionar temporariamente para 504x698 para termos coordenadas de corte fixas e precisas
            img_temp = img.resize((504, 698), Image.Resampling.LANCZOS)
            
            # 2. Recortar Topo: y de 0 a 422 (Rating, Posição, Rosto e PlayStyles)
            topo = img_temp.crop((0, 0, 504, 422))
            
            # 3. Recortar Base: y de 558 a 698 (Borda curva com os emblemas da base)
            base = img_temp.crop((0, 558, 504, 698))
            
            # 4. Mesclar as partes em um canvas de 504x562
            small_canvas = Image.new("RGBA", (504, 562))
            small_canvas.paste(topo, (0, 0))
            small_canvas.paste(base, (0, 422))
            
            # 5. Redimensionar para o tamanho ideal final de 150x169px com alta nitidez
            resized = small_canvas.resize((150, 169), Image.Resampling.LANCZOS)
            resized.save(dest, "PNG")
            
    except Exception as e:
        logger.error(f"Erro ao criar miniatura cropada premium para {input_path}: {e}")



# ── Fase 5: Persistir no banco ────────────────────────────────────────────────

async def upsert_player(session, player_data: Dict):
    """
    Insere ou atualiza um jogador na tabela fc_players.
    """
    from sqlalchemy import text
    
    futbin_id = str(player_data["futbin_id"])
    
    # Verificar se já existe
    result = await session.execute(
        text('SELECT id FROM fc_players WHERE futbin_id = :fid'),
        {"fid": futbin_id}
    )
    existing = result.fetchone()
    
    # Campos a salvar
    fields = {
        "futbin_id":        futbin_id,
        "name":             player_data.get("name", "Unknown"),
        "overall":          player_data.get("overall", 0),
        "position":         player_data.get("position"),
        "nation":           player_data.get("nation"),
        "club":             player_data.get("club"),
        "league":           player_data.get("league"),
        "card_type":        player_data.get("card_type"),
        "face_url":         player_data.get("face_url_raw"),
        "bg_url_raw":       player_data.get("bg_url_raw"),
        "card_template_url": player_data.get("card_template_url"),
        "render_url":       player_data.get("render_url"),
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
        # Sub-stats
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
        "scraped_version":  SCRAPER_VERSION,
        "scraped_at":       datetime.now(UTC).isoformat(),
        "detail_scraped_at": datetime.now(UTC).isoformat() if player_data.get("pace") else None,
    }
    
    # Filtrar valores None para UPDATE parcial
    non_null = {k: v for k, v in fields.items() if v is not None}
    
    if existing:
        # UPDATE
        set_clause = ", ".join(f'"{k}" = :{k}' for k in non_null if k != "futbin_id")
        if set_clause:
            await session.execute(
                text(f'UPDATE fc_players SET {set_clause} WHERE futbin_id = :futbin_id'),
                non_null
            )
    else:
        # INSERT
        cols = ", ".join(f'"{k}"' for k in non_null)
        vals = ", ".join(f":{k}" for k in non_null)
        await session.execute(
            text(f'INSERT INTO fc_players ({cols}) VALUES ({vals})'),
            non_null
        )


# ── Orquestrador principal ────────────────────────────────────────────────────

async def process_player(
    session_futbin: aiohttp.ClientSession,
    session_futgg: aiohttp.ClientSession,
    db_session,
    player_basic: Dict,
    test_mode: bool = False,
    renderer_client: Optional[CardRendererClient] = None,
) -> bool:
    """
    Processa um único jogador:
    1. Busca detalhes no Futbin (stats completos)
    2. Busca imagem HD no FutGG (em paralelo)
    3. Salva imagens localmente
    4. Persiste no banco
    """
    futbin_id = player_basic["futbin_id"]
    name = player_basic["name"]
    overall = player_basic["overall"]
    player_url = player_basic.get("player_url", "")
    
    logger.info(f"  ➤ Processando: {name} (OVR:{overall}, ID:{futbin_id})")
    
    ea_item_id = player_basic.get("ea_item_id", "")
    
    # Executar Fase 2 (Futbin detalhe) e Fase 3 (FutGG) em paralelo
    tasks = [
        scrape_futbin_player_detail(session_futbin, player_url, futbin_id),
        scrape_futgg_card_image(session_futgg, name, overall, futbin_id, ea_item_id),
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    futbin_detail = results[0] if not isinstance(results[0], Exception) else {}
    futgg_data    = results[1] if not isinstance(results[1], Exception) else {}
    
    if isinstance(results[0], Exception):
        logger.debug(f"Futbin detalhe falhou para {name}: {results[0]}")
    if isinstance(results[1], Exception):
        logger.debug(f"FutGG falhou para {name}: {results[1]}")
    
    # Mesclar dados
    player_data = {**player_basic, **futbin_detail, **futgg_data}
    
    # Salvar imagens e gerenciar os cards (Fase 4)
    # Tentar primeiro baixar e cachear as imagens perfeitas originais diretas do CDN
    image_paths = await save_player_images(session_futbin, player_data, futbin_id)
    
    if image_paths.get("card_template_url"):
        # Sucesso absoluto! O card original perfeito foi baixado e preservado intacto.
        # A miniatura Small cropada premium foi gerada de forma nativa a partir dele.
        player_data.update(image_paths)
    elif renderer_client:
        # Fallback de segurança: se o card HD original não for encontrado no CDN,
        # chamamos a nossa engine local Canvas offline como reserva inteligente.
        logger.info(f"  ⚠ Card original indisponível para {name}. Acionando engine local Express...")
        render_res = await renderer_client.render_player(session_futbin, player_data)
        if render_res and render_res.get("success"):
            player_data.update(render_res)
        else:
            logger.error(f"  ❌ Fallback da engine local falhou para {name}.")
    else:
        # Fallback padrão
        player_data.update(image_paths)

    
    # Persistir no banco (Fase 5)
    try:
        await upsert_player(db_session, player_data)
        
        has_card = bool(player_data.get("card_template_url") or player_data.get("bg_url_hd"))
        has_stats = bool(player_data.get("pace"))
        
        logger.info(
            f"  ✅ {name} salvo | "
            f"Card: {'✓' if has_card else '✗'} | "
            f"Stats: {'✓' if has_stats else '✗'} | "
            f"FutGG: {'✓' if futgg_data.get('futgg_player_id') else '✗'}"
        )
        return True
    
    except Exception as e:
        logger.error(f"  ❌ Erro ao salvar {name}: {e}")
        return False


async def main(start_page: int = 1, end_page: int = 3, test_mode: bool = False):
    """Pipeline principal de scraping."""
    
    print("\n" + "="*70)
    print(f"  SCRAPER v2 — EA FC 26 Player Cards")
    print(f"  Páginas: {start_page} a {end_page} | Modo: {'TESTE (5/pág)' if test_mode else 'COMPLETO'}")
    print(f"  Banco: {DATABASE_FILE}")
    print("="*70 + "\n")
    
    state = load_state()
    
    # Criar sessões separadas para Futbin e FutGG
    session_futbin = create_session()
    session_futgg  = create_session()
    
    total_saved = 0
    total_failed = 0
    
    # Instanciar e inicializar o cliente do renderizador local Express Node.js
    renderer_client = CardRendererClient()
    await renderer_client.start_service()
    
    try:
        async with async_session_factory() as db:
            
            for page in range(start_page, end_page + 1):
                print(f"\n{'─'*60}")
                print(f"  📄 PÁGINA {page}/{end_page}")
                print(f"{'─'*60}")
                
                # Fase 1: Listar jogadores da página
                players_basic = await scrape_futbin_player_list(session_futbin, page)
                
                if not players_basic:
                    logger.warning(f"Página {page} sem jogadores. Pulando...")
                    continue
                
                # Em modo teste, limitar a 5 jogadores
                if test_mode:
                    players_basic = players_basic[:5]
                    logger.info(f"[TESTE] Limitado a 5 jogadores por página")
                
                print(f"  👥 {len(players_basic)} jogadores encontrados")
                
                page_saved = 0
                page_failed = 0
                
                # Processar cada jogador
                for i, player in enumerate(players_basic, 1):
                    print(f"\n  [{i}/{len(players_basic)}] ", end="", flush=True)
                    
                    success = await process_player(
                        session_futbin, session_futgg, db, player, test_mode, renderer_client
                    )
                    
                    if success:
                        page_saved += 1
                        total_saved += 1
                    else:
                        page_failed += 1
                        total_failed += 1
                    
                    # Commit a cada 5 jogadores
                    if (i % 5) == 0:
                        await db.commit()
                
                # Commit final da página
                await db.commit()
                
                # Atualizar estado
                state["last_page"] = page
                save_state(state)
                
                print(f"\n\n  ✅ Página {page} concluída: {page_saved} salvos, {page_failed} falhas")
                
                # Delay entre páginas (mais longo para simular usuário)
                if page < end_page:
                    page_delay = 8 + random.uniform(2, 6)
                    logger.info(f"Aguardando {page_delay:.1f}s antes da próxima página...")
                    await asyncio.sleep(page_delay)
    
    finally:
        await session_futbin.close()
        await session_futgg.close()
        # Garantir o encerramento do microserviço Node.js para liberar RAM
        await renderer_client.stop_service()
    
    print("\n" + "="*70)
    print(f"  🏁 SCRAPING CONCLUÍDO")
    print(f"  Total salvo: {total_saved} | Falhas: {total_failed}")
    print(f"  Banco: {DATABASE_FILE}")
    print("="*70 + "\n")


def parse_pages(pages_str: str) -> Tuple[int, int]:
    """Parseia '1-3' → (1, 3)."""
    m = re.match(r"(\d+)[-–](\d+)", pages_str)
    if m:
        return int(m.group(1)), int(m.group(2))
    n = int(pages_str)
    return n, n


if __name__ == "__main__":
    import random
    
    parser = argparse.ArgumentParser(description="Scraper de cards de jogadores EA FC 26 v2")
    parser.add_argument("--pages", default="1-3", help="Páginas a raspar. Ex: '1-3' ou '5-10'. Default: 1-3")
    parser.add_argument("--test", action="store_true", help="Modo teste: apenas 5 jogadores por página")
    parser.add_argument("--reset", action="store_true", help="Resetar dados antes de iniciar")
    args = parser.parse_args()
    
    if args.reset:
        import subprocess
        subprocess.run([
            sys.executable, str(BASE_DIR / "scripts" / "reset_scrape_data.py"), "--force"
        ])
    
    start_p, end_p = parse_pages(args.pages)
    
    asyncio.run(main(start_page=start_p, end_page=end_p, test_mode=args.test))
