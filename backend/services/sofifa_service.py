"""
Help DMEs — SoFIFA API Service
=================================
Cliente assíncrono para a API REST gratuita da SoFIFA.
Sem autenticação. Rate limit: 60 req/min.

Usa:
  - Stats detalhados (30+ atributos)
  - CDN de imagens (rosto, clube, nação, liga)
  - Mapeamento de posições
  - Histórico de ratings

Referência: https://sofifa.com/api/
"""

import asyncio
import logging
import time
from typing import Optional

import aiohttp

logger = logging.getLogger("help_dmes.sofifa")

# ── Configuração ─────────────────────────────────────────────────────────────

SOFIFA_API_BASE = "https://sofifa.com/api"
SOFIFA_CDN_BASE = "https://cdn.sofifa.net"
LATEST_ROSTER = "260032"  # Apr 28, 2026

RATE_LIMIT_SLEEP = 1.0  # 1s entre requests (60 req/min)
REQUEST_TIMEOUT = 15

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
}

# Mapeamento de posições numéricas → código
SOFIFA_POSITIONS = {
    0:  "GK",
    2:  "RWB", 3: "RB", 5: "CB", 7: "LB", 8: "LWB",
    10: "CDM",
    12: "RM", 14: "CM", 16: "LM",
    18: "CAM",
    20: "CF",
    23: "LW", 25: "ST", 27: "RW",
}

# Cache em memória para evitar requests duplicados na mesma sessão
_player_cache: dict[int, dict] = {}
_search_cache: dict[str, dict] = {}


# ── Helpers HTTP ─────────────────────────────────────────────────────────────

async def _api_get(
    http: aiohttp.ClientSession,
    endpoint: str,
    params: Optional[dict] = None,
) -> Optional[dict]:
    """GET na API SoFIFA com rate limiting e retry."""
    url = f"{SOFIFA_API_BASE}/{endpoint}"
    await asyncio.sleep(RATE_LIMIT_SLEEP)

    for attempt in range(3):
        try:
            async with http.get(url, headers=HEADERS, params=params, ssl=True) as resp:
                if resp.status == 200:
                    return await resp.json()
                if resp.status == 429:
                    wait = 2.0 ** (attempt + 2)
                    logger.warning(f"[429] SoFIFA rate limit — aguardando {wait:.1f}s")
                    await asyncio.sleep(wait)
                elif resp.status == 404:
                    logger.debug(f"[404] SoFIFA não encontrado: {url}")
                    return None
                else:
                    logger.error(f"[{resp.status}] SoFIFA erro: {url}")
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"SoFIFA conexão falhou: {e}")
            await asyncio.sleep(2.0 ** attempt)

    return None


# ── Busca de Jogadores ───────────────────────────────────────────────────────

async def fetch_player_by_id(
    http: aiohttp.ClientSession,
    sofifa_id: int,
    roster: str = LATEST_ROSTER,
) -> Optional[dict]:
    """Busca jogador por sofifa_id. Retorna dict com todos os stats."""
    if sofifa_id in _player_cache:
        return _player_cache[sofifa_id]

    data = await _api_get(http, "player", {"id": sofifa_id, "roster": roster})
    if data and "data" in data:
        player = data["data"]
        result = _normalize_player(player)
        _player_cache[sofifa_id] = result
        return result
    elif data:
        result = _normalize_player(data)
        _player_cache[sofifa_id] = result
        return result

    return None


async def fetch_player_by_name(
    http: aiohttp.ClientSession,
    name: str,
    roster: str = LATEST_ROSTER,
) -> Optional[dict]:
    """
    Busca jogador por nome na SoFIFA.
    Usa a página de busca da SoFIFA para encontrar o sofifa_id.
    """
    cache_key = f"{name.lower()}_{roster}"
    if cache_key in _search_cache:
        return _search_cache[cache_key]

    # A API SoFIFA não tem endpoint de busca por nome diretamente.
    # Usamos o endpoint de busca do site via scraping do redirect.
    # Alternativa: buscar via Futbin/Kaggle e cruzar por nome.
    # Por ora, retornamos None e dependemos do futbin_id para enriquecer.
    logger.debug(f"SoFIFA: busca por nome '{name}' — requer sofifa_id para enriquecer")
    return None


