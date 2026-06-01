import asyncio
import json
import logging
import re
import sys
import os
import functools
import unicodedata
import colorsys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import aiohttp
import aiofiles
from PIL import Image, ImageDraw, ImageFont, ImageColor, ImageFilter, ImageOps, ImageChops

# Importar motor de bypass do anti-bot
from backend.services.anti_bot import fetch_binary

logger = logging.getLogger("card_renderer")

# Paths absolutos
SERVICE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SERVICE_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
IMAGES_DIR = PROJECT_ROOT / "images"
JS_DIR = BACKEND_DIR / "card_generator_js"
FONTS_DIR = JS_DIR / "fonts"

BEBAS_FONT_PATH = FONTS_DIR / "BebasNeue-Regular.ttf"
OSWALD_FONT_PATH = FONTS_DIR / "Oswald-Regular.ttf"

FULL_DIR = IMAGES_DIR / "cards" / "full"
SMALL_DIR = IMAGES_DIR / "cards" / "small"

# Dimensões e Resolução Base
CARD_W = 756
CARD_H = 1056

# Cores e Temas por Raridade (Fidelidade EA FC 26)
_DARK_PROFILE = {
    "card_color": "#ffffff", "rating_color": "#ffffff",
    "alt_pos_bg": "#1c1c1c", "alt_pos_border": "#ffffff",
    "extra_info_bg": "#1c1c1c", "extra_info_border": "#ffffff",
    "playstyle_bg": "#0f0f0f", "playstyle_border": "#ffffff"
}

