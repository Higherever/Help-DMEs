"""
Help DMEs — EA FC 26 Ratings Scraper & Sync CLI
==================================================
Fase 1: Coleta todos os URLs e IDs de jogadores prata/bronze da listagem oficial da EA
Fase 2: Fetch assíncrono paralelo e humanizado das páginas de detalhe
Sincronização: Salva os playstyles na tabela fc_players e propaga para o elenco (user_squad)

Uso:
    python backend/scripts/scrape_ea_ratings.py --pages 1-5 [--test]
"""

import asyncio
import aiohttp
import json
import sqlite3
import time
import re
import sys
import argparse
import logging
from bs4 import BeautifulSoup
from datetime import datetime, UTC
from pathlib import Path
from backend.services.asset_downloader import AssetDownloader

# ─── CONFIGURAÇÕES E PATHS ───────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Banco de dados oficial do projeto
DATABASE_FILE = PROJECT_ROOT / "database" / "help_dmes.db"

BASE_URL = "https://www.ea.com"
RATINGS_URL = f"{BASE_URL}/games/ea-sports-fc/ratings"

# Prata: OVR 65–74 | Bronze: OVR 47–64
RATING_RANGES = {
    "silver": (65, 74),
    "bronze": (47, 64),
}

# Configurar logging premium com cores/formato limpo
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / "logs" / "scrape_ea_ratings.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("ea_ratings_scraper")

# Headers humanizados com Pool rotativo simples
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0"
}

# ─── BANCO DE DADOS E SCHEMA MIGRATION ───────────────────────────────────────

