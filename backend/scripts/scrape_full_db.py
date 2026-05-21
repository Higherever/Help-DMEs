import os
import sys
import asyncio
import json
import logging
import re
from pathlib import Path
from datetime import datetime, UTC

from bs4 import BeautifulSoup
import aiohttp

# Configurar path para importar módulos do backend
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from core.database import async_session_factory
from models.models import FCPlayer
from services.image_processor import download_and_process_card_bg

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("scrape_full_db")

STATE_FILE = BASE_DIR / "scripts" / "scraper_state.json"
MAX_CONCURRENT = 3
DELAY_BETWEEN = 2.5 # Evitar ban (Futbin bloqueia rápido)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def load_state():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"last_page": 0, "processed_bg_cache": {}}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

async def _fetch(session: aiohttp.ClientSession, url: str):
    for attempt in range(3):
        try:
            async with session.get(url, headers=HEADERS, ssl=True) as resp:
                if resp.status == 200:
                    return await resp.text()
                elif resp.status == 429:
                    wait = 30 * (attempt + 1)
                    logger.warning(f"Rate limit (429). Aguardando {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"Erro {resp.status} em {url}")
                    await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Falha de conexão: {e}")
            await asyncio.sleep(5)
    return None

async def process_page(session, db, page, state):
    url = f"https://www.futbin.com/players?page={page}"
    logger.info(f"Raspando página {page}...")
    html = await _fetch(session, url)
    if not html:
        return False

    soup = BeautifulSoup(html, "lxml")
    rows = soup.select("table#repTb tr.player_tr_1, table#repTb tr.player_tr_2")
    if not rows:
        logger.warning(f"Nenhum jogador encontrado na página {page}. Fim da lista?")
        return False

    bg_cache = state.setdefault("processed_bg_cache", {})

    for row in rows:
        try:
            # Dados básicos da tabela
            futbin_id = row.get("data-site-id") or row.get("data-player-id", "")
            if not futbin_id:
                continue

            name_el = row.select_one("a.player_name_players_table")
            name = name_el.get_text(strip=True) if name_el else "Unknown"

            overall_el = row.select_one("span.rating")
            overall = int(overall_el.get_text(strip=True)) if overall_el else 0

            # As vezes a versão da carta vem escondida no elemento (ex: Gold, Rare)
            version_el = row.select_one(".mobile-hide-version")
            version = version_el.get_text(strip=True) if version_el else "Gold"

            # Club, Nation, League
            links = row.select("a[href*='/clubs/'], a[href*='/nations/'], a[href*='/leagues/']")
            club, nation, league = None, None, None
            for link in links:
                href = link.get("href", "")
                text = link.get("data-original-title", link.get("title", ""))
                if "/clubs/" in href: club = text
                elif "/nations/" in href: nation = text
                elif "/leagues/" in href: league = text

            pos_el = row.select_one(".font-weight-bold")
            position = pos_el.get_text(strip=True) if pos_el else ""

            # Imagem do Rosto (Face)
            face_img = row.select_one("img.player_img")
            face_url = face_img.get("data-original", face_img.get("src", "")) if face_img else ""
            
            # Tentar achar a imagem de fundo na mesma linha
            # Em listagens, o futbin esconde um mini playercard
            bg_img = row.select_one(".playercard-26-bg")
            bg_url = bg_img.get("src", "") if bg_img else ""

            card_template_url = None
            if bg_url:
                # Otimização híbrida: se já limpamos esse template, reutilizamos!
                if bg_url in bg_cache:
                    card_template_url = bg_cache[bg_url]
                else:
                    # Limpa o fundo via ImageMagick
                    local_bg = await download_and_process_card_bg(bg_url, f"global_{version.replace(' ', '_')}", session)
                    if local_bg:
                        bg_cache[bg_url] = local_bg
                        card_template_url = local_bg

            # Salvar no BD
            from sqlalchemy import select
            existing = await db.execute(select(FCPlayer).where(FCPlayer.futbin_id == str(futbin_id)))
            player = existing.scalar_one_or_none()
            
            if not player:
                player = FCPlayer(futbin_id=str(futbin_id))
                db.add(player)

            player.name = name
            player.overall = overall
            player.position = position
            player.nation = nation
            player.club = club
            player.league = league
            player.card_type = version
            player.face_url = face_url
            player.bg_url_raw = bg_url
            if card_template_url:
                player.card_template_url = card_template_url
            player.scraped_at = datetime.now(UTC)

        except Exception as e:
            logger.error(f"Erro processando jogador na pág {page}: {e}")

    await db.commit()
    
    # Atualiza estado
    state["last_page"] = page
    save_state(state)
    return True

async def main():
    state = load_state()
    start_page = state["last_page"] + 1
    
    logger.info(f"=== INICIANDO SCRAPE GLOBAL DE JOGADORES ===")
    logger.info(f"Retomando a partir da página: {start_page}")
    
    async with async_session_factory() as db:
        timeout = aiohttp.ClientTimeout(total=60)
        connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT, force_close=True)
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            
            page = start_page
            consecutive_empties = 0
            
            while consecutive_empties < 3:
                success = await process_page(session, db, page, state)
                if success:
                    consecutive_empties = 0
                else:
                    consecutive_empties += 1
                
                page += 1
                await asyncio.sleep(DELAY_BETWEEN)
                
    logger.info("=== SCRAPE FINALIZADO ===")

if __name__ == "__main__":
    asyncio.run(main())
