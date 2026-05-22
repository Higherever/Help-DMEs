"""
Script para download e crop dos cards de SBCs de Atletas
=========================================================
Este script sincroniza as imagens dos 18 SBCs de atletas ativos do banco de dados,
buscando os cards premium oficiais consolidado em HD no FutGG, baixando-os localmente
e realizando o crop inteligente de 150x169px (miniaturas transparentes).

Uso:
    cd "/home/gambeta/Documentos/Socorro DMEs/Socorro DMEs"
    .venv/bin/python backend/scripts/download_sbc_cards.py
"""

import asyncio
import re
import os
import sys
import logging
from pathlib import Path
from typing import Optional

import aiohttp
from sqlalchemy import select

# Adiciona o diretório raiz do projeto ao PYTHONPATH para permitir imports do backend
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Imports do core e serviços do backend
from backend.core.database import get_session, init_db
from backend.models.models import PlayerCard
from backend.services.scraping_utils import sanitize_filename_part
from backend.scripts.scrape_players_v2 import scrape_futgg_card_image, download_image, _create_thumbnail
from backend.services.image_processor import remove_white_background_inplace

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("download_sbc_cards")


def extract_ea_item_id(url: str) -> Optional[str]:
    """
    Extrai o ID único da EA (ea_item_id) a partir da URL de render ou face do Futbin.
    Exemplo:
        https://cdn3.futbin.com/content/fifa26/img/players/p67370719.png?fm=png -> 67370719
    """
    if not url:
        return None
    
    # Procura por padrões do tipo p12345.png ou 12345.png
    match = re.search(r'/players/p?(\d+)\.png', url)
    if match:
        return match.group(1)
    
    # Alternativo para caso a URL venha em formato diferente
    match_alt = re.search(r'/(\d+)\.png', url)
    if match_alt:
        return match_alt.group(1)
        
    return None


async def process_sbc_card(session: aiohttp.ClientSession, pc: PlayerCard, db) -> bool:
    """
    Processa um único card de jogador de SBC: busca no FutGG, faz download HD, crop e atualiza banco.
    """
    logger.info(f"--------------------------------------------------")
    logger.info(f"Processando jogador de SBC: {pc.name} (Overall: {pc.overall})")
    
    # 1. Extrair o ea_item_id
    ea_item_id = extract_ea_item_id(pc.render_url) or extract_ea_item_id(pc.face_url)
    if not ea_item_id:
        logger.warning(f"Não foi possível extrair ea_item_id para {pc.name}. render_url: {pc.render_url}")
        return False
        
    logger.info(f"EA Item ID extraído com sucesso: {ea_item_id}")
    
    # 2. Gerar o slug limpo para o nome do arquivo
    slug = sanitize_filename_part(pc.name)
    futbin_id = pc.futbin_id or ea_item_id
    
    # 3. Buscar a URL consolidada do card em HD no FutGG
    try:
        futgg_data = await scrape_futgg_card_image(
            session=session,
            player_name=pc.name,
            overall=pc.overall,
            futbin_id=futbin_id,
            ea_item_id=ea_item_id
        )
    except Exception as e:
        logger.error(f"Erro ao buscar informações no FutGG para {pc.name}: {e}")
        return False
        
    hd_url = futgg_data.get("futgg_card_image_url")
    if not hd_url:
        logger.warning(f"Card consolidado HD não foi encontrado no FutGG para {pc.name}.")
        return False
        
    logger.info(f"Card consolidado HD encontrado no FutGG: {hd_url}")
    
    # 4. Definir nomes de arquivos e caminhos de salvamento físicos locais
    card_filename = f"sbc_player_{pc.id}_{slug}.png"
    full_path = PROJECT_ROOT / "images" / "cards" / "full" / card_filename
    small_path = PROJECT_ROOT / "images" / "cards" / "small" / card_filename
    
    # Garantir que os diretórios existam
    full_path.parent.mkdir(parents=True, exist_ok=True)
    small_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 5. Fazer download físico do card HD completo para a pasta full
    logger.info(f"Baixando card HD para: {full_path}")
    download_success = await download_image(session, hd_url, full_path)
    if not download_success:
        logger.error(f"Falha ao realizar o download do card HD para {pc.name} da URL {hd_url}")
        return False
        
    logger.info(f"Download concluído com sucesso!")
    
    # Remover fundo branco da imagem baixada
    logger.info(f"Removendo fundo branco da imagem do card completo...")
    try:
        await remove_white_background_inplace(full_path)
    except Exception as e:
        logger.error(f"Erro ao remover fundo branco do card: {e}")
    
    # 6. Gerar a miniatura cropada de 150x169px (Small Card) usando Pillow
    logger.info(f"Gerando miniatura cropada transparente de 150x169px em: {small_path}")
    try:
        _create_thumbnail(str(full_path), str(small_path))
        logger.info(f"Miniatura gerada com sucesso!")
    except Exception as e:
        logger.error(f"Falha ao gerar a miniatura cropada para {pc.name}: {e}")
        return False
        
    # 7. Atualizar as referências locais no banco de dados
    pc.card_image_url = f"/images/cards/full/{card_filename}"
    
    # Atualizar também outras URLs úteis se houver no FutGG
    if futgg_data.get("futgg_render_url"):
        pc.face_url = futgg_data["futgg_render_url"]
        
    # A render_url aponta para a miniatura se desejado ou podemos mantê-la ou atualizá-la
    pc.render_url = f"/images/cards/small/{card_filename}"
    
    logger.info(f"✅ Banco de dados atualizado localmente para {pc.name}!")
    return True


async def run():
    logger.info("Iniciando a sincronização e download dos cards de SBC...")
    await init_db()
    
    # Criar a sessão aiohttp com configurações apropriadas do anti-bot
    from backend.services.anti_bot import create_session
    session = create_session()
    
    async with get_session() as db:
        # Obter todos os PlayerCards que representam atletas de verdade (com overall > 0)
        result = await db.execute(
            select(PlayerCard).where(PlayerCard.overall > 0)
        )
        player_cards = result.scalars().all()
        
        logger.info(f"Foram encontrados {len(player_cards)} atletas de SBC na base de dados.")
        
        success_count = 0
        for pc in player_cards:
            try:
                success = await process_sbc_card(session, pc, db)
                if success:
                    success_count += 1
                # Delay sutil entre jogadores para simular comportamento humano no scraping do FutGG
                await asyncio.sleep(2.0)
            except Exception as e:
                logger.error(f"Erro inesperado no processamento de {pc.name}: {e}")
                
        # Commit para persistir todas as atualizações no banco SQLite
        await db.commit()
        logger.info(f"==================================================")
        logger.info(f"Sincronização concluída! {success_count} de {len(player_cards)} cards processados com sucesso.")
        
    await session.close()


if __name__ == "__main__":
    asyncio.run(run())