def migrate_database_schema(db_path: str):
    """Garante que as colunas necessárias existam no banco de dados local help_dmes.db de forma idempotente."""
    logger.info("Verificando consistência do schema de fc_players e user_squad...")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Garantir que a tabela fc_players tenha a coluna ea_id
    cur.execute("PRAGMA table_info(fc_players)")
    cols = {row[1] for row in cur.fetchall()}
    if "ea_id" not in cols:
        logger.info("Adicionando coluna 'ea_id' na tabela 'fc_players'...")
        try:
            cur.execute('ALTER TABLE fc_players ADD COLUMN "ea_id" TEXT')
            cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_fc_players_ea_id ON fc_players(ea_id)')
            logger.info("✓ Coluna 'ea_id' adicionada com sucesso!")
        except Exception as e:
            logger.warning(f"  ⚠ Não foi possível adicionar ea_id via ALTER TABLE (talvez já exista): {e}")

    # 2. Garantir que a tabela user_squad tenha playstyles_json
    cur.execute("PRAGMA table_info(user_squad)")
    squad_cols = {row[1] for row in cur.fetchall()}
    if "playstyles_json" not in squad_cols:
        logger.info("Adicionando coluna 'playstyles_json' na tabela 'user_squad'...")
        try:
            cur.execute('ALTER TABLE user_squad ADD COLUMN "playstyles_json" TEXT')
            logger.info("✓ Coluna 'playstyles_json' adicionada com sucesso!")
        except Exception as e:
            logger.warning(f"  ⚠ Não foi possível adicionar playstyles_json via ALTER TABLE (talvez já exista): {e}")

    # 3. Criar a tabela de log de scrape da EA se não existir
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ea_scrape_log (
                ea_id       TEXT PRIMARY KEY,
                status      TEXT,  -- 'ok', 'error', 'skip'
                timestamp   TEXT
            )
        """)
    except Exception as e:
        logger.warning(f"  ⚠ Não foi possível criar tabela ea_scrape_log: {e}")
    
    conn.commit()
    conn.close()
    logger.info("✓ Schema do banco de dados verificado e compatibilizado!")


# ─── FASE 1: COLETAR URLs E IDS DA LISTAGEM ───────────────────────────────────

async def fetch_listing_page(session: aiohttp.ClientSession, page: int = 1) -> str:
    """Busca a página de listagem com parâmetros de paginação e headers premium."""
    # A EA gerencia paginação via query string
    params = {"page": page}
    async with session.get(RATINGS_URL, params=params, headers=HEADERS, timeout=20) as resp:
        if resp.status != 200:
            logger.error(f"Erro HTTP {resp.status} ao acessar página de listagem {page}")
            return ""
        return await resp.text()


def parse_players_from_listing(html: str) -> list[dict]:
    """
    Parseia a página de listagem da EA Sports.
    Suporta tabelas estáticas server-rendered e tags Next.js __NEXT_DATA__ para máxima resiliência!
    """
    players = []
    if not html:
        return players

    soup = BeautifulSoup(html, "html.parser")

    # --- Abordagem 1: Extração via tags de tabela HTML ---
    # O site da EA FC Ratings tradicionalmente expõe jogadores em links dentro de tr/td
    rows = soup.select("table tr, div[class*='row'], div[class*='PlayerRow']")
    for row in rows:
        link = row.select_one("a[href*='/player-ratings/'], a[href*='/ratings/player-ratings/']")
        if not link:
            continue

        href = link.get("href", "")
        # Extrai o EA ID numérico da URL: /ratings/player-ratings/{slug}/{ea_id}
        match = re.search(r"/player-ratings/[^/]+/(\d+)$", href)
        if not match:
            # Tentar match secundário sem o prefixo do slug
            match = re.search(r"/(\d+)$", href)
            if not match:
                continue

        ea_id = match.group(1)

        # Tentar ler o Overall (OVR)
        ovr_el = (
            row.select_one("[class*='ovr']") or
            row.select_one("[class*='rating']") or
            row.select_one("td:nth-child(6)") or
            row.select_one("div:nth-child(6)")
        )
        ovr = 0
        if ovr_el:
            try:
                ovr = int(re.sub(r"\D", "", ovr_el.get_text()))
            except Exception:
                pass

        # Filtrar pratas (65-74) e bronzes (47-64)
        rarity = None
        if 65 <= ovr <= 74:
            rarity = "silver"
        elif 47 <= ovr <= 64:
            rarity = "bronze"
        else:
            # Se não conseguir descobrir o rating na listagem, guardamos como pendente para filtrar na página individual
            rarity = "pending"

        name = link.get_text(strip=True)
        full_url = href if href.startswith("http") else f"{BASE_URL}{href}"

        players.append({
            "ea_id": ea_id,
            "name": name,
            "overall": ovr,
            "rarity": rarity,
            "url": full_url,
        })

    # --- Abordagem 2 (Fallback Premium): Extração direta do __NEXT_DATA__ JSON ---
    if not players:
        next_data_script = soup.select_one("script#__NEXT_DATA__")
        if next_data_script:
            try:
                json_data = json.loads(next_data_script.string)
                # Navegar na árvore do Next.js buscando a lista de jogadores
                # Geralmente fica em props.pageProps.initialState.ratings.items ou similar
                props = json_data.get("props", {}).get("pageProps", {})
                
                # Tenta localizar listas recursivamente
                def find_player_items(d):
                    if isinstance(d, dict):
                        if "items" in d and isinstance(d["items"], list) and len(d["items"]) > 0:
                            if "eaId" in d["items"][0] or "id" in d["items"][0] or "firstName" in d["items"][0]:
                                return d["items"]
                        for v in d.values():
                            res = find_player_items(v)
                            if res: return res
                    elif isinstance(d, list):
                        for item in d:
                            res = find_player_items(item)
                            if res: return res
                    return None

                items = find_player_items(props)
                if items:
                    for item in items:
                        ea_id = str(item.get("id") or item.get("eaId") or "")
                        if not ea_id: continue
                        
                        ovr = int(item.get("overallRating") or item.get("rating") or 0)
                        
                        # Filtrar pratas e bronzes
                        rarity = None
                        if 65 <= ovr <= 74:
                            rarity = "silver"
                        elif 47 <= ovr <= 64:
                            rarity = "bronze"
                        else:
                            continue

                        name = item.get("displayName") or f"{item.get('firstName', '')} {item.get('lastName', '')}".strip()
                        slug = item.get("slug") or name.lower().replace(" ", "-")
                        full_url = f"{BASE_URL}/games/ea-sports-fc/ratings/player-ratings/{slug}/{ea_id}"
                        
                        players.append({
                            "ea_id": ea_id,
                            "name": name,
                            "overall": ovr,
                            "rarity": rarity,
                            "url": full_url,
                        })
                    logger.info(f"✓ Extraídos {len(players)} jogadores via __NEXT_DATA__ JSON do Next.js!")
            except Exception as e:
                logger.debug(f"Falha ao parsear __NEXT_DATA__: {e}")

    return players


async def collect_all_player_urls(session: aiohttp.ClientSession, start_page: int, end_page: int, delay: float) -> list[dict]:
    """Itera e coleta jogadores prata e bronze de um range de páginas da EA Ratings."""
    all_players = []
    total_pages = end_page - start_page + 1
    logger.info(f"📋 Iniciando Fase 1: Coletando listagem das páginas {start_page} a {end_page}...")

    for idx, page in enumerate(range(start_page, end_page + 1), 1):
        percent = (idx / total_pages) * 100
        logger.info(f"  → Acessando Página {page}/{end_page} ({percent:.1f}%) ...")
        try:
            html = await fetch_listing_page(session, page)
            batch = parse_players_from_listing(html)
            if not batch:
                logger.warning(f"  ⚠ Nenhum jogador encontrado na página {page}. Fim da listagem ou anti-bot detectado.")
                break
            
            # Filtrar apenas pratas, bronzes e indefinidos (pending)
            filtered_batch = [p for p in batch if p["rarity"] in ("silver", "bronze", "pending")]
            all_players.extend(filtered_batch)
            logger.info(f"    ✓ {len(filtered_batch)} jogadores prata/bronze qualificados na página (Total coletado: {len(all_players)})")
            
            # Delay gaussiano humanizado
            import random
            gaussian_delay = random.gauss(delay, delay * 0.25)
            gaussian_delay = max(0.1, gaussian_delay)  # Evitar delays negativos ou excessivamente curtos
            await asyncio.sleep(gaussian_delay)
        except Exception as e:
            logger.error(f"  ✗ Falha ao processar página {page}: {e}")
            break

    # Deduplicação robusta baseada em ea_id
    seen = set()
    unique = []
    for p in all_players:
        if p["ea_id"] not in seen:
            seen.add(p["ea_id"])
            unique.append(p)

    logger.info(f"\n✅ Fase 1 Concluída! Total de {len(unique)} jogadores prata/bronze únicos mapeados.")
    
    # Alerta crítico de manutenção/anti-bot caso a coleta de um escopo amplo retorne poucos jogadores
    pages_count = end_page - start_page + 1
    if pages_count >= 150 and len(unique) < 8000:
        logger.critical(
            "\n" + "🚨" * 30 +
            "\n🚨 ALERTA CRÍTICO DE MANUTENÇÃO DO SCRAPER 🚨\n"
            f"Detectado um número anormalmente baixo de jogadores prata/bronze ({len(unique)}) para o range de {pages_count} páginas.\n"
            "Isso geralmente indica que:\n"
            "1. A EA Sports FC Ratings alterou a estrutura do Next.js ou o padrão do JSON '__NEXT_DATA__'.\n"
            "2. Uma proteção anti-bot agressiva (como Cloudflare ou rate limiting rigoroso) bloqueou a listagem de forma silenciosa.\n"
            "Por favor, verifique o site oficial e audite o script do scraper de ratings.\n" +
            "🚨" * 30 + "\n"
        )
        
    return unique


# ─── FASE 2: RASPAGEM ASSÍNCRONA E INDIVIDUAL DE PLAYSTYLES ───────────────────

def parse_playstyles_from_player_page(html: str) -> list[dict]:
    """
    Parseia a página de detalhe do jogador na EA Sports Ratings.
    Identifica playstyles normais e Playstyles Plus (is_plus=True).
    """
    soup = BeautifulSoup(html, "html.parser")
    playstyles = []

    # Seletor baseado em links ou containers de Habilidades / Habilidades Especiais
    # A EA usa links apontando para abilities-ratings
    abilities_links = soup.select("a[href*='/abilities-ratings/'], div[class*='playstyle'], div[class*='ability']")
    
    for link in abilities_links:
        # Se for link, tentar pegar o nome da tag
        name_el = (
            link.select_one("h5") or
            link.select_one("strong") or
            link.select_one("p") or
            link.select_one("[class*='name']")
        )
        name = name_el.get_text(strip=True) if name_el else link.get_text(strip=True)
        if not name:
            continue

        href = link.get("href", "") if hasattr(link, "get") else ""
        
        # Dedução de Playstyle+ (Plus)
        # 1. URL contém 'play-style-plus'
        # 2. O nome termina com '+' (ex: 'Finesse Shot+')
        # 3. Componente possui classe que indica plus
        is_plus = "play-style-plus" in href or "plus" in str(link.get("class", "")).lower() or name.endswith("+")

        cleaned_name = name.rstrip("+").strip()
        
        # Evitar duplicatas
        if not any(ps["name"] == cleaned_name for ps in playstyles):
            playstyles.append({
                "name": cleaned_name,
                "is_plus": is_plus,
                "icon_url": "" # O renderizador carrega localmente baseado no nome
            })

    # Fallback: se nenhum playstyle for achado por seletores, buscar texto plano em scripts ou divs
    if not playstyles:
        # Padrões comuns no JSON injetado
        playstyle_matches = re.findall(r'"playstyle"\s*:\s*"([^"]+)"', html, re.I)
        for pm in playstyle_matches:
            if pm not in [ps["name"] for ps in playstyles]:
                playstyles.append({
                    "name": pm.strip(),
                    "is_plus": False,
                    "icon_url": ""
                })

    return playstyles


def parse_player_details(html: str, player: dict) -> dict:
    """Extrai estatísticas e playstyles adicionais da página individual do jogador na EA."""
    soup = BeautifulSoup(html, "html.parser")

    # Extrair estatísticas (PAC, SHO, PAS, DRI, DEF, PHY)
    stats_map = {"pac": None, "sho": None, "pas": None, "dri": None, "def": None, "phy": None}
    
    # Varre todos os textos procurando padrões como "Pace 82", "Shooting 65", etc.
    text_blocks = soup.select("li, div, span, td")
    stat_labels = {
        "Pace": "pac", "Shooting": "sho", "Passing": "pas", 
        "Dribbling": "dri", "Defending": "def", "Physicality": "phy", "Physical": "phy"
    }
    
    for block in text_blocks:
        text = block.get_text(strip=True)
        for label, key in stat_labels.items():
            m = re.match(rf"^{label}\s*(\d+)$", text, re.I)
            if m:
                stats_map[key] = int(m.group(1))

    # Posição
    pos_el = soup.select_one("[class*='position'], [class*='preferredPosition']")
    position = pos_el.get_text(strip=True) if pos_el else player.get("position")

    # Playstyles
    playstyles = parse_playstyles_from_player_page(html)

    # Extrair URLs e Nomes de Clube, Nação, Liga e Face/Foto
    club = player.get("club", "")
    nation = player.get("nation", "")
    league = player.get("league", "")
    
    # 1. Clube
    club_img = soup.select_one("img[src*='/clubs/'], img[src*='/crests/'], img[class*='crest'], img[class*='club']")
    club_logo_url = club_img.get("src", "") if club_img else ""
    if club_img and not club:
        club = (club_img.get("alt") or club_img.get("title") or "").strip()
    if not club:
        club_el = soup.select_one("[class*='clubName'], [class*='club-name'], [class*='team-name']")
        if club_el:
            club = club_el.get_text(strip=True)

    # 2. Nação
    nation_img = soup.select_one("img[src*='/nation/'], img[src*='nations/'], img[src*='nation_flags/'], img[src*='/flags/'], img[class*='flag']")
    nation_flag_url = nation_img.get("src", "") if nation_img else ""
    if nation_img and not nation:
        nation = (nation_img.get("alt") or nation_img.get("title") or "").strip()
    if not nation:
        nation_el = soup.select_one("[class*='nationalityName'], [class*='nation-name']")
        if nation_el:
            nation = nation_el.get_text(strip=True)

    # 3. Liga
    league_img = soup.select_one("img[src*='/leagues/'], img[class*='league']")
    league_logo_url = league_img.get("src", "") if league_img else ""
    if league_img and not league:
        league = (league_img.get("alt") or league_img.get("title") or "").strip()
    if not league:
        league_el = soup.select_one("[class*='leagueName'], [class*='league-name']")
        if league_el:
            league = league_el.get_text(strip=True)

    # 4. Face/Render
    face_img = soup.select_one("img[class*='player-image'], img[class*='avatar'], img[src*='/players/'], img[src*='/renders/']")
    face_url = face_img.get("src", "") if face_img else ""

    return {
        **player,
        "position": position,
        "pace": stats_map["pac"],
        "shooting": stats_map["sho"],
        "passing": stats_map["pas"],
        "dribbling_stat": stats_map["dri"],
        "defending": stats_map["def"],
        "physic": stats_map["phy"],
        "playstyles": playstyles,
        "club": club,
        "nation": nation,
        "league": league,
        "face_url_raw": face_url,
        "nation_flag_url": nation_flag_url,
        "club_logo_url": club_logo_url,
        "league_logo_url": league_logo_url,
        "scraped_at": datetime.now(UTC).isoformat(),
    }


async def scrape_single_player(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    player: dict,
    db_path: str,
    stats: dict,
    delay: float
) -> bool:
    """Faz o scraping assíncrono de um jogador com semáforo, persistindo diretamente no banco do projeto."""
    async with semaphore:
        ea_id = player["ea_id"]

        # 1. Verificar se o jogador já foi coletado com sucesso anteriormente
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM ea_scrape_log WHERE ea_id = ?", (ea_id,))
        row = cursor.fetchone()
        if row and row[0] == "ok":
            stats["skipped"] += 1
            conn.close()
            return True

        # Delay gaussiano humanizado
        import random
        gaussian_delay = random.gauss(delay, delay * 0.25)
        gaussian_delay = max(0.1, gaussian_delay)  # Evitar delays negativos ou excessivamente curtos
        await asyncio.sleep(gaussian_delay)

        try:
            # Acessar a página de detalhes do jogador na EA
            async with session.get(
                player["url"],
                headers=HEADERS,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"HTTP {resp.status}")
                html = await resp.text()

            # Parsear dados
            data = parse_player_details(html, player)

            # 1.5. Baixar e higienizar todos os assets (faces, bandeiras, clubes, ligas) localmente
            # Geramos um futbin_id temporário para ser usado como chave física no disco
            temp_futbin_id = f"ea-{ea_id}"
            local_assets = {}
            try:
                # O downloader do AssetDownloader centralizado fará os downloads em paralelo
                local_assets = await AssetDownloader.enrich_and_download_player_assets(session, data, temp_futbin_id, semaphore)
            except Exception as download_err:
                logger.warning(f"  ⚠ Falha ao baixar assets para {data['name']}: {download_err}")

            # 2. Persistir no catálogo global (fc_players) do projeto
            # A tabela fc_players tem colunas como: futbin_id, ea_id, name, overall, position, playstyles_json, etc.
            # Verificamos se o jogador já existe na tabela por ea_id ou nome/overall para sincronizar
            cursor.execute("SELECT id, playstyles_json FROM fc_players WHERE ea_id = ? OR (name = ? AND overall = ?)", 
                           (ea_id, data["name"], data["overall"]))
            existing = cursor.fetchone()

            playstyles_str = json.dumps(data["playstyles"], ensure_ascii=False) if data["playstyles"] else None

            # Construir queries seguras
            if existing:
                # Se já existe, atualizamos as colunas coletadas
                cursor.execute("""
                    UPDATE fc_players 
                    SET ea_id = ?, position = ?, playstyles_json = ?, scraped_at = ?,
                        pace = COALESCE(pace, ?), shooting = COALESCE(shooting, ?), 
                        passing = COALESCE(passing, ?), dribbling_stat = COALESCE(dribbling_stat, ?), 
                        defending = COALESCE(defending, ?), physic = COALESCE(physic, ?),
                        club = COALESCE(club, ?), nation = COALESCE(nation, ?), league = COALESCE(league, ?),
                        face_url = COALESCE(face_url, ?), render_url = COALESCE(render_url, ?),
                        nation_flag_url = COALESCE(nation_flag_url, ?), club_logo_url = COALESCE(club_logo_url, ?),
                        league_logo_url = COALESCE(league_logo_url, ?), bg_url_hd = COALESCE(bg_url_hd, ?)
                    WHERE id = ?
                """, (
                    ea_id, data.get("position"), playstyles_str, data["scraped_at"],
                    data.get("pace"), data.get("shooting"), data.get("passing"), 
                    data.get("dribbling_stat"), data.get("defending"), data.get("physic"),
                    data.get("club"), data.get("nation"), data.get("league"),
                    local_assets.get("face_url"), local_assets.get("render_url"),
                    local_assets.get("nation_flag_url"), local_assets.get("club_logo_url"),
                    local_assets.get("league_logo_url"), local_assets.get("card_template_url") or local_assets.get("bg_url_hd"),
                    existing[0]
                ))
            else:
                # Se não existe, inserimos um novo registro (geramos um futbin_id temporário)
                cursor.execute("""
                    INSERT INTO fc_players 
                    (futbin_id, ea_id, name, overall, position, playstyles_json, scraped_at,
                     pace, shooting, passing, dribbling_stat, defending, physic,
                     club, nation, league, face_url, render_url, nation_flag_url, club_logo_url, league_logo_url, bg_url_hd)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    temp_futbin_id, ea_id, data["name"], data["overall"], data.get("position"), 
                    playstyles_str, data["scraped_at"], data.get("pace"), data.get("shooting"), 
                    data.get("passing"), data.get("dribbling_stat"), data.get("defending"), data.get("physic"),
                    data.get("club"), data.get("nation"), data.get("league"),
                    local_assets.get("face_url"), local_assets.get("render_url"),
                    local_assets.get("nation_flag_url"), local_assets.get("club_logo_url"),
                    local_assets.get("league_logo_url"), local_assets.get("card_template_url") or local_assets.get("bg_url_hd")
                ))

            # 3. Registrar o sucesso no log de scraping
            cursor.execute("INSERT OR REPLACE INTO ea_scrape_log (ea_id, status, timestamp) VALUES (?, 'ok', ?)",
                           (ea_id, datetime.now(UTC).isoformat()))
            
            conn.commit()
            stats["success"] += 1
            logger.info(f"  ✓ {data['name']} (OVR:{data['overall']}) enriquecido com {len(data['playstyles'])} playstyles!")
            return True

        except Exception as e:
            cursor.execute("INSERT OR REPLACE INTO ea_scrape_log (ea_id, status, timestamp) VALUES (?, 'error', ?)",
                           (ea_id, datetime.now(UTC).isoformat()))
            conn.commit()
            stats["errors"] += 1
            logger.error(f"  ✗ Erro ao coletar playstyles de {player['name']} ({ea_id}): {e}")
            return False
        finally:
            conn.close()


