import asyncio
import json
import logging
import re
import sys
import os
import functools
import unicodedata
import colorsys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import aiohttp
import aiofiles
from PIL import Image, ImageDraw, ImageFont, ImageColor, ImageFilter, ImageOps, ImageChops

# Importar motor de bypass do anti-bot
from backend.services.anti_bot import fetch_binary

logger = logging.getLogger("card_renderer")

# Paths absolutos
SERVICE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SERVICE_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
IMAGES_DIR = PROJECT_ROOT / "images"
JS_DIR = BACKEND_DIR / "card_generator_js"
FONTS_DIR = JS_DIR / "fonts"

BEBAS_FONT_PATH = FONTS_DIR / "BebasNeue-Regular.ttf"
OSWALD_FONT_PATH = FONTS_DIR / "Oswald-Regular.ttf"

FULL_DIR = IMAGES_DIR / "cards" / "full"
SMALL_DIR = IMAGES_DIR / "cards" / "small"

# Dimensões e Resolução Base
CARD_W = 756
CARD_H = 1056

# Cores e Temas por Raridade (Fidelidade EA FC 26)
CARD_THEMES = {
    "gold": {
        "card_color": "#443a22", "rating_color": "#443a22",
        "alt_pos_bg": "#D0B77F", "alt_pos_border": "#443a22",
        "extra_info_bg": "#D0B77F", "extra_info_border": "#443a22",
        "playstyle_bg": "#2c2616", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Normal_bg.png"
    },
    "gold_rare": {
        "card_color": "#443a22", "rating_color": "#443a22",
        "alt_pos_bg": "#C8A020", "alt_pos_border": "#443a22",
        "extra_info_bg": "#C8A020", "extra_info_border": "#443a22",
        "playstyle_bg": "#2c2616", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Normal_bg.png"
    },
    "silver": {
        "card_color": "#5a5a5a", "rating_color": "#5a5a5a",
        "alt_pos_bg": "#C0C0C0", "alt_pos_border": "#5a5a5a",
        "extra_info_bg": "#C0C0C0", "extra_info_border": "#5a5a5a",
        "playstyle_bg": "#2b2b2b", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Normal_bg.png"
    },
    "bronze": {
        "card_color": "#5c3a1e", "rating_color": "#5c3a1e",
        "alt_pos_bg": "#CD7F32", "alt_pos_border": "#5c3a1e",
        "extra_info_bg": "#CD7F32", "extra_info_border": "#5c3a1e",
        "playstyle_bg": "#2c1b0e", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Normal_bg.png"
    },
    "end_of_era": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#191452", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#191452", "extra_info_border": "#ffffff",
        "playstyle_bg": "#100d35", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_End_of_an_Era_bg.png"
    },
    "toty": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#0a0a3a", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#0a0a3a", "extra_info_border": "#ffffff",
        "playstyle_bg": "#080828", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_TOTY_bg.png"
    },
    "hero": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#1a0a2e", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#1a0a2e", "extra_info_border": "#ffffff",
        "playstyle_bg": "#10051e", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Hero_SBC_bg.png"
    },
    "totw": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#1a1a1a", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#1a1a1a", "extra_info_border": "#ffffff",
        "playstyle_bg": "#121212", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_TOTW_bg.png"
    },
    "icon": {
        "card_color": "#f0e6c8", "rating_color": "#f0e6c8",
        "alt_pos_bg": "#2a1a0a", "alt_pos_border": "#f0e6c8",
        "extra_info_bg": "#2a1a0a", "extra_info_border": "#f0e6c8",
        "playstyle_bg": "#1f1307", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Icon_bg.png"
    },
    "ucl_rttf": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#121a3b", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#121a3b", "extra_info_border": "#ffffff",
        "playstyle_bg": "#0a0f2b", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_UCL_RTTF_bg.png"
    },
    "potm_la_liga": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#2c1c38", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#2c1c38", "extra_info_border": "#ffffff",
        "playstyle_bg": "#1d1226", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_LaLiga_POTM_SBC_bg.png"
    },
    "festival_of_football_captains": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#0f2c1f", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#0f2c1f", "extra_info_border": "#ffffff",
        "playstyle_bg": "#081a12", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_FoF_Captains_bg.png"
    },
    "star_performer": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#300b14", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#300b14", "extra_info_border": "#ffffff",
        "playstyle_bg": "#1e070d", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Star_Performer_bg.png"
    }
}

SPECIAL_CARD_TYPES = {"toty", "tots", "hero", "end_of_era", "icon", "totw",
                      "fantasy_fc", "fut_birthday", "winter_wildcards"}

# Cache de fontes para otimização
@functools.lru_cache(maxsize=64)
def font_bebas(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(BEBAS_FONT_PATH), size)

@functools.lru_cache(maxsize=64)
def font_oswald(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(OSWALD_FONT_PATH), size)

def px(percent_of_width: float) -> int:
    return int(CARD_W * percent_of_width)

def py(percent_of_height: float) -> int:
    return int(CARD_H * percent_of_height)

def pf(base_multiplier: float) -> int:
    base = CARD_W * 0.0557  # ~42.1px no canvas 3x (756px)
    return int(base * base_multiplier)

