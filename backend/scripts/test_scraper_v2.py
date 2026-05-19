import asyncio
import sys
import os
from pathlib import Path

# Adicionar o diretório raiz ao PYTHONPATH
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from playwright.async_api import async_playwright
from backend.services.scraping_utils import create_stealth_context
from backend.services.fut_gg_service import _extract_sbc_details

async def test_scraper(url: str):
    print(f"🚀 Testando scraper na URL: {url}")
    
    async with async_playwright() as p:
        browser, context, page = await create_stealth_context(p)
        
        try:
            print("⏳ Acessando página...")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)  # Esperar renderização extra para JS-heavy pages
            
            print("🔍 Extraindo detalhes...")
            details = await _extract_sbc_details(page)
            
            print("\n" + "="*50)
            print("DADOS EXTRAÍDOS:")
            print("="*50)
            print(f"Nome (URL): {url.split('/')[-2]}")
            print(f"Descrição: {details.get('description')}")
            print(f"Custo Total: {details.get('total_cost')}")
            print(f"URL Imagem: {details.get('image_url')}")
            print(f"Expira em: {details.get('expires_text')}")
            print(f"Repetível: {details.get('repeatable_text')}")
            print(f"Atualiza em: {details.get('refresh_text')}")
            print(f"Total Desafios: {details.get('challenges_count')}")
            
            print("\nDesafios:")
            for i, ch in enumerate(details.get('challenges', []), 1):
                print(f"  {i}. {ch.get('name')}")
                print(f"     Requisitos: {len(ch.get('requirements', []))} encontrados")
            print("="*50)
            
        except Exception as e:
            print(f"❌ Erro durante o teste: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    test_url = "https://www.fut.gg/sbc/players/26-880-lennart-karl/"
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    
    asyncio.run(test_scraper(test_url))
