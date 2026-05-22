"""
Help DMEs — Script de Auto-Healing de Traduções
================================================
Aplica as novas regras polidas de pós-processamento do translation_service
ao cache persistente (translation_cache.json) e corrige qualquer registro
no banco de dados SQLite legados para garantir 100% de qualidade técnica.
"""

import sys
import os
import json
import re
import asyncio
from sqlalchemy import select

# Adiciona o diretório do projeto ao path para importar módulos do backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.core.database import async_session_factory
from backend.models.models import SBCSet, SBCChallenge, ChallengeRequirement, SBCReward
from backend.services.translation_service import translator, CACHE_FILE

async def heal_translations():
    print("🩹 Iniciando o Auto-Healing de traduções no cache e no banco de dados...")

    # 1. Corrigir o cache JSON
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
            
            corrected_cache = {}
            corrected_count = 0
            for en_key, pt_val in cache.items():
                # Passa pelo pós-processador do translator
                new_val = translator._post_process_translation(pt_val)
                
                # Se o valor mudou com as correções refinadas
                if new_val != pt_val:
                    corrected_count += 1
                    print(f"  [Cache] '{pt_val}' ➔ '{new_val}'")
                corrected_cache[en_key] = new_val
            
            # Gravar cache atualizado
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(corrected_cache, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Cache de tradução atualizado: {corrected_count} chaves corrigidas.")
            # Atualizar o cache em memória do translator global
            translator.cache = corrected_cache
        except Exception as e:
            print(f"❌ Erro ao ler/gravar cache: {e}")
            return

    # 2. Corrigir os registros no banco de dados
    async with async_session_factory() as session:
        # --- SBC Sets ---
        result = await session.execute(select(SBCSet))
        sbc_sets = result.scalars().all()
        updated_sets = 0
        for sbc in sbc_sets:
            old_name = sbc.name
            old_desc = sbc.description or ""
            old_exp = sbc.expires_text or ""
            
            if sbc.name:
                sbc.name = translator._post_process_translation(sbc.name)
            if sbc.description:
                sbc.description = translator._post_process_translation(sbc.description)
            if sbc.expires_text:
                sbc.expires_text = translator._post_process_translation(sbc.expires_text)
                
            if old_name != sbc.name or old_desc != sbc.description or old_exp != sbc.expires_text:
                updated_sets += 1
                print(f"  [SBC Set] '{old_name}' ➔ '{sbc.name}'")
                
        # --- Challenges ---
        result = await session.execute(select(SBCChallenge))
        challenges = result.scalars().all()
        updated_challenges = 0
        for ch in challenges:
            old_name = ch.name
            old_desc = ch.description or ""
            
            if ch.name:
                ch.name = translator._post_process_translation(ch.name)
            if ch.description:
                ch.description = translator._post_process_translation(ch.description)
                
            if old_name != ch.name or old_desc != ch.description:
                updated_challenges += 1
                print(f"  [Challenge] '{old_name}' ➔ '{ch.name}'")
                
        # --- Requirements ---
        result = await session.execute(select(ChallengeRequirement))
        requirements = result.scalars().all()
        updated_reqs = 0
        for req in requirements:
            if req.detail:
                old_detail = req.detail
                req.detail = translator._post_process_translation(req.detail)
                if old_detail != req.detail:
                    updated_reqs += 1
                    print(f"  [Requisito] '{old_detail}' ➔ '{req.detail}'")
                    
        # --- Rewards ---
        result = await session.execute(select(SBCReward))
        rewards = result.scalars().all()
        updated_rewards = 0
        for rw in rewards:
            if rw.name:
                old_name = rw.name
                rw.name = translator._post_process_translation(rw.name)
                if old_name != rw.name:
                    updated_rewards += 1
                    print(f"  [Recompensa] '{old_name}' ➔ '{rw.name}'")
                    
        if updated_sets > 0 or updated_challenges > 0 or updated_reqs > 0 or updated_rewards > 0:
            print("💾 Gravando correções no banco de dados SQLite...")
            await session.commit()
            print("✅ Banco de dados corrigido e atualizado com sucesso!")
        else:
            print("ℹ️ Nenhum dado precisou de correção no banco de dados.")

        print("=" * 60)
        print("📊 RESUMO DO HEALING DE TRADUÇÃO:")
        print(f"  - SBC Sets corrigidos: {updated_sets}")
        print(f"  - Challenges corrigidos: {updated_challenges}")
        print(f"  - Requisitos corrigidos: {updated_reqs}")
        print(f"  - Recompensas corrigidas: {updated_rewards}")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(heal_translations())