def get_card_theme(card_type: Optional[str]) -> Dict[str, str]:
    if not card_type:
        return CARD_THEMES["gold"]
    ct_lower = card_type.lower().replace(" ", "_").replace("-", "_")
    if ct_lower in CARD_THEMES:
        return CARD_THEMES[ct_lower]
    for key, val in CARD_THEMES.items():
        if key in ct_lower:
            return val
    return CARD_THEMES["gold"]

def parse_color_rgba(color_str: str) -> Tuple[int, int, int, int]:
    if not color_str:
        return (255, 255, 255, 255)
    if color_str.startswith("rgba"):
        parts = color_str.replace("rgba(", "").replace(")", "").split(",")
        r = int(parts[0].strip())
        g = int(parts[1].strip())
        b = int(parts[2].strip())
        a = int(float(parts[3].strip()) * 255)
        return (r, g, b, a)
    elif color_str.startswith("#"):
        rgb = ImageColor.getrgb(color_str)
        if len(rgb) == 3:
            return (rgb[0], rgb[1], rgb[2], 255)
        return rgb
    else:
        rgb = ImageColor.getrgb(color_str)
        return (rgb[0], rgb[1], rgb[2], 255)

def remove_white_corners_pillow(image: Image.Image, thresh: int = 15) -> Image.Image:
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    w, h = image.size
    corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    for corner in corners:
        ImageDraw.floodfill(image, corner, (0, 0, 0, 0), thresh=thresh)
    return image

def remove_background_photo(image_path: Path) -> Image.Image:
    img = Image.open(image_path).convert("RGBA")
    
    # Verificar se a imagem já possui canal alfa com transparência ativa (ex: PNG recortado do Futbin)
    if img.mode == "RGBA":
        alpha = img.split()[3]
        min_alpha, max_alpha = alpha.getextrema()
        if min_alpha < 255:
            logger.info(f"A imagem {image_path.name} já possui canal de transparência (alfa mínimo: {min_alpha}). Pulando remoção de fundo para preservar qualidade.")
            return img
            
    try:
        from rembg import remove
        logger.debug("Usando rembg (IA) para remoção de fundo da foto.")
        return remove(img)
    except Exception as e:
        logger.debug(f"rembg indisponível ({e}). Iniciando fallback Chroma Key nativo com Pillow.")
        w, h = img.size
        bg_r, bg_g, bg_b, _ = img.getpixel((5, 5))
        
        pixels = img.load()
        new_pixels = []
        tolerance = 45
        
        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
                dist = ((r - bg_r)**2 + (g - bg_g)**2 + (b - bg_b)**2)**0.5
                if dist < tolerance:
                    new_pixels.append((r, g, b, 0))
                else:
                    new_pixels.append((r, g, b, a))
        
        img.putdata(new_pixels)
        
        alpha = img.split()[3]
        alpha = alpha.filter(ImageFilter.GaussianBlur(1.0))
        img.putalpha(alpha)
        return img

def draw_default_avatar() -> Image.Image:
    avatar = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(avatar)
    gray = (120, 125, 130, 255)
    
    cx, cy, cr = px(0.53), py(0.35), px(0.15)
    draw.ellipse((cx - cr, cy - cr, cx + cr, cy + cr), fill=gray)
    
    draw.polygon([
        (px(0.28), py(0.68)),
        (px(0.78), py(0.68)),
        (px(0.85), py(0.85)),
        (px(0.21), py(0.85))
    ], fill=gray)
    return avatar

def sanitize_slug(text: str) -> str:
    if not text:
        return "unknown"
    clean = re.sub(r"[^a-zA-Z0-9\s_-]", "", text)
    clean = re.sub(r"[\s_-]+", "_", clean)
    return clean.strip("_").lower()[:50]

async def ensure_asset_local(
    session: aiohttp.ClientSession,
    url: str,
    dest_path: Path
) -> Optional[str]:
    if not url:
        return None
        
    if url.startswith("/images/"):
        local_target = PROJECT_ROOT / url.lstrip("/")
        if local_target.exists() and local_target.stat().st_size > 200:
            return str(local_target.resolve())
            
    if dest_path.exists() and dest_path.stat().st_size > 200:
        return str(dest_path.resolve())
        
    if "futbin.com" in url:
        clean_url = url
    else:
        clean_url = url.split("?")[0] if "?" in url else url
        
    if clean_url.startswith("//"):
        clean_url = "https:" + clean_url
        
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        data = await fetch_binary(session, clean_url)
        if data and len(data) > 200:
            async with aiofiles.open(dest_path, "wb") as f:
                await f.write(data)
            logger.debug(f"[Renderer Cache] Baixou asset com sucesso para: {dest_path.name}")
            return str(dest_path.resolve())
    except Exception as e:
        logger.error(f"[Renderer Cache] Falha ao baixar asset {clean_url}: {e}")
        
    return str(dest_path.resolve()) if dest_path.exists() else None