CARD_THEMES = {
    "gold": {
        "card_color": "#443a22", "rating_color": "#443a22",
        "alt_pos_bg": "#D0B77F", "alt_pos_border": "#443a22",
        "extra_info_bg": "#D0B77F", "extra_info_border": "#443a22",
        "playstyle_bg": "#2c2616", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Normal_bg.png"
    },
    "gold_rare": {
        "card_color": "#443a22", "rating_color": "#443a22",
        "alt_pos_bg": "#C8A020", "alt_pos_border": "#443a22",
        "extra_info_bg": "#C8A020", "extra_info_border": "#443a22",
        "playstyle_bg": "#2c2616", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Normal_bg.png"
    },
    "silver": {
        "card_color": "#5a5a5a", "rating_color": "#5a5a5a",
        "alt_pos_bg": "#C0C0C0", "alt_pos_border": "#5a5a5a",
        "extra_info_bg": "#C0C0C0", "extra_info_border": "#5a5a5a",
        "playstyle_bg": "#2b2b2b", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Normal_bg.png"
    },
    "bronze": {
        "card_color": "#5c3a1e", "rating_color": "#5c3a1e",
        "alt_pos_bg": "#CD7F32", "alt_pos_border": "#5c3a1e",
        "extra_info_bg": "#CD7F32", "extra_info_border": "#5c3a1e",
        "playstyle_bg": "#2c1b0e", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Normal_bg.png"
    },
    "icon": {
        "card_color": "#f0e6c8", "rating_color": "#f0e6c8",
        "alt_pos_bg": "#2a1a0a", "alt_pos_border": "#f0e6c8",
        "extra_info_bg": "#2a1a0a", "extra_info_border": "#f0e6c8",
        "playstyle_bg": "#1f1307", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Icon_bg.png"
    },
    "captains_icon": {
        "card_color": "#f0e6c8", "rating_color": "#f0e6c8",
        "alt_pos_bg": "#2a1a0a", "alt_pos_border": "#f0e6c8",
        "extra_info_bg": "#2a1a0a", "extra_info_border": "#f0e6c8",
        "playstyle_bg": "#1f1307", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Icon_bg.png"
    },
    "champion_icon": {
        "card_color": "#f0e6c8", "rating_color": "#f0e6c8",
        "alt_pos_bg": "#2a1a0a", "alt_pos_border": "#f0e6c8",
        "extra_info_bg": "#2a1a0a", "extra_info_border": "#f0e6c8",
        "playstyle_bg": "#1f1307", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Icon_bg.png"
    },
    "debut_icon": {
        "card_color": "#f0e6c8", "rating_color": "#f0e6c8",
        "alt_pos_bg": "#2a1a0a", "alt_pos_border": "#f0e6c8",
        "extra_info_bg": "#2a1a0a", "extra_info_border": "#f0e6c8",
        "playstyle_bg": "#1f1307", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Icon_bg.png"
    },
    "knockout_royalty_icon": {
        "card_color": "#f0e6c8", "rating_color": "#f0e6c8",
        "alt_pos_bg": "#2a1a0a", "alt_pos_border": "#f0e6c8",
        "extra_info_bg": "#2a1a0a", "extra_info_border": "#f0e6c8",
        "playstyle_bg": "#1f1307", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Icon_bg.png"
    },
    "winter_wilcard_icon": {
        "card_color": "#f0e6c8", "rating_color": "#f0e6c8",
        "alt_pos_bg": "#2a1a0a", "alt_pos_border": "#f0e6c8",
        "extra_info_bg": "#2a1a0a", "extra_info_border": "#f0e6c8",
        "playstyle_bg": "#1f1307", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Icon_bg.png"
    },
    "winter_wildcards_icon_sbc": {
        "card_color": "#f0e6c8", "rating_color": "#f0e6c8",
        "alt_pos_bg": "#2a1a0a", "alt_pos_border": "#f0e6c8",
        "extra_info_bg": "#2a1a0a", "extra_info_border": "#f0e6c8",
        "playstyle_bg": "#1f1307", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Icon_bg.png"
    },
    
    # Custom special card themes
    "toty": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#0a0a3a", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#0a0a3a", "extra_info_border": "#ffffff",
        "playstyle_bg": "#080828", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_TOTY_bg.png"
    },
    "toty_hm_heroes": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#0a0a3a", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#0a0a3a", "extra_info_border": "#ffffff",
        "playstyle_bg": "#080828", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_TOTY_bg.png"
    },
    "toty_honourable_mention": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#081b33", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#081b33", "extra_info_border": "#ffffff",
        "playstyle_bg": "#041021", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_TOTY_Honourable_Ment_bg.png"
    },
    "toty_icon": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#0e1a30", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#0e1a30", "extra_info_border": "#ffffff",
        "playstyle_bg": "#070e1c", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_TOTY_Icon_bg.png"
    },
    "toty_icon_sbc": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#0e1a30", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#0e1a30", "extra_info_border": "#ffffff",
        "playstyle_bg": "#070e1c", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_TOTY_Icon_SBC_bg.png"
    },
    "hero": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#1a0a2e", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#1a0a2e", "extra_info_border": "#ffffff",
        "playstyle_bg": "#10051e", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Hero_SBC_bg.png"
    },
    "hero_sbc": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#1a0a2e", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#1a0a2e", "extra_info_border": "#ffffff",
        "playstyle_bg": "#10051e", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Hero_SBC_bg.png"
    },
    "base_heroes": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#1a0a2e", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#1a0a2e", "extra_info_border": "#ffffff",
        "playstyle_bg": "#10051e", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Base_Heroes_bg.png"
    },
    "prime_heroes": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#1a0a2e", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#1a0a2e", "extra_info_border": "#ffffff",
        "playstyle_bg": "#10051e", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Base_Heroes_bg.png"
    },
    "team_of_the_season": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#00122e", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#00122e", "extra_info_border": "#ffffff",
        "playstyle_bg": "#000a1a", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_TOTS_bg.png"
    },
    "tots": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#00122e", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#00122e", "extra_info_border": "#ffffff",
        "playstyle_bg": "#000a1a", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_TOTS_bg.png"
    },
    "tots_highlights": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#00122e", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#00122e", "extra_info_border": "#ffffff",
        "playstyle_bg": "#000a1a", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_TOTS_Highlights_bg.png"
    },
    "winter_wildcards": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#0a2e1d", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#0a2e1d", "extra_info_border": "#ffffff",
        "playstyle_bg": "#051a0f", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Winter_Wildcards_bg.png"
    },
    "winter_wildcard_hero": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#0a2e1d", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#0a2e1d", "extra_info_border": "#ffffff",
        "playstyle_bg": "#051a0f", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Winter_Wildcard_Hero_bg.png"
    },
    "winter_wildcard_icon": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#0a2e1d", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#0a2e1d", "extra_info_border": "#ffffff",
        "playstyle_bg": "#051a0f", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Winter_Wildcard_ICON_bg.png"
    },
    "winter_wildcards_sbc": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#0a2e1d", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#0a2e1d", "extra_info_border": "#ffffff",
        "playstyle_bg": "#051a0f", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Winter_Wildcards_SBC_bg.png"
    },
    "ultimate_scream": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#230b02", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#230b02", "extra_info_border": "#ffffff",
        "playstyle_bg": "#150601", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Ultimate_Scream_bg.png"
    },
    "ultimate_scream_hero": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#230b02", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#230b02", "extra_info_border": "#ffffff",
        "playstyle_bg": "#150601", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Ultimate_Scream_bg.png"
    },
    "thunderstruck": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#0c1b2b", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#0c1b2b", "extra_info_border": "#ffffff",
        "playstyle_bg": "#06101c", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Thunderstruck_bg.png"
    },
    "thunderstruck_icon": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#0c1b2b", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#0c1b2b", "extra_info_border": "#ffffff",
        "playstyle_bg": "#06101c", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Thunderstruck_Icon_bg.png"
    },
    "fut_birthday": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#2b0d3d", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#2b0d3d", "extra_info_border": "#ffffff",
        "playstyle_bg": "#1a0526", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_FUT_Birthday_bg.png"
    },
    "fut_birthday_hero": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#2b0d3d", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#2b0d3d", "extra_info_border": "#ffffff",
        "playstyle_bg": "#1a0526", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_FUT_Birthday_Hero_bg.png"
    },
    "fut_birthday_icon": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#2b0d3d", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#2b0d3d", "extra_info_border": "#ffffff",
        "playstyle_bg": "#1a0526", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_FUT_Birthday_Icon_bg.png"
    },
    "fantasy_fc": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#0a1c3d", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#0a1c3d", "extra_info_border": "#ffffff",
        "playstyle_bg": "#051026", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Fantasy_FC_bg.png"
    },
    "fantasy_fc_hero": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#0a1c3d", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#0a1c3d", "extra_info_border": "#ffffff",
        "playstyle_bg": "#051026", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Fantasy_FC_Hero_bg.png"
    },
    "flashback": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#1c202b", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#1c202b", "extra_info_border": "#ffffff",
        "playstyle_bg": "#10131c", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Flashback_SBC_bg.png"
    },
    "ucl_rttf": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#121a3b", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#121a3b", "extra_info_border": "#ffffff",
        "playstyle_bg": "#0a0f2b", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_UCL_RTTF_bg.png"
    },
    "potm_la_liga": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#2c1c38", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#2c1c38", "extra_info_border": "#ffffff",
        "playstyle_bg": "#1d1226", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_LaLiga_POTM_SBC_bg.png"
    },
    "festival_of_football_captains": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#0f2c1f", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#0f2c1f", "extra_info_border": "#ffffff",
        "playstyle_bg": "#081a12", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_FoF_Captains_bg.png"
    },
    "star_performer": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#300b14", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#300b14", "extra_info_border": "#ffffff",
        "playstyle_bg": "#1e070d", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_Star_Performer_bg.png"
    },
    "end_of_era": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#191452", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#191452", "extra_info_border": "#ffffff",
        "playstyle_bg": "#100d35", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_End_of_an_Era_bg.png"
    },
    "totw": {
        "card_color": "#ffffff", "rating_color": "#ffffff",
        "alt_pos_bg": "#1a1a1a", "alt_pos_border": "#ffffff",
        "extra_info_bg": "#1a1a1a", "extra_info_border": "#ffffff",
        "playstyle_bg": "#121212", "playstyle_border": "#ffffff",
        "default_bg": "sbc_global_TOTW_bg.png"
    },

    # Automatically map other SBC global backgrounds
    "answer_the_call": {**_DARK_PROFILE, "default_bg": "sbc_global_Answer_the_call_bg.png"},
    "classic_xi_hero": {**_DARK_PROFILE, "default_bg": "sbc_global_Classic_XI_Hero_bg.png"},
    "cornerstones": {**_DARK_PROFILE, "default_bg": "sbc_global_Cornerstones_bg.png"},
    "fc_pro_icon_sbc": {**_DARK_PROFILE, "default_bg": "sbc_global_FC_Pro_Icon_SBC_bg.png"},
    "fc_pro_leagues_live": {**_DARK_PROFILE, "default_bg": "sbc_global_FC_Pro_Leagues_Live_bg.png"},
    "fc_pro": {**_DARK_PROFILE, "default_bg": "sbc_global_FC_Pro_bg.png"},
    "fantasy_captain_icon": {**_DARK_PROFILE, "default_bg": "sbc_global_Fantasy_Captain_Icon_bg.png"},
    "fantasy_fpl": {**_DARK_PROFILE, "default_bg": "sbc_global_Fantasy_FPL_bg.png"},
    "fantasy_premier_league": {**_DARK_PROFILE, "default_bg": "sbc_global_Fantasy_FPL_bg.png"},
    "joga_bonito_hero": {**_DARK_PROFILE, "default_bg": "sbc_global_Joga_Bonito_Hero_bg.png"},
    "joga_bonito": {**_DARK_PROFILE, "default_bg": "sbc_global_Joga_Bonito_bg.png"},
    "knockout_hero": {**_DARK_PROFILE, "default_bg": "sbc_global_Knockout_Hero_bg.png"},
    "knockout_icon": {**_DARK_PROFILE, "default_bg": "sbc_global_Knockout_Icon_bg.png"},
    "knockout_royalty": {**_DARK_PROFILE, "default_bg": "sbc_global_Knockout_Royalty_bg.png"},
    "potm_bundesliga": {**_DARK_PROFILE, "default_bg": "sbc_global_Bundes_POTM_SBC_bg.png"},
    "potm_liga_f": {**_DARK_PROFILE, "default_bg": "sbc_global_Liga_F_POTM_SBC_bg.png"},
    "potm_ligue_1": {**_DARK_PROFILE, "default_bg": "sbc_global_Ligue_1_POTM_SBC_bg.png"},
    "potm_pl": {**_DARK_PROFILE, "default_bg": "sbc_global_PL_POTM_SBC_bg.png"},
    "potm_serie_a": {**_DARK_PROFILE, "default_bg": "sbc_global_PL_POTM_SBC_bg.png"},
    "player_moments": {**_DARK_PROFILE, "default_bg": "sbc_global_Player_Moments_bg.png"},
    "moments": {**_DARK_PROFILE, "default_bg": "sbc_global_Player_Moments_bg.png"},
    "premium_world_tour": {**_DARK_PROFILE, "default_bg": "sbc_global_Premium_World_Tour_bg.png"},
    "ratings_reload": {**_DARK_PROFILE, "default_bg": "sbc_global_Ratings_Reload_bg.png"},
    "sbc": {**_DARK_PROFILE, "default_bg": "sbc_global_SBC_bg.png"},
    "showdown": {**_DARK_PROFILE, "default_bg": "sbc_global_ShowDown_bg.png"},
    "squad_foundations": {**_DARK_PROFILE, "default_bg": "sbc_global_Squad_Foundations_bg.png"},
    "foundations": {**_DARK_PROFILE, "default_bg": "sbc_global_Squad_Foundations_bg.png"},
    "time_warp_icon_sbc": {**_DARK_PROFILE, "default_bg": "sbc_global_Time_Warp_Icon_SBC_bg.png"},
    "time_warp_icon": {**_DARK_PROFILE, "default_bg": "sbc_global_Time_Warp_Icon_bg.png"},
    "time_warp": {**_DARK_PROFILE, "default_bg": "sbc_global_Time_Warp_bg.png"},
    "trophy_titans_hero": {**_DARK_PROFILE, "default_bg": "sbc_global_Trophy_Titans_Hero_bg.png"},
    "trophy_titans_icon": {**_DARK_PROFILE, "default_bg": "sbc_global_Trophy_Titans_Icon_bg.png"},
    "ucl_heroes": {**_DARK_PROFILE, "default_bg": "sbc_global_UCL_Heroes_bg.png"},
    "ucl_primetime": {**_DARK_PROFILE, "default_bg": "sbc_global_UCL_Primetime_bg.png"},
    "uecl_primetime": {**_DARK_PROFILE, "default_bg": "sbc_global_UECL_Primetime_bg.png"},
    "uecl_rttf": {**_DARK_PROFILE, "default_bg": "sbc_global_UECL_RTTF_bg.png"},
    "uel_primetime": {**_DARK_PROFILE, "default_bg": "sbc_global_UEL_Primetime_bg.png"},
    "uel_rttf": {**_DARK_PROFILE, "default_bg": "sbc_global_UEL_RTTF_bg.png"},
    "uwcl_heroes": {**_DARK_PROFILE, "default_bg": "sbc_global_UWCL_Heroes_bg.png"},
    "uwcl_primetime": {**_DARK_PROFILE, "default_bg": "sbc_global_UWCL_Primetime_bg.png"},
    "uwcl_rttf": {**_DARK_PROFILE, "default_bg": "sbc_global_UWCL_RTTF_bg.png"},
    "ultimate_scream_icon": {**_DARK_PROFILE, "default_bg": "sbc_global_Ultimate_Scream_Icon_bg.png"},
    "unbreakables_hero": {**_DARK_PROFILE, "default_bg": "sbc_global_Unbreakables_Hero_bg.png"},
    "unbreakables_icon": {**_DARK_PROFILE, "default_bg": "sbc_global_Unbreakables_Icon_bg.png"},
    "unbreakables": {**_DARK_PROFILE, "default_bg": "sbc_global_Unbreakables_bg.png"},
    "wildcards_hero_sbc": {**_DARK_PROFILE, "default_bg": "sbc_global_Wildcards_Hero_SBC_bg.png"},
    "wildcards_icon_sbc": {**_DARK_PROFILE, "default_bg": "sbc_global_Wildcards_Icon_SBC_bg.png"},
    "world_tour": {**_DARK_PROFILE, "default_bg": "sbc_global_World_Tour_bg.png"}
}

