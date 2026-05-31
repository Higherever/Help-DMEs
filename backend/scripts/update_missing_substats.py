import asyncio
import logging
import sys
import unicodedata
import re
import os
import aiofiles
from pathlib import Path

# Configurar path para importar módulos do backend de qualquer lugar
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import text
from backend.core.database import async_session_factory
from backend.services.anti_bot import create_session
from backend.services.futbin_service import _fetch_and_parse_player

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
logger = logging.getLogger("update_missing_stats")

def to_snake_case(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-zA-Z0-9]+', '_', text.lower()).strip('_')
    return text

async def download_image(http, url: str, local_rel_path: str) -> bool:
    if not url:
        return False
    
    clean_url = url.split("?")[0] if "?" in url else url
    if clean_url.startswith("//"):
        clean_url = "https:" + clean_url
    clean_url = clean_url.replace("cdn3.futbin.com", "cdn.futbin.com")

    abs_path = BASE_DIR / local_rel_path.lstrip('/')
    
    if abs_path.exists() and abs_path.stat().st_size > 100:
        return True
        
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://www.futbin.com/"
    }
    try:
        async with http.get(clean_url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.read()
                if len(data) > 100:
                    async with aiofiles.open(abs_path, "wb") as f:
                        await f.write(data)
                    return True
    except Exception as e:
        logger.warning(f"Erro ao baixar {clean_url}: {e}")
        
    return False

async def update_missing_stats():
    async with async_session_factory() as db:
        # Busca apenas jogadores das duas tabelas que não têm aceleração (como proxy de sub-atributos ausentes)
        # Primeiro, FC_PLAYERS (Base de jogadores completa)
        result_fc = await db.execute(text("""
            SELECT id, futbin_id, name, face_url, nation_flag_url, club_logo_url, league_logo_url 
            FROM fc_players 
            WHERE futbin_id IS NOT NULL AND futbin_id NOT LIKE 'ea-%'
            AND (substats_source IS NULL OR substats_source != 'futbin')
            AND (
                acceleration IS NULL 
                OR card_type NOT IN ('Gold Rare', 'Gold Non Rare', 'Silver Rare', 'Silver Non Rare', 'Bronze Rare', 'Bronze Non Rare', 'Gold', 'Silver', 'Bronze')
                OR face_url IS NULL 
                OR face_url NOT LIKE '/images/%'
            )
        """))
        missing_fc = result_fc.fetchall()

        # Segundo, PLAYER_CARDS (Cartas de DMEs)
        # Para cartas de DME, o futbin_id pode ser nulo, mas a player_url estará preenchida.
        result_sbc = await db.execute(text("""
            SELECT id, futbin_id, player_url, name, face_url, nation_flag_url, club_logo_url, league_logo_url 
            FROM player_cards 
            WHERE (futbin_id IS NOT NULL OR player_url IS NOT NULL)
            AND (futbin_id IS NULL OR futbin_id NOT LIKE 'ea-%')
            AND (substats_source IS NULL OR substats_source != 'futbin')
            AND (
                face_url IS NULL 
                OR face_url NOT LIKE '/images/%'
            )
        """))
        missing_sbc = result_sbc.fetchall()

    logger.info(f"Encontrados {len(missing_fc)} na fc_players e {len(missing_sbc)} na player_cards sem sub-atributos.")

    all_missing = []
    for row in missing_fc:
        all_missing.append({"table": "fc_players", "id": row.id, "futbin_id": row.futbin_id, "player_url": None, "name": row.name, "face_url": row.face_url, "nation_flag_url": row.nation_flag_url, "club_logo_url": row.club_logo_url, "league_logo_url": row.league_logo_url})
    for row in missing_sbc:
        all_missing.append({"table": "player_cards", "id": row.id, "futbin_id": row.futbin_id, "player_url": row.player_url, "name": row.name, "face_url": row.face_url, "nation_flag_url": row.nation_flag_url, "club_logo_url": row.club_logo_url, "league_logo_url": row.league_logo_url})

    if not all_missing:
        logger.info("Nenhum registro precisa de atualização. Todos já possuem sub-atributos!")
        return

    # Iniciar sessão HTTP (Anti-Bot)
    async with create_session() as http:
        async with async_session_factory() as db:
            for item in all_missing:
                logger.info(f"Atualizando [{item['table']}] {item['name']}...")
                
                # Montar URL da página HD da carta
                if item["table"] == "player_cards" and item["player_url"]:
                    player_url = item["player_url"]
                else:
                    # O Futbin exige um slug no final da URL para não retornar 404
                    name_slug = unicodedata.normalize('NFKD', item['name']).encode('ASCII', 'ignore').decode('utf-8')
                    name_slug = re.sub(r'[^a-z0-9]+', '-', name_slug.lower()).strip('-') or 'player'
                    player_url = f"https://www.futbin.com/26/player/{item['futbin_id']}/{name_slug}"
                
                # Aproveitar nossa nova lógica de extração do Futbin
                data = await _fetch_and_parse_player(http, player_url)
                
                if not data or not data.get("acceleration"):
                    logger.warning(f"  ⚠ Não foi possível extrair atributos de {player_url}")
                    continue

                # Download das imagens e definição dos caminhos relativos
                futbin_face = data.get("face_url_hd")
                if futbin_face:
                    local_face = f"/images/cards/renders/{item['futbin_id']}.png"
                    success = await download_image(http, futbin_face, local_face)
                    data["face_url"] = local_face if success else item["face_url"]
                
                futbin_club = data.get("club_url")
                club_name = data.get("club_name")
                if futbin_club and club_name:
                    local_club = f"/images/cards/clubs/club_{to_snake_case(club_name)}.png"
                    success = await download_image(http, futbin_club, local_club)
                    data["club_logo_url"] = local_club if success else item["club_logo_url"]
                    
                futbin_nation = data.get("nation_url")
                nation_name = data.get("nation_name")
                if futbin_nation and nation_name:
                    local_nation = f"/images/cards/nations/nation_{to_snake_case(nation_name)}.png"
                    success = await download_image(http, futbin_nation, local_nation)
                    data["nation_flag_url"] = local_nation if success else item["nation_flag_url"]
                    
                futbin_league = data.get("league_url")
                league_name = data.get("league_name")
                if futbin_league and league_name:
                    local_league = f"/images/cards/leagues/league_{to_snake_case(league_name)}.png"
                    success = await download_image(http, futbin_league, local_league)
                    data["league_logo_url"] = local_league if success else item["league_logo_url"]

                # Preparar colunas que vieram do Futbin para UPDATE apenas dos que são NULL
                fields_to_update = [
                    "acceleration", "sprint_speed", "finishing", "shot_power",
                    "long_shots", "volleys", "positioning_att",
                    "short_passing", "long_passing", "crossing", "curve",
                    "free_kick", "vision", "agility", "balance", "reactions",
                    "ball_control", "composure", "skill_dribbling",
                    "interceptions", "heading", "marking",
                    "standing_tackle", "sliding_tackle",
                    "jumping", "stamina", "strength", "aggression", "penalties",
                    "gk_diving", "gk_handling", "gk_kicking", "gk_positioning", "gk_reflexes",
                    "face_url", "club_logo_url", "nation_flag_url", "league_logo_url"
                ]

                updates = []
                values = {"id": item["id"]}
                
                for field in fields_to_update:
                    if data.get(field) is not None:
                        # Sobrescreve o banco SE E SOMENTE SE o Futbin retornar um valor válido
                        updates.append(f'"{field}" = :{field}')
                        values[field] = data[field]

                if updates:
                    updates.append('"substats_source" = :substats_source')
                    values["substats_source"] = "futbin"
                    set_clause = ", ".join(updates)
                    query = f'UPDATE {item["table"]} SET {set_clause} WHERE id = :id'
                    await db.execute(text(query), values)
                    await db.commit()
                    logger.info(f"  ✅ Sub-atributos salvos com sucesso!")
                
                # Delay de segurança anti-bot (1 a 2 segundos)
                await asyncio.sleep(1.5)

if __name__ == "__main__":
    asyncio.run(update_missing_stats())
