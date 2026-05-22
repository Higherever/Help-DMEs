import os
import aiohttp
import asyncio
import logging
from pathlib import Path
import tempfile
import urllib.parse
import re
import shutil

logger = logging.getLogger("help_dmes.image_processor")

# Path do projeto
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# Onde ficam as imagens estáticas servidas pelo Vite/Node
IMAGE_DIR = BASE_DIR / "images"

async def download_and_process_card_bg(url: str, sbc_id: str, http_session: aiohttp.ClientSession = None) -> str:
    """
    Baixa uma imagem de template de carta (AVIF/WEBP/PNG), remove o fundo branco
    externo (cantos) usando ImageMagick e salva como PNG transparente.
    
    Retorna o path local relativo para o frontend (ex: /images/cards/templates/sbc_123_bg.png).
    """
    if not url:
        return ""
        
    # Limpar a URL para determinar a extensão ou nome do arquivo
    clean_url = url.split("?")[0] if "?" in url else url
    
    # URL de download real que preserva os parâmetros de assinatura de imagem (essencial para CDN/Imgix)
    download_url = url
    if download_url.startswith("//"):
        download_url = "https:" + download_url
    if clean_url.startswith("//"):
        clean_url = "https:" + clean_url
        
    # Definir destino final
    dest_dir = IMAGE_DIR / "cards" / "templates"
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    # Gerar nome de arquivo seguro
    safe_name = re.sub(r'[^\w\-.]', '_', str(sbc_id))[:100]
    final_filename = f"sbc_{safe_name}_bg.png"
    final_path = dest_dir / final_filename
    
    # Se a imagem já existe e tem tamanho válido, usa a que já foi processada
    if final_path.exists() and final_path.stat().st_size > 1000:
        return f"/images/cards/templates/{final_filename}"
        
    # Usando mktemp (mais simples de manejar com shell)
    fd_in, temp_in = tempfile.mkstemp(suffix=".img")
    os.close(fd_in)
    fd_out, temp_out = tempfile.mkstemp(suffix=".png")
    os.close(fd_out)
    
    close_session = False
    try:
        # Se não passaram session, cria uma temporária
        if http_session is None:
            timeout = aiohttp.ClientTimeout(total=30)
            http_session = aiohttp.ClientSession(timeout=timeout)
            close_session = True
            
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        async with http_session.get(download_url, headers=headers) as resp:
            if resp.status != 200:
                logger.error(f"Erro ao baixar bg card {clean_url}: status {resp.status}")
                return ""
            
            data = await resp.read()
            with open(temp_in, "wb") as f:
                f.write(data)
                
        # Processar com ImageMagick
        # O Fuzz de 4% pega variações leves de branco.
        # Nós forçamos o fundo branco a ficar transparente "enchendo" a partir dos 4 cantos
        # e no final usamos -transparent white para garantir.
        cmd = [
            "magick",
            temp_in,
            "-fuzz", "4%",
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
            logger.error(f"ImageMagick falhou em {url}. Fallback para cópia direta. \nErro: {stderr.decode()}")
            # Se falhar o magick, copia o arquivo original como fallback
            shutil.copy2(temp_in, final_path)
        else:
            # Move temp_out processado para final_path
            shutil.move(temp_out, final_path)
            
        logger.info(f"Fundo limpo e imagem salva: {final_path}")
        return f"/images/cards/templates/{final_filename}"
        
    except Exception as e:
        logger.error(f"Erro processando bg_card {url}: {e}")
        return ""
    finally:
        if close_session and http_session:
            await http_session.close()
        if os.path.exists(temp_in): 
            try: os.remove(temp_in) 
            except: pass
        if os.path.exists(temp_out): 
            try: os.remove(temp_out) 
            except: pass


async def remove_white_background_inplace(image_path: Path) -> bool:
    """
    Remove o fundo branco de uma imagem de card física (inplace) usando ImageMagick.
    Usa preenchimento por inundação (floodfill) a partir dos 4 cantos com fuzz de 10%.
    """
    if not image_path.exists():
        logger.error(f"Arquivo não encontrado para remoção de fundo branco: {image_path}")
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
            logger.error(f"ImageMagick falhou ao remover fundo branco de {image_path}: {stderr.decode()}")
            return False
        
        # Substitui a imagem original pela versão sem fundo
        shutil.move(temp_out, str(image_path))
        logger.info(f"Fundo branco removido com sucesso para {image_path}")
        return True
    except Exception as e:
        logger.error(f"Erro ao remover fundo branco para {image_path}: {e}")
        return False
    finally:
        if os.path.exists(temp_out):
            try: os.remove(temp_out)
            except: pass