# ─── FASE 3: PROPAGAÇÃO PARA O ELENCO (USER SQUAD) ───────────────────────────

def propagate_playstyles_to_user_squad(db_path: str) -> int:
    """
    Propaga os playstyles coletados no catálogo global fc_players para os
    jogadores do elenco do usuário na tabela user_squad de forma auditada e transparente,
    exibindo métricas detalhadas de matching e listando eventuais falhas.
    """
    logger.info("🔗 Iniciando sincronização e propagação de playstyles para o elenco (user_squad)...")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Contar estado inicial de pratas e bronzes no elenco
    cur.execute("SELECT COUNT(*) FROM user_squad WHERE rating <= 74")
    total_silver_bronze = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM user_squad WHERE rating <= 74 AND playstyles_json IS NOT NULL")
    already_had_playstyles = cur.fetchone()[0]

    # 2. Query de atualização direta em lote (Fase 3 - Cruzamento exato de DefinitionId)
    cur.execute("""
        UPDATE user_squad 
        SET playstyles_json = (
            SELECT playstyles_json 
            FROM fc_players 
            WHERE fc_players.ea_id = user_squad.definition_id
        )
        WHERE definition_id IN (
            SELECT ea_id 
            FROM fc_players 
            WHERE playstyles_json IS NOT NULL
        )
    """)
    affected = cur.rowcount
    conn.commit()

    # 3. Mapeamento de fallback secundário por Nome + Overall caso definition_id divirja
    cur.execute("""
        UPDATE user_squad
        SET playstyles_json = (
            SELECT playstyles_json 
            FROM fc_players 
            WHERE LOWER(fc_players.name) = LOWER(user_squad.name) 
              AND fc_players.overall = user_squad.rating
            LIMIT 1
        )
        WHERE playstyles_json IS NULL 
          AND EXISTS (
              SELECT 1 
              FROM fc_players 
              WHERE LOWER(fc_players.name) = LOWER(user_squad.name) 
                AND fc_players.overall = user_squad.rating
                AND playstyles_json IS NOT NULL
          )
    """)
    fallback_affected = cur.rowcount
    conn.commit()

    # 4. Auditoria de matching detalhada
    cur.execute("SELECT COUNT(*) FROM user_squad WHERE rating <= 74 AND playstyles_json IS NOT NULL")
    updated_had_playstyles = cur.fetchone()[0]
    
    # Jogadores prata/bronze que continuam sem playstyles
    cur.execute("SELECT name, rating, preferred_position FROM user_squad WHERE rating <= 74 AND playstyles_json IS NULL")
    orphaned_players = cur.fetchall()
    
    conn.close()

    logger.info(f"✅ Propagação Concluída com Sucesso!")
    logger.info(f"   ↳ 📊 Total de jogadores Prata/Bronze no seu elenco: {total_silver_bronze}")
    logger.info(f"   ↳ 🔄 Jogadores com playstyles antes da sincronização: {already_had_playstyles}")
    logger.info(f"   ↳ 🔌 Atualizados via cruzamento exato (DefinitionId): {affected}")
    logger.info(f"   ↳ 🧩 Atualizados via fallback secundário (Nome + Rating): {fallback_affected}")
    logger.info(f"   ↳ 📈 Total com playstyles após sincronização: {updated_had_playstyles} ({updated_had_playstyles/max(1, total_silver_bronze)*100:.1f}%)")

    if orphaned_players:
        logger.warning(f"  ⚠ Alerta: {len(orphaned_players)} jogadores prata/bronze do seu elenco continuaram SEM MATCH de playstyle:")
        for idx, p in enumerate(orphaned_players, 1):
            logger.warning(f"     [{idx}] Nome: {p[0]:<25} | Rating: {p[1]} | Pos: {p[2]}")
        logger.info("  💡 Dica: Você pode rodar o scraper da EA em um range de páginas maior (ex: --pages 1-10) para encontrar esses jogadores e preencher seus playstyles!")
    else:
        logger.info("  🎉 Excelente! 100% dos seus jogadores prata/bronze no elenco foram mapeados e enriquecidos com playstyles!")

    return affected + fallback_affected


