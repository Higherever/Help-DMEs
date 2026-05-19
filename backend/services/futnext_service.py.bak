"""
Help DMEs — FutNext Scraping Service
======================================
Serviço de coleta de SBCs do site futnext.com.
Usa Playwright com stealth para contornar proteções anti-bot.

Fluxo de coleta:
  1. Acessa futnext.com/sbc → coleta lista de SBC sets
  2. Para cada SBC set → acessa página de detalhes (formato /sbc/{slug}/{id})
  3. Persiste tudo no banco via SQLAlchemy async
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

logger = logging.getLogger("help_dmes." + __name__.split(".")[-1])


# ──────────────────────────────────────────────
# Estado global do scraper
# ──────────────────────────────────────────────

_futnext_status = {
    "status": "idle",       # idle / running / failed
    "message": "",          # Progresso
    "last_scrape_at": None,
    "sbcs_count": 0,
    "error": None,
}


def get_futnext_status() -> dict:
    """Retorna o status atual do scraper FutNext."""
    return _futnext_status.copy()


# ──────────────────────────────────────────────
# Scraper principal
# ──────────────────────────────────────────────

async def scrape_all_sbcs_futnext(session: AsyncSession) -> dict:
    """
    Coleta TODOS os SBCs do futnext.com/sbc.
    Atualiza o status global durante a execução.

    Retorna: {"status": str, "sbcs_scraped": int, "error": str | None}
    """
    global _futnext_status
    _futnext_status["status"] = "running"
    _futnext_status["message"] = "Iniciando scrape FutNext..."
    _futnext_status["error"] = None

    log = ScrapeLog(
        source="futnext",
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
            _futnext_status["message"] = "Acessando lista de SBCs no FutNext..."
            await page.goto("https://www.futnext.com/sbc", wait_until="load", timeout=30000)
            await page.wait_for_timeout(2000)

            sbc_data = await _extract_sbc_list(page)

            if not sbc_data:
                raise Exception("Nenhum SBC encontrado na página futnext.com/sbc")

            # ── Passo 2: Para cada SBC, coletar detalhes ──
            scraped_count = 0
            total_sbcs = len(sbc_data)
            for sbc_info in sbc_data:
                _futnext_status["message"] = f"Processando SBC {scraped_count + 1}/{total_sbcs}: {sbc_info.get('name', 'Unknown')}"
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
        _futnext_status["status"] = "idle"
        _futnext_status["message"] = "Concluído"
        _futnext_status["last_scrape_at"] = datetime.now(UTC)
        _futnext_status["sbcs_count"] = scraped_count

        await session.flush()
        return {"status": "success", "sbcs_scraped": scraped_count, "error": None}

    except Exception as e:
        error_msg = str(e)
        print(f"CRITICAL SCRAPE ERROR (futnext): {error_msg}")
        log.status = "failed"
        log.error_message = error_msg
        log.finished_at = datetime.now(UTC)
        _futnext_status["status"] = "failed"
        _futnext_status["message"] = "Erro: " + error_msg
        _futnext_status["error"] = error_msg

        await session.flush()
        return {"status": "failed", "sbcs_scraped": 0, "error": error_msg}


async def _extract_sbc_list(page) -> list[dict]:
    """
    Extrai a lista de SBCs da página principal do FutNext.
    Retorna lista de dicts com dados básicos de cada SBC.
    """
    sbcs = []

    data = await page.evaluate("""
        () => {
            const results = [];
            // FutNext example logic
            const links = document.querySelectorAll('a[href*="/sbc/"]');
            const seen = new Set();

            for (const link of links) {
                const href = link.getAttribute('href');
                if (!href || seen.has(href) || href === '/sbc/' || href === '/sbc') continue;
                seen.add(href);

                // No FutNext a URL é /sbc/{slug}/{id}
                const match = href.match(/\\/sbc\\/([\\w-]+)\\/(\\d+)/);
                if (!match) continue;

                const slug = match[1];
                const futggId = match[2]; // ID na plataforma

                const text = link.textContent?.trim() || '';
                const name = text.split('\\n')[0]?.trim() || slug;

                results.push({
                    futgg_id: futggId, // usando como ID local
                    name: name,
                    url: href.startsWith('http') ? href : 'https://www.futnext.com' + href,
                });
            }
            return results;
        }
    """)

    return data or []


async def _process_sbc(session: AsyncSession, page, sbc_info: dict):
    """
    Processa um SBC individual no FutNext: acessa a página de detalhes e
    extrai challenges, requisitos.
    """
    futgg_id = sbc_info["futgg_id"]
    url = sbc_info["url"]

    existing = await session.execute(
        select(SBCSet).where(SBCSet.futgg_id == futgg_id)
    )
    sbc_set = existing.scalar_one_or_none()

    if sbc_set:
        sbc_set.scraped_at = datetime.now(UTC)
        # Update source
        sbc_set.source = "futnext"
    else:
        sbc_set = SBCSet(
            futgg_id=futgg_id,
            name=sbc_info.get("name", futgg_id),
            category="players",
            source="futnext",
            scraped_at=datetime.now(UTC),
        )
        session.add(sbc_set)

    await session.flush()

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

        details = await _extract_sbc_details(page)

        if details:
            sbc_set.description = details.get("description")
            sbc_set.total_cost = details.get("total_cost")
            sbc_set.challenges_count = details.get("challenges_count", 0)
            sbc_set.image_url = details.get("image_url")
            if details.get("category"):
                sbc_set.category = details["category"]

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
        pass


async def _extract_sbc_details(page) -> dict:
    """Extrai detalhes de um SBC da sua página no FutNext."""
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

                const descEl = document.querySelector('.sbc-set-description, [class*="description"]');
                if (descEl) result.description = descEl.textContent?.trim();

                const costText = document.body.innerText;
                const costMatch = costText.match(/(?:Est|Cost)[^\\d]*(\\d[\\d,\\.]+)/i);
                if (costMatch) {
                    result.total_cost = parseInt(costMatch[1].replace(/[,\\.]/g, ''));
                }

                const img = document.querySelector('img[class*="sbc"]');
                if (img) result.image_url = img.src;

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
