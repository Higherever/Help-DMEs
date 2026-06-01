"""
Help DMEs — Scraper Global Resiliente de Jogadores (Catálogo Completo)
======================================================================
Este script realiza a raspagem de todo o catálogo global de cartas de jogadores do jogo
(EA FC 26) do Futbin e FutGG, persistindo-os na tabela `fc_players` no banco de dados SQLite.

Funcionalidades Principais:
  1. Independência de Diretório: Deduz dinamicamente a pasta raiz do projeto (PROJECT_ROOT)
     a partir do próprio arquivo, permitindo execução a partir de qualquer local no terminal.
  2. Resiliência e Continuidade (Resume-on-Failure): Salva o progresso das páginas em
     `scrape_all_state.json`. Antes de qualquer request, faz checagem ultrarrápida no banco
     de dados e no disco. Se o jogador já estiver gravado e com as imagens baixadas, ele é
     pulado instantaneamente sem consumir requests ou banda.
  3. Pós-processamento de Imagem (Transparência): Remove o fundo branco de todas as cartas
     completas usando ImageMagick (floodfill a partir dos 4 cantos, fuzz de 10%) e gera as
     miniaturas transparentes premium de 150x169px cropadas via Pillow (Small Cards) a partir
     delas.
  4. Proteção Anti-Bot Premium: Reutiliza a engine anti-bot existente do projeto com rotação
     de User-Agents, cookies persistentes por sessão e delays gaussianos inteligentes.
  5. Tratamento de Erros Isolado: Erros de jogadores específicos não derrubam o script, sendo
     registrados e reportados no resumo final para máxima autonomia de execução.

Modo de uso:
    python backend/scripts/scrape_all_players.py [--pages 1-750] [--test] [--force]
"""

import sys
import os
import json
import logging
import re
import argparse
import unicodedata
import asyncio
import tempfile
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime, UTC
from typing import Optional, Dict, List, Tuple

import aiohttp
import aiofiles
from bs4 import BeautifulSoup

# ── Configurar paths e importações de forma 100% dinâmica ───────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

# Insere a raiz do projeto no path do sistema para resolver os imports
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Imports dos serviços existentes
try:
    from backend.services.anti_bot import fetch_html, fetch_binary, create_session
except ImportError:
    print("❌ Erro: Não foi possível importar backend.services.anti_bot.")
    print("Por favor, verifique se o script está localizado em 'backend/scripts/' dentro do projeto.")
    sys.exit(1)

# Configuração de Logs
LOG_FILE = SCRIPT_DIR / "scrape_all_players.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ]
)
logger = logging.getLogger("scrape_all")

# ── Constantes do Projeto ────────────────────────────────────────────────────
FUTBIN_BASE    = "https://www.futbin.com"
FUTGG_BASE     = "https://www.fut.gg"
DATABASE_FILE  = PROJECT_ROOT / "database" / "help_dmes.db"
IMAGES_DIR     = PROJECT_ROOT / "images"
STATE_FILE     = SCRIPT_DIR / "scrape_all_state.json"
SCRAPER_VERSION = "v2.0-all"

# Semáforos de concorrência — simula comportamento de usuário humano lento
FUTBIN_SEM = asyncio.Semaphore(2)
FUTGG_SEM  = asyncio.Semaphore(2)
IMG_SEM    = asyncio.Semaphore(4)


# ── State Management (Resiliência) ──────────────────────────────────────────