# ─── EXPORTAÇÃO JSON DE BACKUP ───────────────────────────────────────────────

def export_json_backup(db_path: str, output_json: Path):
    """Gera um arquivo JSON de backup consolidado contendo os playstyles coletados."""
    logger.info(f"💾 Exportando backup JSON consolidado para: {output_json}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT ea_id, name, overall, position, playstyles_json, scraped_at 
        FROM fc_players 
        WHERE ea_id IS NOT NULL AND playstyles_json IS NOT NULL
    """)
    
    backup_data = []
    for r in cur.fetchall():
        try:
            ps = json.loads(r["playstyles_json"])
        except Exception:
            ps = []
            
        backup_data.append({
            "ea_id": r["ea_id"],
            "name": r["name"],
            "overall": r["overall"],
            "position": r["position"],
            "playstyles": ps,
            "scraped_at": r["scraped_at"]
        })
    
    conn.close()
    
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=2)
    logger.info(f"✅ Backup JSON exportado com sucesso contendo {len(backup_data)} jogadores!")


# ─── INTERFACE E FUNÇÃO PRINCIPAL ────────────────────────────────────────────

async def main(start_page: int, end_page: int, test_mode: bool, max_concurrent: int, delay: float, progress_callback=None):
    print("=" * 70)
    print("  EA SPORTS FC 26 — Coletor e Sincronizador de PlayStyles (Prata & Bronze)")
    print("=" * 70)
    print(f"  Banco de dados: {DATABASE_FILE}")
    print(f"  Páginas a raspar: {start_page} a {end_page}")
    print(f"  Modo de teste: {'ATIVADO (limite de 5 p/ página)' if test_mode else 'DESATIVADO (completo)'}")
    print(f"  Concorrência Máxima: {max_concurrent} requisições simultâneas")
    print(f"  Delay humanizado: {delay}s")
    print("=" * 70 + "\n")

    start_time = time.time()

    if progress_callback:
        progress_callback("Verificando consistência do banco de dados...", 0, 100)

    # 1. Garantir que as tabelas existam e possuam colunas corretas
    migrate_database_schema(str(DATABASE_FILE))

    if progress_callback:
        progress_callback(f"Fase 1: Coletando URLs da listagem da EA (Páginas {start_page}-{end_page})...", 10, 100)

    stats = {"success": 0, "errors": 0, "skipped": 0}
    semaphore = asyncio.Semaphore(max_concurrent)

    connector = aiohttp.TCPConnector(limit=max_concurrent, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:

        # --- Fase 1: Coleta das URLs da listagem oficial da EA ---
        players = await collect_all_player_urls(session, start_page, end_page, delay)

        if not players:
            logger.error("Nenhum jogador qualificado encontrado. Encerrando coleta.")
            if progress_callback:
                progress_callback("Nenhum jogador prata/bronze qualificado encontrado na listagem.", 0, 0)
            return

        if test_mode:
            players = players[:5]
            logger.info(f"[Modo Teste] Limitado a processar apenas os 5 primeiros jogadores.")

        # --- Fase 2: Scraping paralelo das páginas individuais ---
        logger.info(f"\n🔄 Iniciando Fase 2: Coleta de playstyles de {len(players)} jogadores em paralelo...")
        if progress_callback:
            progress_callback(f"Fase 2: Coletando playstyles de {len(players)} jogadores em paralelo...", 20, 100)
        
        tasks = [
            scrape_single_player(session, semaphore, p, str(DATABASE_FILE), stats, delay)
            for p in players
        ]

        # Execução controlada em blocos para exibir progresso bonito
        batch_size = 50
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            await asyncio.gather(*batch, return_exceptions=True)

            done = min(i + batch_size, len(tasks))
            elapsed = time.time() - start_time
            rate = done / elapsed if elapsed > 0 else 0
            eta = (len(tasks) - done) / rate if rate > 0 else 0
            
            percent = (done / len(tasks)) * 100
            bar_width = 25
            filled = int(bar_width * done // len(tasks))
            bar_str = "█" * filled + "░" * (bar_width - filled)

            print(
                f"  [{bar_str}] {percent:.1f}% | "
                f"Progresso: {done}/{len(tasks)} | "
                f"✅ Sucessos: {stats['success']} | "
                f"⚠️  Erros: {stats['errors']} | "
                f"⏩ Pulados: {stats['skipped']} | "
                f"ETA: {eta/60:.1f}min"
            )
            
            if progress_callback:
                progress_percent = int(20 + (done / len(tasks)) * 60)
                progress_callback(
                    f"Fase 2: Raspando playstyles... {done}/{len(tasks)} processados (Sucessos: {stats['success']})",
                    done,
                    len(tasks)
                )

    # --- Fase 3: Propagação para o Elenco do Usuário (user_squad) ---
    if progress_callback:
        progress_callback("Fase 3: Propagando playstyles coletados para o seu elenco (user_squad)...", 85, 100)
    
    propagate_playstyles_to_user_squad(str(DATABASE_FILE))

    # --- Fase 4: Exportação de Backup JSON ---
    if progress_callback:
        progress_callback("Fase 4: Exportando backup JSON consolidado...", 95, 100)
        
    output_json_path = PROJECT_ROOT / "database" / "playstyles_prata_bronze.json"
    export_json_backup(str(DATABASE_FILE), output_json_path)

    elapsed_time = time.time() - start_time
    
    if progress_callback:
        progress_callback(
            f"Concluído! Sincronizados: {stats['success']} | Pulados: {stats['skipped']} | Erros: {stats['errors']}",
            len(tasks),
            len(tasks)
        )
        
    print("\n" + "=" * 70)
    print("  🏁 EXECUÇÃO CONCLUÍDA COM SUCESSO!")
    print(f"  Tempo decorrido: {elapsed_time/60:.1f} minutos")
    print(f"  📊 Sucessos:     {stats['success']}")
    print(f"  ⚠️  Erros:        {stats['errors']}")
    print(f"  ⏩ Pulados:      {stats['skipped']} (já atualizados no banco)")
    print(f"  💾 Backup JSON:  {output_json_path}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    def parse_pages(pages_str: str) -> tuple[int, int]:
        m = re.match(r"(\d+)[-–](\d+)", pages_str)
        if m:
            return int(m.group(1)), int(m.group(2))
        return int(pages_str), int(pages_str)

    parser = argparse.ArgumentParser(description="EA Sports FC 26 Ratings Playstyles Scraper")
    parser.add_argument("--pages", default="1-3", help="Páginas a varrer da listagem (Ex: '1-3' ou '5'). Default: 1-3")
    parser.add_argument("--test", action="store_true", help="Modo teste rápido: coleta apenas 5 jogadores")
    parser.add_argument("--concurrency", type=int, default=15, help="Nível de concorrência simultânea (10-25)")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay entre requisições (anti-bot)")
    
    args = parser.parse_args()
    
    sp, ep = parse_pages(args.pages)
    
    asyncio.run(main(
        start_page=sp, 
        end_page=ep, 
        test_mode=args.test, 
        max_concurrent=args.concurrency, 
        delay=args.delay
    ))
