"""
Help DMEs — Futbin Scraping Service
====================================
Serviço assíncrono de scraping usando aiohttp + BeautifulSoup.
Fonte: futbin.com — substitui Playwright (fut.gg / futnext).

Fluxo:
  1. fetch_sbc_index()  → lista todos os SBCs ativos (paginado)
  2. fetch_sbc_detail() → detalhes + requisitos de cada SBC
  3. download_image()   → cache local de imagens
  4. persist to DB      → salva via SQLAlchemy async
"""

import asyncio
import logging
import re
import os
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional
import json

import aiohttp
import aiofiles
from bs4 import BeautifulSoup, Tag
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.models import (
    SBCSet, SBCChallenge, ChallengeRequirement,
    SBCReward, PlayerCard, ScrapeLog,
)

logger = logging.getLogger("help_dmes.futbin")

# ── Configuração ─────────────────────────────────────────────────────────────

BASE_URL = "https://www.futbin.com"
IMAGE_DIR = Path("images")

MAX_CONCURRENT = 5
DELAY_BETWEEN = 0.4
RETRY_ATTEMPTS = 3
RETRY_BACKOFF = 2.0

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.futbin.com/",
    "Connection": "keep-alive",
}

# ── Estado global do scraping ────────────────────────────────────────────────

_scrape_state = {
    "status": "idle",
    "message": None,
    "last_scrape_at": None,
    "sbcs_count": 0,
    "current": 0,
    "total": 0,
}


def get_scrape_status() -> dict:
    return dict(_scrape_state)


# ── HTTP helpers ─────────────────────────────────────────────────────────────

async def _fetch(session: aiohttp.ClientSession, url: str) -> Optional[str]:
    """GET com retry exponencial. Retorna texto ou None."""
    for attempt in range(RETRY_ATTEMPTS):
        try:
            async with session.get(url, headers=HEADERS, ssl=True) as resp:
                if resp.status == 200:
                    return await resp.text()
                if resp.status == 429:
                    wait = RETRY_BACKOFF ** (attempt + 2)
                    logger.warning(f"[429] Rate limited {url} — aguardando {wait:.1f}s")
                    await asyncio.sleep(wait)
                elif resp.status == 403:
                    logger.warning(f"[403] Bloqueado {url} — tentativa {attempt+1}")
                    await asyncio.sleep(RETRY_BACKOFF ** attempt)
                else:
                    logger.error(f"[{resp.status}] Erro em {url}")
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Conexão falhou {url}: {e}")
            await asyncio.sleep(RETRY_BACKOFF ** attempt)
    return None


async def _fetch_binary(session: aiohttp.ClientSession, url: str) -> Optional[bytes]:
    """GET binário para imagens."""
    for attempt in range(RETRY_ATTEMPTS):
        try:
            async with session.get(url, headers=HEADERS) as resp:
                if resp.status == 200:
                    return await resp.read()
                if resp.status == 404:
                    return None
        except aiohttp.ClientError:
            await asyncio.sleep(RETRY_BACKOFF ** attempt)
    return None


# ── Download de imagens ──────────────────────────────────────────────────────

async def _download_image(
    session: aiohttp.ClientSession, url: str, subdir: str, filename: str
) -> str:
    """Baixa imagem para IMAGE_DIR/subdir/filename. Retorna path local."""
    if not url:
        return ""

    # Limpar URL (remover query params do CDN imgix)
    clean_url = url.split("?")[0] if "?" in url else url
    if clean_url.startswith("//"):
        clean_url = "https:" + clean_url
    clean_url = clean_url.replace("cdn3.futbin.com", "cdn.futbin.com")

    dest_dir = IMAGE_DIR / subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / filename

    if dest_path.exists() and dest_path.stat().st_size > 100:
        return str(dest_path)

    data = await _fetch_binary(session, clean_url)
    if data and len(data) > 100:
        async with aiofiles.open(dest_path, "wb") as f:
            await f.write(data)
        return str(dest_path)
    return ""


# ── Parsing: Lista de SBCs ───────────────────────────────────────────────────

