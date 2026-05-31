"""
Help DMEs — Script de Reset Seguro dos Dados de Scraping
=========================================================
Limpa todos os dados de scraping de jogadores (fc_players, player_cards)
e reseta o estado do scraper.

PRESERVA: sbc_sets, sbc_challenges, user_squad, app_settings, etc.
APAGA: fc_players, player_cards, scrape_logs (de jogadores)

Uso:
    cd backend
    python scripts/reset_scrape_data.py [--force]
"""

import asyncio
import argparse
import json
import sys
import logging
from pathlib import Path
from datetime import datetime, UTC

# Configurar path
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.database import async_session_factory, engine, DATABASE_FILE
from backend.models.models import Base

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("reset_scrape")


STATE_FILE = BASE_DIR / "scripts" / "scraper_state.json"
IMAGES_CARDS_FULL = PROJECT_ROOT / "images" / "cards" / "full"
IMAGES_CARDS_SMALL = PROJECT_ROOT / "images" / "cards" / "small"
IMAGES_RENDERS = PROJECT_ROOT / "images" / "cards" / "renders"
IMAGES_CLUBS = PROJECT_ROOT / "images" / "cards" / "clubs"
IMAGES_NATIONS = PROJECT_ROOT / "images" / "cards" / "nations"
IMAGES_LEAGUES = PROJECT_ROOT / "images" / "cards" / "leagues"


async def count_records(session, table_name: str) -> int:
    """Conta registros em uma tabela."""
    from sqlalchemy import text
    result = await session.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
    return result.scalar() or 0