SPECIAL_CARD_TYPES = {"toty", "tots", "hero", "end_of_era", "icon", "totw",
                      "fantasy_fc", "fut_birthday", "winter_wildcards"}

# Cache de fontes para otimização
@functools.lru_cache(maxsize=64)
def font_bebas(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(BEBAS_FONT_PATH), size)

@functools.lru_cache(maxsize=64)
def font_oswald(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(OSWALD_FONT_PATH), size)

def px(percent_of_width: float) -> int:
    return int(CARD_W * percent_of_width)

def py(percent_of_height: float) -> int:
    return int(CARD_H * percent_of_height)

def pf(base_multiplier: float) -> int:
    base = CARD_W * 0.0557  # ~42.1px no canvas 3x (756px)
    return int(base * base_multiplier)

def get_card_theme(card_type: Optional[str]) -> Dict[str, str]:
    if not card_type:
        return CARD_THEMES["gold"]
    ct_lower = card_type.lower().replace(" ", "_").replace("-", "_")
    if ct_lower in CARD_THEMES:
        return CARD_THEMES[ct_lower]
    for key, val in CARD_THEMES.items():
        if key in ct_lower:
            return val
    return CARD_THEMES["gold"]

def parse_color_rgba(color_str: str) -> Tuple[int, int, int, int]:
    if not color_str:
        return (255, 255, 255, 255)
    if color_str.startswith("rgba"):
        parts = color_str.replace("rgba(", "").replace(")", "").split(",")
        r = int(parts[0].strip())
        g = int(parts[1].strip())
        b = int(parts[2].strip())
        a = int(float(parts[3].strip()) * 255)
        return (r, g, b, a)
    elif color_str.startswith("#"):
        rgb = ImageColor.getrgb(color_str)
        if len(rgb) == 3:
            return (rgb[0], rgb[1], rgb[2], 255)
        return rgb
    else:
        rgb = ImageColor.getrgb(color_str)
        return (rgb[0], rgb[1], rgb[2], 255)

def remove_white_corners_pillow(image: Image.Image, thresh: int = 15) -> Image.Image:
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    w, h = image.size
    corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    for corner in corners:
        ImageDraw.floodfill(image, corner, (0, 0, 0, 0), thresh=thresh)
    return image

def analyze_template_palette(bg_img: Image.Image) -> Dict[str, Tuple[int, int, int]]:
    # Reduzir a imagem para agilizar o processamento e remover detalhes finos
    small_img = bg_img.resize((100, 140), Image.Resampling.NEAREST)
    w, h = small_img.size
    
    # Coletar cores dos pixels
    pixels = []
    for y in range(h):
        for x in range(w):
            r, g, b, a = small_img.getpixel((x, y))
            if a > 150: # Apenas pixels visíveis
                pixels.append((r, g, b))
                
    if not pixels:
        return {
            "bg": (15, 15, 15),
            "accent": (255, 255, 255),
            "text": (255, 255, 255)
        }
        
    # Converter para HSL
    hsl_pixels = []
    for r, g, b in pixels:
        h_val, l_val, s_val = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
        hsl_pixels.append((h_val, l_val, s_val, (r, g, b)))
        
    # 1. Cor de fundo (dominante escura)
    bg_candidates = [p for p in hsl_pixels if p[1] < 0.45]
    if not bg_candidates:
        bg_candidates = hsl_pixels
    bg_candidates.sort(key=lambda x: x[1])
    num_bg = max(1, len(bg_candidates) // 3)
    avg_bg_r = sum(p[3][0] for p in bg_candidates[:num_bg]) // num_bg
    avg_bg_g = sum(p[3][1] for p in bg_candidates[:num_bg]) // num_bg
    avg_bg_b = sum(p[3][2] for p in bg_candidates[:num_bg]) // num_bg
    bg_color = (avg_bg_r, avg_bg_g, avg_bg_b)
    
    # 2. Cor de destaque (saturada intermediária)
    accent_candidates = [p for p in hsl_pixels if 0.25 < p[1] < 0.88 and p[2] > 0.15]
    if not accent_candidates:
        accent_candidates = hsl_pixels
    accent_candidates.sort(key=lambda x: x[2], reverse=True)
    num_accent = max(1, len(accent_candidates) // 10)
    avg_acc_r = sum(p[3][0] for p in accent_candidates[:num_accent]) // num_accent
    avg_acc_g = sum(p[3][1] for p in accent_candidates[:num_accent]) // num_accent
    avg_acc_b = sum(p[3][2] for p in accent_candidates[:num_accent]) // num_accent
    accent_color = (avg_acc_r, avg_acc_g, avg_acc_b)
    
    # 3. Cor do texto (alto contraste)
    bg_l = 0.299 * bg_color[0] + 0.587 * bg_color[1] + 0.114 * bg_color[2]
    if bg_l < 120:
        h_acc, l_acc, s_acc = colorsys.rgb_to_hls(accent_color[0] / 255.0, accent_color[1] / 255.0, accent_color[2] / 255.0)
        r_t, g_t, b_t = colorsys.hls_to_rgb(h_acc, 0.90, max(s_acc, 0.50))
        text_color = (int(r_t * 255), int(g_t * 255), int(b_t * 255))
    else:
        h_acc, l_acc, s_acc = colorsys.rgb_to_hls(accent_color[0] / 255.0, accent_color[1] / 255.0, accent_color[2] / 255.0)
        r_t, g_t, b_t = colorsys.hls_to_rgb(h_acc, 0.15, max(s_acc, 0.50))
        text_color = (int(r_t * 255), int(g_t * 255), int(b_t * 255))
        
    return {
        "bg": bg_color,
        "accent": accent_color,
        "text": text_color
    }

def get_adaptive_colors(palette: Dict[str, Tuple[int, int, int]]) -> Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int]]:
    accent_rgb = palette["accent"]
    text_rgb = palette["text"]
    
    # 1. Borda/Texto/Linhas: A cor de texto harmonizada brilhante
    border_rgba = (text_rgb[0], text_rgb[1], text_rgb[2], 255)
    
    # 2. Fundo da Caixa: O accent escurecido a 7% de luminosidade no HSL
    r, g, b = accent_rgb[0] / 255.0, accent_rgb[1] / 255.0, accent_rgb[2] / 255.0
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    target_l_bg = 0.07
    target_s_bg = max(s * 0.8, 0.20)
    r_bg, g_bg, b_bg = colorsys.hls_to_rgb(h, target_l_bg, target_s_bg)
    bg_rgba = (int(r_bg * 255), int(g_bg * 255), int(b_bg * 255), 255)
    
    return border_rgba, bg_rgba