def _parse_sbc_list(html: str) -> list[dict]:
    """Parseia a página de listagem de SBCs da futbin."""
    soup = BeautifulSoup(html, "lxml")
    results = []

    # Cada SBC card é um <a> dentro de .sbc-cards-parent
    cards = soup.select(".sbc-card-wrapper a[href*='squad-building-challenge/']")

    for card in cards:
        href = card.get("href", "")
        # Extrair ID numérico da URL: /26/squad-building-challenge/964
        id_match = re.search(r"/squad-building-challenge/(\d+)", href)
        if not id_match:
            continue

        sbc_id = id_match.group(1)

        # Nome do SBC — seletor específico para não pegar o badge "New"
        name_el = card.select_one(".og-card-wrapper-top .xs-font > .text-ellipsis")
        name = name_el.get_text(strip=True) if name_el else ""
        if not name:
            # fallback
            name_el = card.select_one(".og-card-wrapper-top .text-ellipsis")
            raw = name_el.get_text(strip=True) if name_el else ""
            # Remover sufixos de badge
            for suffix in ["New", "Expiring soon", "Expired", "Hot"]:
                if raw.endswith(suffix):
                    raw = raw[:-len(suffix)].strip()
            name = raw

        # Badge "New"
        badge_el = card.select_one(".sbc-badge")
        is_new = badge_el is not None and "new" in (badge_el.get_text(strip=True).lower())

        # Imagem do SBC (card ou player)
        img_el = card.select_one("img[src*='sbc_set_image'], img[src*='players/p']")
        image_url = ""
        if img_el:
            src = img_el.get("src", "")
            image_url = src.split("?")[0] if src else ""

        # Expiração
        expires_text = ""
        expires_label = card.find(string="Expires")
        if expires_label:
            expires_div = expires_label.find_next("div", class_="bold")
            if expires_div:
                expires_text = expires_div.get_text(strip=True)

        # Dados brutos da carta (raw_card_data) se houver
        raw_card_data_str = None
        player_card_el = card.select_one(".playercard-26")
        if player_card_el:
            card_info = {}
            bg_el = player_card_el.select_one(".playercard-26-bg")
            if bg_el:
                card_info["bg_url"] = bg_el.get("src")
            face_el = player_card_el.select_one(".playercard-26-special-img")
            if face_el:
                card_info["face_url"] = face_el.get("src")
            
            rating_el = player_card_el.select_one(".playercard-26-rating")
            if rating_el:
                card_info["rating"] = rating_el.get_text(strip=True)
            
            pos_el = player_card_el.select_one(".playercard-26-position")
            if pos_el:
                card_info["position"] = pos_el.get_text(strip=True)

            name_el = player_card_el.select_one(".playercard-26-name")
            if name_el:
                card_info["name"] = name_el.get_text(strip=True)

            # Extrair os 6 stats (PAC, SHO, PAS, DRI, DEF, PHY)
            stats = []
            stat_els = player_card_el.select(".playercard-26-stats")
            for s in stat_els:
                val = s.select_one(".playercard-stat-number")
                lbl = s.select_one(".playercard-26-stat-value")
                if val and lbl:
                    stats.append({
                        "name": lbl.get_text(strip=True),
                        "value": val.get_text(strip=True)
                    })
            if stats:
                card_info["stats"] = stats
            
            raw_card_data_str = json.dumps(card_info) if card_info else None

        results.append({
            "futbin_id": sbc_id,
            "name": name,
            "is_new": is_new,
            "image_url": image_url,
            "expires_text": expires_text,
            "raw_card_data": raw_card_data_str,
            "url": f"{BASE_URL}{href}" if not href.startswith("http") else href,
        })

    return results


def _get_total_pages(html: str) -> int:
    """Descobre quantas páginas de SBCs existem."""
    soup = BeautifulSoup(html, "lxml")
    page_links = soup.select("a[href*='page=']")
    max_page = 1
    for link in page_links:
        href = link.get("href", "")
        m = re.search(r"page=(\d+)", href)
        if m:
            max_page = max(max_page, int(m.group(1)))
    return max_page


# ── Parsing: Detalhe de SBC ──────────────────────────────────────────────────

