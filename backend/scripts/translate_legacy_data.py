"""
Help DMEs — Script de Tradução dos Dados Legados
================================================
Varre as tabelas do banco de dados SQLite e traduz todos os SBC Sets, 
Challenges, Requirements e Rewards legados para Português do Brasil (PT-BR).
"""

import sys
import os
import asyncio
import logging
from sqlalchemy import select

# Adiciona o diretório do projeto ao path para importar módulos do backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.core.database import async_session_factory, engine
from backend.models.models import SBCSet, SBCChallenge, ChallengeRequirement, SBCReward
from backend.services.translation_service import translator

# Configurar logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("help_dmes.translate_legacy")

async def translate_legacy_data():
    logger.info("🚀 Iniciando a tradução dos dados legados no banco de dados...")
    
    async with async_session_factory() as session:
        # ── 1. Traduzir SBC Sets ──
        logger.info("⏳ Carregando SBC Sets...")
        result = await session.execute(select(SBCSet))
        sbc_sets = result.scalars().all()
        logger.info(f"Encontrados {len(sbc_sets)} SBC Sets para verificar.")
        
        translated_sets = 0
        for sbc in sbc_sets:
            original_name = sbc.name
            original_desc = sbc.description or ""
            original_exp = sbc.expires_text or ""
            
            sbc.name = translator.translate(sbc.name)
            if sbc.description:
                sbc.description = translator.translate(sbc.description)
            if sbc.expires_text:
                sbc.expires_text = translator.translate(sbc.expires_text)
                
            if original_name != sbc.name or original_desc != sbc.description or original_exp != sbc.expires_text:
                translated_sets += 1
                logger.info(f"  [SBC Set] '{original_name}' ➔ '{sbc.name}'")
                
        # ── 2. Traduzir SBC Challenges ──
        logger.info("⏳ Carregando SBC Challenges...")
        result = await session.execute(select(SBCChallenge))
        challenges = result.scalars().all()
        logger.info(f"Encontrados {len(challenges)} Challenges para verificar.")
        
        translated_challenges = 0
        for ch in challenges:
            original_name = ch.name
            original_desc = ch.description or ""
            
            ch.name = translator.translate(ch.name)
            if ch.description:
                ch.description = translator.translate(ch.description)
                
            if original_name != ch.name or original_desc != ch.description:
                translated_challenges += 1
                logger.info(f"  [Challenge] '{original_name}' ➔ '{ch.name}'")
                
        # ── 3. Traduzir Requisitos ──
        logger.info("⏳ Carregando Requisitos de Desafios...")
        result = await session.execute(select(ChallengeRequirement))
        requirements = result.scalars().all()
        logger.info(f"Encontrados {len(requirements)} Requisitos para verificar.")
        
        translated_reqs = 0
        for req in requirements:
            if req.detail:
                original_detail = req.detail
                req.detail = translator.translate(req.detail)
                
                if original_detail != req.detail:
                    translated_reqs += 1
                    logger.info(f"  [Requisito] '{original_detail}' ➔ '{req.detail}'")
                    
        # ── 4. Traduzir Recompensas ──
        logger.info("⏳ Carregando Recompensas (Rewards)...")
        result = await session.execute(select(SBCReward))
        rewards = result.scalars().all()
        logger.info(f"Encontrados {len(rewards)} Recompensas para verificar.")
        
        translated_rewards = 0
        for rw in rewards:
            original_name = rw.name
            rw.name = translator.translate(rw.name)
            
            if original_name != rw.name:
                translated_rewards += 1
                logger.info(f"  [Recompensa] '{original_name}' ➔ '{rw.name}'")
                
        # ── Salvar alterações no banco ──
        if translated_sets > 0 or translated_challenges > 0 or translated_reqs > 0 or translated_rewards > 0:
            logger.info("💾 Salvando as alterações no banco de dados SQLite...")
            await session.commit()
            logger.info("✅ Alterações salvas com sucesso!")
        else:
            logger.info("ℹ️ Nenhum dado precisou de tradução (todos os dados já estavam em português).")
            
        logger.info("=" * 60)
        logger.info("📊 RESUMO DE TRADUÇÃO DOS DADOS LEGADOS:")
        logger.info(f"  - SBC Sets traduzidos: {translated_sets}")
        logger.info(f"  - Challenges traduzidos: {translated_challenges}")
        logger.info(f"  - Requisitos traduzidos: {translated_reqs}")
        logger.info(f"  - Recompensas traduzidas: {translated_rewards}")
        logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(translate_legacy_data())