async def reset_data(force: bool = False):
    """Executa o reset dos dados de scraping."""
    
    print("\n" + "="*60)
    print("  RESET DE DADOS DE SCRAPING")
    print("="*60)
    print(f"  Banco: {DATABASE_FILE}")
    print(f"  Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("="*60 + "\n")
    
    # Verificar estado atual
    async with async_session_factory() as session:
        fc_count = await count_records(session, "fc_players")
        pc_count = await count_records(session, "player_cards")
        logs_count = await count_records(session, "scrape_logs")
        sbc_count = await count_records(session, "sbc_sets")
        squad_count = await count_records(session, "user_squad")
    
    print("📊 Estado atual do banco:")
    print(f"   fc_players:   {fc_count:,} registros  ← SERÁ APAGADO")
    print(f"   player_cards: {pc_count:,} registros  ← SERÁ APAGADO")
    print(f"   scrape_logs:  {logs_count:,} registros  ← SERÁ APAGADO")
    print(f"   sbc_sets:     {sbc_count:,} registros  (preservado)")
    print(f"   user_squad:   {squad_count:,} registros  (preservado)")
    
    # Verificar imagens
    full_count = len(list(IMAGES_CARDS_FULL.glob("*.png"))) if IMAGES_CARDS_FULL.exists() else 0
    small_count = len(list(IMAGES_CARDS_SMALL.glob("*.png"))) if IMAGES_CARDS_SMALL.exists() else 0
    
    print(f"\n🖼️ Imagens em disco:")
    print(f"   images/cards/full/:  {full_count} PNGs  ← SERÁ APAGADO")
    print(f"   images/cards/small/: {small_count} PNGs  ← SERÁ APAGADO")
    print(f"   images/cards/templates/: (preservado)")
    
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            state = json.load(f)
        print(f"\n📄 scraper_state.json:")
        print(f"   Última página raspada: {state.get('last_page', 0)}")
        print(f"   Caches de BG: {len(state.get('processed_bg_cache', {}))} entradas")
    
    print("\n" + "="*60)
    
    if not force:
        confirm = input("\n⚠️  Confirma o reset? Digite 'CONFIRMAR' para prosseguir: ").strip()
        if confirm != "CONFIRMAR":
            print("❌ Reset cancelado.")
            return False
    else:
        print("\n🔄 Modo --force: executando sem confirmação...")
    
    print("\n🗑️  Iniciando limpeza...\n")
    
    # 1. Apagar registros do banco
    async with async_session_factory() as session:
        from sqlalchemy import text
        
        logger.info("Apagando player_cards...")
        await session.execute(text('DELETE FROM "player_cards"'))
        
        logger.info("Apagando fc_players...")
        await session.execute(text('DELETE FROM "fc_players"'))
        
        logger.info("Apagando scrape_logs...")
        await session.execute(text('DELETE FROM "scrape_logs"'))
        
        await session.commit()
        
        # Verificar limpeza
        fc_after = await count_records(session, "fc_players")
        pc_after = await count_records(session, "player_cards")
        
        print(f"   ✅ fc_players:   {fc_count} → {fc_after} registros")
        print(f"   ✅ player_cards: {pc_count} → {pc_after} registros")
        print(f"   ✅ scrape_logs:  {logs_count} → 0 registros")
    
    # 2. Resetar scraper_state.json
    new_state = {
        "last_page": 0,
        "processed_bg_cache": {},
        "reset_at": datetime.now(UTC).isoformat(),
        "version": "v2"
    }
    with open(STATE_FILE, "w") as f:
        json.dump(new_state, f, indent=2)
    print(f"\n   ✅ scraper_state.json resetado (página 0)")
    
    # 3. Limpar imagens de cards (full e small)
    deleted_images = 0
    for img_dir in [IMAGES_CARDS_FULL, IMAGES_CARDS_SMALL, IMAGES_RENDERS]:
        if img_dir.exists():
            for img in img_dir.glob("*.png"):
                img.unlink()
                deleted_images += 1
            for img in img_dir.glob("*.jpg"):
                img.unlink()
                deleted_images += 1
    
    print(f"   ✅ {deleted_images} imagens de cards apagadas")
    
    # 4. Garantir que diretórios de imagens existam
    for d in [IMAGES_CARDS_FULL, IMAGES_CARDS_SMALL, IMAGES_RENDERS, 
              IMAGES_CLUBS, IMAGES_NATIONS, IMAGES_LEAGUES]:
        d.mkdir(parents=True, exist_ok=True)
    print("   ✅ Estrutura de diretórios de imagens criada")
    
    # 5. Rodar VACUUM para compactar SQLite
    async with engine.begin() as conn:
        await conn.execute(__import__("sqlalchemy").text("VACUUM"))
    print("   ✅ VACUUM executado no banco")
    
    print("\n" + "="*60)
    print("  ✅ RESET COMPLETO! Pronto para novo scraping.")
    print("="*60 + "\n")
    
    return True


async def migrate_fc_players_schema():
    """
    Garante que a tabela fc_players tenha todas as colunas necessárias
    para o novo scraper v2. Adiciona colunas faltantes via ALTER TABLE.
    """
    logger.info("Verificando schema de fc_players...")
    
    new_columns = [
        # Stats principais
        ("pace",            "INTEGER"),
        ("shooting",        "INTEGER"),
        ("passing",         "INTEGER"),
        ("dribbling_stat",  "INTEGER"),
        ("defending",       "INTEGER"),
        ("physic",          "INTEGER"),
        # Sub-atributos PAC
        ("acceleration",    "INTEGER"),
        ("sprint_speed",    "INTEGER"),
        # Sub-atributos SHO
        ("finishing",       "INTEGER"),
        ("shot_power",      "INTEGER"),
        ("long_shots",      "INTEGER"),
        ("volleys",         "INTEGER"),
        ("positioning_att", "INTEGER"),
        ("penalties",       "INTEGER"),
        # Sub-atributos PAS
        ("short_passing",   "INTEGER"),
        ("long_passing",    "INTEGER"),
        ("crossing",        "INTEGER"),
        ("curve",           "INTEGER"),
        ("free_kick",       "INTEGER"),
        ("vision",          "INTEGER"),
        # Sub-atributos DRI
        ("agility",         "INTEGER"),
        ("balance",         "INTEGER"),
        ("reactions",       "INTEGER"),
        ("ball_control",    "INTEGER"),
        ("composure",       "INTEGER"),
        ("skill_dribbling", "INTEGER"),
        # Sub-atributos DEF
        ("interceptions",   "INTEGER"),
        ("heading",         "INTEGER"),
        ("marking",         "INTEGER"),
        ("standing_tackle", "INTEGER"),
        ("sliding_tackle",  "INTEGER"),
        # Sub-atributos PHY
        ("jumping",         "INTEGER"),
        ("stamina",         "INTEGER"),
        ("strength",        "INTEGER"),
        ("aggression",      "INTEGER"),
        # GK
        ("gk_diving",       "INTEGER"),
        ("gk_handling",     "INTEGER"),
        ("gk_kicking",      "INTEGER"),
        ("gk_positioning",  "INTEGER"),
        ("gk_reflexes",     "INTEGER"),
        # Metadados
        ("skill_moves",     "INTEGER"),
        ("weak_foot",       "INTEGER"),
        ("foot",            "TEXT"),
        ("height",          "INTEGER"),
        ("weight",          "INTEGER"),
        ("age",             "INTEGER"),
        ("alt_positions",   "TEXT"),
        ("workrates",       "TEXT"),
        ("accelerate_type", "TEXT"),
        # IDs cruzados
        ("futgg_player_id", "TEXT"),
        ("ea_id",           "TEXT"),
        # URLs extras
        ("render_url",      "TEXT"),
        ("portrait_url",    "TEXT"),
        ("bg_url_hd",       "TEXT"),
        ("nation_flag_url", "TEXT"),
        ("club_logo_url",   "TEXT"),
        ("league_logo_url", "TEXT"),
        # Playstyles (JSON)
        ("playstyles_json", "TEXT"),
        # Controle
        ("scraped_version", "TEXT"),
        ("detail_scraped_at", "TEXT"),
    ]
    
    import sqlite3
    db_path = str(DATABASE_FILE)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Verificar colunas existentes
    cur.execute("PRAGMA table_info(fc_players)")
    existing_cols = {row[1] for row in cur.fetchall()}
    
    added = 0
    for col_name, col_type in new_columns:
        if col_name not in existing_cols:
            try:
                cur.execute(f'ALTER TABLE fc_players ADD COLUMN "{col_name}" {col_type}')
                logger.info(f"  + Coluna adicionada: {col_name} ({col_type})")
                added += 1
            except Exception as e:
                logger.error(f"  ✗ Erro ao adicionar {col_name}: {e}")
    
    conn.commit()
    conn.close()
    
    if added > 0:
        print(f"\n   ✅ {added} novas colunas adicionadas à tabela fc_players")
    else:
        print(f"\n   ℹ️ Tabela fc_players já está atualizada ({len(existing_cols)} colunas)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset de dados de scraping do Help DMEs")
    parser.add_argument("--force", action="store_true", help="Pular confirmação interativa")
    parser.add_argument("--migrate-only", action="store_true", help="Apenas migrar schema (não apagar dados)")
    args = parser.parse_args()
    
    async def run():
        if args.migrate_only:
            await migrate_fc_players_schema()
        else:
            success = await reset_data(force=args.force)
            if success:
                await migrate_fc_players_schema()
    
    asyncio.run(run())
