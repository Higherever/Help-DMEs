import asyncio
import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional
import aiohttp
import aiofiles

# Importar motor de bypass do anti-bot
from backend.services.anti_bot import fetch_binary

logger = logging.getLogger("card_renderer")

# Paths absolutos
SERVICE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SERVICE_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
IMAGES_DIR = PROJECT_ROOT / "images"
JS_DIR = BACKEND_DIR / "card_generator_js"

# Mapeamento de Cores e Templates Dinâmicos por Tipo de Card
CARD_THEMES = {
    "normal":             {"bg": "sbc_global_Normal_bg.png", "color": "#3c3c3c"},
    "gold":               {"bg": "sbc_global_Normal_bg.png", "color": "#3c3c3c"},
    "rare_gold":          {"bg": "sbc_global_Normal_bg.png", "color": "#3c3c3c"},
    "icon":               {"bg": "sbc_global_Icon_bg.png", "color": "#3c2a12"},
    "totw":               {"bg": "sbc_global_TOTW_bg.png", "color": "#e6b000"},
    "tots":               {"bg": "sbc_global_TOTS_bg.png", "color": "#ffffff"},
    "sbc":                {"bg": "sbc_global_SBC_bg.png", "color": "#ffffff"},
    "hero":               {"bg": "sbc_global_Hero_SBC_bg.png", "color": "#ffffff"},
    "future_stars":       {"bg": "sbc_global_Future_Stars_bg.png", "color": "#ffffff"},
    "fut_birthday":       {"bg": "sbc_global_FUT_Birthday_bg.png", "color": "#ffffff"},
    "toty":               {"bg": "sbc_global_TOTY_bg.png", "color": "#ffffff"},
    "winter_wildcards":   {"bg": "sbc_global_Winter_Wildcards_bg.png", "color": "#ffffff"},
    "ucl_heroes":         {"bg": "sbc_global_UCL_Heroes_bg.png", "color": "#ffffff"},
    "fantasy_fc":         {"bg": "sbc_global_Fantasy_FC_bg.png", "color": "#ffffff"},
    "classic_xi_hero":    {"bg": "sbc_global_Classic_XI_Hero_bg.png", "color": "#ffffff"},
}

def get_card_theme(card_type: Optional[str]) -> Dict[str, str]:
    """Retorna o template de fundo e a cor do texto com base no tipo do card."""
    if not card_type:
        return CARD_THEMES["normal"]
    
    ct_lower = card_type.lower()
    
    # Busca por correspondência exata
    if ct_lower in CARD_THEMES:
        return CARD_THEMES[ct_lower]
    
    # Busca por correspondência parcial
    for key, val in CARD_THEMES.items():
        if key in ct_lower:
            return val
            
    return CARD_THEMES["normal"]

def sanitize_slug(text: str) -> str:
    if not text:
        return "unknown"
    clean = re.sub(r"[^a-zA-Z0-9\s_-]", "", text)
    clean = re.sub(r"[\s_-]+", "_", clean)
    return clean.strip("_").lower()[:50]

async def ensure_asset_local(
    session: aiohttp.ClientSession,
    url: str,
    dest_path: Path
) -> Optional[str]:
    """
    Garante que um asset de imagem (face, logo, bandeira) esteja salvo localmente.
    Se não existir, faz download rápido usando o motor anti-bot. Retorna o caminho absoluto.
    """
    if not url:
        return None
        
    if dest_path.exists() and dest_path.stat().st_size > 100:
        return str(dest_path.resolve())
        
    # Limpar URL (preservando query string/assinatura para o Futbin para evitar sig_invalid)
    if "futbin.com" in url:
        clean_url = url
    else:
        clean_url = url.split("?")[0] if "?" in url else url
        
    if clean_url.startswith("//"):
        clean_url = "https:" + clean_url
        
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        # Usar o bypass do fetch_binary que injeta cabeçalhos e referer corretos
        data = await fetch_binary(session, clean_url)
        if data and len(data) > 100:
            async with aiofiles.open(dest_path, "wb") as f:
                await f.write(data)
            logger.debug(f"[Renderer Cache] Baixou asset com sucesso para: {dest_path.name}")
            return str(dest_path.resolve())
    except Exception as e:
        logger.error(f"[Renderer Cache] Falha ao baixar asset {clean_url}: {e}")
        
    # Retorna o caminho se ele já existe (mesmo vazio, para evitar quebra), caso contrário None
    return str(dest_path.resolve()) if dest_path.exists() else None