class CardRendererClient:
    def __init__(self):
        # Validar fontes no início
        if not BEBAS_FONT_PATH.exists() or not OSWALD_FONT_PATH.exists():
            logger.error(f"Erro crítico: Fontes não encontradas em: {FONTS_DIR}")

    async def start_service(self):
        logger.info("[Renderer] Renderizador nativo com Pillow ativado. Nenhuma inicialização de Node.js necessária.")

    async def stop_service(self):
        logger.info("[Renderer] Nenhuma finalização de Node.js necessária.")

    async def render_player(
        self,
        session: aiohttp.ClientSession,
        player_data: Dict
    ) -> Optional[Dict]:
        futbin_id = str(player_data.get("futbin_id") or player_data.get("id") or "unknown")
        name = player_data.get("name", "Unknown Player")
        name_slug = sanitize_slug(name)
        filename = f"fc_player_{futbin_id}_{name_slug}.png"
        
        # Face do jogador — diferenciada por tipo de card:
        # - Cards BASE (Gold/Silver/Bronze): face_url é a foto retrato padrão.
        #   O render_url pode conter um render especial ERRADO (ex: TOTY salvo no Gold).
        # - Cards ESPECIAIS (TOTY, POTM, UCL...): render_url é o render full-body correto.
        BASE_CARD_TYPES_RENDER = {
            "gold", "gold rare", "gold non-rare",
            "silver", "silver rare", "silver non-rare",
            "bronze", "bronze rare", "bronze non-rare",
        }
        card_type_lower = (player_data.get("card_type") or "").lower()
        is_base_card = card_type_lower in BASE_CARD_TYPES_RENDER

        face_local = None

        if is_base_card:
            # ORDEM CORRETA de resolução de face para cards base:
            # 1. portrait_url do banco (novo campo - path local)
            portrait_url_db = player_data.get("portrait_url")
            if portrait_url_db and portrait_url_db.startswith("/images/"):
                local_portrait = PROJECT_ROOT / portrait_url_db.lstrip("/")
                if local_portrait.exists() and local_portrait.stat().st_size > 200:
                    face_local = str(local_portrait.resolve())
                    logger.debug(f"[Renderer] Portrait base encontrado via portrait_url: {local_portrait.name}")
            # 2. Fallback: buscar por resource_id em images/cards/portraits/
            if not face_local:
                # O portrait está em images/cards/portraits/ NÃO em renders/
                portraits_dir = IMAGES_DIR / "cards" / "portraits"
                possible = list(portraits_dir.glob(f"portrait_{futbin_id}_*.png")) if portraits_dir.exists() else []
                if possible:
                    face_local = str(possible[0].resolve())
            if not face_local:
                logger.warning(
                    f"[Renderer] Portrait base NÃO encontrado para ID {futbin_id} ({card_type_lower}). "
                    f"Execute maintain_players_db.py para baixar."
                )
        else:
            # Cards especiais: render_url tem o render full-body correto
            render_url_local = player_data.get("render_url")
            if render_url_local and render_url_local.startswith("/images/"):
                local_face = PROJECT_ROOT / render_url_local.lstrip("/")
                if local_face.exists() and local_face.stat().st_size > 200:
                    face_local = str(local_face.resolve())
            # Fallback: caminho padrão derivado do futbin_id
            if not face_local:
                face_path_fallback = IMAGES_DIR / "cards" / "renders" / f"render_{futbin_id}_{name_slug}.png"
                if face_path_fallback.exists() and face_path_fallback.stat().st_size > 200:
                    face_local = str(face_path_fallback.resolve())

        # Template de fundo: usa o arquivo local dyn_* gerado pelo scraper
        bg_local = None
        bg_url_raw = player_data.get("bg_url_raw")
        if bg_url_raw:
            bg_dyn_filename = bg_url_raw.split("/")[-1].split("?")[0]
            dyn_path = IMAGES_DIR / "cards" / "templates" / f"dyn_{bg_dyn_filename}"
            if dyn_path.exists() and dyn_path.stat().st_size > 200:
                bg_local = str(dyn_path.resolve())
                logger.debug(f"[Renderer] Template local encontrado: {dyn_path.name}")
            else:
                logger.warning(f"[Renderer] Template não encontrado localmente: {dyn_path.name}. Execute o scraper para baixar os templates.")

        # Bandeira da nação: caminho local
        nation_local = None
        nation_url = player_data.get("nation_flag_url") or player_data.get("nation_url")
        if nation_url and nation_url.startswith("/images/"):
            local_nation = PROJECT_ROOT / nation_url.lstrip("/")
            if local_nation.exists() and local_nation.stat().st_size > 200:
                nation_local = str(local_nation.resolve())
        nation_slug = sanitize_slug(player_data.get("nation", "unknown"))
        if not nation_local:
            nation_path_fallback = IMAGES_DIR / "cards" / "nations" / f"nation_{nation_slug}.png"
            if nation_path_fallback.exists() and nation_path_fallback.stat().st_size > 200:
                nation_local = str(nation_path_fallback.resolve())

        # Logo do clube: caminho local
        club_local = None
        club_url = player_data.get("club_logo_url") or player_data.get("club_url")
        if club_url and club_url.startswith("/images/"):
            local_club = PROJECT_ROOT / club_url.lstrip("/")
            if local_club.exists() and local_club.stat().st_size > 200:
                club_local = str(local_club.resolve())
        club_slug = sanitize_slug(player_data.get("club", "unknown"))
        if not club_local:
            club_path_fallback = IMAGES_DIR / "cards" / "clubs" / f"club_{club_slug}.png"
            if club_path_fallback.exists() and club_path_fallback.stat().st_size > 200:
                club_local = str(club_path_fallback.resolve())

        # Logo da liga: caminho local
        league_local = None
        league_url = player_data.get("league_logo_url") or player_data.get("league_url")
        if league_url and league_url.startswith("/images/"):
            local_league = PROJECT_ROOT / league_url.lstrip("/")
            if local_league.exists() and local_league.stat().st_size > 200:
                league_local = str(local_league.resolve())
        league_slug = sanitize_slug(player_data.get("league", "unknown"))
        if not league_local:
            league_path_fallback = IMAGES_DIR / "cards" / "leagues" / f"league_{league_slug}.png"
            if league_path_fallback.exists() and league_path_fallback.stat().st_size > 200:
                league_local = str(league_path_fallback.resolve())

        # Tratar Playstyles
        playstyles_input = player_data.get("playstyles") or []
        if not playstyles_input:
            import sqlite3
            db_path = PROJECT_ROOT / "database" / "help_dmes.db"
            if not db_path.exists():
                db_path = PROJECT_ROOT / "help_dmes.db"
                
            if db_path.exists():
                try:
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    
                    futbin_id = player_data.get("futbin_id") or player_data.get("id")
                    sofifa_id = player_data.get("sofifa_id")
                    p_name = player_data.get("name")
                    
                    row = None
                    if futbin_id:
                        cursor.execute("SELECT playstyles_json FROM player_cards WHERE futbin_id = ?", (str(futbin_id),))
                        row = cursor.fetchone()
                    if not row and sofifa_id:
                        cursor.execute("SELECT playstyles_json FROM player_cards WHERE sofifa_id = ?", (sofifa_id,))
                        row = cursor.fetchone()
                    if not row and p_name:
                        cursor.execute("SELECT playstyles_json FROM player_cards WHERE name LIKE ?", (f"%{p_name}%",))
                        row = cursor.fetchone()
                        
                    if not row and futbin_id:
                        cursor.execute("SELECT playstyles_json FROM fc_players WHERE futbin_id = ?", (str(futbin_id),))
                        row = cursor.fetchone()
                    if not row and p_name:
                        cursor.execute("SELECT playstyles_json FROM fc_players WHERE name LIKE ?", (f"%{p_name}%",))
                        row = cursor.fetchone()
                        
                    if row and row[0]:
                        try:
                            playstyles_input = json.loads(row[0])
                            logger.info(f"Playstyles para o jogador {name} carregados com sucesso do banco de dados SQLite.")
                        except Exception as e:
                            logger.warning(f"Erro ao deserializar playstyles_json para {name}: {e}")
                    conn.close()
                except Exception as e:
                    logger.warning(f"Erro ao acessar banco de dados SQLite para buscar playstyles de {name}: {e}")

        playstyles_payload = []
        seen_slugs = set()
        
        for idx, ps in enumerate(playstyles_input):
            ps_url = ps.get("icon_url") or ps.get("icon_path")
            if ps_url:
                ps_name = ps.get("name", f"ps_{idx}")
                is_plus = ps.get("is_plus", False) or "plus" in ps_name.lower() or "plus" in ps_url.lower()
                
                # Regra: Renderizar apenas Playstyles+ (omitir os base)
                if not is_plus:
                    continue
                    
                ps_slug = sanitize_slug(ps_name).replace("_plus", "")
                
                # Regra: Remover duplicatas
                if ps_slug in seen_slugs:
                    continue
                seen_slugs.add(ps_slug)
                
                suffix = "_plus" if is_plus else ""
                ps_path = IMAGES_DIR / "cards" / "renders" / f"playstyle_{ps_slug}{suffix}.png"
                ps_local = await ensure_asset_local(session, ps_url, ps_path)
                if ps_local:
                    playstyles_payload.append({
                        "icon_path": ps_local,
                        "is_plus": is_plus,
                        "slug": ps_slug
                    })

        # Tratar estatísticas (PAC, SHO, PAS, DRI, DEF, PHY)
        stats_input = player_data.get("stats") or []
        if not stats_input and "pace" in player_data:
            stats_input = [
                {"name": "PAC", "value": player_data.get("pace") or 0},
                {"name": "SHO", "value": player_data.get("shooting") or 0},
                {"name": "PAS", "value": player_data.get("passing") or 0},
                {"name": "DRI", "value": player_data.get("dribbling_stat") or player_data.get("dribbling") or 0},
                {"name": "DEF", "value": player_data.get("defending") or 0},
                {"name": "PHY", "value": player_data.get("physic") or player_data.get("physical") or 0},
            ]

        # Posições Alternativas
        raw_alt = player_data.get("alt_positions")
        alt_positions_payload = []
        if raw_alt:
            if isinstance(raw_alt, list):
                alt_positions_payload = [str(x) for x in raw_alt]
            elif isinstance(raw_alt, str):
                alt_positions_payload = [x.strip() for x in raw_alt.split(",") if x.strip()]

        # Perna Preferida
        raw_foot = player_data.get("foot") or player_data.get("preferred_foot")
        preferred_foot_payload = ""
        if raw_foot:
            foot_str = str(raw_foot).strip().lower()
            if "right" in foot_str or foot_str == "r":
                preferred_foot_payload = "R"
            elif "left" in foot_str or foot_str == "l":
                preferred_foot_payload = "L"
            else:
                preferred_foot_payload = str(raw_foot)[:1].upper()

        # Fintas e WF
        skills_wf_payload = player_data.get("skills_wf") or ""
        if not skills_wf_payload:
            sm = player_data.get("skill_moves")
            wf = player_data.get("weak_foot")
            if sm is not None and wf is not None:
                skills_wf_payload = f"{sm}-{wf}"
            elif sm is not None:
                skills_wf_payload = f"{sm}-?"
            elif wf is not None:
                skills_wf_payload = f"?-{wf}"

        # Montar dados estruturados para renderização
        render_data = {
            "name": name,
            "overall": player_data.get("overall") or player_data.get("rating") or 99,
            "position": player_data.get("position", "ST"),
            "card_type": player_data.get("card_type"),
            "bg_path": bg_local,
            "face_path": face_local,
            "nation_path": nation_local,
            "club_path": club_local,
            "league_path": league_local,
            "stats": stats_input,
            "playstyles": playstyles_payload,
            "alt_positions": alt_positions_payload,
            "preferred_foot": preferred_foot_payload,
            "skills_wf": skills_wf_payload
        }

        try:
            full_path, small_path = await asyncio.to_thread(
                self._draw_and_save_pillow,
                render_data,
                filename
            )
            
            res_json = {
                "success": True,
                "filename": filename,
                "full_path": str(full_path.resolve()),
                "small_path": str(small_path.resolve()),
                "card_template_url": f"/images/cards/full/{filename}",
                "card_small_url": f"/images/cards/small/{filename}",
                "render_url": f"/images/cards/renders/render_{futbin_id}_{name_slug}.png" if face_local else None,
                "nation_flag_url": f"/images/cards/nations/nation_{nation_slug}.png" if nation_local else None,
                "club_logo_url": f"/images/cards/clubs/club_{club_slug}.png" if club_local else None,
                "league_logo_url": f"/images/cards/leagues/league_{league_slug}.png" if league_local else None
            }
            logger.info(f"[Renderer] Card gerado nativamente via Pillow com sucesso para {name}.")
            return res_json
        except Exception as e:
            logger.error(f"[Renderer] Erro na renderização nativa de {name}: {e}", exc_info=True)
            return None

    def _draw_and_save_pillow(self, data: Dict, filename: str) -> Tuple[Path, Path]:
        canvas = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
        theme = get_card_theme(data.get("card_type"))
        
        # 1. Carregar Template de Fundo
        bg_loaded = False
        bg_path_str = data.get("bg_path")
        
        if bg_path_str:
            bg_path = Path(bg_path_str)
        else:
            bg_filename = theme["default_bg"]
            bg_path = IMAGES_DIR / "cards" / "templates" / bg_filename
            
        if bg_path and bg_path.exists():
            try:
                bg_img = Image.open(bg_path).convert("RGBA")
                bg_img = remove_white_corners_pillow(bg_img)
                bg_img = bg_img.resize((CARD_W, CARD_H), Image.Resampling.LANCZOS)
                canvas.paste(bg_img, (0, 0))
                bg_loaded = True
            except Exception as e:
                logger.warning(f"Erro ao abrir template {bg_filename}: {e}")
                
        if not bg_loaded:
            fallback_bg = IMAGES_DIR / "cards" / "templates" / "sbc_global_Normal_bg.png"
            if fallback_bg.exists():
                try:
                    bg_img = Image.open(fallback_bg).convert("RGBA")
                    bg_img = remove_white_corners_pillow(bg_img)
                    bg_img = bg_img.resize((CARD_W, CARD_H), Image.Resampling.LANCZOS)
                    canvas.paste(bg_img, (0, 0))
                except:
                    canvas.paste(Image.new("RGBA", (CARD_W, CARD_H), (50, 50, 50, 255)), (0, 0))
            else:
                canvas.paste(Image.new("RGBA", (CARD_W, CARD_H), (50, 50, 50, 255)), (0, 0))
                
        # 2. Carregar e Colar Foto do Jogador
        face_path_str = data.get("face_path")
        face_loaded = False
        
        if face_path_str:
            face_path = Path(face_path_str)
            if face_path.exists():
                try:
                    face_img = remove_background_photo(face_path)
                    
                    # Detecção inteligente baseada no aspect ratio (largura / altura)
                    aspect_ratio = face_img.width / face_img.height
                    if aspect_ratio <= 0.85:
                        # É um render oficial em formato de card (ex: 252x349 do Futbin)
                        # Escalar para cobrir a largura do card (756px) mantendo a proporção de aspecto
                        face_w = CARD_W
                        face_h = int(face_img.height * (CARD_W / face_img.width))
                        face_img = face_img.resize((face_w, face_h), Image.Resampling.LANCZOS)
                        # Colamos na coordenada Y=0 para alinhar perfeitamente no topo
                        canvas.alpha_composite(face_img, (0, 0))
                    else:
                        # Foto padrão: 64.28% de largura
                        face_w = int(CARD_W * 0.6428)
                        face_h = int(face_img.height * (face_w / face_img.width))
                        face_img = face_img.resize((face_w, face_h), Image.Resampling.LANCZOS)
                        face_x = int(CARD_W * 0.22)
                        face_y = int(CARD_H * 0.174)
                        canvas.alpha_composite(face_img, (face_x, face_y))
                        
                    face_loaded = True
                except Exception as e:
                    logger.error(f"Erro ao colar face do jogador: {e}")
                    
        if not face_loaded:
            default_av = draw_default_avatar()
            canvas.alpha_composite(default_av, (0, 0))
            
        draw = ImageDraw.Draw(canvas)
        
        # Cores do texto
        card_color = parse_color_rgba(theme.get("card_color"))
        rating_color = parse_color_rgba(theme.get("rating_color"))
        alt_pos_bg = parse_color_rgba(theme.get("alt_pos_bg"))
        alt_pos_border = parse_color_rgba(theme.get("alt_pos_border"))
        extra_info_bg = parse_color_rgba(theme.get("extra_info_bg"))
        extra_info_border = parse_color_rgba(theme.get("extra_info_border"))
        
        # 3. Overall + Posição + Role (CAMADA 3)
        block_x = int(CARD_W * 0.255)  # Afastado dos playstyles como no print
        block_y = int(CARD_H * 0.175)  # Alinhamento vertical ideal
        
        font_overall = pf(2.1373)
        font_position = pf(1.0)
        font_roleplus = pf(1.0606)
        
        # Overall
        draw.text((block_x, block_y), str(data.get("overall", 99)),
                  font=font_bebas(font_overall), fill=rating_color, anchor="mt")
                  
        # Posição
        pos_y = block_y + font_overall + int(CARD_H * 0.005)
        draw.text((block_x, pos_y), str(data.get("position", "ST")).upper(),
                  font=font_oswald(font_position), fill=rating_color, anchor="mt")
                  
        # Role Plus
        if data.get("role_plus") or data.get("position_role") == "plus":
            rp_y = pos_y + font_position + int(CARD_H * 0.003)
            draw.text((block_x, rp_y), "++",
                      font=font_bebas(font_roleplus), fill=rating_color, anchor="mt")
                      
        # 4. Playstyles (CAMADA 4)
        playstyles = data.get("playstyles") or []
        if playstyles:
            icon_size = max(int(CARD_W * 0.10), 20)  # ~75 px
            icon_x = int(CARD_W * 0.04) # ~30 px
            icon_y = int(CARD_H * 0.22) # Alinhado verticalmente com o overall
            gap = 8  # Gap uniforme de 8px
            
            for i, ps in enumerate(playstyles[:4]):
                ps_path_str = ps.get("icon_path")
                is_plus = ps.get("is_plus", False)
                
                if ps_path_str:
                    ps_path = Path(ps_path_str)
                    if ps_path.exists():
                        try:
                            y = icon_y + i * (icon_size + gap)
                            cx = icon_x + icon_size // 2
                            cy = y + icon_size // 2
                            r_ext = icon_size // 2
                            
                            # Lógica cromática adaptativa e inteligente (HSL regional)
                            card_type = data.get("card_type") or ""
                            is_base_card = card_type.lower() in ["gold", "gold_rare", "silver", "bronze"]
                            
                            if not is_base_card and bg_loaded and bg_path.exists():
                                try:
                                    # Extrair amostragem da região dos playstyles no template
                                    # Caixa: x = [4%, 15%], y = [22%, 55%]
                                    region_x1 = int(CARD_W * 0.04)
                                    region_y1 = int(CARD_H * 0.22)
                                    region_x2 = int(CARD_W * 0.15)
                                    region_y2 = int(CARD_H * 0.55)
                                    
                                    sample = bg_img.crop((region_x1, region_y1, region_x2, region_y2))
                                    avg_rgb = sample.resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))
                                    
                                    # Converter RGB para HSL
                                    r_val, g_val, b_val = avg_rgb[0] / 255.0, avg_rgb[1] / 255.0, avg_rgb[2] / 255.0
                                    h_val, l_val, s_val = colorsys.rgb_to_hls(r_val, g_val, b_val)
                                    
                                    # Forçar tom escuro premium (8% de luminosidade) e saturação acentuada
                                    target_l = 0.08
                                    target_s = min(s_val * 1.25, 1.0)
                                    r_new, g_new, b_new = colorsys.hls_to_rgb(h_val, target_l, target_s)
                                    
                                    bg_color = (int(r_new * 255), int(g_new * 255), int(b_new * 255), 255)
                                    border_color = (255, 255, 255, 255)
                                    glyph_color = (255, 255, 255, 255)
                                except Exception as err:
                                    logger.warning(f"Erro na análise cromática HSL regional: {err}. Fallback para cores estáticas.")
                                    bg_color = parse_color_rgba(theme.get("playstyle_bg") or theme.get("alt_pos_bg"))
                                    border_color = (255, 255, 255, 255)
                                    glyph_color = (255, 255, 255, 255)
                            else:
                                # Comportamento original para cards básicos ou se o template não estiver disponível
                                bg_color = parse_color_rgba(theme.get("playstyle_bg") or theme.get("alt_pos_bg"))
                                if "playstyle_border" in theme:
                                    border_color = parse_color_rgba(theme["playstyle_border"])
                                    glyph_color = border_color
                                else:
                                    if is_plus:
                                        border_color = (201, 155, 80, 255)  # Dourado/cobre metálico
                                        glyph_color = (201, 155, 80, 255)
                                    else:
                                        border_color = parse_color_rgba(theme.get("alt_pos_border"))
                                        glyph_color = border_color
                                      
                            # Para extrair o glifo limpo e colorir perfeitamente sem moldura metálica original,
                            # usamos a versão normal do arquivo .png correspondente
                            normal_path_str = str(ps_path).replace("_plus.png", ".png")
                            normal_path = Path(normal_path_str)
                            glyph_img_path = normal_path if normal_path.exists() else ps_path
                            
                            # Desenhar hexágono externo (borda)
                            dy_ext = r_ext // 2
                            dx_ext = int(r_ext * 0.866)
                            pts_ext = [
                                (cx, cy - r_ext),
                                (cx + dx_ext, cy - dy_ext),
                                (cx + dx_ext, cy + dy_ext),
                                (cx, cy + r_ext),
                                (cx - dx_ext, cy + dy_ext),
                                (cx - dx_ext, cy - dy_ext)
                            ]
                            draw.polygon(pts_ext, fill=border_color)
                            
                            # Desenhar hexágono interno (fundo)
                            r_int = r_ext - 3
                            dy_int = r_int // 2
                            dx_int = int(r_int * 0.866)
                            pts_int = [
                                (cx, cy - r_int),
                                (cx + dx_int, cy - dy_int),
                                (cx + dx_int, cy + dy_int),
                                (cx, cy + r_int),
                                (cx - dx_int, cy + dy_int),
                                (cx - dx_int, cy - dy_int)
                            ]
                            draw.polygon(pts_int, fill=bg_color)
                            
                            # Processar o desenho interno: isolar o glifo por threshold de escala de cinza e colorir
                            icon_img = Image.open(glyph_img_path).convert("RGBA")
                            inner_w = int(icon_size * 0.58)
                            inner_h = int(icon_img.height * (inner_w / icon_img.width))
                            icon_img = icon_img.resize((inner_w, inner_h), Image.Resampling.LANCZOS)
                            
                            r_ch, g_ch, b_ch, a_ch = icon_img.split()
                            gray = icon_img.convert("L")
                            
                            # Isolar pixels escuros (<120) do glifo e aplicar a mascara alfa original
                            glyph_mask = gray.point(lambda p: 255 if p < 120 else 0)
                            glyph_alpha = ImageChops.multiply(glyph_mask, a_ch)
                            
                            glyph_r, glyph_g, glyph_b = glyph_color[:3]
                            colored_icon = Image.merge("RGBA", (
                                Image.new("L", icon_img.size, glyph_r),
                                Image.new("L", icon_img.size, glyph_g),
                                Image.new("L", icon_img.size, glyph_b),
                                glyph_alpha
                            ))
                            
                            ix = cx - inner_w // 2
                            iy = cy - inner_h // 2
                            canvas.alpha_composite(colored_icon, (ix, iy))
                        except Exception as e:
                            logger.debug(f"Erro ao colar playstyle: {e}")
                            
        # 5. Posições Alternativas (CAMADA 5)
        alt_positions = data.get("alt_positions") or []
        if alt_positions:
            hex_item_w = max(int(CARD_W * 0.122) + 6, 22) # ~98 px
            hex_item_h = int(CARD_H * 0.07) # ~73 px
            hex_x = CARD_W - int(CARD_W * 0.04) - hex_item_w # ~628 px
            hex_y_start = int(CARD_H * 0.26) # ~274 px
            
            n_pos = len(alt_positions[:3])
            x_left = hex_x
            x_right = hex_x + hex_item_w
            x_center = hex_x + hex_item_w // 2
            h_cap = int(hex_item_w * 0.15) # ~14 px de ponta triangular
            y_start = hex_y_start
            y_end = hex_y_start + n_pos * hex_item_h
            
            # Geometria do hexágono integrado vertical
            pts_outer = [
                (x_center, y_start),
                (x_right, y_start + h_cap),
                (x_right, y_end - h_cap),
                (x_center, y_end),
                (x_left, y_end - h_cap),
                (x_left, y_start + h_cap)
            ]
            
            # Desenhar fundo do polígono
            draw.polygon(pts_outer, fill=alt_pos_bg)
            
            # Desenhar borda de 2px uniforme ligando os vértices
            for k in range(len(pts_outer)):
                p1 = pts_outer[k]
                p2 = pts_outer[(k + 1) % len(pts_outer)]
                draw.line([p1, p2], fill=alt_pos_border, width=2)
                
            for i, pos in enumerate(alt_positions[:3]):
                item_y = y_start + i * hex_item_h
                
                # Texto da Posição
                font_alt = pf(0.8)
                draw.text((x_center, item_y + hex_item_h // 2), pos.upper(),
                          font=font_oswald(font_alt), fill=alt_pos_border, anchor="mm")
                          
                # Divisória horizontal interna
                if i < n_pos - 1:
                    line_y = item_y + hex_item_h
                    draw.line([(x_left, line_y), (x_right, line_y)], fill=alt_pos_border, width=2)
                    
        # 6. Barra Extra Info: Pé | Skill | Weak Foot (CAMADA 6)
        bar_y = int(CARD_H * 0.88)
        bar_font = max(int(pf(0.9)), 9)
        
        foot = data.get("preferred_foot") or "R"
        
        # Desmembrar skills_wf (ex: "5-4")
        skills_wf = data.get("skills_wf", "")
        skill_moves = 3
        weak_foot = 3
        if skills_wf and "-" in skills_wf:
            parts = skills_wf.split("-")
            if len(parts) >= 2:
                try:
                    skill_moves = int(parts[0]) if parts[0].isdigit() else 3
                    weak_foot = int(parts[1]) if parts[1].isdigit() else 3
                except:
                    pass
                    
        skill = f"{skill_moves}*"
        wf = f"{weak_foot} WF" # Número do weak foot seguido de WF (sem emoji)
        
        items = [foot, skill, wf]
        label = "  |  ".join(items)
        
        bbox = draw.textbbox((0, 0), label, font=font_oswald(bar_font))
        text_w = bbox[2] - bbox[0]
        padding_x = int(CARD_W * 0.04)
        
        bar_bg_w = text_w + padding_x * 2
        bar_bg_h = int(pf(0.9) * 1.6)
        bar_bg_x = (CARD_W - bar_bg_w) // 2
        
        draw.rounded_rectangle(
            [bar_bg_x, bar_y - bar_bg_h // 2, bar_bg_x + bar_bg_w, bar_y + bar_bg_h // 2],
            radius=bar_bg_h // 3,
            fill=extra_info_bg,
            outline=extra_info_border,
            width=2
        )
        
        draw.text((CARD_W // 2, bar_y), label,
                  font=font_oswald(bar_font), fill=extra_info_border, anchor="mm")
                  
        # 7. Nome + Atributos + Badges (CAMADA 7)
        # Coordenadas verticais calibradas e fixas no canvas de 756 x 1056 px
        zona_nome = py(0.65)   # ~686 px
        zona_stats = py(0.74)  # ~781 px
        zona_badges = py(0.83) # ~876 px
        
        # 7a — Nome
        font_name = pf(1.5)
        draw.text((CARD_W // 2, zona_nome), data.get("name", "PLAYER").upper(),
                  font=font_bebas(font_name), fill=card_color, anchor="mm")
                  
        # 7b — Atributos
        stats_list = data.get("stats") or []
        stats_dict = {s["name"].upper(): s["value"] for s in stats_list if "name" in s and "value" in s}
        stats = [
            ("PAC", stats_dict.get("PAC", 0)),
            ("SHO", stats_dict.get("SHO", 0)),
            ("PAS", stats_dict.get("PAS", 0)),
            ("DRI", stats_dict.get("DRI", 0)),
            ("DEF", stats_dict.get("DEF", 0)),
            ("PHY", stats_dict.get("PHY", 0)),
        ]
        
        font_stat_num = int(pf(1.2)) # ~50 px
        font_stat_label = int(font_stat_num * 0.77) # ~38 px
        
        n = len(stats)
        max_width = int(CARD_W * 0.78)
        col_w = max_width // n
        start_x = (CARD_W - max_width) // 2
        
        for i, (lbl, val) in enumerate(stats):
            col_cx = start_x + col_w * i + col_w // 2
            
            # Estatística com layout column-reverse usando deslocamentos precisos e âncora "mm"
            # Número acima
            draw.text((col_cx, zona_stats - int(font_stat_num * 0.45)), str(val),
                      font=font_bebas(font_stat_num), fill=card_color, anchor="mm")
            # Rótulo abaixo
            draw.text((col_cx, zona_stats + int(font_stat_num * 0.45)), lbl.upper(),
                      font=font_oswald(font_stat_label), fill=card_color, anchor="mm")
                      
        # 7c — Badges
        badge_size = int(CARD_W * 0.0873)
        badge_gap = int(CARD_W * 0.02)
        
        badge_paths = []
        for path_key in ["nation_path", "league_path", "club_path"]:
            p = data.get(path_key)
            if p and Path(p).exists():
                badge_paths.append(str(Path(p).resolve()))
                
        if badge_paths:
            total_badge_w = len(badge_paths) * badge_size + (len(badge_paths) - 1) * badge_gap
            badge_start_x = (CARD_W - total_badge_w) // 2
            badge_y = zona_badges - badge_size // 2
            
            for j, bp in enumerate(badge_paths):
                try:
                    badge_img = Image.open(bp).convert("RGBA")
                    badge_img = badge_img.resize((badge_size, badge_size), Image.Resampling.LANCZOS)
                    bx = badge_start_x + j * (badge_size + badge_gap)
                    canvas.alpha_composite(badge_img, (bx, badge_y))
                except Exception as e:
                    logger.debug(f"Erro ao colar badge: {e}")
                    
        # Downscaling e Salvamento
        FULL_DIR.mkdir(parents=True, exist_ok=True)
        SMALL_DIR.mkdir(parents=True, exist_ok=True)
        
        full_path = FULL_DIR / filename
        small_path = SMALL_DIR / filename
        
        # Full (2x)
        full_card = canvas.resize((504, 698), Image.Resampling.LANCZOS)
        full_card.save(full_path, format="PNG", optimize=True)
        
        # Small (recorte inteligente)
        top_crop = full_card.crop((0, 0, 504, 302))
        bottom_crop = full_card.crop((0, 558, 504, 698))
        
        mini_canvas = Image.new("RGBA", (504, 442), (0, 0, 0, 0))
        mini_canvas.paste(top_crop, (0, 0))
        mini_canvas.paste(bottom_crop, (0, 302))
        
        small_card = mini_canvas.resize((150, 169), Image.Resampling.LANCZOS)
        small_card.save(small_path, format="PNG", optimize=True)
        
        return full_path, small_path
