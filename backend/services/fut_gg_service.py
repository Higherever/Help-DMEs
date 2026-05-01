"""
Help DMEs — Fut.gg Scraping Service
======================================
Serviço de coleta de SBCs do site fut.gg/sbc/.
Usa Playwright com stealth para contornar proteções anti-bot.

Fluxo de coleta:
  1. Acessa fut.gg/sbc/ → coleta lista de SBC sets (nome, custo, categoria, etc.)
  2. Para cada SBC set → acessa página de detalhes → coleta challenges, requisitos, rewards
  3. Persiste tudo no banco via SQLAlchemy async

Fallback: se Fut.gg falhar, o main.py chama futnext_service.py
"""

import asyncio
import logging
from datetime import datetime, UTC
from typing import Optional
import re
import random

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.models import (
    SBCSet, SBCChallenge, ChallengeRequirement,
    SBCReward, PlayerCard, ScrapeLog,
)
from backend.services.scraping_utils import parse_requirement_text, create_stealth_context, parse_cost_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.models import (
    SBCSet, SBCChallenge, ChallengeRequirement,
    SBCReward, PlayerCard, ScrapeLog,
)

logger = logging.getLogger("help_dmes." + __name__.split(".")[-1])


# ──────────────────────────────────────────────
# Estado global do scraper
# ──────────────────────────────────────────────

_scrape_status = {
    "status": "idle",       # idle / running / failed
    "message": "",          # Progresso
    "last_scrape_at": None,
    "sbcs_count": 0,
    "error": None,
}


def get_scrape_status() -> dict:
    """Retorna o status atual do scraper (sem acessar banco)."""
    return _scrape_status.copy()


# ──────────────────────────────────────────────
# Scraper principal
# ──────────────────────────────────────────────

async def scrape_all_sbcs(session: AsyncSession) -> dict:
    """
    Coleta TODOS os SBCs do fut.gg/sbc/.
    Atualiza o status global durante a execução.

    Retorna: {"status": str, "sbcs_scraped": int, "error": str | None}
    """
    global _scrape_status
    _scrape_status["status"] = "running"
    _scrape_status["message"] = "Iniciando scrape..."
    _scrape_status["error"] = None

    log = ScrapeLog(
        source="fut.gg",
        status="running",
        sbcs_scraped=0,
        started_at=datetime.now(UTC),
    )
    session.add(log)
    await session.flush()

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser, context, page = await create_stealth_context(p)

            # ── Passo 1: Coletar lista de SBCs ──
            _scrape_status["message"] = "Acessando página de SBCs..."
            await page.goto("https://www.fut.gg/sbc/", wait_until="load", timeout=30000)
            await page.wait_for_timeout(2000)

            sbc_data = await _extract_sbc_list(page)

            if not sbc_data:
                raise Exception("Nenhum SBC encontrado na página fut.gg/sbc/")

            # ── Passo 2: Para cada SBC, coletar detalhes ──
            scraped_count = 0
            total_sbcs = len(sbc_data)
            for sbc_info in sbc_data:
                _scrape_status["message"] = f"Processando SBC {scraped_count + 1}/{total_sbcs}: {sbc_info.get('name', 'Unknown')}"
                try:
                    await _process_sbc(session, page, sbc_info)
                    scraped_count += 1
                except Exception:
                    continue  # Pular SBCs com erro e continuar

            await browser.close()

        # Sucesso
        log.status = "success"
        log.sbcs_scraped = scraped_count
        log.finished_at = datetime.now(UTC)
        _scrape_status["status"] = "idle"
        _scrape_status["message"] = "Concluído"
        _scrape_status["last_scrape_at"] = datetime.now(UTC)
        _scrape_status["sbcs_count"] = scraped_count

        await session.flush()
        return {"status": "success", "sbcs_scraped": scraped_count, "error": None}

    except Exception as e:
        error_msg = str(e)
        print(f"CRITICAL SCRAPE ERROR (fut.gg): {error_msg}")
        log.status = "failed"
        log.error_message = error_msg
        log.finished_at = datetime.now(UTC)
        _scrape_status["status"] = "failed"
        _scrape_status["message"] = "Erro: " + error_msg
        _scrape_status["error"] = error_msg

        await session.flush()
        return {"status": "failed", "sbcs_scraped": 0, "error": error_msg}


async def _extract_sbc_list(page) -> list[dict]:
    """
    Extrai a lista de SBCs da página principal fut.gg/sbc/.
    Retorna lista de dicts com dados básicos de cada SBC.
    """
    sbcs = []

    # Tentar extrair dados via JavaScript (mais confiável que seletores CSS)
    data = await page.evaluate("""
        () => {
            const results = [];
            // Buscar links de SBCs na página
            const links = document.querySelectorAll('a[href*="/sbc/"]');
            const seen = new Set();

            for (const link of links) {
                const href = link.getAttribute('href');
                if (!href || seen.has(href) || href === '/sbc/' || href === '/sbc') continue;
                seen.add(href);

                // Extrair ID do futgg da URL
                const match = href.match(/\\/sbc\\/([\\w-]+)/);
                if (!match) continue;

                const futggId = match[1];

                // Tentar extrair texto
                const text = link.textContent?.trim() || '';
                const name = text.split('\\n')[0]?.trim() || futggId;

                results.push({
                    futgg_id: futggId,
                    name: name,
                    url: href.startsWith('http') ? href : 'https://www.fut.gg' + href,
                });
            }
            return results;
        }
    """)

    return data or []