def _parse_sbc_detail(html: str) -> dict:
    """Parseia página de detalhe de um SBC."""
    soup = BeautifulSoup(html, "lxml")
    detail = {
        "description": "",
        "category": "",
        "expires_text": "",
        "repeatable_text": "",
        "total_cost_ps": None,
        "challenges": [],
        "reward_name": "",
        "reward_image": "",
        "player_data": None,
    }

    # Título e descrição
    h1 = soup.select_one("h1")
    h2 = soup.select_one("h2")
    if h2:
        detail["description"] = h2.get_text(strip=True)

    # Categoria via breadcrumb
    breadcrumbs = soup.select(".breadcrumb")
    if len(breadcrumbs) >= 2:
        cat_text = breadcrumbs[-1].get_text(strip=True).lower()
        detail["category"] = _map_category(cat_text)

    # Buscar blocos de challenge individuais
    challenge_sections = _extract_challenges(soup)
    # Deduplicar: se houver challenges com mesmo nome, manter o que tem requisitos
    seen = {}
    for ch in challenge_sections:
        key = ch["name"]
        if key in seen:
            # Manter o que tem mais requisitos
            if len(ch["requirements"]) > len(seen[key]["requirements"]):
                seen[key] = ch
        else:
            seen[key] = ch
    detail["challenges"] = list(seen.values())

    # Custo total
    cost_texts = soup.find_all(string=re.compile(r"\d+\.?\d*K"))
    if cost_texts:
        for ct in cost_texts:
            parent = ct.parent
            if parent and "total" in str(parent.previous_sibling or "").lower():
                detail["total_cost_ps"] = _parse_cost(ct.strip())
                break

    # Player card data (se SBC de jogador)
    player_hover = soup.select_one("[data-player-hover-location]")
    if player_hover:
        # Extrair dados do player card exibido
        card_el = soup.select_one(".player-hover-container-wrapper")
        if card_el:
            # Rating
            parent_link = card_el.find_parent("a")
            if parent_link:
                player_url = parent_link.get("href", "")
                detail["player_data"] = {
                    "url": f"{BASE_URL}{player_url}" if not player_url.startswith("http") else player_url,
                }

    return detail


def _extract_challenges(soup: BeautifulSoup) -> list[dict]:
    """Extrai challenges individuais usando img[sbc_challenge_image] como âncora."""
    challenges = []

    challenge_imgs = soup.select("img[src*='sbc_challenge_image']")

    for img in challenge_imgs:
        # Subir até o container que contém Requirements
        container = img.parent
        for _ in range(15):
            text = container.get_text(separator="|", strip=True) if container else ""
            if "Requirements" in text and ("Min" in text or "Max" in text or "squad" in text.lower()):
                break
            if container.parent and container.parent.name not in ("body", "html", "[document]", "main"):
                container = container.parent
            else:
                break

        if not isinstance(container, Tag):
            continue

        full_text = container.get_text(separator="\n", strip=True)
        lines = full_text.split("\n")

        ch = {
            "name": "",
            "description": "",
            "estimated_cost_ps": None,
            "reward_name": "",
            "reward_image": "",
            "requirements": [],
        }

        # Nome: primeiro texto curto antes de "Info"
        for line in lines:
            if line == "Info":
                break
            if line and len(line) < 60 and line not in ("Reward", "Requirements"):
                ch["name"] = line
                break

        # Descrição
        for line in lines:
            if "exchange a squad" in line.lower():
                ch["description"] = line
                break

        # Reward
        reward_el = container.select_one("img[src*='rewards/']")
        if reward_el:
            ch["reward_image"] = reward_el.get("src", "").split("?")[0]
            # Texto do reward: buscar no texto após "Reward"
            in_reward = False
            for line in lines:
                if line == "Reward":
                    in_reward = True
                    continue
                if in_reward and line and line not in ("Info", "Requirements"):
                    ch["reward_name"] = line
                    break

        # Custo
        cost_els = container.find_all(string=re.compile(r"\d+\.?\d*K"))
        if cost_els:
            ch["estimated_cost_ps"] = _parse_cost(cost_els[0].strip())

        # Requisitos: tudo após "Requirements" até "Completed Challenges"/"Start Challenge"
        in_req = False
        for line in lines:
            if line == "Requirements":
                in_req = True
                continue
            if not in_req:
                continue
            if line in ("Completed Challenges", "Start Challenge", ""):
                break
            req = _parse_requirement_line(line)
            if req:
                ch["requirements"].append(req)

        if ch["name"] or ch["requirements"]:
            challenges.append(ch)

    return challenges


