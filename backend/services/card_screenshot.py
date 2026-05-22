import asyncio
import logging
import os
from pathlib import Path
from playwright.async_api import async_playwright

logger = logging.getLogger("help_dmes.screenshot")

class CardScreenshotService:
    """
    Serviço assíncrono para tirar screenshots das cartas completas no Futbin.
    Mantém uma única instância de navegador Chromium headless ativa para
    evitar sobrecarga de inicialização entre requisições consecutivas.
    """
    def __init__(self):
        self._pw = None
        self._browser = None
        self._context = None
        self._lock = asyncio.Lock()

    async def start(self):
        """Inicializa o navegador Playwright se ainda não estiver ativo."""
        async with self._lock:
            if not self._browser:
                logger.info("Iniciando navegador Chromium do Playwright...")
                self._pw = await async_playwright().start()
                self._browser = await self._pw.chromium.launch(headless=True)
                self._context = await self._browser.new_context(
                    viewport={"width": 1280, "height": 1024},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                )

    async def close(self):
        """Fecha o navegador e encerra a sessão do Playwright."""
        async with self._lock:
            if self._browser:
                logger.info("Encerrando navegador Playwright...")
                try:
                    await self._context.close()
                    await self._browser.close()
                    await self._pw.stop()
                except Exception as e:
                    logger.error(f"Erro ao fechar navegador: {e}")
                finally:
                    self._browser = None
                    self._pw = None

    async def take_card_screenshot(self, player_url: str, output_path: str) -> bool:
        """
        Navega até a página de detalhes do jogador no Futbin, aguarda a montagem
        completa da carta (.playercard-26) e salva um screenshot do elemento.
        
        Bloqueia anúncios e rastreadores automaticamente para maximizar a velocidade.
        """
        if not self._browser:
            await self.start()

        page = await self._context.new_page()
        try:
            # 1. Bloqueador de Anúncios e Rastreamento
            async def block_ads_and_trackers(route):
                url = route.request.url.lower()
                block_keywords = [
                    "google-analytics", "doubleclick", "adservice", "adnxs", "amazon-adsystem",
                    "popads", "adroll", "optimizely", "criteo", "scorecardresearch", "hotjar",
                    "facebook.net", "twitter.com", "ads", "analytics", "tracking", "adsbygoogle",
                    "setupad", "nitropack", "prebid", "quantserve", "pubmatic"
                ]
                if any(kw in url for kw in block_keywords):
                    await route.abort()
                else:
                    await route.continue_()

            await page.route("**/*", block_ads_and_trackers)

            # 2. Navegação ultra-rápida (aguarda apenas o DOM HTML carregar)
            logger.info(f"Navegando para {player_url}...")
            await page.goto(player_url, wait_until="domcontentloaded", timeout=20000)

            # Detecção inteligente de bloqueio anti-bot Cloudflare
            try:
                title = await page.title()
                if any(term in title.lower() for term in ["cloudflare", "attention required", "just a moment"]):
                    logger.warning(f"Bloqueio anti-bot Cloudflare detectado no Futbin (Título: '{title}'). Abortando screenshot para usar fallback rápido.")
                    return False
            except Exception as title_err:
                logger.debug(f"Erro ao ler título da página: {title_err}")

            # 3. Aguardar o elemento específico do card
            logger.info("Aguardando elemento .playercard-26...")
            try:
                card_el = await page.wait_for_selector(".playercard-26", timeout=4000)
            except Exception:
                logger.warning(f"Timeout aguardando pelo elemento .playercard-26 na página {player_url}")
                return False

            if not card_el:
                logger.error(f"Elemento .playercard-26 não encontrado na página {player_url}")
                return False

            # 4. Aguardar um breve momento para garantir carregamento de imagens internas (face/badges)
            await asyncio.sleep(2.0)

            # Limpeza agressiva do DOM para remover anúncios, menus, opções e o rodapé cinza do Futbin
            logger.info("Aplicando limpeza agressiva do DOM via Playwright...")
            try:
                await page.evaluate("""() => {
                    const card = document.querySelector('.playercard-26');
                    if (!card) return;
                    
                    // Remover opções do card (o hexágono verde do Futbin)
                    const options = card.querySelector('.playercard-options');
                    if (options) options.remove();
                    
                    // Remover rodapé de informações adicionais (preço, pé, skills)
                    const extraInfo = card.querySelector('.playercard-26-extra-info');
                    if (extraInfo) extraInfo.remove();
                    
                    // Mover apenas o card para o body e limpar todo o resto
                    document.body.innerHTML = '';
                    document.body.appendChild(card);
                    
                    // Resetar margens e background do body
                    document.body.style.margin = '0';
                    document.body.style.padding = '0';
                    document.body.style.background = 'transparent';
                    
                    // Posicionar o card no canto superior esquerdo absoluto
                    card.style.margin = '0';
                    card.style.position = 'absolute';
                    card.style.top = '0';
                    card.style.left = '0';
                }""")
                # Re-seleciona a referência do card após alterar o DOM
                card_el = page.locator(".playercard-26").first
            except Exception as eval_err:
                logger.warning(f"Erro ao aplicar limpeza do DOM: {eval_err}. Continuando com screenshot padrão...")

            # 5. Criar a pasta de destino se não existir
            dest_file = Path(output_path)
            dest_file.parent.mkdir(parents=True, exist_ok=True)

            # 6. Salvar screenshot do card
            await card_el.screenshot(path=str(dest_file))
            logger.info(f"Screenshot do card completo salvo com sucesso em {output_path}")
            return True

        except Exception as e:
            logger.error(f"Erro ao capturar screenshot do card de {player_url}: {e}")
            return False
        finally:
            await page.close()