async def _process_sbc(session: AsyncSession, page, sbc_info: dict):
    """
    Processa um SBC individual: acessa a página de detalhes e
    extrai challenges, requisitos e rewards.
    """
    futgg_id = sbc_info["futgg_id"]
    url = sbc_info["url"]

    # Verificar se já existe no banco
    existing = await session.execute(
        select(SBCSet).where(SBCSet.futgg_id == futgg_id)
    )
    sbc_set = existing.scalar_one_or_none()

    if sbc_set:
        # Atualizar timestamp
        sbc_set.scraped_at = datetime.now(UTC)
    else:
        # Criar novo
        sbc_set = SBCSet(
            futgg_id=futgg_id,
            name=sbc_info.get("name", futgg_id),
            category="players",  # Padrão, será refinado na página de detalhes
            source="fut.gg",
            scraped_at=datetime.now(UTC),
        )
        session.add(sbc_set)

    await session.flush()

    # Acessar página de detalhes
    try:
        # Loop de 3 tentativas com backoff
        for attempt in range(3):
            try:
                await page.goto(url, wait_until="load", timeout=20000)
                await asyncio.sleep(random.uniform(1.5, 3.0)) # rate limiting
                await page.wait_for_timeout(1500)
                break
            except Exception as e:
                if attempt == 2:
                    raise e
                await asyncio.sleep(2 ** attempt)

        # Extrair detalhes da página
        details = await _extract_sbc_details(page)

        if details:
            sbc_set.description = details.get("description")
            sbc_set.total_cost = details.get("total_cost")
            sbc_set.challenges_count = details.get("challenges_count", 0)
            sbc_set.image_url = details.get("image_url")
            if details.get("category"):
                sbc_set.category = details["category"]

            # Processar challenges
            for idx, ch_data in enumerate(details.get("challenges", [])):
                challenge = SBCChallenge(
                    sbc_set_id=sbc_set.id,
                    name=ch_data.get("name", f"Desafio {idx + 1}"),
                    estimated_cost=ch_data.get("cost"),
                    formation=ch_data.get("formation"),
                    order_index=idx,
                )
                session.add(challenge)
                await session.flush()

                # Processar requisitos do challenge
                for req_data in ch_data.get("requirements", []):
                    req = ChallengeRequirement(
                        challenge_id=challenge.id,
                        requirement_type=req_data.get("requirement_type", "unknown"),
                        operator=req_data.get("operator", "min"),
                        value=str(req_data.get("value", "")),
                        detail=req_data.get("detail"),
                    )
                    session.add(req)

        await session.flush()

    except Exception:
        pass  # Falha silenciosa em detalhes — manter dados básicos


async def _extract_sbc_details(page) -> dict:
    """
    Extrai detalhes de um SBC da sua página individual.
    Retorna dict com description, total_cost, challenges, etc.
    """
    try:
        details = await page.evaluate("""
            () => {
                const result = {
                    description: null,
                    total_cost: null,
                    challenges_count: 0,
                    image_url: null,
                    category: null,
                    challenges: [],
                };

                // Descrição
                const descEl = document.querySelector('.sbc-set-description, [class*="description"]');
                if (descEl) result.description = descEl.textContent?.trim();

                // Custo total
                const costText = document.body.innerText;
                const costMatch = costText.match(/(?:Est|Cost)[^\\d]*(\\d[\\d,\\.]+)/i);
                if (costMatch) {
                    result.total_cost = parseInt(costMatch[1].replace(/[,\\.]/g, ''));
                }

                // Imagem
                const img = document.querySelector('.sbc-set-image img, [class*="sbc"] img');
                if (img) result.image_url = img.src;

                // Challenges
                const challengeEls = document.querySelectorAll('[class*="challenge"], [class*="squad-requirement"]');
                challengeEls.forEach((el, idx) => {
                    const nameEl = el.querySelector('h3, h4, [class*="title"], [class*="name"]');
                    const name = nameEl ? nameEl.textContent?.trim() : 'Desafio ' + (idx + 1);

                    const reqEls = el.querySelectorAll('[class*="requirement"], li');
                    const requirements = [];
                    reqEls.forEach(reqEl => {
                        const text = reqEl.textContent?.trim();
                        if (text && text.length > 3) {
                            requirements.push({ raw: text });
                        }
                    });

                    result.challenges.push({
                        name: name,
                        requirements: requirements,
                    });
                });

                result.challenges_count = result.challenges.length;
                return result;
            }
        """)

        # Pós-processar requisitos
        if details and details.get("challenges"):
            for ch in details["challenges"]:
                parsed_reqs = []
                for raw_req in ch.get("requirements", []):
                    parsed = parse_requirement_text(raw_req.get("raw", ""))
                    if parsed:
                        parsed_reqs.append(parsed)
                ch["requirements"] = parsed_reqs

        return details or {}

    except Exception:
        return {}
