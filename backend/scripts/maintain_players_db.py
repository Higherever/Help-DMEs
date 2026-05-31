"""
Help DMEs — Manutenção do DB de Jogadores
==========================================
Script para diagnóstico, migração de schema e re-scraping inteligente de jogadores
incompletos (sem sub-atributos ou sem portrait).
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Setup paths
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.database import async_session_factory
from sqlalchemy import text

from backend.scripts.reset_scrape_data import migrate_fc_players_schema
from backend.services.anti_bot import create_session
from backend.scripts.scrape_players_v2 import scrape_futbin_player_detail, upsert_player, save_player_images, BASE_CARD_TYPES, sanitize, IMG_SEM
from backend.services.asset_downloader import AssetDownloader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(BASE_DIR / "scripts" / "maintain_players_db.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger("maintain_db")

IMAGES_DIR = PROJECT_ROOT / "images"

async def count_missing_attributes(session) -> int:
    result = await session.execute(text("SELECT COUNT(*) FROM fc_players WHERE acceleration IS NULL"))
    return result.scalar() or 0

async def count_missing_portraits(session) -> int:
    types = tuple(BASE_CARD_TYPES)
    # create placeholder string like "?, ?, ?"
    placeholders = ", ".join([f"'{t}'" for t in types])
    query = f"SELECT COUNT(*) FROM fc_players WHERE LOWER(card_type) IN ({placeholders}) AND portrait_url IS NULL"
    try:
        result = await session.execute(text(query))
        return result.scalar() or 0
    except Exception as e:
        logger.warning("Coluna portrait_url ainda não existe. Será criada na Fase 2.")
        return "N/A (Requer Migração)"

async def get_incomplete_players(session, limit=None, card_type_filter=None):
    types_str = ", ".join([f"'{t}'" for t in BASE_CARD_TYPES])
    
    query = f"""
        SELECT id, futbin_id, name, card_type, portrait_url, acceleration
        FROM fc_players
        WHERE (acceleration IS NULL 
               OR (LOWER(card_type) IN ({types_str}) AND portrait_url IS NULL))
    """
    
    if card_type_filter:
        query += f" AND LOWER(card_type) = '{card_type_filter.lower()}'"
        
    if limit:
        query += f" LIMIT {limit}"
        
    result = await session.execute(text(query))
    return result.fetchall()

def verify_files_on_disk():
    portraits_dir = IMAGES_DIR / "cards" / "portraits"
    renders_dir = IMAGES_DIR / "cards" / "renders"
    templates_dir = IMAGES_DIR / "cards" / "templates"
    nations_dir = IMAGES_DIR / "cards" / "nations"
    clubs_dir = IMAGES_DIR / "cards" / "clubs"
    leagues_dir = IMAGES_DIR / "cards" / "leagues"
    
    counts = {
        "portraits": len(list(portraits_dir.glob("*.png"))) if portraits_dir.exists() else 0,
        "renders": len(list(renders_dir.glob("*.png"))) if renders_dir.exists() else 0,
        "templates": len(list(templates_dir.glob("*.png"))) if templates_dir.exists() else 0,
        "nations": len(list(nations_dir.glob("*.png"))) if nations_dir.exists() else 0,
        "clubs": len(list(clubs_dir.glob("*.png"))) if clubs_dir.exists() else 0,
        "leagues": len(list(leagues_dir.glob("*.png"))) if leagues_dir.exists() else 0,
    }
    return counts

async def phase1_diagnostic(session):
    logger.info("--- Fase 1: Diagnóstico ---")
    missing_accel = await count_missing_attributes(session)
    missing_port = await count_missing_portraits(session)
    logger.info(f"Jogadores sem sub-atributos (acceleration IS NULL): {missing_accel}")
    logger.info(f"Jogadores base sem portrait_url: {missing_port}")
    
    files = verify_files_on_disk()
    logger.info("Arquivos em disco:")
    logger.info(f"  Portraits: {files['portraits']}")
    logger.info(f"  Renders: {files['renders']}")
    logger.info(f"  Templates (dyn_*): {files['templates']}")
    logger.info(f"  Nations: {files['nations']}")
    logger.info(f"  Clubs: {files['clubs']}")
    logger.info(f"  Leagues: {files['leagues']}")
    logger.info("---------------------------")
    return missing_accel, missing_port

async def phase2_migration():
    logger.info("--- Fase 2: Migração de Schema ---")
    await migrate_fc_players_schema()
    logger.info("----------------------------------")

async def phase3_rescraping(session, limit, card_type, is_dry_run):
    logger.info("--- Fase 3: Re-scraping Inteligente ---")
    incompletes = await get_incomplete_players(session, limit, card_type)
    logger.info(f"Total de jogadores a processar nesta rodada: {len(incompletes)}")
    
    if is_dry_run:
        logger.info("[DRY-RUN] Nenhuma alteração será feita.")
        return
        
    if not incompletes:
        return
        
    # Inicializar sessão HTTP anti-bot
    http_session = create_session()
    
    processed = 0
    try:
        for row in incompletes:
            fid = row[1]
            p_name = row[2]
            c_type = row[3]
            slug = sanitize(p_name).replace("_", "-")
            p_url = f"https://www.futbin.com/26/player/{fid}/{slug}"
            
            logger.info(f"[{processed+1}/{len(incompletes)}] Scraping detalhe de {p_name} (ID: {fid}, Tipo: {c_type})")
            
            # Re-scrape da página de detalhe
            scraped_data = await scrape_futbin_player_detail(http_session, p_url, str(fid), c_type)
            
            if not scraped_data:
                logger.warning(f"Falha ao raspar dados de {p_name}")
                continue
                
            # Mesclar os dados novos mantendo valores originais que são importantes (ID, nome, URLs base, etc)
            # Para isso, vamos buscar a linha completa atual
            row_query = f"SELECT * FROM fc_players WHERE futbin_id = '{fid}'"
            res = await session.execute(text(row_query))
            current_row = res.mappings().fetchone()
            if not current_row:
                logger.warning(f"Jogador {fid} não encontrado ao buscar row completa.")
                continue
                
            # Atualizar os dados usando um dicionário para enviar pro upsert
            updated_data = dict(current_row)
            updated_data["futbin_id"] = fid
            
            # Regra Inviolável 4: NUNCA sobrescrever dados corretos
            for k, v in scraped_data.items():
                if v is not None and str(v).strip() != "":
                    # Só sobrescreve se o atual for nulo ou se for um campo que sempre se atualiza do detail
                    current_val = updated_data.get(k)
                    if current_val is None or str(current_val).strip() == "":
                        updated_data[k] = v
                    elif k in ["acceleration", "portrait_url", "portrait_resource_id"]: 
                        # Permite atualizar campos alvo da manutenção
                        updated_data[k] = v
            
            # Baixar novas imagens (portrait, flag, etc)
            img_paths = await AssetDownloader.enrich_and_download_player_assets(http_session, updated_data, str(fid), IMG_SEM)
            updated_data.update(img_paths)
            
            # Salvar no banco
            logger.info(f"Keys no updated_data antes do upsert: {list(updated_data.keys())}")
            await upsert_player(session, updated_data)
            await session.commit()
            processed += 1
            
    finally:
        await http_session.close()
        
    logger.info(f"Re-scraping concluído: {processed} processados.")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Apenas diagnóstico")
    parser.add_argument("--limit", type=int, help="Limitar re-scraping a N registros")
    parser.add_argument("--card-type", type=str, help="Filtrar por card-type (ex: gold)")
    args = parser.parse_args()

    async with async_session_factory() as session:
        # Phase 1
        await phase1_diagnostic(session)
        
        if not args.dry_run:
            # Phase 2
            await phase2_migration()
            
        # Phase 3
        await phase3_rescraping(session, args.limit, args.card_type, args.dry_run)
        
        if not args.dry_run:
            # Phase 4
            logger.info("--- Fase 4: Validação Final ---")
            await phase1_diagnostic(session)
            logger.info("Manutenção concluída.")

if __name__ == "__main__":
    asyncio.run(main())
