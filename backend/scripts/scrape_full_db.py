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
from services.card_screenshot import CardScreenshotService
from services.scraping_utils import sanitize_filename_part, create_thumbnail

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

async def process_page(session, db, page, state, screenshot_service):
    url = f"https://www.futbin.com/players?page={page}"
    logger.info(f"Raspando página {page}...")
    html = await _fetch(session, url)
    if not html:
        return False

    soup = BeautifulSoup(html, "lxml")
    rows = soup.select(".player-row")
    if not rows:
        logger.warning(f"Nenhum jogador encontrado na página {page}. Fim da lista?")
        return False

    bg_cache = state.setdefault("processed_bg_cache", {})

    for row in rows:
        try:
            # 1. Extração do ID do Futbin a partir do link da imagem do card
            card_link = row.select_one("a.player-row-playercard")
            if not card_link:
                continue
            href = card_link.get("href", "")
            match = re.search(r"/player/(\d+)/", href)
            if not match:
                continue
            futbin_id = match.group(1)

            # 2. Nome do jogador
            name_el = row.select_one("a.table-player-name")
            name = name_el.get_text(strip=True) if name_el else "Unknown"

            # 3. Overall / Rating
            rating_el = row.select_one(".table-rating")
            overall = int(rating_el.get_text(strip=True)) if rating_el else 0

            # 4. Posição
            pos_el = row.select_one(".table-pos")
            position = pos_el.get_text(strip=True) if pos_el else ""

            # 5. Versão
            version_el = row.select_one(".table-player-revision")
            version = version_el.get_text(strip=True) if version_el else "Gold"

            # 6. Club, Nation, League
            club_el = row.select_one(".table-player-club img")
            club = club_el.get("title") or club_el.get("data-original-title") if club_el else ""

            nation_el = row.select_one(".table-player-nation img")
            nation = nation_el.get("title") or nation_el.get("data-original-title") if nation_el else ""

            league_el = row.select_one(".table-player-league img")
            league = league_el.get("title") or league_el.get("data-original-title") if league_el else ""

            # 7. Imagens (Capturar a carta inteira por screenshot)
            player_url = f"https://www.futbin.com{href}" if not href.startswith("http") else href
            
            s_name = sanitize_filename_part(name)
            s_league = sanitize_filename_part(league or "unknown_league")
            s_country = sanitize_filename_part(nation or "unknown_country")
            s_club = sanitize_filename_part(club or "unknown_club")
            
            filename = f"fc_player_{futbin_id}_{s_name}_{s_league}_{s_country}_{s_club}.png"
            local_full_path = f"images/cards/full/{filename}"
            local_small_path = f"images/cards/small/{filename}"
            
            logger.info(f"Tentando tirar screenshot do card completo para o jogador {name} (ID: {futbin_id})...")
            success = await screenshot_service.take_card_screenshot(player_url, local_full_path)
            
            card_template_url = None
            face_url = None
            bg_url = ""
            
            if success:
                card_template_url = f"/images/cards/full/{filename}"
                logger.info(f"Screenshot com sucesso para {name}. Path: {card_template_url}")
                # Criar miniatura física
                create_thumbnail(local_full_path, local_small_path, width=150)
            else:
                logger.warning(f"Falha no screenshot para {name}. Utilizando fallback tradicional (rosto + fundo limpo)...")
                # Fallback tradicional:
                face_img = row.select_one("img.playercard-26-special-img") or row.select_one("img.player_img")
                face_url = face_img.get("data-original", face_img.get("src", "")) if face_img else ""
                
                bg_img = row.select_one("img.playercard-s-26-bg") or row.select_one("img.playercard-26-bg")
                bg_url = bg_img.get("src", "") if bg_img else ""

                if bg_url:
                    if bg_url in bg_cache:
                        card_template_url = bg_cache[bg_url]
                    else:
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
    
    screenshot_service = CardScreenshotService()
    
    async with async_session_factory() as db:
        timeout = aiohttp.ClientTimeout(total=60)
        connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT, force_close=True)
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            try:
                await screenshot_service.start()
                page = start_page
                consecutive_empties = 0
                
                while consecutive_empties < 3 and page <= 30:
                    success = await process_page(session, db, page, state, screenshot_service)
                    if success:
                        consecutive_empties = 0
                    else:
                        consecutive_empties += 1
                    
                    page += 1
                    await asyncio.sleep(DELAY_BETWEEN)
            finally:
                await screenshot_service.close()
                
    logger.info("=== SCRAPE FINALIZADO ===")

if __name__ == "__main__":
    asyncio.run(main())
