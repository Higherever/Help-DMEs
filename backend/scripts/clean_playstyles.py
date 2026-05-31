import asyncio
import sqlite3
import json
from bs4 import BeautifulSoup
import sys
import os

# Ajustar o caminho para conseguir importar o backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.services.anti_bot import fetch_html, create_session

DB_PATH = "database/help_dmes.db"

async def clean_player_playstyles(session, futbin_id: str, name: str) -> list:
    url = f"https://www.futbin.com/26/player/{futbin_id}/cleanup"
    html = await fetch_html(session, url)
    if not html:
        return None
    
    soup = BeautifulSoup(html, "lxml")
    playstyles = []
    
    active_wrapper = soup.select_one(".player-abilities-wrapper:not(.hidden)")
    if active_wrapper:
        for anchor in active_wrapper.select("a[href*='/playstyles/']"):
            classes = anchor.get("class", [])
            if "active" in classes:
                name_el = anchor.select_one(".slim-font, div")
                if name_el:
                    ps_name = name_el.get_text(strip=True)
                    is_plus = "psplus" in classes
                    img_el = anchor.select_one("img")
                    icon = img_el.get("src", "") if img_el else ""
                    playstyles.append({"name": ps_name, "is_plus": is_plus, "icon_url": icon})
    return playstyles

async def main():
    print("Iniciando limpeza cirúrgica de Playstyles corrompidos...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Busca jogadores com mais de 10 playstyles
    cursor.execute("SELECT id, futbin_id, name, playstyles_json FROM fc_players WHERE json_array_length(playstyles_json) > 10 ORDER BY CASE WHEN name LIKE '%Mbappé%' THEN 0 ELSE 1 END, id")
    players = cursor.fetchall()
    
    if not players:
        print("✅ Nenhum jogador corrompido encontrado no banco de dados!")
        return
        
    print(f"⚠️ Encontrados {len(players)} jogadores poluídos. Começando a limpeza...")
    
    session = create_session()
    
    success_count = 0
    fail_count = 0
    
    try:
        for row in players:
            player_id, futbin_id, name, old_json_str = row
            old_playstyles = json.loads(old_json_str) if old_json_str else []
            
            print(f"Limpando {name} (ID: {futbin_id}) - Tinha {len(old_playstyles)} playstyles...", end=" ")
            
            try:
                new_playstyles = await clean_player_playstyles(session, futbin_id, name)
                
                if new_playstyles is not None:
                    new_json_str = json.dumps(new_playstyles, ensure_ascii=False)
                    cursor.execute("UPDATE fc_players SET playstyles_json = ? WHERE id = ?", (new_json_str, player_id))
                    conn.commit()
                    success_count += 1
                    print(f"✅ OK! Reduzido para {len(new_playstyles)}")
                else:
                    fail_count += 1
                    print("❌ Falha na extração.")
                    
            except Exception as e:
                fail_count += 1
                print(f"❌ Erro: {e}")
                
            await asyncio.sleep(1.0) # Delay curto para não engasgar no antibot
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Parado pelo usuário.")
    finally:
        await session.close()
        conn.close()
        
    print("\n🏁 RESUMO DA LIMPEZA:")
    print(f"Corrigidos: {success_count}")
    print(f"Falharam: {fail_count}")

if __name__ == "__main__":
    asyncio.run(main())
