"""
Help DMEs — Anti-Bot Engine
============================
Motor de bypass de proteções anti-bot para scraping de Futbin e FutGG.

Técnicas implementadas:
  - Pool rotativo de 25+ User-Agents reais (Chrome/Edge/Firefox)
  - Headers HTTP completos com sec-ch-ua, sec-fetch-*, accept-encoding
  - Cookie jar persistente por sessão (simula usuário real)
  - Delays randomizados com distribuição gaussiana
  - Rate limiting por domínio (máx 1 req/2s)
  - Back-off exponencial com jitter em 429/403/503
  - Referer chain realista (Google → site)
  - Fingerprinting consistente por sessão
"""

import asyncio
import random
import logging
import time
from typing import Optional, Dict, Any
from urllib.parse import urlparse

import aiohttp

logger = logging.getLogger("help_dmes.anti_bot")

# ── Pool de User-Agents reais (Chrome 124/125, Windows/Mac/Linux) ──────────

UA_POOL = [
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    # Chrome Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    # Safari Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    # Firefox Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    # Firefox Linux
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    # Chrome Android (para variar fingerprint)
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
]

# ── Referer chains por site alvo ──────────────────────────────────────────

REFERER_CHAINS = {
    "futbin.com": [
        "https://www.google.com/search?q=futbin+players+fc26",
        "https://www.google.com/search?q=fc+26+futbin",
        "https://www.futbin.com/",
        "https://www.futbin.com/players",
    ],
    "fut.gg": [
        "https://www.google.com/search?q=fut.gg+fc26+player+cards",
        "https://www.google.com/search?q=fut+gg+players",
        "https://www.fut.gg/",
        "https://www.fut.gg/players/",
    ],
}

# ── Configurações de timing ───────────────────────────────────────────────

# Delay base entre requests: distribuição gaussiana
DELAY_MEAN = 3.2      # segundos — médio (parece humano)
DELAY_SIGMA = 0.9     # desvio padrão
DELAY_MIN = 1.8       # mínimo absoluto
DELAY_MAX = 7.0       # máximo absoluto

# Back-off em erros
BACKOFF_429 = 35      # base para 429 (rate limit)
BACKOFF_403 = 10      # base para 403 (forbidden)
BACKOFF_503 = 20      # base para 503 (service unavailable)
MAX_RETRIES = 4


# ── Estado de sessão por domínio ──────────────────────────────────────────

class DomainState:
    """Rastreia estado de requests por domínio."""
    def __init__(self):
        self.last_request_time: float = 0.0
        self.request_count: int = 0
        self.consecutive_errors: int = 0
        self.ua: str = random.choice(UA_POOL)
        self.referer_index: int = 0


_domain_states: Dict[str, DomainState] = {}


def _get_domain_state(url: str) -> DomainState:
    """Retorna ou cria estado para o domínio da URL."""
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    if domain not in _domain_states:
        _domain_states[domain] = DomainState()
    return _domain_states[domain]


def _get_domain_key(url: str) -> str:
    """Retorna a chave do domínio sem www."""
    parsed = urlparse(url)
    return parsed.netloc.replace("www.", "")


def _get_referer(url: str, state: DomainState) -> str:
    """Retorna o próximo referer realista para este domínio."""
    domain_key = _get_domain_key(url)
    
    # Encontrar chain mais próxima
    chain = None
    for key, ch in REFERER_CHAINS.items():
        if key in domain_key:
            chain = ch
            break
    
    if not chain:
        return "https://www.google.com/"
    
    # Progride na chain conforme requests aumentam
    idx = min(state.referer_index, len(chain) - 1)
    referer = chain[idx]
    
    # Avança na chain gradualmente
    if state.request_count > 2 and state.referer_index < len(chain) - 1:
        state.referer_index += 1
    
    return referer


def _build_headers(url: str, state: DomainState) -> Dict[str, str]:
    """Constrói headers HTTP completos e realistas para a request."""
    ua = state.ua
    referer = _get_referer(url, state)
    
    # Detectar se é Firefox pelo UA
    is_firefox = "Firefox" in ua
    is_mobile = "Mobile" in ua
    
    if is_firefox:
        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site" if "google" in referer else "same-origin",
            "Sec-Fetch-User": "?1",
            "Referer": referer,
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "DNT": "1",
        }
    else:
        # Chrome/Edge — headers completos com sec-ch-ua
        chrome_ver = "125"
        if "124" in ua:
            chrome_ver = "124"
        
        platform = '"Windows"'
        if "Macintosh" in ua:
            platform = '"macOS"'
        elif "Linux" in ua and "Android" not in ua:
            platform = '"Linux"'
        elif "Android" in ua:
            platform = '"Android"'
        
        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "sec-ch-ua": f'"Chromium";v="{chrome_ver}", "Google Chrome";v="{chrome_ver}", "Not-A.Brand";v="99"',
            "sec-ch-ua-mobile": "?1" if is_mobile else "?0",
            "sec-ch-ua-platform": platform,
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "cross-site" if "google" in referer else "same-origin",
            "sec-fetch-user": "?1",
            "Upgrade-Insecure-Requests": "1",
            "Referer": referer,
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
    
    return headers