async def search_player_sofifa(
    http: aiohttp.ClientSession,
    name: str,
) -> Optional[int]:
    """
    Tenta encontrar o sofifa_id de um jogador pela página de busca do site.
    Faz scraping leve do resultado de busca.
    """
    import re
    from bs4 import BeautifulSoup

    search_url = f"https://sofifa.com/players?keyword={name.replace(' ', '+')}"
    await asyncio.sleep(RATE_LIMIT_SLEEP)

    try:
        async with http.get(search_url, headers={
            "User-Agent": HEADERS["User-Agent"],
            "Accept": "text/html,application/xhtml+xml",
        }, ssl=True) as resp:
            if resp.status != 200:
                return None
            html = await resp.text()
    except aiohttp.ClientError:
        return None

    soup = BeautifulSoup(html, "lxml")
    # Primeiro resultado de jogador
    player_link = soup.select_one("a[href*='/player/']")
    if player_link:
        href = player_link.get("href", "")
        m = re.search(r"/player/(\d+)", href)
        if m:
            return int(m.group(1))

    return None


# ── Fetch de Ligas e Times ───────────────────────────────────────────────────

async def fetch_leagues(http: aiohttp.ClientSession) -> list[dict]:
    """Retorna todas as ligas disponíveis."""
    data = await _api_get(http, "leagues")
    if data and "data" in data:
        return data["data"]
    return []


async def fetch_teams(
    http: aiohttp.ClientSession,
    league_id: int,
    roster: str = LATEST_ROSTER,
) -> list[dict]:
    """Retorna todos os times de uma liga."""
    data = await _api_get(http, "teams", {"league": league_id, "roster": roster})
    if data and "data" in data:
        return data["data"]
    return []


async def fetch_players_by_team(
    http: aiohttp.ClientSession,
    team_id: int,
    roster: str = LATEST_ROSTER,
) -> list[dict]:
    """Retorna todos os jogadores de um time."""
    data = await _api_get(http, "players", {"team": team_id, "roster": roster})
    if data and "data" in data:
        return [_normalize_player(p) for p in data["data"]]
    return []


# ── Geração de URLs de CDN ───────────────────────────────────────────────────

def build_image_urls(
    sofifa_id: int,
    club_id: Optional[int] = None,
    country_id: Optional[int] = None,
    league_id: Optional[int] = None,
) -> dict:
    """
    Gera URLs do CDN da SoFIFA para imagens.
    Todas as URLs são públicas e não requerem autenticação.
    """
    urls = {}

    if sofifa_id:
        urls["face_60"] = f"{SOFIFA_CDN_BASE}/players/{sofifa_id}/26_60.png"
        urls["face_120"] = f"{SOFIFA_CDN_BASE}/players/{sofifa_id}/26_120.png"
        urls["face_180"] = f"{SOFIFA_CDN_BASE}/players/{sofifa_id}/26_180.png"

    if club_id:
        urls["club_light_60"] = f"{SOFIFA_CDN_BASE}/teams/{club_id}/light_60.png"
        urls["club_light_120"] = f"{SOFIFA_CDN_BASE}/teams/{club_id}/light_120.png"
        urls["club_dark_60"] = f"{SOFIFA_CDN_BASE}/teams/{club_id}/dark_60.png"

    if country_id:
        urls["nation_flag"] = f"{SOFIFA_CDN_BASE}/flags/{country_id}.svg"

    if league_id:
        urls["league_30"] = f"{SOFIFA_CDN_BASE}/leagues/{league_id}/light_30.png"
        urls["league_60"] = f"{SOFIFA_CDN_BASE}/leagues/{league_id}/light_60.png"

    return urls


def build_futbin_image_urls(futbin_id: str) -> dict:
    """Gera URLs do CDN do Futbin para renders FUT."""
    base = "https://cdn.futbin.com/content/fc26/img"
    return {
        "player_render": f"{base}/players/{futbin_id}.png",
        "player_small": f"{base}/players/{futbin_id}_small.png",
    }


# ── Normalização de Dados ────────────────────────────────────────────────────