def draw_vector_star(draw, cx, cy, r_out=7, r_in=3, fill_color=(255, 255, 255, 255)):
    import math
    pts = []
    for i in range(10):
        angle = i * math.pi / 5 - math.pi / 2
        r = r_out if i % 2 == 0 else r_in
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    draw.polygon(pts, fill=fill_color)

def draw_vector_foot(draw, cx, cy, height=13, color=(255, 255, 255, 255)):
    import math
    s = height / 18.0
    # 1. Heel
    draw.ellipse([cx - 2.5 * s, cy + 2 * s, cx + 2.5 * s, cy + 8 * s], fill=color)
    # 2. Front sole
    draw.ellipse([cx - 3.5 * s, cy - 6 * s, cx + 3.5 * s, cy + 2 * s], fill=color)
    # Arch polygon
    draw.polygon([
        (cx - 2.5 * s, cy + 2.5 * s),
        (cx + 2.5 * s, cy + 2.5 * s),
        (cx + 3.5 * s, cy - 1 * s),
        (cx - 3.5 * s, cy - 1 * s)
    ], fill=color)
    # 3. Toes (slightly smaller and positioned beautifully)
    # Big toe
    draw.ellipse([cx - 4 * s, cy - 9.5 * s, cx - 1.8 * s, cy - 7 * s], fill=color)
    # 2nd toe
    draw.ellipse([cx - 1.5 * s, cy - 10.5 * s, cx + 0.1 * s, cy - 8.2 * s], fill=color)
    # 3rd toe
    draw.ellipse([cx + 0.3 * s, cy - 10 * s, cx + 1.7 * s, cy - 8 * s], fill=color)
    # 4th toe
    draw.ellipse([cx + 1.9 * s, cy - 9.5 * s, cx + 3.1 * s, cy - 7.5 * s], fill=color)
    # 5th toe
    draw.ellipse([cx + 3.3 * s, cy - 8.5 * s, cx + 4.3 * s, cy - 6.8 * s], fill=color)

