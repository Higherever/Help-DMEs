import sqlite3
import os
from pathlib import Path

# Configuração de Caminhos
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATABASE_DIR = PROJECT_ROOT / "database"
DATABASE_FILE = DATABASE_DIR / "help_dmes.db"

def migrate_v2():
    """
    Adiciona colunas expires_text, repeatable_text e refresh_text à tabela sbc_sets.
    """
    print(f"🚀 Iniciando migração v2 no banco: {DATABASE_FILE}")
    
    if not DATABASE_FILE.exists():
        print("❌ Erro: Arquivo de banco de dados não encontrado.")
        return

    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Colunas para adicionar
        columns = [
            ("expires_text", "VARCHAR(100)"),
            ("repeatable_text", "VARCHAR(100)"),
            ("refresh_text", "VARCHAR(100)")
        ]

        for col_name, col_type in columns:
            try:
                print(f"➕ Adicionando coluna '{col_name}'...")
                cursor.execute(f"ALTER TABLE sbc_sets ADD COLUMN {col_name} {col_type}")
                print(f"✅ Coluna '{col_name}' adicionada com sucesso.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"⚠️ Coluna '{col_name}' já existe. Pulando.")
                else:
                    raise e

        conn.commit()
        conn.close()
        print("🎉 Migração v2 concluída com sucesso!")

    except Exception as e:
        print(f"💥 Erro durante a migração: {e}")

if __name__ == "__main__":
    migrate_v2()
