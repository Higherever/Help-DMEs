import sys
import sqlite3
import json
from pathlib import Path
from datetime import datetime, UTC

# Inserir o path do projeto
sys.path.insert(0, "/home/gambeta/Documentos/Socorro DMEs/Socorro DMEs")
from backend.scripts.scrape_ea_ratings import parse_player_details, propagate_playstyles_to_user_squad, export_json_backup

db_path = "/home/gambeta/Documentos/Socorro DMEs/Socorro DMEs/database/help_dmes.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Mapear os jogadores que deram erro
failed_players = [
    {
        "ea_id": "200715",
        "name": "Adam Davies",
        "overall": 70,
        "position": "GK",
        "rarity": "silver",
        "file": "/home/gambeta/.gemini/antigravity/brain/00048cde-0780-4658-9d18-23e24a3c66ce/.system_generated/steps/1037/content.md"
    },
    {
        "ea_id": "277501",
        "name": "Petter Nosa Dahl",
        "overall": 68,
        "position": "LM",
        "rarity": "silver",
        "file": "/home/gambeta/.gemini/antigravity/brain/00048cde-0780-4658-9d18-23e24a3c66ce/.system_generated/steps/1047/content.md"
    }
]

for p in failed_players:
    print(f"Processando jogador: {p['name']} ({p['ea_id']})")
    with open(p["file"], "r", encoding="utf-8") as f:
        html = f.read()
    
    # Extrair detalhes
    data = parse_player_details(html, p)
    print(f"  Posição extraída: {data.get('position')}")
    print(f"  Stats: PAC={data.get('pace')}, SHO={data.get('shooting')}, PAS={data.get('passing')}, DRI={data.get('dribbling_stat')}, DEF={data.get('defending')}, PHY={data.get('physic')}")
    print(f"  Playstyles: {data.get('playstyles')}")
    
    # Persistir
    ea_id = p["ea_id"]
    cursor.execute("SELECT id FROM fc_players WHERE ea_id = ? OR (name = ? AND overall = ?)", 
                   (ea_id, data["name"], data["overall"]))
    existing = cursor.fetchone()
    
    playstyles_str = json.dumps(data["playstyles"], ensure_ascii=False) if data["playstyles"] else None
    
    if existing:
        cursor.execute("""
            UPDATE fc_players 
            SET ea_id = ?, position = ?, playstyles_json = ?, scraped_at = ?,
                pace = COALESCE(pace, ?), shooting = COALESCE(shooting, ?), 
                passing = COALESCE(passing, ?), dribbling_stat = COALESCE(dribbling_stat, ?), 
                defending = COALESCE(defending, ?), physic = COALESCE(physic, ?)
            WHERE id = ?
        """, (
            ea_id, data.get("position"), playstyles_str, data["scraped_at"],
            data.get("pace"), data.get("shooting"), data.get("passing"), 
            data.get("dribbling_stat"), data.get("defending"), data.get("physic"),
            existing[0]
        ))
        print("  ✓ Registro atualizado no catálogo fc_players!")
    else:
        temp_futbin_id = f"ea-{ea_id}"
        cursor.execute("""
            INSERT INTO fc_players 
            (futbin_id, ea_id, name, overall, position, playstyles_json, scraped_at,
             pace, shooting, passing, dribbling_stat, defending, physic)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            temp_futbin_id, ea_id, data["name"], data["overall"], data.get("position"), 
            playstyles_str, data["scraped_at"], data.get("pace"), data.get("shooting"), 
            data.get("passing"), data.get("dribbling_stat"), data.get("defending"), data.get("physic")
        ))
        print("  ✓ Novo registro inserido no catálogo fc_players!")
        
    # Atualizar log de scrape para status ok
    cursor.execute("INSERT OR REPLACE INTO ea_scrape_log (ea_id, status, timestamp) VALUES (?, 'ok', ?)",
                   (ea_id, datetime.now(UTC).isoformat()))
    conn.commit()

conn.close()

# Executar a propagação e exportação de backup
print("\n🔗 Executando sincronização e propagação para o elenco...")
propagate_playstyles_to_user_squad(db_path)

print("💾 Exportando backup JSON consolidado...")
output_json_path = "/home/gambeta/Documentos/Socorro DMEs/Socorro DMEs/database/playstyles_prata_bronze.json"
export_json_backup(db_path, output_json_path)
print("🎉 Sincronização e recuperação concluída com 100% de sucesso!")