def _parse_requirements_block(element: Tag, ch: dict):
    """Parseia os requisitos de um bloco de challenge."""
    # Requisitos típicos:
    # "# of players from Spain: Min 1"
    # "TOTW or TOTS: Min 1"
    # "Squad Rating: Min 86"
    # "# of players in squad: 11"
    text = element.get_text(separator="\n", strip=True)
    lines = text.split("\n")

    in_requirements = False
    for line in lines:
        line = line.strip()
        if "requirements" in line.lower():
            in_requirements = True
            continue
        if not in_requirements:
            continue
        if not line or line in ("Completed Challenges", "Start Challenge"):
            continue

        req = _parse_requirement_line(line)
        if req:
            ch["requirements"].append(req)


def _parse_requirement_line(line: str) -> Optional[dict]:
    """Parseia uma linha de requisito em tipo/operador/valor/detalhe."""
    line = line.strip()
    if not line or len(line) < 3:
        return None

    # Padrão: "# of players from LALIGA EA SPORTS: Min 1"
    m = re.match(r"#\s*of\s+players\s+from\s+(.+?):\s*(Min|Max|Exactly)\s+(\d+)", line, re.IGNORECASE)
    if m:
        detail_text = m.group(1).strip()
        # Determinar tipo (nation, league, club)
        rtype = "players_from_league"  # default
        if any(w in detail_text.lower() for w in ["spain", "brazil", "france", "germany", "england", "italy", "argentina"]):
            rtype = "players_from_nation"
        return {
            "requirement_type": rtype,
            "operator": m.group(2).lower(),
            "value": m.group(3),
            "detail": detail_text,
        }

    # "Squad Rating: Min 86"
    m = re.match(r"Squad Rating:\s*(Min|Max|Exactly)\s+(\d+)", line, re.IGNORECASE)
    if m:
        return {
            "requirement_type": "team_rating",
            "operator": m.group(1).lower(),
            "value": m.group(2),
            "detail": None,
        }

    # "# of players in squad: 11"
    m = re.match(r"#\s*of\s+players\s+in\s+squad:\s*(\d+)", line, re.IGNORECASE)
    if m:
        return {
            "requirement_type": "player_count",
            "operator": "exact",
            "value": m.group(1),
            "detail": None,
        }

    # "TOTW or TOTS: Min 1"
    m = re.match(r"(TOTW|TOTS|Rare|Common|Gold|Silver|Bronze)(?:\s+or\s+\w+)?:\s*(Min|Max|Exactly)\s+(\d+)", line, re.IGNORECASE)
    if m:
        rtype = "player_type"
        kw = m.group(1).lower()
        if kw in ("rare", "common"):
            rtype = "player_rarity"
        elif kw in ("gold", "silver", "bronze"):
            rtype = "player_quality"
        return {
            "requirement_type": rtype,
            "operator": m.group(2).lower(),
            "value": m.group(3),
            "detail": m.group(1),
        }

    # "Team Chemistry: Min 22"
    m = re.match(r"(?:Team\s+)?Chemistry:\s*(Min|Max)\s+(\d+)", line, re.IGNORECASE)
    if m:
        return {
            "requirement_type": "squad_chemistry",
            "operator": m.group(1).lower(),
            "value": m.group(2),
            "detail": None,
        }

    # Genérico: "Algo: Min/Max N"
    m = re.match(r"(.+?):\s*(Min|Max|Exactly)\s+(\d+)", line, re.IGNORECASE)
    if m:
        return {
            "requirement_type": "other",
            "operator": m.group(2).lower(),
            "value": m.group(3),
            "detail": m.group(1).strip(),
        }

    return None


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_cost(text: str) -> Optional[int]:
    """Converte '59.7K' → 59700, '1.2M' → 1200000."""
    text = text.strip().replace(",", "")
    m = re.match(r"([\d.]+)\s*K", text, re.IGNORECASE)
    if m:
        return int(float(m.group(1)) * 1000)
    m = re.match(r"([\d.]+)\s*M", text, re.IGNORECASE)
    if m:
        return int(float(m.group(1)) * 1_000_000)
    m = re.match(r"(\d+)", text)
    if m:
        return int(m.group(1))
    return None