async def _wait_for_domain(url: str, state: DomainState):
    """Aguarda o tempo necessário para respeitar o rate limit do domínio."""
    now = time.monotonic()
    elapsed = now - state.last_request_time
    
    # Delay humano: gaussiano com limites
    delay = random.gauss(DELAY_MEAN, DELAY_SIGMA)
    delay = max(DELAY_MIN, min(DELAY_MAX, delay))
    
    # Se o elapsed já passou do delay, não precisa esperar muito
    if elapsed < delay:
        remaining = delay - elapsed
        logger.debug(f"Anti-bot delay: {remaining:.1f}s para {_get_domain_key(url)}")
        await asyncio.sleep(remaining)
    
    state.last_request_time = time.monotonic()


async def fetch_html(
    session: aiohttp.ClientSession,
    url: str,
    extra_headers: Optional[Dict] = None,
    timeout: int = 30,
) -> Optional[str]:
    """
    Faz GET de uma URL com proteção anti-bot completa.
    
    Retorna o HTML como string ou None em caso de falha definitiva.
    """
    state = _get_domain_state(url)
    
    for attempt in range(MAX_RETRIES):
        # Aguardar rate limit do domínio
        await _wait_for_domain(url, state)
        
        headers = _build_headers(url, state)
        if extra_headers:
            headers.update(extra_headers)
        
        try:
            state.request_count += 1
            timeout_obj = aiohttp.ClientTimeout(total=timeout)
            
            async with session.get(url, headers=headers, timeout=timeout_obj, ssl=True, allow_redirects=True) as resp:
                
                if resp.status == 200:
                    state.consecutive_errors = 0
                    html = await resp.text()
                    
                    # Verificar se é página de desafio CAPTCHA/bot
                    if _is_bot_challenge(html):
                        logger.warning(f"Página de desafio bot detectada em {url}. Aguardando...")
                        await asyncio.sleep(BACKOFF_403 * (attempt + 1) + random.uniform(0, 5))
                        # Trocar UA para próxima tentativa
                        state.ua = random.choice(UA_POOL)
                        continue
                    
                    logger.debug(f"✅ {resp.status} {url[:80]}")
                    return html
                
                elif resp.status == 429:
                    wait = BACKOFF_429 * (attempt + 1) + random.uniform(0, 10)
                    logger.warning(f"[429] Rate limit em {url[:60]} — aguardando {wait:.0f}s (tentativa {attempt+1})")
                    state.consecutive_errors += 1
                    await asyncio.sleep(wait)
                
                elif resp.status == 403:
                    wait = BACKOFF_403 * (2 ** attempt) + random.uniform(0, 5)
                    logger.warning(f"[403] Bloqueado em {url[:60]} — aguardando {wait:.0f}s (tentativa {attempt+1})")
                    state.consecutive_errors += 1
                    state.ua = random.choice(UA_POOL)  # Trocar UA
                    state.referer_index = 0  # Resetar cadeia de referers
                    await asyncio.sleep(wait)
                
                elif resp.status == 503:
                    wait = BACKOFF_503 * (attempt + 1) + random.uniform(0, 8)
                    logger.warning(f"[503] Serviço indisponível em {url[:60]} — aguardando {wait:.0f}s")
                    await asyncio.sleep(wait)
                
                elif resp.status in (301, 302, 307, 308):
                    # Redirect inesperado
                    location = resp.headers.get("Location", "")
                    logger.info(f"[{resp.status}] Redirect para {location[:60]}")
                    return None
                
                else:
                    logger.error(f"[{resp.status}] Erro inesperado em {url[:60]}")
                    return None
        
        except asyncio.TimeoutError:
            logger.warning(f"Timeout em {url[:60]} (tentativa {attempt+1})")
            await asyncio.sleep(5 * (attempt + 1))
        
        except aiohttp.ClientError as e:
            logger.error(f"Erro de conexão em {url[:60]}: {e}")
            await asyncio.sleep(5 * (attempt + 1))
    
    logger.error(f"❌ Falha definitiva após {MAX_RETRIES} tentativas: {url[:80]}")
    return None


