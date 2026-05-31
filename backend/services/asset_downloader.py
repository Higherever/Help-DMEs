import os
import re
import sys
import logging
import unicodedata
import aiohttp
import aiofiles
from pathlib import Path
from typing import Dict, Optional

# Garantir paths do projeto
SERVICE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SERVICE_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
IMAGES_DIR = PROJECT_ROOT / "images"

logger = logging.getLogger("asset_downloader")

# Importar fetch_binary do motor anti-bot do projeto
try:
    from backend.services.anti_bot import fetch_binary
except ImportError:
    # Fallback caso executado fora do escopo padrão da API
    async def fetch_binary(session, url):
        async with session.get(url, timeout=15) as r:
            if r.status == 200:
                return await r.read()
        return None

def sanitize_slug(text: str) -> str:
    """Converte qualquer string (nomes, nações, clubes, ligas) em slug amigável para nome de arquivo."""
    if not text:
        return "unknown"
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ASCII", "ignore").decode("ASCII")
    clean = re.sub(r"[^a-zA-Z0-9\s_-]", "", ascii_text)
    clean = re.sub(r"[\s_-]+", "_", clean)
    return clean.strip("_").lower()[:50]

class AssetDownloader:
    """Serviço modular e robusto para download, cache e higienização semântica de assets de cards."""
    
    @staticmethod
    async def download_image(
        session: aiohttp.ClientSession,
        url: str,
        dest_path: Path,
        sem: Optional[asyncio.Semaphore] = None
    ) -> bool:
        """Baixa uma imagem usando aiohttp respeitando semáforos e regras anti-bot."""
        if not url:
            return False
            
        if dest_path.exists() and dest_path.stat().st_size > 200:
            return True
            
        clean_url = url
        if "futbin.com" not in url:
            clean_url = url.split("?")[0] if "?" in url else url
            
        if clean_url.startswith("//"):
            clean_url = "https:" + clean_url
            
        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            if sem:
                async with sem:
                    data = await fetch_binary(session, clean_url)
            else:
                data = await fetch_binary(session, clean_url)
                
            if data and len(data) > 200:
                async with aiofiles.open(dest_path, "wb") as f:
                    await f.write(data)
                logger.debug(f"[AssetDownloader] Imagem baixada em cache: {dest_path.name}")
                return True
        except Exception as e:
            logger.warning(f"[AssetDownloader] Falha ao baixar imagem de {clean_url}: {e}")
            
        return False

    @staticmethod
    def download_image_sync(url: str, dest_path: Path) -> bool:
        """Baixa uma imagem de forma síncrona via urllib (utilitário para scripts CLI síncronos)."""
        if not url:
            return False
            
        if dest_path.exists() and dest_path.stat().st_size > 200:
            return True
            
        clean_url = url
        if "futbin.com" not in url:
            clean_url = url.split("?")[0] if "?" in url else url
            
        if clean_url.startswith("//"):
            clean_url = "https:" + clean_url
            
        try:
            import urllib.request
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            req = urllib.request.Request(
                clean_url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                data = response.read()
                
            if data and len(data) > 200:
                with open(dest_path, "wb") as f:
                    f.write(data)
                logger.debug(f"[AssetDownloader] [Sync] Imagem baixada em cache: {dest_path.name}")
                return True
        except Exception as e:
            logger.warning(f"[AssetDownloader] [Sync] Falha ao baixar síncrono de {clean_url}: {e}")
            
        return False

    @classmethod
    async def enrich_and_download_player_assets(
        cls,
        session: aiohttp.ClientSession,
        player_data: Dict,
        futbin_id: str,
        sem: Optional[asyncio.Semaphore] = None
    ) -> Dict[str, str]:
        """
        Higieniza semanticamente e baixa todos os assets associados a um jogador.
        Retorna dicionário contendo caminhos de imagens locais uniformizados para o banco.
        """
        res_paths = {}
        name_slug = sanitize_slug(player_data.get("name", "unknown"))
        
        # 1. Foto / Render do Jogador
        render_url = (
            player_data.get("futgg_render_url") or
            player_data.get("render_url") or
            player_data.get("face_url_raw") or
            player_data.get("face_url")
        )
        if render_url:
            filename = f"render_{futbin_id}_{name_slug}.png"
            dest = IMAGES_DIR / "cards" / "renders" / filename
            success = await cls.download_image(session, render_url, dest, sem)
            if success:
                res_paths["render_url"] = f"/images/cards/renders/{filename}"
                res_paths["face_url"] = f"/images/cards/renders/{filename}"
                
        # 1.5 Portrait Base do Jogador (se existir)
        portrait_url = player_data.get("portrait_url")
        if portrait_url and portrait_url.startswith("http"):
            filename = f"portrait_{futbin_id}_{name_slug}.png"
            dest = IMAGES_DIR / "cards" / "portraits" / filename
            success = await cls.download_image(session, portrait_url, dest, sem)
            if success:
                res_paths["portrait_url"] = f"/images/cards/portraits/{filename}"
                
        # 2. Bandeira de Nação (Slug Semântico)
        nation_url = player_data.get("nation_flag_url") or player_data.get("nation_url")
        nation_name = player_data.get("nation") or player_data.get("country")
        if nation_url and nation_name:
            nation_slug = sanitize_slug(nation_name)
            filename = f"nation_{nation_slug}.png"
            dest = IMAGES_DIR / "cards" / "nations" / filename
            success = await cls.download_image(session, nation_url, dest, sem)
            if success:
                res_paths["nation_flag_url"] = f"/images/cards/nations/{filename}"
                
        # 3. Escudo do Clube (Slug Semântico)
        club_url = player_data.get("club_logo_url") or player_data.get("club_url")
        club_name = player_data.get("club") or player_data.get("club_name")
        if club_url and club_name:
            club_slug = sanitize_slug(club_name)
            filename = f"club_{club_slug}.png"
            dest = IMAGES_DIR / "cards" / "clubs" / filename
            success = await cls.download_image(session, club_url, dest, sem)
            if success:
                res_paths["club_logo_url"] = f"/images/cards/clubs/{filename}"
                
        # 4. Logo da Liga (Slug Semântico)
        league_url = player_data.get("league_logo_url") or player_data.get("league_url")
        league_name = player_data.get("league") or player_data.get("league_name")
        if league_url and league_name:
            league_slug = sanitize_slug(league_name)
            filename = f"league_{league_slug}.png"
            dest = IMAGES_DIR / "cards" / "leagues" / filename
            success = await cls.download_image(session, league_url, dest, sem)
            if success:
                res_paths["league_logo_url"] = f"/images/cards/leagues/{filename}"
                
        # 5. Card Completo Template
        card_url = (
            player_data.get("futgg_card_image_url") or
            player_data.get("bg_url_hd") or
            player_data.get("bg_url_raw")
        )
        if card_url:
            filename = f"fc_player_{futbin_id}_{name_slug}.png"
            dest = IMAGES_DIR / "cards" / "full" / filename
            success = await cls.download_image(session, card_url, dest, sem)
            if success:
                res_paths["card_template_url"] = f"/images/cards/full/{filename}"
                
                # Gerar miniatura
                try:
                    from backend.scripts.scrape_players_v2 import _create_thumbnail
                    _create_thumbnail(str(dest), str(IMAGES_DIR / "cards" / "small" / filename))
                    res_paths["card_small_url"] = f"/images/cards/small/{filename}"
                except Exception:
                    pass
                    
        return res_paths