class CardRendererClient:
    """
    Cliente assíncrono para gerenciar o microserviço Node.js
    e solicitar a renderização de cartas sob demanda.
    """
    def __init__(self):
        self.node_process = None

    async def start_service(self):
        """Inicializa o microserviço Node.js na porta 3001."""
        # Se um processo já estiver rodando, tentar desligá-lo antes
        await self.stop_service()
        
        logger.info("[Renderer] Iniciando microserviço Node.js de renderização offline...")
        try:
            self.node_process = await asyncio.create_subprocess_exec(
                "node", "generate.js",
                cwd=str(JS_DIR),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            # Aguardar 400ms para o Express levantar a porta 3001
            await asyncio.sleep(0.4)
            logger.info("[Renderer] Microserviço Node.js iniciado com sucesso.")
        except Exception as e:
            logger.error(f"[Renderer] Falha ao iniciar subprocesso Node.js: {e}")
            raise

    async def stop_service(self):
        """Derruba com segurança o microserviço Node.js."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("http://localhost:3001/shutdown", timeout=1) as resp:
                    if resp.status == 200:
                        logger.info("[Renderer] Microserviço encerrado remotamente via /shutdown.")
        except Exception:
            # Ignora erros se o serviço já estava desligado
            pass
            
        # Força encerramento do processo se ainda estiver ativo
        if self.node_process:
            try:
                self.node_process.terminate()
                await self.node_process.wait()
                logger.info("[Renderer] Subprocesso finalizado de forma forçada.")
            except Exception:
                pass
            self.node_process = None

    async def render_player(
        self,
        session: aiohttp.ClientSession,
        player_data: Dict
    ) -> Optional[Dict]:
        """
        Estrutura e dispara a renderização de um jogador no microserviço Node.js.
        Baixa e cacheia todos os assets necessários localmente antes de enviar.
        """
        futbin_id = str(player_data.get("futbin_id"))
        name = player_data.get("name", "Unknown Player")
        name_slug = sanitize_slug(name)
        
        # 1. Resolver caminhos locais de assets com download em cache
        # Face do jogador
        face_url = player_data.get("face_url") or player_data.get("render_url") or player_data.get("face_url_raw")
        face_path = IMAGES_DIR / "cards" / "renders" / f"render_{futbin_id}_{name_slug}.png"
        face_local = await ensure_asset_local(session, face_url, face_path)
        
        # Nação/Bandeira
        nation_url = player_data.get("nation_flag_url") or player_data.get("nation_url")
        nation_slug = sanitize_slug(player_data.get("nation", "unknown"))
        
        # Se a bandeira for "nation_unknown" mas a nação é conhecida, descartamos a URL genérica para usar o slug no fallback
        if nation_url and "nation_unknown" in str(nation_url) and nation_slug != "unknown":
            nation_url = None
            
        nation_path = IMAGES_DIR / "cards" / "nations" / f"nation_{nation_slug}.png"
        nation_local = await ensure_asset_local(session, nation_url, nation_path)
        
        # Clube/Logo
        club_url = player_data.get("club_logo_url") or player_data.get("club_url")
        club_slug = sanitize_slug(player_data.get("club", "unknown"))
        club_path = IMAGES_DIR / "cards" / "clubs" / f"club_{club_slug}.png"
        club_local = await ensure_asset_local(session, club_url, club_path)
        
        # Liga/Logo
        league_url = player_data.get("league_logo_url") or player_data.get("league_url")
        league_slug = sanitize_slug(player_data.get("league", "unknown"))
        league_path = IMAGES_DIR / "cards" / "leagues" / f"league_{league_slug}.png"
        league_local = await ensure_asset_local(session, league_url, league_path)

        # 2. Mapeamento de Cores e Templates
        theme = get_card_theme(player_data.get("card_type"))
        bg_template_path = IMAGES_DIR / "cards" / "templates" / theme["bg"]

        # 3. Formatar Estatísticas
        stats_input = player_data.get("stats") or []
        raw_position = player_data.get("position", "ST")
        is_gk = "GK" in str(raw_position).upper() if raw_position else False

        # Se as estatísticas vierem como chaves puras em player_data (ex: pace, shooting, gk_diving)
        if not stats_input:
            if is_gk:
                stats_input = [
                    {"name": "DIV", "value": player_data.get("gk_diving") or player_data.get("diving") or 0},
                    {"name": "HAN", "value": player_data.get("gk_handling") or player_data.get("handling") or 0},
                    {"name": "KIC", "value": player_data.get("gk_kicking") or player_data.get("kicking") or 0},
                    {"name": "REF", "value": player_data.get("gk_reflexes") or player_data.get("reflexes") or 0},
                    {"name": "SPD", "value": player_data.get("pace") or player_data.get("speed") or player_data.get("gk_speed") or 0},
                    {"name": "POS", "value": player_data.get("gk_positioning") or player_data.get("positioning") or 0},
                ]
            elif "pace" in player_data:
                stats_input = [
                    {"name": "PAC", "value": player_data.get("pace") or 0},
                    {"name": "SHO", "value": player_data.get("shooting") or 0},
                    {"name": "PAS", "value": player_data.get("passing") or 0},
                    {"name": "DRI", "value": player_data.get("dribbling_stat") or player_data.get("dribbling") or 0},
                    {"name": "DEF", "value": player_data.get("defending") or 0},
                    {"name": "PHY", "value": player_data.get("physic") or player_data.get("physical") or 0},
                ]

        # 4. Formatar Playstyles
        playstyles_input = player_data.get("playstyles") or []
        playstyles_payload = []
        for idx, ps in enumerate(playstyles_input):
            ps_url = ps.get("icon_url")
            if ps_url:
                ps_slug = sanitize_slug(ps.get("name", f"ps_{idx}"))
                ps_path = IMAGES_DIR / "cards" / "renders" / f"playstyle_{ps_slug}.png"
                ps_local = await ensure_asset_local(session, ps_url, ps_path)
                if ps_local:
                    playstyles_payload.append({"icon_path": ps_local})

        # 5. Montar Payload JSON
        raw_alt = player_data.get("alt_positions")
        alt_positions_payload = []
        if raw_alt:
            if isinstance(raw_alt, list):
                alt_positions_payload = [str(x) for x in raw_alt]
            elif isinstance(raw_alt, str):
                alt_positions_payload = [x.strip() for x in raw_alt.split(",") if x.strip()]

        raw_foot = player_data.get("foot") or player_data.get("preferred_foot")
        preferred_foot_payload = ""
        if raw_foot:
            foot_str = str(raw_foot).strip().lower()
            if "right" in foot_str or foot_str == "r":
                preferred_foot_payload = "R"
            elif "left" in foot_str or foot_str == "l":
                preferred_foot_payload = "L"
            else:
                preferred_foot_payload = str(raw_foot)[:1].upper()

        skills_wf_payload = player_data.get("skills_wf") or ""
        if not skills_wf_payload:
            sm = player_data.get("skill_moves")
            wf = player_data.get("weak_foot")
            if sm is not None and wf is not None:
                skills_wf_payload = f"{sm}-{wf}"
            elif sm is not None:
                skills_wf_payload = f"{sm}-?"
            elif wf is not None:
                skills_wf_payload = f"?-{wf}"

        payload = {
            "id":               futbin_id,
            "name":             name,
            "overall":          player_data.get("overall") or player_data.get("rating") or 0,
            "position":         player_data.get("position", "ST"),
            "text_color":       theme["color"],
            "bg_template_path": str(bg_template_path.resolve()),
            "face_path":        face_local,
            "nation_path":      nation_local,
            "club_path":        club_local,
            "league_path":      league_local,
            "stats":            stats_input,
            "playstyles":       playstyles_payload,
            "alt_positions":    alt_positions_payload,
            "preferred_foot":   preferred_foot_payload,
            "skills_wf":        skills_wf_payload
        }

        # 6. Disparar POST /generate para o Node Canvas
        try:
            headers = {"Content-Type": "application/json"}
            async with session.post(
                "http://localhost:3001/generate",
                json=payload,
                headers=headers,
                timeout=30
            ) as resp:
                if resp.status == 200:
                    res_json = await resp.json()
                    if res_json.get("success"):
                        logger.info(f"[Renderer] Card gerado offline com sucesso para {name}.")
                        # Injetar caminhos de assets locais para persistência fácil no banco
                        res_json["render_url"] = f"/images/cards/renders/render_{futbin_id}_{name_slug}.png" if face_local else None
                        res_json["nation_flag_url"] = f"/images/cards/nations/nation_{nation_slug}.png" if nation_local else None
                        res_json["club_logo_url"] = f"/images/cards/clubs/club_{club_slug}.png" if club_local else None
                        res_json["league_logo_url"] = f"/images/cards/leagues/league_{league_slug}.png" if league_local else None
                        return res_json
                else:
                    err_txt = await resp.text()
                    logger.error(f"[Renderer] Erro HTTP {resp.status} ao renderizar {name}: {err_txt}")
        except Exception as e:
            logger.error(f"[Renderer] Falha de comunicação com o microserviço Node: {e}")
            
        return None