def _map_category(text: str) -> str:
    """Mapeia texto de categoria para valor padronizado."""
    text = text.lower()
    mapping = {
        "player": "players", "players": "players",
        "upgrade": "upgrades", "upgrades": "upgrades",
        "challenge": "challenges", "challenges": "challenges",
        "icon": "icons", "icons": "icons",
        "foundation": "foundations", "foundations": "foundations",
        "swap": "swaps", "swaps": "swaps",
    }
    for key, val in mapping.items():
        if key in text:
            return val
    return "upgrades"


def _sanitize_filename(name: str) -> str:
    """Remove caracteres inválidos para nome de arquivo."""
    return re.sub(r'[^\w\-.]', '_', name)[:100]


# ── Pipeline Principal ───────────────────────────────────────────────────────

async def scrape_all_sbcs(db: AsyncSession) -> dict:
    """
    Pipeline completo: coleta todos os SBCs da futbin e persiste no banco.
    Retorna dict com status/contagem.
    """
    global _scrape_state
    _scrape_state.update(status="running", message="Iniciando scraping futbin...", current=0, total=0)

    started_at = datetime.now(UTC)
    scraped_count = 0
    errors = []

    try:
        timeout = aiohttp.ClientTimeout(total=120)
        connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT, force_close=True)
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as http:

            # ── Fase 1: Coletar lista de todos os SBCs ───────────────────
            _scrape_state["message"] = "Coletando lista de SBCs..."
            all_sbcs = []

            first_page_html = await _fetch(http, f"{BASE_URL}/squad-building-challenges")
            if not first_page_html:
                raise RuntimeError("Não foi possível acessar futbin.com")

            all_sbcs.extend(_parse_sbc_list(first_page_html))
            total_pages = _get_total_pages(first_page_html)

            # Páginas adicionais
            for page in range(2, total_pages + 1):
                await asyncio.sleep(DELAY_BETWEEN)
                page_html = await _fetch(http, f"{BASE_URL}/squad-building-challenges?page={page}")
                if page_html:
                    all_sbcs.extend(_parse_sbc_list(page_html))

            _scrape_state["total"] = len(all_sbcs)
            logger.info(f"Encontrados {len(all_sbcs)} SBCs em {total_pages} páginas")

            if not all_sbcs:
                raise RuntimeError("Nenhum SBC encontrado na listagem")

            # ── Fase 2: Limpar dados antigos (cascata manual) ─────────
            _scrape_state["message"] = "Limpando dados antigos..."
            await db.execute(delete(ChallengeRequirement))
            await db.execute(delete(SBCReward))
            await db.execute(delete(PlayerCard))
            await db.execute(delete(SBCChallenge))
            await db.execute(delete(SBCSet))
            await db.flush()

            # ── Fase 3: Processar cada SBC ───────────────────────────────
            sem = asyncio.Semaphore(MAX_CONCURRENT)

            for i, sbc_data in enumerate(all_sbcs):
                async with sem:
                    _scrape_state["current"] = i + 1
                    _scrape_state["message"] = f"Processando {i+1}/{len(all_sbcs)}: {sbc_data['name']}"

                    try:
                        await _process_single_sbc(http, db, sbc_data)
                        scraped_count += 1
                    except Exception as e:
                        error_msg = f"Erro em '{sbc_data['name']}': {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)

                    await asyncio.sleep(DELAY_BETWEEN)

            await db.commit()

        # ── Registrar log ────────────────────────────────────────────────
        status = "success" if not errors else "partial"
        log = ScrapeLog(
            source="futbin",
            status=status,
            sbcs_scraped=scraped_count,
            started_at=started_at,
            finished_at=datetime.now(UTC),
            error_message="; ".join(errors[:5]) if errors else None,
        )
        db.add(log)
        await db.commit()

        _scrape_state.update(
            status="completed",
            message=f"Concluído: {scraped_count} SBCs coletados",
            last_scrape_at=datetime.now(UTC).isoformat(),
            sbcs_count=scraped_count,
        )
        return {"status": status, "scraped": scraped_count, "errors": len(errors)}

    except Exception as e:
        logger.exception("Scraping falhou")
        _scrape_state.update(status="failed", message=str(e))

        log = ScrapeLog(
            source="futbin", status="failed", sbcs_scraped=scraped_count,
            started_at=started_at, finished_at=datetime.now(UTC),
            error_message=str(e),
        )
        db.add(log)
        await db.commit()
        return {"status": "failed", "scraped": scraped_count, "error": str(e)}