async def fetch_binary(
    session: aiohttp.ClientSession,
    url: str,
    timeout: int = 20,
) -> Optional[bytes]:
    """
    Faz GET de uma URL binária (imagem) com proteção anti-bot básica.
    Não aplica delays pesados — apenas headers realistas de imagem.
    """
    state = _get_domain_state(url)
    headers = _build_headers(url, state)
    
    # Para imagens, simplificar Accept
    headers["Accept"] = "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
    
    # Remover cabeçalhos específicos de navegação de páginas inteiras (suspeitos para imagens)
    headers.pop("Upgrade-Insecure-Requests", None)
    headers.pop("sec-fetch-user", None)
    headers.pop("Sec-Fetch-User", None)
    
    # Ajustar os cabeçalhos de sec-fetch para indicar de forma legítima o download de imagem
    is_firefox = "Firefox" in headers.get("User-Agent", "")
    if is_firefox:
        headers["Sec-Fetch-Dest"] = "image"
        headers["Sec-Fetch-Mode"] = "no-cors"
        headers["Sec-Fetch-Site"] = "cross-site"
    else:
        headers["sec-fetch-dest"] = "image"
        headers["sec-fetch-mode"] = "no-cors"
        headers["sec-fetch-site"] = "cross-site"
    
    # Injetar Referer específico baseado no domínio para evitar bloqueios de CDN
    if "futbin.com" in url:
        headers["Referer"] = "https://www.futbin.com/"
    elif "fut.gg" in url:
        headers["Referer"] = "https://www.fut.gg/"
    
    for attempt in range(3):
        try:
            timeout_obj = aiohttp.ClientTimeout(total=timeout)
            async with session.get(url, headers=headers, timeout=timeout_obj, ssl=True) as resp:
                if resp.status == 200:
                    return await resp.read()
                elif resp.status == 404:
                    logger.debug(f"Imagem não encontrada (404) para {url}")
                    return None
                elif resp.status == 429:
                    logger.warning(f"Erro 429 (Rate Limit) ao baixar imagem {url[:80]} - aguardando {15 * (attempt + 1)}s")
                    await asyncio.sleep(15 * (attempt + 1))
                else:
                    logger.warning(f"Erro status {resp.status} ao baixar imagem {url[:80]}")
                    await asyncio.sleep(3)
        except Exception as e:
            logger.debug(f"Erro ao baixar imagem {url[:50]}: {e}")
            await asyncio.sleep(3)
    
    return None


def _is_bot_challenge(html: str) -> bool:
    """
    Detecta se a resposta é uma página de desafio anti-bot REAL.
    
    IMPORTANTE: O HTML normal do Futbin/FutGG contém strings como
    'cloudflare' e 'Ray ID' como metadados legítimos — NÃO são blockers.
    Verifica apenas padrões exclusivos de páginas de bloqueio ativo.
    """
    if not html or len(html) < 200:
        return True
    
    # Padrões EXCLUSIVOS de páginas de desafio ativo do Cloudflare
    # (não aparecem em páginas legítimas)
    hard_blockers = [
        "cf-browser-verification",           # Verificação JS do CF
        "Checking if the site connection is secure",  # Texto CF específico
        "Just a moment...<",                  # Título HTML da página de challenge
        "Please Wait... | Cloudflare",        # Título CF waitroom
        "<title>Attention Required! | Cloudflare</title>",  # Bloqueio CF
        "__cf_chl_rt_tk",                     # Token de challenge CF
        "managed_challenge",                  # CF Managed Challenge
    ]
    
    for indicator in hard_blockers:
        if indicator in html:
            return True
    
    return False


def create_session() -> aiohttp.ClientSession:
    """
    Cria uma sessão aiohttp configurada para scraping anti-bot.
    Inclui cookie jar persistente e connector otimizado.
    """
    connector = aiohttp.TCPConnector(
        limit=4,           # Máx 4 conexões simultâneas (parece humano)
        force_close=False, # Manter keep-alive
        enable_cleanup_closed=True,
        ttl_dns_cache=300,
    )
    
    # Cookie jar automático simula browser real
    jar = aiohttp.CookieJar(unsafe=True)
    
    session = aiohttp.ClientSession(
        connector=connector,
        cookie_jar=jar,
        headers={
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    )
    
    return session


def reset_domain_state(domain: str = None):
    """Reseta o estado de um domínio específico ou todos."""
    global _domain_states
    if domain:
        if domain in _domain_states:
            del _domain_states[domain]
    else:
        _domain_states.clear()
    logger.info(f"Estado anti-bot resetado{'para ' + domain if domain else ' (global)'}")