def load_state() -> dict:
    """Carrega o progresso de raspagem a partir do arquivo JSON."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
                # Garantir campos obrigatórios
                if "completed_pages" not in state:
                    state["completed_pages"] = []
                if "failed_players" not in state:
                    state["failed_players"] = []
                if "last_page_processed" not in state:
                    state["last_page_processed"] = 0
                return state
        except Exception as e:
            logger.warning(f"Erro ao carregar scrape_all_state.json ({e}). Inicializando novo estado.")
    
    return {
        "completed_pages": [],
        "last_page_processed": 0,
        "failed_players": [],
        "version": SCRAPER_VERSION,
        "started_at": datetime.now(UTC).isoformat()
    }


def save_state(state: dict):
    """Salva o progresso de raspagem de forma atômica no arquivo JSON."""
    try:
        # Escrever primeiro em arquivo temporário para evitar corrupção de queda no meio da gravação
        fd, temp_path = tempfile.mkstemp(dir=str(SCRIPT_DIR), suffix=".tmp")
        os.close(fd)
        
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
            
        shutil.move(temp_path, str(STATE_FILE))
    except Exception as e:
        logger.error(f"Erro ao salvar scrape_all_state.json: {e}")


# ── Helpers Biográficos e Sanitização ─────────────────────────────────────────

def sanitize(text: str) -> str:
    """Converte o nome do atleta para um slug amigável e seguro de arquivo."""
    if not text:
        return "unknown"
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ASCII", "ignore").decode("ASCII")
    clean = re.sub(r"[^a-zA-Z0-9\s_-]", "", ascii_text)
    clean = re.sub(r"[\s_-]+", "_", clean)
    return clean.strip("_").lower()[:50]


def safe_int(val) -> Optional[int]:
    """Converte valor para inteiro com segurança, retornando None se falhar."""
    try:
        if val is None:
            return None
        return int(str(val).strip())
    except (ValueError, TypeError):
        return None


# ── Validação SQLite e Verificação de Jogador Concluído ──────────────────────

def verify_and_migrate_db():
    """Garante que a tabela fc_players exista e possua todos os campos necessários."""
    if not DATABASE_FILE.parent.exists():
        DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Conectando ao banco de dados: {DATABASE_FILE}")
    conn = sqlite3.connect(str(DATABASE_FILE))
    cur = conn.cursor()
    
    # 1. Garantir que a tabela fc_players base exista
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fc_players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            futbin_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            overall INTEGER NOT NULL,
            position TEXT,
            nation TEXT,
            club TEXT,
            league TEXT,
            card_type TEXT,
            face_url TEXT,
            bg_url_raw TEXT,
            card_template_url TEXT,
            scraped_at TEXT
        )
    """)
    
    # 2. Lista completa de colunas estendidas necessárias para o backend
    extended_columns = [
        ("pace",            "INTEGER"),
        ("shooting",        "INTEGER"),
        ("passing",         "INTEGER"),
        ("dribbling_stat",  "INTEGER"),
        ("defending",       "INTEGER"),
        ("physic",          "INTEGER"),
        ("acceleration",    "INTEGER"),
        ("sprint_speed",    "INTEGER"),
        ("finishing",       "INTEGER"),
        ("shot_power",      "INTEGER"),
        ("long_shots",      "INTEGER"),
        ("volleys",         "INTEGER"),
        ("positioning_att", "INTEGER"),
        ("penalties",       "INTEGER"),
        ("short_passing",   "INTEGER"),
        ("long_passing",    "INTEGER"),
        ("crossing",        "INTEGER"),
        ("curve",           "INTEGER"),
        ("free_kick",       "INTEGER"),
        ("vision",          "INTEGER"),
        ("agility",         "INTEGER"),
        ("balance",         "INTEGER"),
        ("reactions",       "INTEGER"),
        ("ball_control",    "INTEGER"),
        ("composure",       "INTEGER"),
        ("skill_dribbling", "INTEGER"),
        ("interceptions",   "INTEGER"),
        ("heading",         "INTEGER"),
        ("marking",         "INTEGER"),
        ("standing_tackle", "INTEGER"),
        ("sliding_tackle",  "INTEGER"),
        ("jumping",         "INTEGER"),
        ("stamina",         "INTEGER"),
        ("strength",        "INTEGER"),
        ("aggression",      "INTEGER"),
        ("gk_diving",       "INTEGER"),
        ("gk_handling",     "INTEGER"),
        ("gk_kicking",      "INTEGER"),
        ("gk_positioning",  "INTEGER"),
        ("gk_reflexes",     "INTEGER"),
        ("skill_moves",     "INTEGER"),
        ("weak_foot",       "INTEGER"),
        ("foot",            "TEXT"),
        ("height",          "INTEGER"),
        ("weight",          "INTEGER"),
        ("age",             "INTEGER"),
        ("alt_positions",   "TEXT"),
        ("workrates",       "TEXT"),
        ("accelerate_type", "TEXT"),
        ("futgg_player_id", "TEXT"),
        ("render_url",      "TEXT"),
        ("bg_url_hd",       "TEXT"),
        ("nation_flag_url", "TEXT"),
        ("club_logo_url",   "TEXT"),
        ("league_logo_url", "TEXT"),
        ("playstyles_json", "TEXT"),
        ("scraped_version", "TEXT"),
        ("detail_scraped_at", "TEXT")
    ]
    
    # Obter colunas atualmente existentes
    cur.execute("PRAGMA table_info(fc_players)")
    existing_cols = {row[1] for row in cur.fetchall()}
    
    # Adicionar dinamicamente colunas faltantes via ALTER TABLE
    added_count = 0
    for col_name, col_type in extended_columns:
        if col_name not in existing_cols:
            try:
                cur.execute(f'ALTER TABLE fc_players ADD COLUMN "{col_name}" {col_type}')
                logger.info(f"  └─ [+] Nova coluna adicionada ao banco: {col_name} ({col_type})")
                added_count += 1
            except Exception as e:
                logger.error(f"Erro ao adicionar coluna {col_name}: {e}")
                
    conn.commit()
    conn.close()
    
    if added_count > 0:
        logger.info(f"Banco de dados verificado com sucesso. {added_count} colunas adicionadas.")
    else:
        logger.info("Banco de dados verificado. Estrutura do schema já está 100% atualizada.")


def is_player_processed_locally(futbin_id: str, name: str) -> bool:
    """
    Verifica de forma ultrarrápida no SQLite local e no disco se o jogador já
    está completamente raspado (com estatísticas salvas) e com ambas as imagens
    (completa transparente e miniatura transparente) gravadas fisicamente no disco.
    Permite ignorar o processamento do jogador em milissegundos sem requests de rede.
    """
    name_slug = sanitize(name)
    card_filename = f"fc_player_{futbin_id}_{name_slug}.png"
    
    # Caminhos físicos no disco
    card_path_full = IMAGES_DIR / "cards" / "full" / card_filename
    card_path_small = IMAGES_DIR / "cards" / "small" / card_filename
    
    # 1. Se os arquivos físicos não existem no disco, não está completo
    if not card_path_full.exists() or card_path_full.stat().st_size < 1000:
        return False
    if not card_path_small.exists() or card_path_small.stat().st_size < 200:
        return False
        
    # 2. Consultar o SQLite para ver se possui dados salvos e completos
    conn = sqlite3.connect(str(DATABASE_FILE))
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT detail_scraped_at, card_template_url FROM fc_players WHERE futbin_id = ?",
            (str(futbin_id),)
        )
        row = cur.fetchone()
        if not row:
            return False
            
        detail_scraped_at, card_template_url = row
        # Se detail_scraped_at estiver preenchido, os stats detalhados já foram raspados
        if not detail_scraped_at or not card_template_url:
            return False
            
        return True
    except Exception as e:
        logger.error(f"Erro na verificação síncrona SQLite do jogador {futbin_id}: {e}")
        return False
    finally:
        conn.close()


# ── Gravação Síncrona no SQLite (Bypass ORM para Performance) ────────────────

