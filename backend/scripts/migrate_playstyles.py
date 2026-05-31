#!/usr/bin/env python3
"""
Help DMEs — Script de Migração de Banco de Dados
===============================================
Adiciona a coluna `playstyles_json` às tabelas `user_squad` e `fc_players`
caso elas ainda não existam no banco SQLite local.
"""

import sqlite3
import sys
from pathlib import Path

# Deduzir raiz do projeto
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATABASE_FILE = PROJECT_ROOT / "database" / "help_dmes.db"

def run_migration():
    print(f"Connecting to database: {DATABASE_FILE}")
    if not DATABASE_FILE.exists():
        print("❌ Database file does not exist yet. It will be initialized on next server startup.")
        sys.exit(0)

    conn = sqlite3.connect(str(DATABASE_FILE))
    cur = conn.cursor()

    try:
        # 1. Migração para user_squad
        cur.execute("PRAGMA table_info(user_squad)")
        columns_user_squad = {row[1] for row in cur.fetchall()}
        
        if "playstyles_json" not in columns_user_squad:
            print("Adding 'playstyles_json' to 'user_squad' table...")
            cur.execute("ALTER TABLE user_squad ADD COLUMN playstyles_json TEXT")
            print("✅ Successfully added 'playstyles_json' to 'user_squad'!")
        else:
            print("✓ 'playstyles_json' column already exists in 'user_squad'.")

        # 2. Migração para fc_players (garantia)
        cur.execute("PRAGMA table_info(fc_players)")
        columns_fc_players = {row[1] for row in cur.fetchall()}
        
        if "playstyles_json" not in columns_fc_players:
            print("Adding 'playstyles_json' to 'fc_players' table...")
            cur.execute("ALTER TABLE fc_players ADD COLUMN playstyles_json TEXT")
            print("✅ Successfully added 'playstyles_json' to 'fc_players'!")
        else:
            print("✓ 'playstyles_json' column already exists in 'fc_players'.")

        conn.commit()
        print("🎉 Migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
