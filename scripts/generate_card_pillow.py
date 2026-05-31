#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gerador de Cards EA FC 26 utilizando Python e Pillow (PIL).
Calibrado com precisão com base na engenharia reversa do HTML/CSS real do FUTBIN.
"""

import os
import sys
import time
import logging
import functools
import unicodedata
import re
import colorsys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageColor, ImageFilter, ImageOps, ImageChops

# Configuração de Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("FC_Pillow_Generator")

# Configuração de Paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
IMAGES_DIR = PROJECT_ROOT / "images"
FONTS_DIR = PROJECT_ROOT / "backend" / "card_generator_js" / "fonts"

# Fontes locais
BEBAS_FONT_PATH = FONTS_DIR / "BebasNeue-Regular.ttf"
OSWALD_FONT_PATH = FONTS_DIR / "Oswald-Regular.ttf"

# Validar fontes no início da execução
try:
    if not BEBAS_FONT_PATH.exists() or not OSWALD_FONT_PATH.exists():
        raise FileNotFoundError("Fontes Bebas Neue ou Oswald não encontradas no diretório especificado.")
    # Testar carregamento rápido
    _test = ImageFont.truetype(str(BEBAS_FONT_PATH), 10)
    _test = ImageFont.truetype(str(OSWALD_FONT_PATH), 10)
except Exception as e:
    logger.error(f"Erro crítico ao validar fontes: {e}. Verifique as fontes em: {FONTS_DIR}")
    sys.exit(1)

# Dimensões e Resolução (Base 756 × 1056 px)
CARD_W = 756
CARD_H = 1056

# Cores e Temas por Raridade (Conforme especificação)
CARD_THEMES = {
    "gold": {
        "card_color": "#443a22", "rating_color": "#443a22",
        "alt_pos_bg": "#D0B77F", "alt_pos_border": "#443a22",
        "extra_info_bg": "#D0B77F", "extra_info_border": "#443a22",
        "playstyle_bg": "#2c2616", "playstyle_border": "#d8b97a",
        "default_bg": "sbc_global_Normal_bg.png"
    },
    "gold_rare": {
        "card_color": "#443a22", "rating_color": "#443a22",
        "alt_pos_bg": "#C8A020", "alt_pos_border": "#443a22",
        "extra_info_bg": "#C8A020", "extra_info_border": "#443a22",
        "playstyle_bg": "#2c2616", "playstyle_border": "#d8b97a",
        "default_bg": "sbc_global_Normal_bg.png"
    },
    "silver": {
        "card_color": "#5a5a5a", "rating_color": "#5a5a5a",
        "alt_pos_bg": "#C0C0C0", "alt_pos_border": "#5a5a5a",
        "extra_info_bg": "#C0C0C0", "extra_info_border": "#5a5a5a",
        "playstyle_bg": "#2b2b2b", "playstyle_border": "#c0c0c0",
        "default_bg": "sbc_global_Normal_bg.png"
    },
    "bronze": {
        "card_color": "#5c3a1e", "rating_color": "#5c3a1e",
        "alt_pos_bg": "#CD7F32", "alt_pos_border": "#5c3a1e",
        "extra_info_bg": "#CD7F32", "extra_info_border": "#5c3a1e",
        "playstyle_bg": "#2c1b0e", "playstyle_border": "#cd7f32",
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
        "playstyle_bg": "#080828", "playstyle_border": "#ffd700",
        "default_bg": "sbc_global_TOTY_bg.png"
    },
    "hero": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#1a0a2e", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#1a0a2e", "extra_info_border": "#ffffff",
        "playstyle_bg": "#10051e", "playstyle_border": "#ff00d0",
        "default_bg": "sbc_global_Hero_SBC_bg.png"
    },
    "totw": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#1a1a1a", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#1a1a1a", "extra_info_border": "#ffffff",
        "playstyle_bg": "#121212", "playstyle_border": "#e5c158",
        "default_bg": "sbc_global_TOTW_bg.png"
    },
    "icon": {
        "card_color": "#f0e6c8", "rating_color": "#f0e6c8",
        "alt_pos_bg": "#2a1a0a", "alt_pos_border": "#f0e6c8",
        "extra_info_bg": "#2a1a0a", "extra_info_border": "#f0e6c8",
        "playstyle_bg": "#1f1307", "playstyle_border": "#e6c891",
        "default_bg": "sbc_global_Icon_bg.png"
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
    """Calcula o tamanho de fonte baseado na proporção base do card."""
    base = CARD_W * 0.0557  # ~42.1px no canvas de 756px
    return int(base * base_multiplier)

def get_card_theme(card_type: Optional[str]) -> Dict[str, str]:
    if not card_type:
        return CARD_THEMES["gold"]
    ct_lower = card_type.lower()
    if ct_lower in CARD_THEMES:
        return CARD_THEMES[ct_lower]
    # Busca por correspondência parcial
    for key, val in CARD_THEMES.items():
        if key in ct_lower:
            return val
            
    # Se não é base card (gold, silver, bronze), assume que é especial e precisa de cores claras
    is_base = any(base in ct_lower for base in ["gold", "silver", "bronze"])
    if not is_base:
        return {
            "card_color": "#ffffff", "rating_color": "#ffffff",
            "alt_pos_bg": "#121212", "alt_pos_border": "#ffffff",
            "extra_info_bg": "#121212", "extra_info_border": "#ffffff",
            "playstyle_bg": "#121212", "playstyle_border": "#ffffff",
            "default_bg": "sbc_global_Normal_bg.png"
        }
        
    return CARD_THEMES["gold"]


def extract_dynamic_palette(bg_img: Image.Image) -> Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int]]:
    """Extrai uma cor escura e uma vibrante da imagem do template usando quantização (K-Means)."""
    # Focar na região central para pegar os tons principais da carta
    w, h = bg_img.size
    region = bg_img.crop((int(w * 0.05), int(h * 0.2), int(w * 0.95), int(h * 0.9)))
    small = region.resize((50, 50), Image.Resampling.BOX).convert("RGB")
    q = small.quantize(colors=10, method=Image.Quantize.MEDIANCUT)
    
    counts_and_idx = q.getcolors(50 * 50)
    if not counts_and_idx:
        return (20, 20, 20, 255), (255, 255, 255, 255)
        
    palette = q.getpalette()
    
    colors_hls = []
    for count, idx in counts_and_idx:
        r, g, b = palette[idx*3:idx*3+3]
        h_val, l_val, s_val = colorsys.rgb_to_hls(r/255.0, g/255.0, b/255.0)
        colors_hls.append({"count": count, "rgb": (r, g, b), "h": h_val, "l": l_val, "s": s_val})
        
    # Sort by count (dominance)
    colors_hls.sort(key=lambda x: x["count"], reverse=True)
    
    # 1. Procurar cor escura para fundo (L < 0.4)
    dark_colors = [c for c in colors_hls if c["l"] < 0.4]
    if dark_colors:
        dc = dark_colors[0]
    else:
        # Pega a mais escura independente do L
        dc = min(colors_hls, key=lambda x: x["l"])
    bg_color = (dc["rgb"][0], dc["rgb"][1], dc["rgb"][2], 255)
        
    # 2. Procurar cor vibrante para bordas (S > 0.3)
    vibrant_colors = [c for c in colors_hls if c["s"] > 0.3]
    if not vibrant_colors:
        vibrant_colors = [c for c in colors_hls if c["s"] > 0.15]
        
    if vibrant_colors:
        # Pega a mais saturada das vibrantes
        vc = max(vibrant_colors, key=lambda x: x["s"])
        # Garantir luminosidade boa para contraste/visibilidade, mas mantendo a cor real
        r, g, b = colorsys.hls_to_rgb(vc["h"], min(max(vc["l"], 0.5), 0.9), vc["s"])
        accent_color = (int(r*255), int(g*255), int(b*255), 255)
    else:
        # Fallback se não tiver NENHUMA cor com S > 0.15 (ex: card branco e preto)
        accent_color = (255, 255, 255, 255)
        
    return bg_color, accent_color


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
    """Remove os cantos brancos de templates baixados usando floodfill nativo."""
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    w, h = image.size
    corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    for corner in corners:
        ImageDraw.floodfill(image, corner, (0, 0, 0, 0), thresh=thresh)
    return image

def remove_background_photo(image_path: Path) -> Image.Image:
    """
    Remove o fundo de uma imagem de forma inteligente.
    Tenta usar rembg e se falhar/não estiver instalado faz Chroma Key nativo.
    """
    img = Image.open(image_path).convert("RGBA")
    
    # Verificar se a imagem já possui canal alfa com transparência ativa (ex: PNG recortado do Futbin)
    if img.mode == "RGBA":
        alpha = img.split()[3]
        min_alpha, max_alpha = alpha.getextrema()
        if min_alpha < 255:
            logger.info(f"A imagem {image_path.name} já possui canal de transparência (alfa mínimo: {min_alpha}). Pulando remoção de fundo para preservar qualidade.")
            return img
            
    # Tentativa com rembg por IA
    try:
        from rembg import remove
        logger.debug("Usando rembg (IA) para remoção de fundo da foto.")
        return remove(img)
    except Exception as e:
        logger.debug(f"rembg indisponível ({e}). Iniciando fallback Chroma Key nativo com Pillow.")
        
        # Fallback Chroma Key baseando-se na cor do canto (5, 5)
        w, h = img.size
        bg_r, bg_g, bg_b, _ = img.getpixel((5, 5))
        
        pixels = img.load()
        new_pixels = []
        tolerance = 45  # Tolerância cromática
        
        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
                dist = ((r - bg_r)**2 + (g - bg_g)**2 + (b - bg_b)**2)**0.5
                if dist < tolerance:
                    new_pixels.append((r, g, b, 0))
                else:
                    new_pixels.append((r, g, b, a))
        
        img.putdata(new_pixels)
        
        # Suavização de bordas por desfoque Gaussiano no canal alfa
        alpha = img.split()[3]
        alpha = alpha.filter(ImageFilter.GaussianBlur(1.0))
        img.putalpha(alpha)
        
        return img

def draw_default_avatar() -> Image.Image:
    """Gera uma silhueta de jogador simples caso a foto falhe."""
    avatar = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(avatar)
    gray = (120, 125, 130, 255)
    
    # Cabeça
    cx, cy, cr = px(0.53), py(0.35), px(0.15)
    draw.ellipse((cx - cr, cy - cr, cx + cr, cy + cr), fill=gray)
    
    # Ombros (Trapézio/Retângulo)
    draw.polygon([
        (px(0.28), py(0.68)),
        (px(0.78), py(0.68)),
        (px(0.85), py(0.85)),
        (px(0.21), py(0.85))
    ], fill=gray)
    return avatar

def draw_card(player: dict) -> Image.Image:
    """Gera o card do jogador em supersampling 3x (756x1056 px) de acordo com o FUTBIN."""
    canvas = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    theme = get_card_theme(player.get("card_type"))
    
    # 1. Carregar Template de Fundo (CAMADA 1)
    bg_template = player.get("bg_template_path")
    bg_loaded = False
    
    if bg_template:
        bg_path = Path(bg_template)
        if bg_path.exists():
            try:
                bg_img = Image.open(bg_path).convert("RGBA")
                bg_img = remove_white_corners_pillow(bg_img)
                bg_img = bg_img.resize((CARD_W, CARD_H), Image.Resampling.LANCZOS)
                canvas.paste(bg_img, (0, 0))
                bg_loaded = True
            except Exception as e:
                logger.warning(f"Erro ao carregar bg_template_path {bg_template}: {e}")
                
    if not bg_loaded:
        # Tentar carregar a partir do tema
        theme_bg_name = theme["default_bg"]
        theme_bg_path = IMAGES_DIR / "cards" / "templates" / theme_bg_name
        if theme_bg_path.exists():
            try:
                bg_img = Image.open(theme_bg_path).convert("RGBA")
                bg_img = remove_white_corners_pillow(bg_img)
                bg_img = bg_img.resize((CARD_W, CARD_H), Image.Resampling.LANCZOS)
                canvas.paste(bg_img, (0, 0))
            except Exception as e:
                logger.error(f"Erro ao carregar template padrão do tema {theme_bg_name}: {e}")
                canvas.paste(Image.new("RGBA", (CARD_W, CARD_H), (50, 50, 50, 255)), (0, 0))
        else:
            logger.warning(f"Template do tema não encontrado em {theme_bg_path}. Usando fundo cinza padrão.")
            canvas.paste(Image.new("RGBA", (CARD_W, CARD_H), (50, 50, 50, 255)), (0, 0))
            
    # 2. Carregar e Colar Foto do Jogador (CAMADA 2)
    face_path_str = player.get("face_path")
    face_loaded = False
    is_special = player.get("is_special", False) or player.get("card_type", "").lower() in SPECIAL_CARD_TYPES
    
    if face_path_str:
        face_path = Path(face_path_str)
        if face_path.exists():
            try:
                # Remoção de fundo inteligente
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
                logger.error(f"Erro ao colar foto do jogador {face_path_str}: {e}")
                
    if not face_loaded:
        logger.info(f"Usando silhueta de avatar padrão para o jogador {player.get('name')}.")
        default_av = draw_default_avatar()
        canvas.alpha_composite(default_av, (0, 0))
        
    # Inicializar a ferramenta de desenho
    draw = ImageDraw.Draw(canvas)
    
    # Cores do texto
    card_color = parse_color_rgba(player.get("card_color") or theme.get("card_color"))
    rating_color = parse_color_rgba(player.get("rating_color") or theme.get("rating_color"))
    alt_pos_bg = parse_color_rgba(player.get("alt_pos_bg") or theme.get("alt_pos_bg"))
    alt_pos_border = parse_color_rgba(player.get("alt_pos_border") or theme.get("alt_pos_border"))
    extra_info_bg = parse_color_rgba(player.get("extra_info_bg") or theme.get("extra_info_bg"))
    extra_info_border = parse_color_rgba(player.get("extra_info_border") or theme.get("extra_info_border"))
    
    is_base_card = player.get("card_type", "").lower() in ["gold", "gold_rare", "silver", "bronze"]
    
    # Extração dinâmica de paleta
    bg_color_adaptive = None
    accent_color_adaptive = None
    if not is_base_card and bg_loaded and bg_template:
        try:
            bg_color_adaptive, accent_color_adaptive = extract_dynamic_palette(bg_img)
        except Exception as e:
            logger.warning(f"Erro na extração dinâmica de paleta: {e}")
            
    # Sobrescrever cores de alt_pos e extra_info com base na paleta extraída
    if bg_color_adaptive and accent_color_adaptive:
        alt_pos_bg = bg_color_adaptive
        alt_pos_border = accent_color_adaptive
        extra_info_bg = bg_color_adaptive
        extra_info_border = accent_color_adaptive
        
        # Aplicar cor vibrante da paleta nos textos (Overall, Nome, Stats)
        card_color = accent_color_adaptive
        rating_color = accent_color_adaptive

    
    # 3. Overall + Posição + Role (CAMADA 3)
    block_x = int(CARD_W * 0.255)  # Afastado dos playstyles como no print
    block_y = int(CARD_H * 0.175)  # Alinhamento vertical ideal
    
    font_overall = pf(2.1373)
    font_position = pf(1.0)
    font_roleplus = pf(1.0606)
    
    # Overall
    draw.text((block_x, block_y), str(player.get("overall", 99)),
              font=font_bebas(font_overall), fill=rating_color, anchor="mt")
              
    # Posição
    pos_y = block_y + font_overall + int(CARD_H * 0.005)
    draw.text((block_x, pos_y), player.get("position", "ST").upper(),
              font=font_oswald(font_position), fill=rating_color, anchor="mt")
              
    # Role Plus
    if player.get("role_plus") or player.get("role") == "plus":
        rp_y = pos_y + font_position + int(CARD_H * 0.003)
        draw.text((block_x, rp_y), "++",
                  font=font_bebas(font_roleplus), fill=rating_color, anchor="mt")
                  
    # 4. Playstyles (CAMADA 4)
    playstyles_input = player.get("playstyles") or []
    playstyles_plus = player.get("playstyles_plus") or []
    
    if not playstyles_input:
        import sqlite3
        import json
        db_path = PROJECT_ROOT / "database" / "help_dmes.db"
        if not db_path.exists():
            db_path = PROJECT_ROOT / "help_dmes.db"
            
        if db_path.exists():
            try:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                
                futbin_id = player.get("futbin_id") or player.get("id")
                p_name = player.get("name")
                
                row = None
                if futbin_id:
                    cursor.execute("SELECT playstyles_json FROM player_cards WHERE futbin_id = ?", (str(futbin_id),))
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
                        db_ps_list = json.loads(row[0])
                        # Se veio do banco de dados, mantemos a lista original com URLs
                        playstyles_input = db_ps_list
                        logger.info(f"Playstyles para {p_name} carregados com sucesso do SQLite de desenvolvimento.")
                    except Exception as e:
                        logger.warning(f"Erro ao deserializar playstyles_json para {p_name}: {e}")
                conn.close()
            except Exception as e:
                logger.warning(f"Erro ao acessar SQLite de desenvolvimento para playstyles de {p_name}: {e}")

    playstyles = playstyles_input
    if playstyles:
        icon_size = max(int(CARD_W * 0.10), 20)  # ~75 px para se ajustar perfeitamente
        icon_x = int(CARD_W * 0.04) # ~30 px
        icon_y = int(CARD_H * 0.22) # Alinhado verticalmente com o overall
        gap = 8  # Gap uniforme de 8px entre os hexágonos
        
        for i, ps_name in enumerate(playstyles[:4]):
            # Aceita se for string simples ou dicionario deserializado
            is_plus = False
            ps_url = None
            if isinstance(ps_name, dict):
                is_plus = ps_name.get("is_plus", False) or "plus" in ps_name.get("name", "").lower()
                ps_url = ps_name.get("icon_url") or ps_name.get("icon_path")
                ps_name = ps_name.get("name", "")
            else:
                is_plus = ps_name in playstyles_plus or (ps_name + "+") in playstyles_plus or "plus" in ps_name.lower()
                
            ps_slug = ps_name.lower().replace(" ", "_").replace("+", "").replace("_plus", "")
            
            # Buscar arquivo de imagem no disco
            suffix = "_plus" if is_plus else ""
            ps_path = IMAGES_DIR / "cards" / "renders" / f"playstyle_{ps_slug}{suffix}.png"
            if not ps_path.exists():
                ps_path = IMAGES_DIR / "cards" / "renders" / f"{ps_slug}{suffix}.png"
                
            if not ps_path.exists() and ps_url:
                # Fazer download lazy de fallback para testes
                try:
                    import urllib.request
                    logger.info(f"Baixando playstyle '{ps_name}' de {ps_url} para {ps_path.name}...")
                    req = urllib.request.Request(
                        ps_url, 
                        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                    )
                    with urllib.request.urlopen(req, timeout=5) as response, open(ps_path, 'wb') as out_file:
                        out_file.write(response.read())
                    logger.info(f"Playstyle '{ps_name}' baixado com sucesso.")
                except Exception as e:
                    logger.warning(f"Erro ao baixar playstyle '{ps_name}' de {ps_url}: {e}")
                    
            if ps_path.exists():
                try:
                    y = icon_y + i * (icon_size + gap)
                    cx = icon_x + icon_size // 2
                    cy = y + icon_size // 2
                    r_ext = icon_size // 2
                    
                    # Lógica cromática super robusta para Playstyles Comuns vs Plus (Regras 3 e 4)
                    if is_plus:
                        # Playstyle Plus (+) se adapta ao template dinamicamente
                        if bg_color_adaptive and accent_color_adaptive:
                            bg_color = bg_color_adaptive
                            border_color = accent_color_adaptive
                            glyph_color = accent_color_adaptive
                        else:
                            # Caso padrão se falhar a extração
                            if not is_base_card:
                                bg_color = parse_color_rgba(theme.get("playstyle_bg") or theme.get("alt_pos_bg"))
                                border_color = (255, 255, 255, 255)
                                glyph_color = (255, 255, 255, 255)
                            else:
                                bg_color = (24, 19, 11, 255) # Tom escuro de dourado
                                border_color = (201, 155, 80, 255) # Dourado
                                glyph_color = (255, 255, 255, 255)
                    else:
                        # Playstyle Comum (Normal) - Regra 4: manter o azul escuro e deixar o glifo/borda em branco
                        bg_color = (8, 19, 36, 255)  # Azul escuro clássico da EA (#081324)
                        border_color = (255, 255, 255, 255)  # Branco
                        glyph_color = (255, 255, 255, 255)  # Branco

                            
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
                    logger.debug(f"Erro ao colar playstyle {ps_name}: {e}")
                    
    # 5. Posições Alternativas (CAMADA 5)
    alt_positions = player.get("alt_positions") or []
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
        
        # Desenhar borda de 4px uniforme ligando os vértices
        for k in range(len(pts_outer)):
            p1 = pts_outer[k]
            p2 = pts_outer[(k + 1) % len(pts_outer)]
            draw.line([p1, p2], fill=alt_pos_border, width=4)
            
        for i, pos in enumerate(alt_positions[:3]):
            item_y = y_start + i * hex_item_h
            
            # Texto da Posição
            font_alt = pf(0.8)
            draw.text((x_center, item_y + hex_item_h // 2), pos.upper(),
                      font=font_oswald(font_alt), fill=alt_pos_border, anchor="mm")
                      
            # Divisória horizontal interna
            if i < n_pos - 1:
                line_y = item_y + hex_item_h
                draw.line([(x_left, line_y), (x_right, line_y)], fill=alt_pos_border, width=4)
                
    # 6. Barra Extra Info: Pé | Skill | Weak Foot (CAMADA 6)
    foot = player.get("preferred_foot") or player.get("foot") or "R"
    foot = "L" if "left" in str(foot).lower() or str(foot).upper() == "L" else "R"
    
    sm_val = player.get("skill_moves") or 3
    wf_val = player.get("weak_foot") or 3
    
    # Dimensions
    box_w = max(int(CARD_W * 0.122) + 6, 22) # Mesma largura da box de posições (~98 px)
    box_h = int(CARD_H * 0.045) # Altura da pílula (~47 px)
    gap = int(CARD_H * 0.005) # Distância entre as pílulas
    
    # Positioning
    box_x = CARD_W - int(CARD_W * 0.04) - box_w
    # Colocar substancialmente mais acima para não encostar nos valores dos atributos (ex: 62 PHY)
    box_y_bottom = py(0.66)
    box_y_top = box_y_bottom - (box_h * 2 + gap)
    
    # Função auxiliar para desenhar estrela
    import math
    def draw_star(center_x, center_y, outer_radius, inner_radius, fill_color):
        num_points = 5
        angle = math.pi / 2 # Começa apontando pra cima
        points = []
        for i in range(num_points * 2):
            radius = outer_radius if i % 2 == 0 else inner_radius
            x = center_x + radius * math.cos(angle)
            y = center_y - radius * math.sin(angle)
            points.append((x, y))
            angle -= math.pi / num_points
        draw.polygon(points, fill=fill_color)

    font_ext = pf(0.95) # Texto sutilmente maior para ler bem
    
    # TOP BOX (Foot)
    rect_top = [box_x, box_y_top, box_x + box_w, box_y_top + box_h]
    draw.rounded_rectangle(rect_top, radius=box_h//3, fill=extra_info_bg, outline=extra_info_border, width=4)
    draw.text((box_x + box_w//2, box_y_top + box_h//2), foot, font=font_oswald(font_ext), fill=extra_info_border, anchor="mm")
    
    # BOTTOM BOX (SM Star WF)
    rect_bot = [box_x, box_y_top + box_h + gap, box_x + box_w, box_y_top + box_h * 2 + gap]
    draw.rounded_rectangle(rect_bot, radius=box_h//3, fill=extra_info_bg, outline=extra_info_border, width=4)
    
    mid_y = box_y_top + box_h + gap + box_h//2
    # Deslocar os números do centro para dar espaço para a estrela
    offset_x = int(box_w * 0.28)
    draw.text((box_x + box_w//2 - offset_x, mid_y), str(sm_val), font=font_oswald(font_ext), fill=extra_info_border, anchor="mm")
    draw.text((box_x + box_w//2 + offset_x, mid_y), str(wf_val), font=font_oswald(font_ext), fill=extra_info_border, anchor="mm")
    
    # Estrela central
    star_r_out = int(box_h * 0.22)
    star_r_in = int(star_r_out * 0.4)
    draw_star(box_x + box_w//2, mid_y, star_r_out, star_r_in, extra_info_border)
              
    # 7. Nome + Atributos + Badges (CAMADA 7)
    # 7. Nome + Atributos + Badges (CAMADA 7)
    # Coordenadas verticais calibradas e fixas no canvas de 756 x 1056 px
    zona_nome = py(0.65)   # ~686 px
    zona_stats = py(0.74)  # ~781 px
    zona_badges = py(0.83) # ~876 px
    
    # 7a — Nome do jogador (MAIÚSCULAS)
    font_name = pf(1.5)
    draw.text((CARD_W // 2, zona_nome), player.get("name", "PLAYER NAME").upper(),
              font=font_bebas(font_name), fill=card_color, anchor="mm")
              
    # 7b — Atributos (stats)
    stats_list = player.get("stats") or []
    stats_dict = {}
    if isinstance(stats_list, list):
        stats_dict = {s["name"].upper(): s["value"] for s in stats_list if isinstance(s, dict) and "name" in s and "value" in s}
        
    stats = [
        ("PAC", stats_dict.get("PAC") or player.get("pac") or player.get("pace") or 0),
        ("SHO", stats_dict.get("SHO") or player.get("sho") or player.get("shooting") or 0),
        ("PAS", stats_dict.get("PAS") or player.get("pas") or player.get("passing") or 0),
        ("DRI", stats_dict.get("DRI") or player.get("dri") or player.get("dribbling") or player.get("dribbling_stat") or 0),
        ("DEF", stats_dict.get("DEF") or player.get("def") or player.get("defending") or 0),
        ("PHY", stats_dict.get("PHY") or player.get("phy") or player.get("physical") or player.get("physic") or 0),
    ]


    
    font_stat_num = int(pf(1.2)) # ~50 px
    font_stat_label = int(font_stat_num * 0.77) # ~38 px
    
    n = len(stats)
    max_width = int(CARD_W * 0.78)
    col_w = max_width // n
    start_x = (CARD_W - max_width) // 2
    
    for i, (lbl, val) in enumerate(stats):
        col_cx = start_x + col_w * i + col_w // 2
        
        # Estatística com layout idêntico ao do print 2 (Label em cima, Número embaixo)
        # Rótulo acima
        draw.text((col_cx, zona_stats - int(font_stat_num * 0.45)), lbl.upper(),
                  font=font_oswald(font_stat_label), fill=card_color, anchor="mm")
        # Número abaixo
        draw.text((col_cx, zona_stats + int(font_stat_num * 0.45)), str(val),
                  font=font_bebas(font_stat_num), fill=card_color, anchor="mm")
                  
    # 7c — Badges (Nação | Liga | Clube)
    # Tamanho e espaçamento menores, de acordo com o print 2
    badge_size = int(CARD_W * 0.055) # Reduzido de 0.0873
    badge_gap = int(CARD_W * 0.015)  # Gap ligeiramente menor para compactar
    
    # Carregar imagens locais dos badges
    badge_paths = []
    for path_key in ["nation_path", "league_path", "club_path"]:
        p = player.get(path_key)
        if p and Path(p).exists():
            badge_paths.append(str(Path(p).resolve()))
        else:
            # Fallbacks baseados em IDs
            if path_key == "nation_path" and player.get("nation_id"):
                p_fallback = IMAGES_DIR / "cards" / "nations" / f"nation_{player.get('nation_id')}.png"
                if p_fallback.exists(): badge_paths.append(str(p_fallback))
            elif path_key == "league_path" and player.get("league_id"):
                p_fallback = IMAGES_DIR / "cards" / "leagues" / f"league_{player.get('league_id')}.png"
                if p_fallback.exists(): badge_paths.append(str(p_fallback))
            elif path_key == "club_path" and player.get("club_id"):
                p_fallback = IMAGES_DIR / "cards" / "clubs" / f"club_{player.get('club_id')}.png"
                if p_fallback.exists(): badge_fallback = p_fallback
                if p_fallback.exists(): badge_paths.append(str(p_fallback))
                
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
                logger.debug(f"Erro ao renderizar badge {bp}: {e}")
                
    return canvas

def save_card(card_3x: Image.Image, output_dir: Path, filename: str) -> Tuple[Path, Path]:
    """Salva a imagem do card nos formatos Full HD 2x e Small."""
    full_dir = output_dir / "full"
    small_dir = output_dir / "small"
    
    full_dir.mkdir(parents=True, exist_ok=True)
    small_dir.mkdir(parents=True, exist_ok=True)
    
    full_path = full_dir / filename
    small_path = small_dir / filename
    
    # 1. Salvar versão Full no tamanho original máximo da lona (756x1056 px) sem compressão
    full_card = card_3x
    full_card.save(full_path, format="PNG", optimize=False)
    
    # 2. Recorte inteligente para Small Card (150 x 169 px)
    # Redimensiona temporariamente para 504x698 para usar a matemática de recorte existente
    temp_card = card_3x.resize((504, 698), Image.Resampling.LANCZOS)
    
    # Parte superior: linhas 0 a 302 do temp_card (overall, foto)
    # Parte inferior: linhas 558 a 698 do temp_card (nome, atributos, badges)
    top_crop = temp_card.crop((0, 0, 504, 302))
    bottom_crop = temp_card.crop((0, 558, 504, 698))
    
    mini_canvas = Image.new("RGBA", (504, 442), (0, 0, 0, 0))
    mini_canvas.paste(top_crop, (0, 0))
    mini_canvas.paste(bottom_crop, (0, 302))
    
    small_card = mini_canvas.resize((150, 169), Image.Resampling.LANCZOS)
    small_card.save(small_path, format="PNG", optimize=True)
    
    return full_path, small_path

def generate_batch(player_list: List[dict], output_dir: Path) -> List[dict]:
    """Gera cards em lote com log de progresso e tolerância a falhas individuais."""
    total = len(player_list)
    logger.info(f"Iniciando processamento em lote de {total} cards...")
    
    results = []
    success_count = 0
    start_time = time.time()
    
    for idx, player in enumerate(player_list, 1):
        name = player.get("name", "Unknown Player")
        pid = player.get("id") or player.get("futbin_id") or f"idx_{idx}"
        
        # Higienizar o nome do arquivo
        name_slug = name.lower()
        name_slug = unicodedata.normalize('NFD', name_slug).encode('ascii', 'ignore').decode('utf-8')
        name_slug = re.sub(r'[^a-z0-9]', '_', name_slug)
        name_slug = re.sub(r'_+', '_', name_slug).strip('_')
        
        filename = f"fc_player_{pid}_{name_slug}.png"
        logger.info(f"[{idx}/{total}] Processando: {name} (ID: {pid})")
        
        card_start = time.time()
        try:
            # 1. Desenhar card
            card_3x = draw_card(player)
            
            # 2. Salvar outputs
            full_path, small_path = save_card(card_3x, output_dir, filename)
            elapsed = (time.time() - card_start) * 1000
            
            logger.info(f"✅ Card gerado para {name} com sucesso em {elapsed:.1f}ms")
            results.append({
                "id": pid,
                "name": name,
                "success": True,
                "filename": filename,
                "full_path": str(full_path.resolve()),
                "small_path": str(small_path.resolve())
            })
            success_count += 1
        except Exception as e:
            elapsed = (time.time() - card_start) * 1000
            logger.error(f"❌ Falha ao processar {name} após {elapsed:.1f}ms: {e}", exc_info=True)
            results.append({
                "id": pid,
                "name": name,
                "success": False,
                "error": str(e)
            })
            
    total_elapsed = time.time() - start_time
    logger.info(f"Processamento em lote finalizado. Sucesso: {success_count}/{total} em {total_elapsed:.2f}s.")
    return results

if __name__ == "__main__":
    # Demonstração simples (Jadon Sancho UEL Road to the Final 96 mockado)
    logger.info("Rodando demonstração do gerador Pillow para Jadon Sancho UEL RTTF...")
    
    mock_player = {
        "id": 190871,
        "futbin_id": 190871,
        "name": "Sancho",
        "full_name": "Jadon Sancho",
        "card_type": "uel_rttf",
        "is_special": True,
        "overall": 96,
        "position": "LM",
        "alt_positions": ["RM", "CAM"],
        "role_plus": True,
        "pac": 95,
        "sho": 92,
        "pas": 96,
        "dri": 98,
        "def": 45,
        "phy": 78,
        "preferred_foot": "R",
        "skill_moves": 5,
        "weak_foot": 4,
        "playstyles": [
            {"name": "technical", "is_plus": True, "icon_url": "https://www.futbin.com/design/img/playstyles/technical.png"},
            {"name": "finesse_shot", "is_plus": False, "icon_url": "https://www.futbin.com/design/img/playstyles/finesse_shot.png"},
            {"name": "quick_step", "is_plus": False, "icon_url": "https://www.futbin.com/design/img/playstyles/quick_step.png"},
            {"name": "trickster", "is_plus": True, "icon_url": "https://www.futbin.com/design/img/playstyles/trickster.png"}
        ],
        "playstyles_plus": ["technical", "trickster"],
        "nation_id": 14,
        "league_id": 13,
        "club_id": 11, # Chelsea ou similar
        "face_path": "images/cards/renders/render_25365_griezmann.png", # Usando foto do Griezmann como placeholder
        "bg_template_path": "images/cards/templates/sbc_global_UEL_RTTF_bg.png",
        "nation_path": "images/cards/nations/nation_18.png", # Usando bandeira de frança como placeholder
        "league_path": "images/cards/leagues/league_53.png",
        "club_path": "images/cards/clubs/club_240.png"
    }
    
    output_directory = IMAGES_DIR / "cards"
    res = generate_batch([mock_player], output_directory)
    print("Resultado da demonstração:", res)
