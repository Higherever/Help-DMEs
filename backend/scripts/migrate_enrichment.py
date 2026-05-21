"""
Help DMEs — Migração: Enrichment de PlayerCard
================================================
Adiciona ~45 colunas novas ao player_cards para suportar:
  - 30 sub-atributos detalhados
  - IDs cruzados (sofifa_id, futbin_id)
  - Metadados biográficos
  - URLs de CDN (SoFIFA + Futbin)
  - Meta rating (easySBC)

Executar: python -m backend.scripts.migrate_enrichment
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "database" / "help_dmes.db"

NEW_COLUMNS = [
    # IDs cruzados
    ("sofifa_id", "INTEGER"),
    ("futbin_id", "VARCHAR(50)"),

    # Face stats
    ("pace", "INTEGER"),
    ("shooting", "INTEGER"),
    ("passing", "INTEGER"),
    ("dribbling_stat", "INTEGER"),
    ("defending", "INTEGER"),
    ("physic", "INTEGER"),

    # Sub-atributos (30)
    ("acceleration", "INTEGER"),
    ("sprint_speed", "INTEGER"),
    ("finishing", "INTEGER"),
    ("shot_power", "INTEGER"),
    ("long_shots", "INTEGER"),
    ("volleys", "INTEGER"),
    ("positioning_att", "INTEGER"),
    ("short_passing", "INTEGER"),
    ("long_passing", "INTEGER"),
    ("crossing", "INTEGER"),
    ("curve", "INTEGER"),
    ("free_kick", "INTEGER"),
    ("vision", "INTEGER"),
    ("agility", "INTEGER"),
    ("balance", "INTEGER"),
    ("reactions", "INTEGER"),
    ("ball_control", "INTEGER"),
    ("composure", "INTEGER"),
    ("skill_dribbling", "INTEGER"),
    ("interceptions", "INTEGER"),
    ("heading", "INTEGER"),
    ("marking", "INTEGER"),
    ("standing_tackle", "INTEGER"),
    ("sliding_tackle", "INTEGER"),
    ("jumping", "INTEGER"),
    ("stamina", "INTEGER"),
    ("strength", "INTEGER"),
    ("aggression", "INTEGER"),
    ("penalties", "INTEGER"),

    # GK stats
    ("gk_diving", "INTEGER"),
    ("gk_handling", "INTEGER"),
    ("gk_kicking", "INTEGER"),
    ("gk_positioning", "INTEGER"),
    ("gk_reflexes", "INTEGER"),

    # Metadados biográficos
    ("skill_moves", "INTEGER"),
    ("weak_foot", "INTEGER"),
    ("foot", "VARCHAR(10)"),
    ("height", "INTEGER"),
    ("weight", "INTEGER"),
    ("age", "INTEGER"),
    ("country", "VARCHAR(100)"),
    ("country_id", "INTEGER"),
    ("club_name", "VARCHAR(255)"),
    ("club_id", "INTEGER"),
    ("league_name", "VARCHAR(255)"),
    ("league_id", "INTEGER"),
    ("alt_positions", "VARCHAR(50)"),
    ("workrates", "VARCHAR(30)"),
    ("accelerate_type", "VARCHAR(20)"),

    # URLs de CDN
    ("face_url", "TEXT"),
    ("render_url", "TEXT"),
    ("club_logo_url", "TEXT"),
    ("nation_flag_url", "TEXT"),
    ("league_logo_url", "TEXT"),

    # Meta
    ("meta_tier", "VARCHAR(10)"),
    ("playstyles_json", "TEXT"),
]


def migrate():
    if not DB_PATH.exists():
        print(f"❌ Banco não encontrado: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Verificar colunas existentes
    cursor.execute("PRAGMA table_info(player_cards)")
    existing = {row[1] for row in cursor.fetchall()}

    added = 0
    skipped = 0
    for col_name, col_type in NEW_COLUMNS:
        if col_name in existing:
            skipped += 1
            continue
        try:
            cursor.execute(f"ALTER TABLE player_cards ADD COLUMN {col_name} {col_type}")
            added += 1
            print(f"  ✅ {col_name} ({col_type})")
        except sqlite3.OperationalError as e:
            print(f"  ⚠️ {col_name}: {e}")

    conn.commit()
    conn.close()

    print(f"\n🎯 Migração concluída: {added} colunas adicionadas, {skipped} já existiam")


if __name__ == "__main__":
    print(f"🔧 Migrando banco: {DB_PATH}")
    migrate()
