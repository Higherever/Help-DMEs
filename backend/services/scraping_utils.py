import re
import asyncio
import random
from typing import Dict, Optional, Any

def parse_requirement_text(text: str) -> Dict:
    """
    Converte texto de requisito de DME em um dicionário estruturado.
    """
    if not text:
        return {"requirement_type": "unknown", "operator": "min", "value": "0", "detail": None}

    patterns = [
        (r"(?:Min\.?|Minimum)\s*Team\s*(?:Overall\s*)?Rating[:\s]*(\d+)", "team_rating"),
        (r"(?:Min\.?|Minimum)\s*(?:Squad\s*)?Chemistry[:\s]*(\d+)", "squad_chemistry"),
        (r"(?:Min\.?|Minimum)\s*(\d+)\s*Players?\s*(?:from|de)[:\s]*(.*)", "players_from"),
        (r"(?:Exactly|Exact)\s*(\d+)\s*Players?\s*(?:from|de)[:\s]*(.*)", "players_from"),
        (r"Max\.?\s*(\d+)\s*Players?\s*same\s*(Nation|League|Club)", "same_attribute"),
        (r"(?:Min\.?|Minimum)\s*(\d+)\s*Players?\s*same\s*(Nation|League|Club)", "same_attribute"),
        (r"(?:Min\.?|Minimum)\s*(\d+)\s*Players?[:\s]*(Rare|Common|Gold|Silver|Bronze)", "player_quality"),
        (r"(?:Min\.?|Minimum)\s*(\d+)\s*Players?[:\s]*(Any\s+.*)", "player_type"),
    ]

    for pattern, req_type in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            operator = "max" if "Max" in text else ("exact" if "Exact" in text or "Exactly" in text else "min")
            
            # Captura valor e detalhe baseado no número de grupos do regex
            groups = match.groups()
            if len(groups) == 1:
                return {
                    "requirement_type": req_type,
                    "operator": operator,
                    "value": groups[0],
                    "detail": None
                }
            elif len(groups) == 2:
                # Para patterns onde o primeiro grupo é o número e o segundo é o detalhe
                # exceto same_attribute onde a ordem pode variar ou ser específica
                if req_type == "same_attribute":
                    return {
                        "requirement_type": req_type,
                        "operator": operator,
                        "value": groups[0],
                        "detail": groups[1]
                    }
                else:
                    return {
                        "requirement_type": req_type,
                        "operator": operator,
                        "value": groups[0],
                        "detail": groups[1].strip()
                    }

    return {"requirement_type": "unknown", "operator": "min", "value": "0", "detail": text}

def parse_cost_text(text: str) -> Optional[int]:
    """
    Limpa strings de preço e converte para inteiro.
    Ex: "10,000" -> 10000
    """
    if not text:
        return None
    cleaned = re.sub(r"[,.\s]", "", text.strip())
    return int(cleaned) if cleaned.isdigit() else None

def parse_expiry_text(text: str) -> Optional[str]:
    """
    Normaliza textos de expiração (ex: "7 days", "23 hours").
    """
    if not text:
        return None
    # No momento apenas retorna o texto limpo, pode ser expandido para objetos datetime se necessário
    return text.strip().lower()

def normalize_category(raw: str) -> str:
    """
    Mapeia categorias brutas para slugs padronizados.
    """
    mapping = {
        "Players": "players",
        "Upgrades": "upgrades",
        "Challenges": "challenges",
        "Icons": "icons",
        "Foundations": "foundations",
        "Swaps": "swaps"
    }
    return mapping.get(raw, raw.lower())



# Nota: create_stealth_context removida na v0.4.0 — Playwright substituído por aiohttp.

import unicodedata
from pathlib import Path
from PIL import Image

def sanitize_filename_part(text: str) -> str:
    """
    Remove acentos, caracteres especiais e espaços, convertendo a string
    para um formato limpo e seguro para nomes de arquivos (snake_case minúsculo).
    """
    if not text:
        return "unknown"
    # Normaliza a string para decompor caracteres acentuados
    normalized = unicodedata.normalize('NFKD', text)
    # Remove acentos mantendo apenas caracteres ASCII
    ascii_text = normalized.encode('ASCII', 'ignore').decode('ASCII')
    # Remove caracteres especiais que não sejam letras, números, espaços, hífens ou underlines
    clean_text = re.sub(r'[^a-zA-Z0-9\s_-]', '', ascii_text)
    # Converte espaços e hífens em underlines
    clean_text = re.sub(r'[\s_-]+', '_', clean_text)
    # Remove underlines extras do início e do fim e coloca em minúsculo
    return clean_text.strip('_').lower()

def create_thumbnail(input_path: str, output_path: str, width: int = 150) -> bool:
    """
    Cria uma miniatura compacta da imagem do card completo (HD), recortando
    o topo (rosto, rating, etc.) e a base (bandeiras e contorno inferior)
    e unindo-as, ocultando o nome e as estatísticas.
    Redimensiona o resultado para ter a largura especificada (default 150px).
    Caso a imagem original não pareça ser um card completo (proporção incorreta),
    aplica apenas o redimensionamento proporcional básico como fallback.
    """
    try:
        dest_path = Path(output_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        with Image.open(input_path) as img:
            w, h = img.size
            
            # Um card completo padrão tem proporção altura/largura de ~1.4.
            # Se a imagem tiver proporção compatível, aplicamos o crop composto.
            if h > w and h > 250:
                y_top = int(h * 0.605)
                y_bottom = int(h * 0.80)
                
                top_part = img.crop((0, 0, w, y_top))
                bottom_part = img.crop((0, y_bottom, w, h))
                
                # Composição
                comp_h = top_part.size[1] + bottom_part.size[1]
                comp_img = Image.new("RGBA", (w, comp_h))
                comp_img.paste(top_part, (0, 0))
                comp_img.paste(bottom_part, (0, top_part.size[1]))
                
                # Redimensiona mantendo a proporção da imagem composta
                w_percent = (width / float(w))
                h_size = int((float(comp_img.size[1]) * float(w_percent)))
                resized_img = comp_img.resize((width, h_size), Image.Resampling.LANCZOS)
            else:
                # Fallback: redimensionamento proporcional simples
                w_percent = (width / float(w))
                h_size = int((float(h) * float(w_percent)))
                resized_img = img.resize((width, h_size), Image.Resampling.LANCZOS)
                
            resized_img.save(dest_path, "PNG")
            
        return True
    except Exception as e:
        # Logger alternativo para evitar dependências circulares
        import logging
        logging.getLogger("help_dmes.scraping_utils").error(
            f"Falha ao gerar miniatura de {input_path} para {output_path}: {e}"
        )
        return False