def upsert_player_sqlite(player_data: dict) -> bool:
    """
    Realiza o INSERT ou UPDATE do jogador na tabela `fc_players` de forma síncrona direta.
    Lê dinamicamente as colunas físicas da tabela para evitar tentar gravar campos
    inexistentes no SQLite, fornecendo compatibilidade e performance absolutas.
    """
    conn = sqlite3.connect(str(DATABASE_FILE))
    cur = conn.cursor()
    try:
        futbin_id = str(player_data["futbin_id"])
        
        # 1. Verificar se registro já existe no SQLite
        cur.execute("SELECT id FROM fc_players WHERE futbin_id = ?", (futbin_id,))
        row = cur.fetchone()
        
        # 2. Ler colunas físicas reais da tabela fc_players no banco
        cur.execute("PRAGMA table_info(fc_players)")
        valid_cols = {r[1] for r in cur.fetchall()}
        
        # 3. Mapear chaves para gravação
        fields = {
            "futbin_id":        futbin_id,
            "name":             player_data.get("name", "Unknown"),
            "overall":          player_data.get("overall", 0),
            "position":         player_data.get("position"),
            "nation":           player_data.get("nation"),
            "club":             player_data.get("club"),
            "league":           player_data.get("league"),
            "card_type":        player_data.get("card_type"),
            "face_url":         player_data.get("face_url_raw") or player_data.get("face_url"),
            "bg_url_raw":       player_data.get("bg_url_raw"),
            "card_template_url": player_data.get("card_template_url"),
            "render_url":       player_data.get("render_url"),
            "bg_url_hd":        player_data.get("card_template_url") or player_data.get("bg_url_hd") or player_data.get("futgg_card_image_url"),
            "nation_flag_url":  player_data.get("nation_flag_url"),
            "club_logo_url":    player_data.get("club_logo_url"),
            "league_logo_url":  player_data.get("league_logo_url"),
            "futgg_player_id":  player_data.get("futgg_player_id"),
            "playstyles_json":  player_data.get("playstyles_json"),
            "alt_positions":    player_data.get("alt_positions"),
            "workrates":        player_data.get("workrates"),
            "accelerate_type":  player_data.get("accelerate_type"),
            "foot":             player_data.get("foot"),
            "skill_moves":      player_data.get("skill_moves"),
            "weak_foot":        player_data.get("weak_foot"),
            "height":           player_data.get("height"),
            "weight":           player_data.get("weight"),
            "age":              player_data.get("age"),
            # Stats principais
            "pace":             player_data.get("pace"),
            "shooting":         player_data.get("shooting"),
            "passing":          player_data.get("passing"),
            "dribbling_stat":   player_data.get("dribbling_stat"),
            "defending":        player_data.get("defending"),
            "physic":           player_data.get("physic"),
            # Sub-atributos
            "acceleration":     player_data.get("acceleration"),
            "sprint_speed":     player_data.get("sprint_speed"),
            "finishing":        player_data.get("finishing"),
            "shot_power":       player_data.get("shot_power"),
            "long_shots":       player_data.get("long_shots"),
            "volleys":          player_data.get("volleys"),
            "positioning_att":  player_data.get("positioning_att"),
            "penalties":        player_data.get("penalties"),
            "short_passing":    player_data.get("short_passing"),
            "long_passing":     player_data.get("long_passing"),
            "crossing":         player_data.get("crossing"),
            "curve":            player_data.get("curve"),
            "free_kick":        player_data.get("free_kick"),
            "vision":           player_data.get("vision"),
            "agility":          player_data.get("agility"),
            "balance":          player_data.get("balance"),
            "reactions":        player_data.get("reactions"),
            "ball_control":     player_data.get("ball_control"),
            "composure":        player_data.get("composure"),
            "skill_dribbling":  player_data.get("skill_dribbling"),
            "interceptions":    player_data.get("interceptions"),
            "heading":          player_data.get("heading"),
            "marking":          player_data.get("marking"),
            "standing_tackle":  player_data.get("standing_tackle"),
            "sliding_tackle":   player_data.get("sliding_tackle"),
            "jumping":          player_data.get("jumping"),
            "stamina":          player_data.get("stamina"),
            "strength":         player_data.get("strength"),
            "aggression":       player_data.get("aggression"),
            "gk_diving":        player_data.get("gk_diving"),
            "gk_handling":      player_data.get("gk_handling"),
            "gk_kicking":       player_data.get("gk_kicking"),
            "gk_positioning":   player_data.get("gk_positioning"),
            "gk_reflexes":      player_data.get("gk_reflexes"),
            # Auditoria
            "scraped_version":  SCRAPER_VERSION,
            "detail_scraped_at": datetime.now(UTC).isoformat() if player_data.get("pace") else None,
        }
        
        # Inserir scraped_at apenas se for um registro inteiramente novo
        if not row:
            fields["scraped_at"] = datetime.now(UTC).isoformat()
            
        # Filtrar o dicionário mantendo apenas colunas válidas no banco e valores não Nulos
        db_fields = {k: v for k, v in fields.items() if k in valid_cols and v is not None}
        
        if row:
            # 4. Executar UPDATE no registro existente
            set_clause = ", ".join(f'"{k}" = ?' for k in db_fields if k != "futbin_id")
            values = [db_fields[k] for k in db_fields if k != "futbin_id"]
            values.append(futbin_id)
            cur.execute(f'UPDATE fc_players SET {set_clause} WHERE futbin_id = ?', values)
        else:
            # 5. Executar INSERT no banco
            cols = ", ".join(f'"{k}"' for k in db_fields)
            placeholders = ", ".join("?" for _ in db_fields)
            values = [db_fields[k] for k in db_fields]
            cur.execute(f'INSERT INTO fc_players ({cols}) VALUES ({placeholders})', values)
            
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erro no upsert SQLite síncrono para {player_data.get('name')} (ID: {player_data.get('futbin_id')}): {e}")
        return False
    finally:
        conn.close()


# ── Download de Arquivo Binário Genérico com Concorrência Controlada ──────────

async def download_binary_file(
    session: aiohttp.ClientSession,
    url: str,
    dest_path: Path,
) -> bool:
    """Realiza o download de arquivos binários gerais, respeitando o semáforo de imagens."""
    if not url:
        return False
        
    # Se o arquivo já existe e possui tamanho decente, pular
    if dest_path.exists() and dest_path.stat().st_size > 200:
        return True
        
    # Preservar a URL do Futbin intacta (com assinaturas de cache)
    if "futbin.com" in url:
        clean_url = url
    else:
        clean_url = url.split("?")[0] if "?" in url else url
        
    if clean_url.startswith("//"):
        clean_url = "https:" + clean_url
        
    async with IMG_SEM:
        data = await fetch_binary(session, clean_url)
        
    if data and len(data) > 200:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(dest_path, "wb") as f:
            await f.write(data)
        return True
        
    return False


# ── Remoção de Fundo Branco (ImageMagick) e Miniaturas (Pillow) ──────────────