async def _process_single_sbc(
    http: aiohttp.ClientSession, db: AsyncSession, sbc_data: dict
):
    """Processa um SBC individual: busca detalhes, imagens, persiste."""
    sbc_id = sbc_data["futbin_id"]
    detail_url = f"{BASE_URL}/26/squad-building-challenge/{sbc_id}"

    # Buscar página de detalhe
    detail_html = await _fetch(http, detail_url)
    detail = _parse_sbc_detail(detail_html) if detail_html else {}

    # Determinar categoria
    category = detail.get("category", "upgrades")

    # Download da imagem principal do SBC
    local_image = ""
    if sbc_data.get("image_url"):
        fname = _sanitize_filename(f"sbc_{sbc_id}.png")
        local_image = await _download_image(http, sbc_data["image_url"], "sbcs", fname)

    # Criar SBCSet
    sbc_set = SBCSet(
        futgg_id=f"futbin-{sbc_id}",
        name=sbc_data["name"],
        description=detail.get("description", ""),
        category=category,
        total_cost=detail.get("total_cost_ps"),
        challenges_count=len(detail.get("challenges", [])),
        is_repeatable=False,
        is_new=sbc_data.get("is_new", False),
        image_url=local_image or sbc_data.get("image_url", ""),
        expires_text=sbc_data.get("expires_text", ""),
        raw_card_data=sbc_data.get("raw_card_data", None),
        scraped_at=datetime.now(UTC),
        source="futbin",
    )
    db.add(sbc_set)
    await db.flush()  # Para obter o ID

    # Processar challenges
    for idx, ch_data in enumerate(detail.get("challenges", [])):
        challenge = SBCChallenge(
            sbc_set_id=sbc_set.id,
            name=ch_data.get("name", f"Challenge {idx+1}"),
            description=ch_data.get("description", ""),
            estimated_cost=ch_data.get("estimated_cost_ps"),
            order_index=idx,
        )
        db.add(challenge)
        await db.flush()

        # Requisitos
        for req_data in ch_data.get("requirements", []):
            req = ChallengeRequirement(
                challenge_id=challenge.id,
                requirement_type=req_data["requirement_type"],
                operator=req_data["operator"],
                value=str(req_data["value"]),
                detail=req_data.get("detail"),
            )
            db.add(req)

        # Reward do challenge
        if ch_data.get("reward_name"):
            reward = SBCReward(
                challenge_id=challenge.id,
                reward_type="pack",
                name=ch_data["reward_name"],
                is_untradeable="untradeable" in ch_data.get("reward_name", "").lower(),
                image_url=ch_data.get("reward_image", ""),
            )
            db.add(reward)

    # Player card (se SBC de jogador)
    if detail.get("player_data"):
        pd = detail["player_data"]
        player_card = PlayerCard(
            sbc_set_id=sbc_set.id,
            name=sbc_data["name"],  # Nome já limpo do _parse_sbc_list
            overall=0,
            player_url=pd.get("url", ""),
        )
        db.add(player_card)

    logger.debug(f"✓ {sbc_data['name']} ({len(detail.get('challenges', []))} challenges)")
