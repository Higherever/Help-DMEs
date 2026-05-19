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