def draw_integrated_hex_box(
    draw, x_center, x_left, x_right, y_start, hex_item_h, h_cap, items, font, bg_color, border_color, border_width=4
) -> int:
    n = len(items)
    y_end = y_start + n * hex_item_h
    
    # Vértices do polígono integrado
    pts = [
        (x_center, y_start),
        (x_right, y_start + h_cap),
        (x_right, y_end - h_cap),
        (x_center, y_end),
        (x_left, y_end - h_cap),
        (x_left, y_start + h_cap)
    ]
    
    # Desenhar fundo
    draw.polygon(pts, fill=bg_color)
    
    # Desenhar contorno de 4px
    for k in range(len(pts)):
        p1 = pts[k]
        p2 = pts[(k + 1) % len(pts)]
        draw.line([p1, p2], fill=border_color, width=border_width)
        
    # Desenhar textos e divisórias
    for i, item in enumerate(items):
        cell_y = y_start + i * hex_item_h
        cell_cy = cell_y + hex_item_h // 2
        
        if isinstance(item, tuple):
            # It's a custom rating item: (number_str, icon_type)
            num_str, icon_type = item
            
            # Measure text size of the number
            bbox = draw.textbbox((0, 0), num_str, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            
            # Let's say we want a small gap between the number and the icon
            gap = 6
            if icon_type == "foot":
                icon_size = max(int(text_h * 0.65), 10)
            else:
                icon_size = 14
            
            # Total width of text + gap + icon
            total_w = text_w + gap + icon_size
            
            # Start X so it's centered
            start_x = x_center - total_w // 2
            
            # Draw number
            draw.text((start_x + text_w // 2, cell_cy), num_str,
                      font=font, fill=border_color, anchor="mm")
                      
            # Draw icon
            icon_cx = start_x + text_w + gap + icon_size // 2
            icon_cy = cell_cy
            
            if icon_type == "star":
                draw_vector_star(draw, icon_cx, icon_cy, r_out=7, r_in=3, fill_color=border_color)
            elif icon_type == "foot":
                try:
                    shoe_path = PROJECT_ROOT / "images" / "cards" / "renders" / "left_shoe.png"
                    if not shoe_path.exists():
                        shoe_path = Path("images/cards/renders/left_shoe.png")
                    
                    shoe_img = Image.open(shoe_path).convert("RGBA")
                    _, _, _, a_ch = shoe_img.split()
                    
                    r_col, g_col, b_col = border_color[:3]
                    colored_shoe = Image.merge("RGBA", (
                        Image.new("L", shoe_img.size, r_col),
                        Image.new("L", shoe_img.size, g_col),
                        Image.new("L", shoe_img.size, b_col),
                        a_ch
                    ))
                    
                    resized_shoe = colored_shoe.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
                    canvas_img = draw._image
                    canvas_img.alpha_composite(resized_shoe, (icon_cx - icon_size // 2, icon_cy - icon_size // 2))
                except Exception as e:
                    draw_vector_foot(draw, icon_cx, icon_cy, height=icon_size, color=border_color)
        else:
            # Normal text
            draw.text((x_center, cell_cy), item.upper() if hasattr(item, "upper") else str(item),
                      font=font, fill=border_color, anchor="mm")
                  
        # Divisória interna
        if i < n - 1:
            line_y = cell_y + hex_item_h
            draw.line([(x_left, line_y), (x_right, line_y)], fill=border_color, width=border_width)
            
    return y_end

def remove_background_photo(image_path: Path) -> Image.Image:
    img = Image.open(image_path).convert("RGBA")
    
    # Verificar se a imagem já possui canal alfa com transparência ativa (ex: PNG recortado do Futbin)
    if img.mode == "RGBA":
        alpha = img.split()[3]
        min_alpha, max_alpha = alpha.getextrema()
        if min_alpha < 255:
            logger.info(f"A imagem {image_path.name} já possui canal de transparência (alfa mínimo: {min_alpha}). Pulando remoção de fundo para preservar qualidade.")
            return img
            
    try:
        from rembg import remove
        logger.debug("Usando rembg (IA) para remoção de fundo da foto.")
        return remove(img)
    except Exception as e:
        logger.debug(f"rembg indisponível ({e}). Iniciando fallback Chroma Key nativo com Pillow.")
        w, h = img.size
        bg_r, bg_g, bg_b, _ = img.getpixel((5, 5))
        
        pixels = img.load()
        new_pixels = []
        tolerance = 45
        
        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
                dist = ((r - bg_r)**2 + (g - bg_g)**2 + (b - bg_b)**2)**0.5
                if dist < tolerance:
                    new_pixels.append((r, g, b, 0))
                else:
                    new_pixels.append((r, g, b, a))
        
        img.putdata(new_pixels)
        
        alpha = img.split()[3]
        alpha = alpha.filter(ImageFilter.GaussianBlur(1.0))
        img.putalpha(alpha)
        return img

def draw_default_avatar() -> Image.Image:
    avatar = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(avatar)
    gray = (120, 125, 130, 255)
    
    cx, cy, cr = px(0.53), py(0.35), px(0.15)
    draw.ellipse((cx - cr, cy - cr, cx + cr, cy + cr), fill=gray)
    
    draw.polygon([
        (px(0.28), py(0.68)),
        (px(0.78), py(0.68)),
        (px(0.85), py(0.85)),
        (px(0.21), py(0.85))
    ], fill=gray)
    return avatar

def sanitize_slug(text: str) -> str:
    if not text:
        return "unknown"
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ASCII", "ignore").decode("ASCII")
    clean = re.sub(r"[^a-zA-Z0-9\s_-]", "", ascii_text)
    clean = re.sub(r"[\s_-]+", "_", clean)
    return clean.strip("_").lower()[:50]


async def ensure_asset_local(
    session: aiohttp.ClientSession,
    url: str,
    dest_path: Path
) -> Optional[str]:
    if not url:
        return None

    # Tratar URLs malformadas que contêm URLs encodadas encadeadas
    if "https://cdn2.futbin.com/https" in url:
        import urllib.parse
        encoded_part = url.replace("https://cdn2.futbin.com/", "")
        url = urllib.parse.unquote(encoded_part)

    # Corrigir múltiplos pontos de interrogação que quebram query strings
    if url.count("?") > 1:
        parts = url.split("?")
        url = parts[0] + "?" + "&".join(parts[1:])
        
    # Se for uma imagem de playstyle, remover query string para baixar na resolução original (HD)
    if "/playstyles/" in url:
        url = url.split("?")[0]
        
    if url.startswith("/images/"):
        local_target = PROJECT_ROOT / url.lstrip("/")
        if local_target.exists() and local_target.stat().st_size > 200:
            return str(local_target.resolve())
            
    if dest_path.exists() and dest_path.stat().st_size > 200:
        return str(dest_path.resolve())
        
    if "futbin.com" in url:
        clean_url = url
    else:
        clean_url = url.split("?")[0] if "?" in url else url
        
    if clean_url.startswith("//"):
        clean_url = "https:" + clean_url
        
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        data = await fetch_binary(session, clean_url)
        if data and len(data) > 200:
            async with aiofiles.open(dest_path, "wb") as f:
                await f.write(data)
            logger.debug(f"[Renderer Cache] Baixou asset com sucesso para: {dest_path.name}")
            return str(dest_path.resolve())
    except Exception as e:
        logger.error(f"[Renderer Cache] Falha ao baixar asset {clean_url}: {e}")
        
    return str(dest_path.resolve()) if dest_path.exists() else None


class CardRendererClient:
    def __init__(self):
        # Validar fontes no início
        if not BEBAS_FONT_PATH.exists() or not OSWALD_FONT_PATH.exists():
            logger.error(f"Erro crítico: Fontes não encontradas em: {FONTS_DIR}")

    async def start_service(self):
        logger.info("[Renderer] Renderizador nativo com Pillow ativado. Nenhuma inicialização de Node.js necessária.")

    async def stop_service(self):
        logger.info("[Renderer] Nenhuma finalização de Node.js necessária.")

    async def render_player(
        self,
        session: aiohttp.ClientSession,
        player_data: Dict
    ) -> Optional[Dict]:
        futbin_id = str(player_data.get("futbin_id") or player_data.get("id") or "unknown")
        name = player_data.get("name", "Unknown Player")
        name_slug = sanitize_slug(name)
        filename = f"fc_player_{futbin_id}_{name_slug}.png"
        
        # Face do jogador — diferenciada por tipo de card:
        # - Cards BASE (Gold/Silver/Bronze): face_url é a foto retrato padrão.
        #   O render_url pode conter um render especial ERRADO (ex: TOTY salvo no Gold).
        # - Cards ESPECIAIS (TOTY, POTM, UCL...): render_url é o render full-body correto.
        BASE_CARD_TYPES_RENDER = {
            "gold", "gold rare", "gold non-rare",
            "silver", "silver rare", "silver non-rare",
            "bronze", "bronze rare", "bronze non-rare",
        }
        card_type_lower = (player_data.get("card_type") or "").lower()
        is_base_card = card_type_lower in BASE_CARD_TYPES_RENDER

        # Resolução inteligente de face do jogador (escolhe a imagem de maior qualidade disponível)
        face_local = None
        face_paths = []
        for key in ["face_url", "render_url", "portrait_url"]:
            val = player_data.get(key)
            if val and val.startswith("/images/"):
                p = PROJECT_ROOT / val.lstrip("/")
                if p.exists() and p.stat().st_size > 200:
                    face_paths.append(p)
                    
        # Fallbacks em caso de falha de mapeamento de banco
        portraits_dir = IMAGES_DIR / "cards" / "portraits"
        renders_dir = IMAGES_DIR / "cards" / "renders"
        
        possible_portraits = list(portraits_dir.glob(f"portrait_{futbin_id}_*.png")) if portraits_dir.exists() else []
        for p in possible_portraits:
            face_paths.append(p)
            
        possible_renders = list(renders_dir.glob(f"render_{futbin_id}_*.png")) if renders_dir.exists() else []
        for p in possible_renders:
            face_paths.append(p)
            
        p_id = renders_dir / f"{futbin_id}.png"
        if p_id.exists():
            face_paths.append(p_id)
            
        # Filtra duplicatas e ordena por tamanho em disco (maior resolução e detalhes)
        if face_paths:
            unique_paths = list(set(p.resolve() for p in face_paths))
            unique_paths.sort(key=lambda p: p.stat().st_size, reverse=True)
            face_local = str(unique_paths[0])
            logger.debug(f"[Renderer] Face resolvida com maior qualidade: {Path(face_local).name} ({unique_paths[0].stat().st_size} bytes)")
        else:
            logger.warning(f"[Renderer] Nenhuma face/portrait encontrada para ID {futbin_id} ({card_type_lower}).")

        # Template de fundo: usa o arquivo local dyn_* gerado pelo scraper ou baixa versão HD sob demanda
        bg_local = None
        bg_url_raw = player_data.get("bg_url_raw")
        if bg_url_raw:
            bg_dyn_filename = bg_url_raw.split("/")[-1].split("?")[0]
            dyn_path = IMAGES_DIR / "cards" / "templates" / f"dyn_{bg_dyn_filename}"
            
            # Se o arquivo não existir ou for muito pequeno (ex: 64x89 pixels tem ~3KB-8KB), baixa em HD
            if not dyn_path.exists() or dyn_path.stat().st_size < 15000:
                name_slug_dashes = sanitize_slug(name).replace("_", "-")
                player_url = f"https://www.futbin.com/26/player/{futbin_id}/{name_slug_dashes}"
                if player_url:
                    logger.info(f"[Renderer] Tentando obter template HD na web para: {name} (URL: {player_url})")
                    try:
                        from bs4 import BeautifulSoup
                        from backend.services.anti_bot import fetch_html
                        html = await fetch_html(session, player_url)
                        if html:
                            soup = BeautifulSoup(html, "lxml")
                            bg_img = soup.select_one("img.playercard-26-bg")
                            if bg_img:
                                # Priorizar srcset (que contém a versão @2x / HD de 504px)
                                srcset = bg_img.get("srcset", "")
                                bg_url_hd = None
                                if srcset:
                                    urls = [u.strip().split(" ")[0] for u in srcset.split(",")]
                                    bg_url_hd = urls[-1]
                                else:
                                    bg_url_hd = bg_img.get("src", "")
                                    
                                if bg_url_hd:
                                    logger.info(f"[Renderer] Baixando template HD de: {bg_url_hd}")
                                    await ensure_asset_local(session, bg_url_hd, dyn_path)
                    except Exception as e:
                        logger.warning(f"[Renderer] Falha ao obter template HD para {name}: {e}")
            
            if dyn_path.exists() and dyn_path.stat().st_size > 200:
                bg_local = str(dyn_path.resolve())
                logger.debug(f"[Renderer] Template local encontrado: {dyn_path.name} ({dyn_path.stat().st_size} bytes)")
            else:
                logger.warning(f"[Renderer] Template não encontrado localmente: {dyn_path.name}.")

        # Bandeira da nação: caminho local
        nation_local = None
        nation_url = player_data.get("nation_flag_url") or player_data.get("nation_url")
        if nation_url and nation_url.startswith("/images/"):
            local_nation = PROJECT_ROOT / nation_url.lstrip("/")
            if local_nation.exists() and local_nation.stat().st_size > 200:
                nation_local = str(local_nation.resolve())
        nation_slug = sanitize_slug(player_data.get("nation", "unknown"))
        if not nation_local:
            nation_path_fallback = IMAGES_DIR / "cards" / "nations" / f"nation_{nation_slug}.png"
            if nation_path_fallback.exists() and nation_path_fallback.stat().st_size > 200:
                nation_local = str(nation_path_fallback.resolve())

        # Logo do clube: caminho local
        club_local = None
        club_url = player_data.get("club_logo_url") or player_data.get("club_url")
        if club_url and club_url.startswith("/images/"):
            local_club = PROJECT_ROOT / club_url.lstrip("/")
            if local_club.exists() and local_club.stat().st_size > 200:
                club_local = str(local_club.resolve())
        club_slug = sanitize_slug(player_data.get("club", "unknown"))
        if not club_local:
            club_path_fallback = IMAGES_DIR / "cards" / "clubs" / f"club_{club_slug}.png"
            if club_path_fallback.exists() and club_path_fallback.stat().st_size > 200:
                club_local = str(club_path_fallback.resolve())

        # Logo da liga: caminho local
        league_local = None
        league_url = player_data.get("league_logo_url") or player_data.get("league_url")
        if league_url and league_url.startswith("/images/"):
            local_league = PROJECT_ROOT / league_url.lstrip("/")
            if local_league.exists() and local_league.stat().st_size > 200:
                league_local = str(local_league.resolve())
        league_slug = sanitize_slug(player_data.get("league", "unknown"))
        if not league_local:
            league_path_fallback = IMAGES_DIR / "cards" / "leagues" / f"league_{league_slug}.png"
            if league_path_fallback.exists() and league_path_fallback.stat().st_size > 200:
                league_local = str(league_path_fallback.resolve())

        # Tratar Playstyles
        playstyles_input = player_data.get("playstyles") or []
        if not playstyles_input:
            import sqlite3
            db_path = PROJECT_ROOT / "database" / "help_dmes.db"
            if not db_path.exists():
                db_path = PROJECT_ROOT / "help_dmes.db"
                
            if db_path.exists():
                try:
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    
                    futbin_id = player_data.get("futbin_id") or player_data.get("id")
                    sofifa_id = player_data.get("sofifa_id")
                    p_name = player_data.get("name")
                    
                    row = None
                    if futbin_id:
                        cursor.execute("SELECT playstyles_json FROM player_cards WHERE futbin_id = ?", (str(futbin_id),))
                        row = cursor.fetchone()
                    if not row and sofifa_id:
                        cursor.execute("SELECT playstyles_json FROM player_cards WHERE sofifa_id = ?", (sofifa_id,))
                        row = cursor.fetchone()
                    if not row and p_name:
                        cursor.execute("SELECT playstyles_json FROM player_cards WHERE name LIKE ?", (f"%{p_name}%",))
                        row = cursor.fetchone()
                        
                    if not row and futbin_id:
                        cursor.execute("SELECT playstyles_json FROM fc_players WHERE futbin_id = ?", (str(futbin_id),))
                        row = cursor.fetchone()
                    if not row and p_name:
                        cursor.execute("SELECT playstyles_json FROM fc_players WHERE name LIKE ?", (f"%{p_name}%",))
                        row = cursor.fetchone()
                        
                    if row and row[0]:
                        try:
                            playstyles_input = json.loads(row[0])
                            logger.info(f"Playstyles para o jogador {name} carregados com sucesso do banco de dados SQLite.")
                        except Exception as e:
                            logger.warning(f"Erro ao deserializar playstyles_json para {name}: {e}")
                    conn.close()
                except Exception as e:
                    logger.warning(f"Erro ao acessar banco de dados SQLite para buscar playstyles de {name}: {e}")

        playstyles_payload = []
        seen_slugs = set()
        
        for idx, ps in enumerate(playstyles_input):
            ps_url = ps.get("icon_url") or ps.get("icon_path")
            if ps_url:
                ps_name = ps.get("name", f"ps_{idx}")
                is_plus = ps.get("is_plus", False) or "plus" in ps_name.lower() or "plus" in ps_url.lower()
                
                # Regra: Renderizar apenas Playstyles+ (omitir os base)
                if not is_plus:
                    continue
                    
                ps_slug = sanitize_slug(ps_name).replace("_plus", "")
                
                # Regra: Remover duplicatas
                if ps_slug in seen_slugs:
                    continue
                seen_slugs.add(ps_slug)
                
                suffix = "_plus" if is_plus else ""
                ps_path = IMAGES_DIR / "cards" / "renders" / f"playstyle_{ps_slug}{suffix}.png"
                ps_local = await ensure_asset_local(session, ps_url, ps_path)
                if ps_local:
                    playstyles_payload.append({
                        "icon_path": ps_local,
                        "is_plus": is_plus,
                        "slug": ps_slug
                    })

        # Tratar estatísticas (PAC, SHO, PAS, DRI, DEF, PHY)
        stats_input = player_data.get("stats") or []
        if not stats_input and "pace" in player_data:
            stats_input = [
                {"name": "PAC", "value": player_data.get("pace") or 0},
                {"name": "SHO", "value": player_data.get("shooting") or 0},
                {"name": "PAS", "value": player_data.get("passing") or 0},
                {"name": "DRI", "value": player_data.get("dribbling_stat") or player_data.get("dribbling") or 0},
                {"name": "DEF", "value": player_data.get("defending") or 0},
                {"name": "PHY", "value": player_data.get("physic") or player_data.get("physical") or 0},
            ]

        # Parser dinâmico de Posição Principal, Posições Alternativas e Role Plus
        raw_position = player_data.get("position", "ST")
        position_main = "ST"
        role_plus = False
        alt_positions_parsed = []
        
        if raw_position:
            if "++" in raw_position:
                role_plus = True
                parts = raw_position.split("++")
                position_main = parts[0].strip()
                if len(parts) > 1 and parts[1].strip():
                    alt_parts = [p.strip() for p in parts[1].split(",") if p.strip()]
                    alt_positions_parsed.extend(alt_parts)
            else:
                parts = [p.strip() for p in raw_position.split(",") if p.strip()]
                if parts:
                    position_main = parts[0]
                    if len(parts) > 1:
                        alt_positions_parsed.extend(parts[1:])
                        
        # Adicionar as posições alternativas originais do banco de dados se existirem
        raw_alt = player_data.get("alt_positions")
        if raw_alt:
            if isinstance(raw_alt, list):
                alt_positions_parsed.extend([str(x) for x in raw_alt])
            elif isinstance(raw_alt, str):
                alt_positions_parsed.extend([x.strip() for x in raw_alt.split(",") if x.strip()])
                
        # Limpar duplicatas e remover a posição principal das posições alternativas
        seen_alt = set()
        alt_positions_payload = []
        for pos in alt_positions_parsed:
            pos_upper = pos.upper()
            if pos_upper != position_main.upper() and pos_upper not in seen_alt:
                seen_alt.add(pos_upper)
                alt_positions_payload.append(pos_upper)

        # Perna Preferida
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

        # Fintas e WF
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

        # Montar dados estruturados para renderização
        render_data = {
            "name": name,
            "overall": player_data.get("overall") or player_data.get("rating") or 99,
            "position": position_main,
            "role_plus": role_plus,
            "card_type": player_data.get("card_type"),
            "bg_path": bg_local,
            "face_path": face_local,
            "nation_path": nation_local,
            "club_path": club_local,
            "league_path": league_local,
            "stats": stats_input,
            "playstyles": playstyles_payload,
            "alt_positions": alt_positions_payload,
            "preferred_foot": preferred_foot_payload,
            "skills_wf": skills_wf_payload
        }

        try:
            full_path, small_path = await asyncio.to_thread(
                self._draw_and_save_pillow,
                render_data,
                filename
            )
            
            res_json = {
                "success": True,
                "filename": filename,
                "full_path": str(full_path.resolve()),
                "small_path": str(small_path.resolve()),
                "card_template_url": f"/images/cards/full/{filename}",
                "card_small_url": f"/images/cards/small/{filename}",
                "render_url": f"/images/cards/renders/render_{futbin_id}_{name_slug}.png" if face_local else None,
                "nation_flag_url": f"/images/cards/nations/nation_{nation_slug}.png" if nation_local else None,
                "club_logo_url": f"/images/cards/clubs/club_{club_slug}.png" if club_local else None,
                "league_logo_url": f"/images/cards/leagues/league_{league_slug}.png" if league_local else None
            }
            logger.info(f"[Renderer] Card gerado nativamente via Pillow com sucesso para {name}.")
            return res_json
        except Exception as e:
            logger.error(f"[Renderer] Erro na renderização nativa de {name}: {e}", exc_info=True)
            return None

    def _draw_and_save_pillow(self, data: Dict, filename: str) -> Tuple[Path, Path]:
        canvas = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
        theme = get_card_theme(data.get("card_type"))
        
        # 1. Carregar Template de Fundo
        bg_loaded = False
        bg_path_str = data.get("bg_path")
        bg_img = None
        
        if bg_path_str:
            bg_path = Path(bg_path_str)
        else:
            bg_filename = theme["default_bg"]
            bg_path = IMAGES_DIR / "cards" / "templates" / bg_filename
            
        if bg_path and bg_path.exists():
            try:
                bg_img = Image.open(bg_path).convert("RGBA")
                bg_img = remove_white_corners_pillow(bg_img)
                bg_img = bg_img.resize((CARD_W, CARD_H), Image.Resampling.LANCZOS)
                canvas.paste(bg_img, (0, 0))
                bg_loaded = True
            except Exception as e:
                logger.warning(f"Erro ao abrir template {bg_filename}: {e}")
                
        if not bg_loaded:
            fallback_bg = IMAGES_DIR / "cards" / "templates" / "sbc_global_Normal_bg.png"
            if fallback_bg.exists():
                try:
                    bg_img = Image.open(fallback_bg).convert("RGBA")
                    bg_img = remove_white_corners_pillow(bg_img)
                    bg_img = bg_img.resize((CARD_W, CARD_H), Image.Resampling.LANCZOS)
                    canvas.paste(bg_img, (0, 0))
                    bg_loaded = True
                except:
                    canvas.paste(Image.new("RGBA", (CARD_W, CARD_H), (50, 50, 50, 255)), (0, 0))
            else:
                canvas.paste(Image.new("RGBA", (CARD_W, CARD_H), (50, 50, 50, 255)), (0, 0))
                
        # Detecção de cor de destaque da borda do template
        accent_color_rgb = None
        if bg_loaded and bg_img:
            accent_color_rgb = analyze_template_palette(bg_img)
                
        # 2. Carregar e Colar Foto do Jogador
        face_path_str = data.get("face_path")
        face_loaded = False
        
        if face_path_str:
            face_path = Path(face_path_str)
            if face_path.exists():
                try:
                    face_img = remove_background_photo(face_path)
                    
                    # Detecção inteligente baseada no aspect ratio (largura / altura)
                    aspect_ratio = face_img.width / face_img.height
                    if aspect_ratio <= 0.85:
                        # É um render oficial em formato de card (ex: 252x349 do Futbin)
                        # Escalar para cobrir a largura do card (756px) mantendo a proporção de aspecto
                        face_w = CARD_W
                        face_h = int(face_img.height * (CARD_W / face_img.width))
                        face_img = face_img.resize((face_w, face_h), Image.Resampling.LANCZOS)
                        # Colamos na coordenada Y=0 para alinhar perfeitamente no topo
                        canvas.alpha_composite(face_img, (0, 0))
                    else:
                        # Foto padrão: 64.28% de largura
                        face_w = int(CARD_W * 0.6428)
                        face_h = int(face_img.height * (face_w / face_img.width))
                        face_img = face_img.resize((face_w, face_h), Image.Resampling.LANCZOS)
                        face_x = int(CARD_W * 0.22)
                        face_y = int(CARD_H * 0.174)
                        canvas.alpha_composite(face_img, (face_x, face_y))
                        
                    face_loaded = True
                except Exception as e:
                    logger.error(f"Erro ao colar face do jogador: {e}")
                    
        if not face_loaded:
            default_av = draw_default_avatar()
            canvas.alpha_composite(default_av, (0, 0))
            
        draw = ImageDraw.Draw(canvas)
        
        # Cores do texto
        card_color = parse_color_rgba(theme.get("card_color"))
        rating_color = parse_color_rgba(theme.get("rating_color"))
        alt_pos_bg = parse_color_rgba(theme.get("alt_pos_bg"))
        alt_pos_border = parse_color_rgba(theme.get("alt_pos_border"))
        extra_info_bg = parse_color_rgba(theme.get("extra_info_bg"))
        extra_info_border = parse_color_rgba(theme.get("extra_info_border"))
        
        # Aplicar cores adaptativas a partir da cor de destaque detectada
        if accent_color_rgb:
            border_rgba, bg_rgba = get_adaptive_colors(accent_color_rgb)
            card_color = border_rgba
            rating_color = border_rgba
            alt_pos_bg = bg_rgba
            alt_pos_border = border_rgba
            extra_info_border = border_rgba
            
        # 3. Overall + Posição + Role (CAMADA 3)
        block_x = int(CARD_W * 0.255)  # Afastado dos playstyles como no print
        block_y = int(CARD_H * 0.175)  # Alinhamento vertical ideal
        
        font_overall = pf(2.1373)
        font_position = pf(1.0)
        font_roleplus = pf(1.0606)
        
        # Overall
        draw.text((block_x, block_y), str(data.get("overall", 99)),
                  font=font_bebas(font_overall), fill=rating_color, anchor="mt")
                  
        # Posição
        pos_y = block_y + font_overall + int(CARD_H * 0.005)
        draw.text((block_x, pos_y), str(data.get("position", "ST")).upper(),
                  font=font_oswald(font_position), fill=rating_color, anchor="mt")
                  
        # Role Plus
        if data.get("role_plus") or data.get("position_role") == "plus":
            rp_y = pos_y + font_position + int(CARD_H * 0.003)
            draw.text((block_x, rp_y), "++",
                      font=font_bebas(font_roleplus), fill=rating_color, anchor="mt")
                      
        # 4. Playstyles (CAMADA 4)
        playstyles = data.get("playstyles") or []
        if playstyles:
            icon_size = max(int(CARD_W * 0.10), 20)  # ~75 px
            icon_x = int(CARD_W * 0.04) # ~30 px
            icon_y = int(CARD_H * 0.50) # Metade do card para baixo
            gap = 8  # Gap uniforme de 8px
            
            for i, ps in enumerate(playstyles[:4]):
                ps_path_str = ps.get("icon_path")
                is_plus = ps.get("is_plus", False)
                
                if ps_path_str:
                    ps_path = Path(ps_path_str)
                    if ps_path.exists():
                        try:
                            y = icon_y + i * (icon_size + gap)
                            cx = icon_x + icon_size // 2
                            cy = y + icon_size // 2
                            r_ext = icon_size // 2
                            
                            # Lógica cromática adaptativa de fundo, borda e glifo
                            if accent_color_rgb:
                                bg_color = alt_pos_bg
                                border_color = alt_pos_border
                                glyph_color = alt_pos_border
                            else:
                                bg_color = parse_color_rgba(theme.get("playstyle_bg") or theme.get("alt_pos_bg"))
                                card_type = (data.get("card_type") or "").lower()
                                is_base_card = card_type in ["gold", "gold_rare", "silver", "bronze"]
                                if not is_base_card:
                                    border_color = (255, 255, 255, 255)
                                    glyph_color = (255, 255, 255, 255)
                                else:
                                    if "playstyle_border" in theme:
                                        border_color = parse_color_rgba(theme["playstyle_border"])
                                        glyph_color = border_color
                                    else:
                                        if is_plus:
                                            border_color = (201, 155, 80, 255)
                                            glyph_color = (201, 155, 80, 255)
                                        else:
                                            border_color = parse_color_rgba(theme.get("alt_pos_border"))
                                            glyph_color = border_color
                                       
                            normal_path_str = str(ps_path).replace("_plus.png", ".png")
                            normal_path = Path(normal_path_str)
                            glyph_img_path = normal_path if normal_path.exists() else ps_path
                            
                            # Desenhar hexágono externo (borda)
                            dy_ext = r_ext // 2
                            dx_ext = int(r_ext * 0.866)
                            pts_ext = [
                                (cx, cy - r_ext),
                                (cx + dx_ext, cy - dy_ext),
                                (cx + dx_ext, cy + dy_ext),
                                (cx, cy + r_ext),
                                (cx - dx_ext, cy + dy_ext),
                                (cx - dx_ext, cy - dy_ext)
                            ]
                            draw.polygon(pts_ext, fill=border_color)
                            
                            # Desenhar hexágono interno (fundo) - Borda com espessura de 4px
                            r_int = r_ext - 4
                            dy_int = r_int // 2
                            dx_int = int(r_int * 0.866)
                            pts_int = [
                                (cx, cy - r_int),
                                (cx + dx_int, cy - dy_int),
                                (cx + dx_int, cy + dy_int),
                                (cx, cy + r_int),
                                (cx - dx_int, cy + dy_int),
                                (cx - dx_int, cy - dy_int)
                            ]
                            draw.polygon(pts_int, fill=bg_color)
                            
                            # Processar o desenho interno: isolar o glifo com threshold suave
                            icon_img = Image.open(glyph_img_path).convert("RGBA")
                            inner_w = int(icon_size * 0.58)
                            inner_h = int(icon_img.height * (inner_w / icon_img.width))
                            icon_img = icon_img.resize((inner_w, inner_h), Image.Resampling.LANCZOS)
                            
                            r_ch, g_ch, b_ch, a_ch = icon_img.split()
                            gray = icon_img.convert("L")
                            
                            def smooth_threshold(p):
                                if p < 80:
                                    return 255
                                elif p > 180:
                                    return 0
                                else:
                                    return int(255 * (180 - p) / 100)
                                    
                            glyph_mask = gray.point(smooth_threshold)
                            glyph_alpha = ImageChops.multiply(glyph_mask, a_ch)
                            
                            glyph_r, glyph_g, glyph_b = glyph_color[:3]
                            colored_icon = Image.merge("RGBA", (
                                Image.new("L", icon_img.size, glyph_r),
                                Image.new("L", icon_img.size, glyph_g),
                                Image.new("L", icon_img.size, glyph_b),
                                glyph_alpha
                            ))
                            
                            ix = cx - inner_w // 2
                            iy = cy - inner_h // 2
                            canvas.alpha_composite(colored_icon, (ix, iy))
                        except Exception as e:
                            logger.debug(f"Erro ao colar playstyle: {e}")
                            
        # 5. Posições e Informações Extras à Direita (CAMADA 5)
        alt_positions = data.get("alt_positions") or []
        if alt_positions:
            pos_list = alt_positions[:3]
        else:
            pos_list = [data.get("position", "ST")]
            
        hex_item_w = max(int(CARD_W * 0.122) + 6, 22) # ~98 px
        hex_item_h = int(CARD_H * 0.07) # ~73 px
        hex_x = CARD_W - int(CARD_W * 0.04) - hex_item_w # ~628 px
        hex_y_start = int(CARD_H * 0.26) # ~274 px
        
        x_left = hex_x
        x_right = hex_x + hex_item_w
        x_center = hex_x + hex_item_w // 2
        h_cap = int(hex_item_w * 0.15) # ~14 px de ponta triangular
        
        # 5a — Desenhar Box Superior (Posições)
        font_alt = font_oswald(pf(0.8))
        y_end_sup = draw_integrated_hex_box(
            draw, x_center, x_left, x_right, hex_y_start, hex_item_h, h_cap,
            pos_list, font_alt, alt_pos_bg, alt_pos_border, border_width=4
        )
        
        # 5b — Desenhar Box Médio (Pé Preferido)
        foot = data.get("preferred_foot") or "R"
        foot_txt = "D" if foot == "R" else "E"
        
        y_start_mid = y_end_sup + 8 # gap de 8px
        font_foot = font_oswald(pf(0.8))
        y_end_mid = draw_integrated_hex_box(
            draw, x_center, x_left, x_right, y_start_mid, hex_item_h, h_cap,
            [foot_txt], font_foot, alt_pos_bg, alt_pos_border, border_width=4
        )
        
        # 5c — Desenhar Box Inferior (Fintas e Perna Ruim)
        skills_wf = data.get("skills_wf", "")
        skill_moves = 3
        weak_foot = 3
        if skills_wf and "-" in skills_wf:
            parts = skills_wf.split("-")
            if len(parts) >= 2:
                try:
                    skill_moves = int(parts[0]) if parts[0].isdigit() else 3
                    weak_foot = int(parts[1]) if parts[1].isdigit() else 3
                except:
                    pass
                    
        skill_item = (str(skill_moves), "star")
        wf_item = (str(weak_foot), "foot")
        skills_list = [skill_item, wf_item]
        
        y_start_inf = y_end_mid + 8 # gap de 8px
        font_skills = font_oswald(pf(0.8))
        draw_integrated_hex_box(
            draw, x_center, x_left, x_right, y_start_inf, hex_item_h, h_cap,
            skills_list, font_skills, alt_pos_bg, alt_pos_border, border_width=4
        )
                
        # 6. Nome + Atributos + Badges (CAMADA 6)
        # Coordenadas verticais calibradas e fixas no canvas de 756 x 1056 px
        zona_nome = py(0.675)
        zona_stats = py(0.765)
        zona_badges = py(0.855)
        
        # 7a — Nome
        font_name = pf(1.5)
        draw.text((CARD_W // 2, zona_nome), data.get("name", "PLAYER").upper(),
                  font=font_bebas(font_name), fill=card_color, anchor="mm")
                  
        # 7b — Atributos
        stats_list = data.get("stats") or []
        stats_dict = {s["name"].upper(): s["value"] for s in stats_list if "name" in s and "value" in s}
        stats = [
            ("PAC", stats_dict.get("PAC", 0)),
            ("SHO", stats_dict.get("SHO", 0)),
            ("PAS", stats_dict.get("PAS", 0)),
            ("DRI", stats_dict.get("DRI", 0)),
            ("DEF", stats_dict.get("DEF", 0)),
            ("PHY", stats_dict.get("PHY", 0)),
        ]
        
        font_stat_num = int(pf(1.2)) # ~50 px
        font_stat_label = int(font_stat_num * 0.77) # ~38 px
        
        n = len(stats)
        max_width = int(CARD_W * 0.78)
        col_w = max_width // n
        start_x = (CARD_W - max_width) // 2
        
        for i, (lbl, val) in enumerate(stats):
            col_cx = start_x + col_w * i + col_w // 2
            
            # Estatística com layout column-reverse usando deslocamentos precisos e âncora "mm"
            # Número acima
            draw.text((col_cx, zona_stats - int(font_stat_num * 0.45)), str(val),
                      font=font_bebas(font_stat_num), fill=card_color, anchor="mm")
            # Rótulo abaixo
            draw.text((col_cx, zona_stats + int(font_stat_num * 0.45)), lbl.upper(),
                      font=font_oswald(font_stat_label), fill=card_color, anchor="mm")
                      
        # Downscaling e Salvamento
        FULL_DIR.mkdir(parents=True, exist_ok=True)
        SMALL_DIR.mkdir(parents=True, exist_ok=True)
        
        full_path = FULL_DIR / filename
        small_path = SMALL_DIR / filename
        
        # Full (2x)
        full_card = canvas.resize((504, 698), Image.Resampling.LANCZOS)
        
        # 7c — Colar Badges com a máxima nitidez diretamente no full_card (504 x 698)
        # para evitar dupla interpolação/escala e garantir foco nítido pós-geração.
        badge_size_final = int(504 * 0.0873) # ~44 px
        badge_gap_final = int(504 * 0.02)   # ~10 px
        zona_badges_final = int(698 * 0.855) # ~596 px
        
        badge_paths = []
        for path_key in ["nation_path", "league_path", "club_path"]:
            p = data.get(path_key)
            if p and Path(p).exists():
                badge_paths.append(str(Path(p).resolve()))
                
        if badge_paths:
            total_badge_w = len(badge_paths) * badge_size_final + (len(badge_paths) - 1) * badge_gap_final
            badge_start_x = (504 - total_badge_w) // 2
            badge_y = zona_badges_final - badge_size_final // 2
            
            for j, bp in enumerate(badge_paths):
                try:
                    badge_img = Image.open(bp).convert("RGBA")
                    badge_img = badge_img.resize((badge_size_final, badge_size_final), Image.Resampling.LANCZOS)
                    bx = badge_start_x + j * (badge_size_final + badge_gap_final)
                    full_card.alpha_composite(badge_img, (bx, badge_y))
                except Exception as e:
                    logger.debug(f"Erro ao colar badge de alta qualidade no full_card: {e}")
        full_card.save(full_path, format="PNG", optimize=True)
        
        # Small (recorte inteligente)
        top_crop = full_card.crop((0, 0, 504, 302))
        bottom_crop = full_card.crop((0, 558, 504, 698))
        
        mini_canvas = Image.new("RGBA", (504, 442), (0, 0, 0, 0))
        mini_canvas.paste(top_crop, (0, 0))
        mini_canvas.paste(bottom_crop, (0, 302))
        
        small_card = mini_canvas.resize((150, 169), Image.Resampling.LANCZOS)
        small_card.save(small_path, format="PNG", optimize=True)
        
        return full_path, small_path