def _normalize_player(raw: dict) -> dict:
    """Normaliza os dados brutos da API SoFIFA para formato padronizado."""
    # Posições
    pos1 = SOFIFA_POSITIONS.get(raw.get("position1", -1), "")
    pos2 = SOFIFA_POSITIONS.get(raw.get("position2", -1), "")
    pos3 = SOFIFA_POSITIONS.get(raw.get("position3", -1), "")
    alt_positions = ",".join(filter(None, [pos2, pos3]))

    # Pé preferido
    foot_map = {1: "Left", 2: "Right"}
    foot = foot_map.get(raw.get("foot"), "Right")

    # Calcular face stats (PAC, SHO, PAS, DRI, DEF, PHY)
    # A API SoFIFA não retorna esses diretamente — calculamos pela média dos sub-stats
    pace = _calc_avg(raw, ["acceleration", "sprintSpeed"])
    shooting = _calc_avg(raw, ["finishing", "shotPower", "longShots", "volleys", "positioning"])
    passing = _calc_avg(raw, ["shortPassing", "longPassing", "crossing", "curve", "freeKick", "vision"])
    dribbling_stat = _calc_avg(raw, ["dribbling", "ballControl", "agility", "balance", "reactions"])
    defending = _calc_avg(raw, ["interceptions", "marking", "standingTackle", "slidingTackle"])
    physic = _calc_avg(raw, ["jumping", "stamina", "strength", "aggression"])

    return {
        "sofifa_id": raw.get("id"),
        "name": raw.get("commonName") or f"{raw.get('firstName', '')} {raw.get('lastName', '')}".strip(),
        "first_name": raw.get("firstName", ""),
        "last_name": raw.get("lastName", ""),
        "overall": raw.get("overall", 0),
        "potential": raw.get("potential", 0),
        "position": pos1,
        "alt_positions": alt_positions,
        "foot": foot,
        "weak_foot": raw.get("weakFoot"),
        "skill_moves": raw.get("skillMoves"),
        "age": raw.get("age"),
        "height": raw.get("height"),
        "weight": raw.get("weight"),
        "country": raw.get("country", ""),
        "country_id": raw.get("countryId"),
        "value": raw.get("value", 0),
        "wage": raw.get("wage", 0),
        "international_reputation": raw.get("internationalReputation"),

        # Face stats (calculados)
        "pace": pace,
        "shooting": shooting,
        "passing": passing,
        "dribbling_face": dribbling_stat,
        "defending": defending,
        "physic": physic,

        # Sub-atributos detalhados
        "acceleration": raw.get("acceleration"),
        "sprint_speed": raw.get("sprintSpeed"),
        "finishing": raw.get("finishing"),
        "shot_power": raw.get("shotPower"),
        "long_shots": raw.get("longShots"),
        "volleys": raw.get("volleys"),
        "positioning_att": raw.get("positioning"),
        "heading": raw.get("heading"),
        "short_passing": raw.get("shortPassing"),
        "long_passing": raw.get("longPassing"),
        "crossing": raw.get("crossing"),
        "curve": raw.get("curve"),
        "free_kick": raw.get("freeKick"),
        "vision": raw.get("vision"),
        "agility": raw.get("agility"),
        "balance": raw.get("balance"),
        "reactions": raw.get("reactions"),
        "ball_control": raw.get("ballControl"),
        "composure": raw.get("composure"),
        "skill_dribbling": raw.get("dribbling"),
        "interceptions": raw.get("interceptions"),
        "marking": raw.get("marking"),
        "standing_tackle": raw.get("standingTackle"),
        "sliding_tackle": raw.get("slidingTackle"),
        "jumping": raw.get("jumping"),
        "stamina": raw.get("stamina"),
        "strength": raw.get("strength"),
        "aggression": raw.get("aggression"),
        "penalties": raw.get("penalties"),

        # GK stats
        "gk_diving": raw.get("gkDiving"),
        "gk_handling": raw.get("gkHandling"),
        "gk_kicking": raw.get("gkKicking"),
        "gk_positioning": raw.get("gkPositioning"),
        "gk_reflexes": raw.get("gkReflexes"),
    }


def _calc_avg(data: dict, keys: list[str]) -> Optional[int]:
    """Calcula média dos stats para derivar face stat."""
    vals = [data.get(k) for k in keys if data.get(k) is not None]
    if not vals:
        return None
    return round(sum(vals) / len(vals))


# ── Limpar Cache ─────────────────────────────────────────────────────────────

def clear_cache():
    """Limpa o cache em memória."""
    _player_cache.clear()
    _search_cache.clear()
    logger.debug("SoFIFA cache limpo")