async def remove_white_background_inplace(image_path: Path) -> bool:
    """
    Remove o fundo branco dos cantos externos das cartas de forma assíncrona.
    Executa o binário do ImageMagick ('magick') aplicando floodfill transparente
    nos 4 cantos com fuzz tolerante de 10% para suavização de bordas curvas.
    """
    if not image_path.exists():
        logger.error(f"Arquivo não localizado para remoção de fundo branco: {image_path}")
        return False

    fd_out, temp_out = tempfile.mkstemp(suffix=".png")
    os.close(fd_out)

    try:
        cmd = [
            "magick",
            str(image_path),
            "-fuzz", "10%",
            "-fill", "none",
            "-draw", "color 0,0 floodfill",
            "-gravity", "NorthEast", "-draw", "color 0,0 floodfill",
            "-gravity", "SouthWest", "-draw", "color 0,0 floodfill",
            "-gravity", "SouthEast", "-draw", "color 0,0 floodfill",
            temp_out
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.warning(f"ImageMagick falhou em {image_path.name}: {stderr.decode()}. Usando arquivo original.")
            if os.path.exists(temp_out):
                os.remove(temp_out)
            return False
        
        # Substitui a imagem física original pela versão com transparência Alpha nos cantos
        shutil.move(temp_out, str(image_path))
        return True
    except Exception as e:
        logger.error(f"Erro ao remover fundo branco do card {image_path.name}: {e}")
        if os.path.exists(temp_out):
            try: os.remove(temp_out)
            except: pass
        return False


def create_premium_thumbnail(input_path: str, output_path: str) -> bool:
    """
    Gera a miniatura cropada premium (Small Card) de 150x169px a partir do card HD
    original (que já está transparente), recortando o topo e a base curva do card
    e descartando o centro para dar o visual oficial.
    """
    try:
        from PIL import Image
        dest = Path(output_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        
        with Image.open(input_path) as img:
            # 1. Redimensionar para 504x698 para termos coordenadas de corte perfeitas e fixas
            img_temp = img.resize((504, 698), Image.Resampling.LANCZOS)
            
            # 2. Cortar o Topo: y de 0 a 422 (Rating, Posição, Rosto e PlayStyles)
            topo = img_temp.crop((0, 0, 504, 422))
            
            # 3. Cortar a Base: y de 558 a 698 (Curva inferior do card com os emblemas)
            base = img_temp.crop((0, 558, 504, 698))
            
            # 4. Criar canvas transparente de 504x562 e mesclar as fatias
            small_canvas = Image.new("RGBA", (504, 562), (0, 0, 0, 0))
            small_canvas.paste(topo, (0, 0))
            small_canvas.paste(base, (0, 422))
            
            # 5. Redimensionar para a miniatura definitiva de 150x169px em alta definição
            resized = small_canvas.resize((150, 169), Image.Resampling.LANCZOS)
            resized.save(dest, "PNG")
            return True
            
    except Exception as e:
        logger.error(f"Erro ao criar miniatura small de {input_path}: {e}")
        return False


# ── Pipeline de Processamento de Imagens do Jogador ───────────────────────────

async def download_and_process_images(
    session: aiohttp.ClientSession,
    player_data: Dict,
    futbin_id: str,
) -> Dict:
    """
    Gerencia o download e o tratamento de todas as imagens associadas ao jogador:
    1. Baixa a carta completa HD do FutGG (ou fallback Futbin).
    2. Aplica o ImageMagick inplace para remover o fundo branco dos cantos (Alpha transparente).
    3. Gera a miniatura transparente (small) a partir do card HD limpo via Pillow.
    4. Baixa os renders do rosto, emblema do clube, nação e liga.
    """
    image_paths = {}
    name_slug = sanitize(player_data.get("name", "unknown"))
    
    # 1. CARD COMPLETO HD
    card_url = (
        player_data.get("futgg_card_image_url") or
        player_data.get("bg_url_hd") or
        player_data.get("bg_url_raw")
    )
    if card_url:
        card_filename = f"fc_player_{futbin_id}_{name_slug}.png"
        card_path = IMAGES_DIR / "cards" / "full" / card_filename
        
        # Baixar imagem
        success_download = await download_binary_file(session, card_url, card_path)
        if success_download:
            # Remover fundo branco (Fundo transparente nos cantos do card)
            await remove_white_background_inplace(card_path)
            
            # Registrar caminho relativo para o frontend
            image_paths["card_template_url"] = f"/images/cards/full/{card_filename}"
            image_paths["bg_url_hd"] = f"/images/cards/full/{card_filename}"
            
            # Gerar a miniatura transparente de 150x169px baseada na imagem já limpa pelo ImageMagick
            small_path = IMAGES_DIR / "cards" / "small" / card_filename
            create_premium_thumbnail(str(card_path), str(small_path))

    # 2. FOTO / RENDER DO ROSTO DO ATLETA
    render_url = (
        player_data.get("futgg_render_url") or
        player_data.get("render_url") or
        player_data.get("face_url_raw")
    )
    if render_url:
        render_filename = f"render_{futbin_id}_{name_slug}.png"
        render_path = IMAGES_DIR / "cards" / "renders" / render_filename
        if await download_binary_file(session, render_url, render_path):
            image_paths["render_url"] = f"/images/cards/renders/{render_filename}"
            image_paths["face_url"] = f"/images/cards/renders/{render_filename}"
            
    # 3. ESCUDO DO CLUBE
    club_url = player_data.get("club_logo_url")
    if club_url:
        club_slug = sanitize(player_data.get("club", "unknown"))
        club_filename = f"club_{club_slug}.png"
        club_path = IMAGES_DIR / "cards" / "clubs" / club_filename
        if await download_binary_file(session, club_url, club_path):
            image_paths["club_logo_url"] = f"/images/cards/clubs/{club_filename}"

    # 4. BANDEIRA DA NAÇÃO
    nation_url = player_data.get("nation_flag_url")
    if nation_url:
        nation_slug = sanitize(player_data.get("nation", "unknown"))
        nation_filename = f"nation_{nation_slug}.png"
        nation_path = IMAGES_DIR / "cards" / "nations" / nation_filename
        if await download_binary_file(session, nation_url, nation_path):
            image_paths["nation_flag_url"] = f"/images/cards/nations/{nation_filename}"

    # 5. LOGO DA LIGA
    league_url = player_data.get("league_logo_url")
    if league_url:
        league_slug = sanitize(player_data.get("league", "unknown"))
        league_filename = f"league_{league_slug}.png"
        league_path = IMAGES_DIR / "cards" / "leagues" / league_filename
        if await download_binary_file(session, league_url, league_path):
            image_paths["league_logo_url"] = f"/images/cards/leagues/{league_filename}"

    return image_paths


# ── FASE 1: Raspagem de Listagem do Futbin ───────────────────────────────────

async def scrape_futbin_page_list(
    session: aiohttp.ClientSession,
    page: int,
) -> List[Dict]:
    """Coleta a lista de jogadores de uma determinada página do Futbin."""
    url = f"{FUTBIN_BASE}/players?page={page}"
    
    async with FUTBIN_SEM:
        html = await fetch_html(session, url)
        
    if not html:
        logger.error(f"Falha ao carregar listagem da página {page} no Futbin.")
        return []
        
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select(".player-row")
    
    if not rows:
        logger.warning(f"Nenhum jogador encontrado na página {page}.")
        # Gravar para debug se falhar inesperadamente
        debug_path = SCRIPT_DIR / f"debug_page_{page}.html"
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(html)
        return []
        
    players = []
    for row in rows:
        try:
            player = _parse_player_row_simple(row, page)
            if player and player.get("futbin_id"):
                players.append(player)
        except Exception as e:
            logger.debug(f"Erro ao analisar linha da listagem na página {page}: {e}")
            
    return players


def _parse_player_row_simple(row, page: int) -> Optional[Dict]:
    """Extrai os dados essenciais da listagem básica de uma linha do Futbin."""
    # 1. ID do Futbin
    futbin_id = None
    card_link = (
        row.select_one("a.player-row-playercard") or
        row.select_one("a[href*='/26/player/']") or
        row.select_one("a[href*='/player/']")
    )
    if card_link:
        href = card_link.get("href", "")
        m = re.search(r"/player/(\d+)/", href)
        if m:
            futbin_id = m.group(1)
            
    if not futbin_id:
        return None
        
    # 2. Nome
    name_el = row.select_one("a.table-player-name") or row.select_one(".table-player-info a")
    name = name_el.get_text(strip=True) if name_el else "Unknown"
    
    # 3. Overall
    rating_el = row.select_one(".playercard-s-26-rating") or row.select_one(".table-rating") or row.select_one(".rating")
    overall = safe_int(rating_el.get_text(strip=True)) or 0 if rating_el else 0
    
    # 4. Posição
    pos_el = row.select_one(".playercard-s-26-pos") or row.select_one(".table-pos") or row.select_one(".position")
    position = pos_el.get_text(strip=True) if pos_el else ""
    
    # 5. Versão/Tipo de Card
    bg_img = row.select_one("img.playercard-s-26-bg") or row.select_one("img[src*='/cards/tiny/']") or row.select_one("img[src*='/cards/small/']")
    bg_url = bg_img.get("src", "") if bg_img else ""
    
    card_type = ""
    if bg_url:
        m_version = re.search(r"/cards/tiny/\d+_(.+?)\.png", bg_url)
        if m_version:
            card_type = m_version.group(1).replace("_", " ").title()
            
    if not card_type:
        version_el = row.select_one(".table-player-revision, .revision")
        card_type = version_el.get_text(strip=True) if version_el else ""
        
    # 6. Biografia
    club_el = row.select_one(".table-player-club img")
    club = (club_el.get("data-original-title") or club_el.get("title") or club_el.get("alt") or "").strip() if club_el else ""
    
    nation_el = row.select_one(".table-player-nation img")
    nation = (nation_el.get("data-original-title") or nation_el.get("title") or nation_el.get("alt") or "").strip() if nation_el else ""
    
    league_el = row.select_one(".table-player-league img")
    league = (league_el.get("data-original-title") or league_el.get("title") or league_el.get("alt") or "").strip() if league_el else ""
    
    # 7. URLs
    href = card_link.get("href", "") if card_link else ""
    player_url = f"{FUTBIN_BASE}{href}" if href and not href.startswith("http") else href
    
    # 8. Extrair o EA ITEM ID do jogador a partir do avatar da face
    face_el = row.select_one("img.playercard-26-special-img") or row.select_one("img[src*='/players/p']") or row.select_one(".playercard-s-26-img-column img")
    face_url = ""
    ea_item_id = ""
    if face_el:
        face_url = face_el.get("data-original") or face_el.get("data-src") or face_el.get("src") or ""
        if face_url:
            m_ea = re.search(r'/players/p?(\d+)\.png', face_url)
            if m_ea:
                ea_item_id = m_ea.group(1)
                
    return {
        "futbin_id": futbin_id,
        "ea_item_id": ea_item_id,
        "name": name,
        "overall": overall,
        "position": position,
        "card_type": card_type,
        "nation": nation,
        "club": club,
        "league": league,
        "player_url": player_url,
        "face_url_raw": face_url,
        "bg_url_raw": bg_url,
        "page": page
    }


# ── FASE 2 & 3: Detalhes Futbin e Imagem HD FutGG ────────────────────────────

async def scrape_futbin_player_detail(
    session: aiohttp.ClientSession,
    player_url: str,
    futbin_id: str,
) -> Dict:
    """Acessa a página de perfil individual do jogador no Futbin e colhe as estatísticas completas."""
    if not player_url:
        return {}
        
    async with FUTBIN_SEM:
        html = await fetch_html(session, player_url)
        
    if not html:
        return {}
        
    soup = BeautifulSoup(html, "lxml")
    data = {}
    
    # 1. Imagens do Card e Rosto originais como fallback
    try:
        bg_img = soup.select_one("img.playercard-s-26-bg")
        if bg_img:
            data["bg_url_hd"] = bg_img.get("src", "")
            
        face_img = soup.select_one("img.playercard-26-special-img")
        if face_img:
            data["render_url"] = face_img.get("src", "")
    except Exception:
        pass
        
    # 2. Estatísticas Principais (PAC, SHO, PAS, DRI, DEF, PHY)
    try:
        stat_map = {
            "PAC": "pace", "SHO": "shooting", "PAS": "passing",
            "DRI": "dribbling_stat", "DEF": "defending", "PHY": "physic"
        }
        for stat_div in soup.select(".playercard-26-stats, .playercard-s-26-stats, .playercard-stats"):
            val_el = stat_div.select_one(".playercard-26-stat-number, .playercard-s-26-stat-value, .playercard-stat-number")
            lbl_el = stat_div.select_one(".playercard-26-stat-value, .playercard-s-26-stat-label, .playercard-stat-value")
            if val_el and lbl_el:
                lbl = lbl_el.get_text(strip=True).upper()
                col = stat_map.get(lbl)
                if col:
                    val = safe_int(val_el.get_text(strip=True))
                    if val and 1 <= val <= 99:
                        data[col] = val
    except Exception:
        pass
        
    # 3. Sub-atributos detalhados (ex: Finalização, Fôlego, Visão)
    try:
        # Mapa expandido com TODOS os rótulos conhecidos do Futbin (atuais e legados)
        sub_map = {
            # Ritmo (PAC)
            "Acceleration": "acceleration", "Accel": "acceleration",
            "Sprint Speed": "sprint_speed", "Sprint Spd": "sprint_speed",
            # Finalização (SHO)
            "Finishing": "finishing", "Shot Power": "shot_power", "Shot Pwr": "shot_power",
            "Long Shots": "long_shots", "Long Shot": "long_shots",
            "Volleys": "volleys",
            "Positioning": "positioning_att", "Att. Position": "positioning_att",
            "Att Position": "positioning_att", "Att.Position": "positioning_att",
            "Penalties": "penalties", "Penalty": "penalties",
            # Passe (PAS)
            "Short Passing": "short_passing", "Short Pass": "short_passing",
            "Long Passing": "long_passing", "Long Pass": "long_passing",
            "Crossing": "crossing", "Curve": "curve",
            "FK Accuracy": "free_kick", "Free Kick Accuracy": "free_kick",
            "FK Acc.": "free_kick", "FK Acc": "free_kick", "Free Kick": "free_kick",
            "Vision": "vision",
            # Drible (DRI)
            "Agility": "agility", "Balance": "balance",
            "Reactions": "reactions", "Ball Control": "ball_control", "Ball Ctrl": "ball_control",
            "Composure": "composure", "Dribbling": "skill_dribbling",
            # Defesa (DEF)
            "Interceptions": "interceptions",
            "Heading Accuracy": "heading", "Heading Acc.": "heading",
            "Heading Acc": "heading", "Heading": "heading", "Head. Acc.": "heading",
            "Def Awareness": "marking", "Def. Awareness": "marking",
            "Defensive Awareness": "marking", "Marking": "marking", "Def Aware": "marking",
            "Standing Tackle": "standing_tackle", "Stand Tackle": "standing_tackle",
            "Stand. Tackle": "standing_tackle",
            "Sliding Tackle": "sliding_tackle", "Slide Tackle": "sliding_tackle",
            "Slide. Tackle": "sliding_tackle",
            # Físico (PHY)
            "Jumping": "jumping", "Stamina": "stamina",
            "Strength": "strength", "Aggression": "aggression",
            # Goleiro
            "GK Diving": "gk_diving", "GK Handling": "gk_handling",
            "GK Kicking": "gk_kicking", "GK Positioning": "gk_positioning",
            "GK Reflexes": "gk_reflexes",
        }
        # Seletores primários
        for stat_row in soup.select(".player-stat-row"):
            name_el = stat_row.select_one(".player-stat-name")
            val_el = stat_row.select_one(".player-stat-value")
            if name_el and val_el:
                label = name_el.get_text(strip=True)
                col = sub_map.get(label)
                if col and col not in data:
                    val = safe_int(val_el.get_text(strip=True))
                    if val and 1 <= val <= 99:
                        data[col] = val
        # Fallback: seletores alternativos
        if not data.get("short_passing"):
            for row_el in soup.select("tr, .stat-row, .sub-stat-row, div[class*='stat']"):
                cells = row_el.find_all(["td", "span", "div"])
                if len(cells) >= 2:
                    label_text = cells[0].get_text(strip=True)
                    col = sub_map.get(label_text)
                    if col and col not in data:
                        val = safe_int(cells[-1].get_text(strip=True))
                        if val and 1 <= val <= 99:
                            data[col] = val
    except Exception:
        pass
        
    # 4. Dados Biográficos (Pé Preferido, Fintas, Altura, Idade)
    try:
        profile_map = {
            "Weak Foot": "weak_foot",
            "WF": "weak_foot",
            "Skill Moves": "skill_moves",
            "Skills": "skill_moves",
            "SM": "skill_moves",
            "Foot": "foot",
            "Preferred Foot": "foot",
            "Height": "height",
            "Age": "age",
            "Weight": "weight",
            "Work Rates": "workrates",
            "Work Rate": "workrates",
            "WR": "workrates",
            "AcceleRATE": "accelerate_type",
            "Accelerate": "accelerate_type",
            "AccelType": "accelerate_type",
            "Alt Pos": "alt_positions",
            "Alt. Pos": "alt_positions",
            "Alternative Positions": "alt_positions",
        }
        for profile_div in soup.select(".align-center, .xs-font"):
            label_el = profile_div.select_one(".text-faded")
            if label_el:
                label = label_el.get_text(strip=True)
                col = profile_map.get(label)
                if col and col not in data:
                    value_els = [el for el in profile_div.children if el != label_el and hasattr(el, "get_text")]
                    if value_els:
                        val_text = " ".join(el.get_text(strip=True) for el in value_els).strip()
                        if col in ["weak_foot", "skill_moves"]:
                            val_text = re.sub(r"[^\d]", "", val_text)
                            data[col] = safe_int(val_text)
                        elif col == "height":
                            cm_match = re.search(r"(\d+)\s*cm", val_text, re.IGNORECASE)
                            data[col] = safe_int(cm_match.group(1)) if cm_match else val_text
                        elif col == "weight":
                            kg_match = re.search(r"(\d+)\s*kg", val_text, re.IGNORECASE)
                            data[col] = safe_int(kg_match.group(1)) if kg_match else val_text
                        elif col == "age":
                            age_match = re.search(r"(\d+)", val_text)
                            data[col] = safe_int(age_match.group(1)) if age_match else val_text
                        else:
                            data[col] = val_text
    except Exception:
        pass
        
    # 5. Posições Alternativas e Player Roles
    try:
        roles = []
        for role_div in soup.select(".xxs-row.align-center"):
            pos_el = role_div.select_one(".xs-font.uppercase.text-faded")
            role_el = role_div.select_one("a[href*='/roles']")
            if pos_el and role_el:
                pos = pos_el.get_text(strip=True)
                role_text = role_el.get_text(" ", strip=True)
                role_text = re.sub(r"\s+", " ", role_text).strip()
                roles.append(f"{pos}: {role_text}")
        if roles:
            data["workrates"] = " | ".join(roles)
    except Exception:
        pass
        
    # 6. Playstyles e Playstyles+ (FC 26)
    try:
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
        if playstyles:
            data["playstyles_json"] = json.dumps(playstyles, ensure_ascii=False)
    except Exception:
        pass
        
    # 7. Imagens extras de clube, liga, nação preservando signatures
    try:
        nation_img = soup.select_one("img[src*='/nation/'], img[src*='nations/'], img[src*='nation_flags/'], img[src*='/flags/']")
        if nation_img:
            data["nation_flag_url"] = nation_img.get("src", "")
            
        club_img = soup.select_one("img[src*='/clubs/']")
        if club_img:
            data["club_logo_url"] = club_img.get("src", "")
            
        league_img = soup.select_one("img[src*='/leagues/']")
        if league_img:
            data["league_logo_url"] = league_img.get("src", "")
    except Exception:
        pass
        
    return data


async def scrape_futgg_premium_card(
    session: aiohttp.ClientSession,
    player_name: str,
    ea_item_id: str,
) -> Dict:
    """Busca a URL consolidada da imagem HD da carta e render do atleta diretamente no FutGG usando o ea_item_id."""
    result = {}
    if not ea_item_id:
        return result
        
    url = f"{FUTGG_BASE}/players/{ea_item_id}/"
    
    async with FUTGG_SEM:
        html = await fetch_html(session, url)
        
    if not html:
        return result
        
    soup = BeautifulSoup(html, "lxml")
    card_img = None
    target_pattern = f"26-{ea_item_id}"
    
    # 1. Procurar imagem do item com padrão do ano 26
    for img in soup.select("img[src*='futgg-player-item-card']"):
        src = img.get("src", "")
        if target_pattern in src:
            card_img = img
            break
            
    # Fallback 1: Sem ano específico
    if not card_img:
        for img in soup.select("img[src*='futgg-player-item-card']"):
            src = img.get("src", "")
            if f"-{ea_item_id}" in src:
                card_img = img
                break
                
    # Fallback 2: Primeiro do FC 26
    if not card_img:
        card_img = soup.select_one("img[src*='/2026/futgg-player-item-card/']")
        
    if card_img:
        img_url = card_img.get("src", "")
        if img_url:
            # Retirar o otimizador Cloudflare do FutGG se houver, para download direto e limpo
            if "cdn-cgi/image" in img_url:
                img_url = re.sub(r"cdn-cgi/image/[^/]*/", "", img_url)
            result["futgg_card_image_url"] = img_url
            
    # 2. Foto/Render de rosto premium no FutGG
    render_img = (
        soup.select_one("img[src*='/players/p']") or
        soup.select_one("img[src*='/player-renders/']") or
        soup.select_one("img[src*='/renders/']")
    )
    if render_img:
        r_url = render_img.get("src", "")
        if "cdn-cgi/image" in r_url:
            r_url = re.sub(r"cdn-cgi/image/[^/]*/", "", r_url)
        result["futgg_render_url"] = r_url
        
    result["futgg_player_id"] = ea_item_id
    return result


# ── Processamento de um Único Jogador (Fase Unificada) ───────────────────────

async def process_single_player(
    session_futbin: aiohttp.ClientSession,
    session_futgg: aiohttp.ClientSession,
    player_basic: Dict,
) -> bool:
    """
    Orquestra o pipeline individual de um jogador:
    1. Executa em paralelo o scraper de detalhe (Futbin) e imagem HD (FutGG).
    2. Baixa e processa imagens no disco (remove fundo e gera miniatura cropada transparente).
    3. Persiste de forma síncrona direta no SQLite local.
    """
    futbin_id = player_basic["futbin_id"]
    name = player_basic["name"]
    overall = player_basic["overall"]
    player_url = player_basic.get("player_url", "")
    ea_item_id = player_basic.get("ea_item_id", "")
    
    logger.info(f"  ➤ Processando: {name} (OVR:{overall}, ID:{futbin_id}, EA:{ea_item_id or '✗'})")
    
    # 1. Scraping paralelo Futbin + FutGG
    tasks = [
        scrape_futbin_player_detail(session_futbin, player_url, futbin_id),
        scrape_futgg_premium_card(session_futgg, name, ea_item_id)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    futbin_detail = results[0] if not isinstance(results[0], Exception) else {}
    futgg_data    = results[1] if not isinstance(results[1], Exception) else {}
    
    if isinstance(results[0], Exception):
        logger.debug(f"Falha de raspagem Futbin para {name}: {results[0]}")
    if isinstance(results[1], Exception):
        logger.debug(f"Falha de raspagem FutGG para {name}: {results[1]}")
        
    # Mesclar dados biográficos e estatísticas
    player_combined = {**player_basic, **futbin_detail, **futgg_data}
    
    # 2. Download e pós-processamento de imagens (Magick + Pillow)
    image_paths = await download_and_process_images(session_futbin, player_combined, futbin_id)
    player_combined.update(image_paths)
    
    # 3. Persistência de dados síncrona direta no SQLite
    success_db = upsert_player_sqlite(player_combined)
    if success_db:
        has_card = bool(player_combined.get("card_template_url"))
        has_stats = bool(player_combined.get("pace"))
        logger.info(
            f"  ✅ {name} salvo | "
            f"Card Transparente: {'✓' if has_card else '✗'} | "
            f"Stats: {'✓' if has_stats else '✗'}"
        )
        return True
    else:
        logger.error(f"  ❌ Erro ao salvar {name} no banco de dados.")
        return False


# ── Pipeline Principal de Raspagem Global ────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="Scraper de catálogo completo de jogadores do EA FC 26")
    parser.add_argument("--pages", default="1-750", help="Intervalo de páginas a raspar do Futbin. Ex: '1-100', '150-250'. Default: 1-750")
    parser.add_argument("--test", action="store_true", help="Modo teste rápido: apenas 5 jogadores por página.")
    parser.add_argument("--force", action="store_true", help="Força a reprocessar páginas e jogadores já completados.")
    parser.add_argument("--delay-mult", type=float, default=1.0, help="Multiplicador do tempo de delay entre requests para simulação anti-bot.")
    args = parser.parse_args()

    # 1. Parsear intervalo de páginas
    try:
        m = re.match(r"(\d+)[-–](\d+)", args.pages)
        if m:
            start_page, end_page = int(m.group(1)), int(m.group(2))
        else:
            n = int(args.pages)
            start_page, end_page = n, n
    except Exception:
        logger.error(f"Formato de páginas inválido: '{args.pages}'. Use algo como '1-750' ou '12'.")
        sys.exit(1)

    print("\n" + "═"*80)
    print("   🚀 HELP DMEs — MOTORES DE RASPAGEM GLOBAL DE CARTAS (FC 26)")
    print(f"   Páginas: {start_page} a {end_page} | Modo: {'TESTE (5 por pág)' if args.test else 'COMPLETO'}")
    print(f"   Projeto: {PROJECT_ROOT}")
    print(f"   Banco de Dados: {DATABASE_FILE}")
    print(f"   Logs: {LOG_FILE}")
    print("═"*80 + "\n")

    # 2. Verificar e migrar banco de dados SQLite local
    verify_and_migrate_db()
    
    # 3. Carregar progresso anterior (Resiliência)
    state = load_state()
    completed_pages = set(state.get("completed_pages", []))
    
    # Criar sessões de conexão com anti-bot
    session_futbin = create_session()
    session_futgg  = create_session()
    
    total_saved = 0
    total_skipped = 0
    total_failed = 0
    
    try:
        for page in range(start_page, end_page + 1):
            # Verificar se a página já foi totalmente completada com sucesso anteriormente
            if page in completed_pages and not args.force:
                print(f"📄 Página {page}/{end_page} já completada anteriormente. [PULADA]")
                continue
                
            print(f"\n{'─'*70}")
            print(f"  📄 PROCESSANDO PÁGINA {page}/{end_page}")
            print(f"{'─'*70}")
            
            # FASE 1: Buscar lista de jogadores da página
            players_basic = await scrape_futbin_page_list(session_futbin, page)
            if not players_basic:
                logger.warning(f"Nenhum jogador retornado na página {page}. Se for o fim do catálogo, concluído!")
                # Se não retornar nada em modo normal, pode ser o fim dos registros do Futbin
                if page > 100:
                    break
                continue
                
            if args.test:
                players_basic = players_basic[:5]
                logger.info(f"[TESTE] Processando apenas 5 atletas da página {page}")
                
            page_saved = 0
            page_skipped = 0
            page_failed = 0
            
            # Processar cada jogador na listagem da página
            for i, player in enumerate(players_basic, 1):
                futbin_id = player["futbin_id"]
                name = player["name"]
                
                print(f"\n  [{i}/{len(players_basic)}] ", end="", flush=True)
                
                # ── Checagem de Resiliência no Banco de Dados + Disco ──
                if is_player_processed_locally(futbin_id, name) and not args.force:
                    print(f"  [PULADO] {name} (ID: {futbin_id}) já se encontra completo e salvo.")
                    page_skipped += 1
                    total_skipped += 1
                    continue
                    
                # Executar a raspagem completa do jogador
                try:
                    success = await process_single_player(session_futbin, session_futgg, player)
                    if success:
                        page_saved += 1
                        total_saved += 1
                    else:
                        page_failed += 1
                        total_failed += 1
                        state["failed_players"].append({
                            "futbin_id": futbin_id,
                            "name": name,
                            "page": page,
                            "reason": "db_save_failure",
                            "at": datetime.now(UTC).isoformat()
                        })
                except Exception as e:
                    logger.error(f"Erro crítico no processamento de {name}: {e}")
                    page_failed += 1
                    total_failed += 1
                    state["failed_players"].append({
                        "futbin_id": futbin_id,
                        "name": name,
                        "page": page,
                        "reason": str(e),
                        "at": datetime.now(UTC).isoformat()
                    })
                    
                # Delay gaussiano entre jogadores para respeitar o Cloudflare
                base_delay = 3.0 * args.delay_mult
                gaussian_delay = max(1.5, min(8.0, import_random().gauss(base_delay, 0.8)))
                logger.debug(f"Aguardando {gaussian_delay:.2f}s entre jogadores...")
                await asyncio.sleep(gaussian_delay)
                
            # Registrar página como concluída
            if page_failed == 0 and len(players_basic) > 0:
                completed_pages.add(page)
                state["completed_pages"] = sorted(list(completed_pages))
                state["last_page_processed"] = page
                save_state(state)
                logger.info(f"✅ Página {page} concluída com sucesso: {page_saved} salvos, {page_skipped} pulados.")
            else:
                logger.warning(f"⚠️ Página {page} finalizada com {page_failed} falhas. Ela será tentada novamente na próxima sessão.")
                state["last_page_processed"] = page
                save_state(state)
                
            # Delay maior entre páginas do catálogo
            if page < end_page:
                page_delay = (8.0 + import_random().uniform(2, 6)) * args.delay_mult
                logger.info(f"Aguardando {page_delay:.1f}s antes da próxima página do catálogo...")
                await asyncio.sleep(page_delay)
                
    finally:
        # Garantir fechamento de conexões HTTP da sessão
        await session_futbin.close()
        await session_futgg.close()
        
    print("\n" + "═"*80)
    print("   🏁 SCRAPING GLOBAL FINALIZADO!")
    print(f"   Atletas Salvos/Atualizados: {total_saved}")
    print(f"   Atletas Pulados (Já Existentes): {total_skipped}")
    print(f"   Atletas com Falha no Processo: {total_failed}")
    print(f"   Banco de Dados: {DATABASE_FILE}")
    print("═"*80 + "\n")


def import_random():
    import random
    return random


if __name__ == "__main__":
    # Garante loop de execução asyncio robusto
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Processo interrompido manualmente pelo usuário via Ctrl+C.")
        print("O progresso atual foi salvo com sucesso em scrape_all_state.json.")
        print("Ao iniciar novamente, o sistema retomará exatamente de onde parou.\n")
        sys.exit(130)
