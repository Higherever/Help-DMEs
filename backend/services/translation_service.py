"""
Help DMEs — Serviço de Tradução
===============================
Mecanismo inteligente de tradução híbrida (dicionário FIFA/EA FC + API de Tradução)
para garantir traduções de altíssima fidelidade e sem erros para o Português do Brasil (PT-BR).
"""

import logging
import re
import json
from pathlib import Path
from typing import Dict, Optional
from deep_translator import GoogleTranslator

logger = logging.getLogger("help_dmes.translation")

# Caminho para o cache persistente de traduções
CACHE_FILE = Path(__file__).parent.parent / "translation_cache.json"

# ══════════════════════════════════════════════
# Dicionário Estático FIFA / EA FC (Fidelidade Absoluta)
# ══════════════════════════════════════════════
FIFA_DICTIONARY: Dict[str, str] = {
    # Categorias e Estruturas de SBCs
    "Intro to SBCs": "Introdução aos DMEs",
    "Intro to Player SBCs": "Introdução a DMEs de Jogadores",
    "Intro to Challenge SBCs": "Introdução a DMEs de Desafios",
    "Intro to Upgrade SBCs": "Introdução a DMEs de Melhorias",
    "Foundations": "Fundamentos",
    "Upgrades": "Melhorias",
    "Challenges": "Desafios",
    "Players": "Jogadores",
    "Icons": "Ídolos",
    "Swaps": "Trocas",

    # Termos Técnicos Gerais
    "Squad Rating": "Classificação do Elenco",
    "Team Rating": "Classificação do Time",
    "Team Chemistry": "Entrosamento do Time",
    "Squad Chemistry": "Entrosamento do Elenco",
    "Chemistry": "Entrosamento",
    "Min": "Mín.",
    "Max": "Máx.",
    "Exactly": "Exatamente",
    "Overall": "Geral",
    "Position": "Posição",
    "Positions": "Posições",
    "Rating": "Classificação",
    "Quality": "Qualidade",
    "Rarity": "Raridade",
    "Any": "Qualquer",
    "Rare": "Raro",
    "Common": "Comum",
    "Gold": "Ouro",
    "Silver": "Prata",
    "Bronze": "Bronze",
    "Untradeable": "Intransferível",
    "Tradeable": "Negociável",
    "Loan": "Empréstimo",
    "Duplicate": "Duplicado",
    "Active 11": "Time Titular",
    "Exchanged": "Trocado",

    # Requisitos do Sistema
    "team_rating": "Classificação do Elenco",
    "players_from_league": "Jogadores de uma liga específica",
    "players_from_nation": "Jogadores de uma nacionalidade",
    "players_from_club": "Jogadores de um clube",
    "players_same_nation": "Jogadores da mesma nacionalidade",
    "players_same_league": "Jogadores da mesma liga",
    "players_same_club": "Jogadores do mesmo clube",
    "leagues_in_squad": "Ligas no elenco",
    "nations_in_squad": "Nacionalidades no elenco",
    "clubs_in_squad": "Clubes no elenco",
    "player_quality": "Qualidade do jogador",
    "player_rarity": "Raridade do jogador",
    "player_type": "Tipo do jogador",
    "squad_chemistry": "Entrosamento do time",
    "player_count": "Número de jogadores",
    "other": "Outros",

    # Pacotes / Recompensas Específicas
    "Two Rare Gold Players Pack": "Pacote de Dois Jogadores de Ouro Raros",
    "Rare Gold Players Pack": "Pacote de Jogadores de Ouro Raros",
    "Gold Players Pack": "Pacote de Jogadores de Ouro",
    "Premium Gold Pack": "Pacote de Ouro Premium",
    "Rare Gold Pack": "Pacote de Ouro Raro",
    "Gold Pack": "Pacote de Ouro",
    "Mega Pack": "Mega Pacote",
    "Rare Mega Pack": "Mega Pacote Raro",
    "Jumbo Rare Players Pack": "Pacote Jumbo de Jogadores Raros",
    "Rare Players Pack": "Pacote de Jogadores Raros",
    "Jumbo Premium Gold Pack": "Pacote Jumbo de Ouro Premium",
    "Jumbo Premium Silver Pack": "Pacote Jumbo de Prata Premium",
    "Prime Gold Players Pack": "Pacote Prime de Jogadores de Ouro",
    "Small Prime Gold Players Pack": "Pequeno Pacote Prime de Jogadores de Ouro",
    "Small Rare Gold Players Pack": "Pequeno Pacote de Jogadores de Ouro Raros",
    "Premium Gold Players Pack": "Pacote de Jogadores de Ouro Premium",
    "Ultimate Pack": "Pacote Ultimate",
    "Electrum Players Pack": "Pacote de Jogadores Electrum",
    "Rare Electrum Players Pack": "Pacote Raro de Jogadores Electrum",
    "Prime Electrum Players Pack": "Pacote Prime de Jogadores Electrum",
    "Premium Electrum Players Pack": "Pacote Premium de Jogadores Electrum",
    "Silver Players Pack": "Pacote de Jogadores de Prata",
    "Rare Silver Pack": "Pacote de Prata Raro",
    "Premium Silver Pack": "Pacote de Prata Premium",
    "Silver Pack": "Pacote de Prata",
    "Bronze Players Pack": "Pacote de Jogadores de Bronze",
    "Rare Bronze Pack": "Pacote de Bronze Raro",
    "Premium Bronze Pack": "Pacote de Bronze Premium",
    "Bronze Pack": "Pacote de Bronze",
    "Jumbo Premium Bronze Pack": "Pacote Jumbo de Bronze Premium",

    # Picks e Melhorias Específicas
    "Gold Upgrade": "Melhoria de Ouro",
    "Silver Upgrade": "Melhoria de Prata",
    "Bronze Upgrade": "Melhoria de Bronze",
    "Daily Gold Upgrade": "Melhoria de Ouro Diária",
    "83+ Double Upgrade": "Melhoria Dupla 83+",
    "84+ Double Upgrade": "Melhoria Dupla 84+",
    "85+ Double Upgrade": "Melhoria Dupla 85+",
    "82+ Player Pick": "Escolha de Jogador 82+",
    "83+ Player Pick": "Escolha de Jogador 83+",
    "84+ Player Pick": "Escolha de Jogador 84+",
    "85+ Player Pick": "Escolha de Jogador 85+",
    "81+ Player Pick": "Escolha de Jogador 81+",
    "Player Pick": "Escolha de Jogador",
    "Campaign Mix Upgrade": "Melhoria Mista de Campanha",
    "Top Form": "Em boa fase",
    "80-Rated Squad": "Elenco com classificação 80",
    "81-Rated Squad": "Elenco com classificação 81",
    "82-Rated Squad": "Elenco com classificação 82",
    "83-Rated Squad": "Elenco com classificação 83",
    "84-Rated Squad": "Elenco com classificação 84",
    "85-Rated Squad": "Elenco com classificação 85",
    "86-Rated Squad": "Elenco com classificação 86",
    "87-Rated Squad": "Elenco com classificação 87",
    "88-Rated Squad": "Elenco com classificação 88",
    "89-Rated Squad": "Elenco com classificação 89",
    "90-Rated Squad": "Elenco com classificação 90",
    "91-Rated Squad": "Elenco com classificação 91",
    "92-Rated Squad": "Elenco com classificação 92",
    "TOTS Crafting Upgrade": "Melhoria de Criação do TOTS",
    "TOTS Daily Login Upgrade": "Melhoria de Login Diário do TOTS",
    "Daily Login Upgrade": "Melhoria de Login Diário",
    "84+ TOTW Upgrade": "Melhoria do TOTW 84+",
    "83+ TOTW Upgrade": "Melhoria do TOTW 83+",
    "TOTW Upgrade": "Melhoria do TOTW",
    "EFL Championship": "EFL Championship",
    "Ligue 1": "Ligue 1",
    "Serie A": "Serie A",
    "LALIGA EA SPORTS": "LALIGA EA SPORTS",
    "LALIGA": "LALIGA",
    "Bundesliga": "Bundesliga",
    "Eredivisie": "Eredivisie",
    "Liga Portugal": "Liga Portugal",
    "Major League Soccer": "MLS",
    "ROSHN Saudi League": "ROSHN Saudi League",
    "Süper Lig": "Süper Lig",
    "Room to Grow": "Espaço para crescer",
    "Build Up Play": "Construa o jogo",
    "Let's Keep Going": "Vamos em frente",
    "Moving On Up": "Subindo de nível",
    "First Steps": "Primeiros passos",
    "The Vuvuzelas": "As Vuvuzelas",
    "This is Africa!": "Esta é a África!",
    "Soccer City": "Cidade do Futebol",
    "Bafana Bafana's Dream: South Africa '10": "O sonho do Bafana Bafana: África do Sul '10",
    "Lennart Karl": "Lennart Karl",
    "Victor Osimhen": "Victor Osimhen",
    "Khvicha Kvaratskhelia": "Khvicha Kvaratskhelia",
    "Alper Yılmaz": "Alper Yılmaz",
    "Blaise Matuidi": "Blaise Matuidi",
}


# Classe principal para gerenciar traduções com cache e resiliência
class TranslationService:
    def __init__(self):
        self.cache: Dict[str, str] = {}
        self.translator = GoogleTranslator(source="en", target="pt")
        self._load_cache()

    def _load_cache(self):
        """Carrega o cache persistente do disco."""
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
                logger.info(f"Cache de tradução carregado: {len(self.cache)} registros.")
            except Exception as e:
                logger.warning(f"Falha ao carregar cache de tradução: {e}")

    def _save_cache(self):
        """Salva o cache persistente no disco."""
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Falha ao salvar cache de tradução: {e}")

    def translate(self, text: Optional[str]) -> str:
        """
        Traduz o texto de inglês para português do Brasil de forma assíncrona/síncrona robusta.
        Se text estiver vazio, retorna string vazia.
        """
        if not text:
            return ""

        text_str = str(text).strip()
        if not text_str:
            return ""

        # 1. Verificar dicionário exato de FIFA/EA FC
        if text_str in FIFA_DICTIONARY:
            return FIFA_DICTIONARY[text_str]

        # Verificar dicionário com case-insensitive
        text_lower = text_str.lower()
        for en_term, pt_term in FIFA_DICTIONARY.items():
            if en_term.lower() == text_lower:
                return pt_term

        # 2. Verificar cache em memória/disco
        if text_str in self.cache:
            return self.cache[text_str]

        # 3. Aplicar Regex inteligentes para padrões comuns antes de bater na API
        translated_pattern = self._translate_patterns(text_str)
        if translated_pattern:
            self.cache[text_str] = translated_pattern
            self._save_cache()
            return translated_pattern

        # 4. Traduzir via API Google Translate (com tratamento de exceção estrito)
        try:
            translated = self.translator.translate(text_str)
            if translated:
                # Pós-processar tradução para garantir consistência de termos técnicos do EA FC
                translated = self._post_process_translation(translated)
                self.cache[text_str] = translated
                self._save_cache()
                return translated
        except Exception as e:
            logger.warning(f"Erro na API de Tradução para '{text_str}': {e}. Usando fallbacks...")

        # 5. Fallback local: fazer substituição parcial de termos conhecidos
        fallback_translated = self._local_fallback_translate(text_str)
        return fallback_translated

    def _translate_patterns(self, text: str) -> Optional[str]:
        """Aplica expressões regulares para traduzir padrões numéricos e técnicos recorrentes do EA FC."""
        # Ex: "87-Rated Squad" ou "87 Rated Squad" -> "Elenco com classificação 87"
        m = re.match(r"(\d+)-?Rated\s+Squad", text, re.IGNORECASE)
        if m:
            rating = m.group(1)
            return f"Elenco com classificação {rating}"

        # Ex: "Squad Rated 87" -> "Elenco com classificação 87"
        m = re.match(r"Squad\s+Rated\s+(\d+)", text, re.IGNORECASE)
        if m:
            rating = m.group(1)
            return f"Elenco com classificação {rating}"

        # Ex: "1 of 4 ..." -> "1 de 4 ..."
        m = re.match(r"1\s+of\s+(\d+)\s+(.+)", text, re.IGNORECASE)
        if m:
            count = m.group(1)
            rest = m.group(2)
            # Traduzir o restante de forma recursiva ou substituição
            translated_rest = self._local_fallback_translate(rest)
            return f"1 de {count} {translated_rest}"

        # Ex: "Expires in 3 days" -> "Expira em 3 dias"
        m = re.match(r"Expires in (\d+) days?", text, re.IGNORECASE)
        if m:
            days = m.group(1)
            return f"Expira em {days} dias"
        
        m = re.match(r"Expires in (\d+) hours?", text, re.IGNORECASE)
        if m:
            hours = m.group(1)
            return f"Expira em {hours} horas"

        # Ex: "Complete these OVR-based challenges to earn rewards."
        if "complete these ovr-based challenges" in text.lower():
            return "Complete estes desafios baseados em GER para ganhar recompensas."

        # Ex: "Complete these Player-based challenges to earn rewards."
        if "complete these player-based challenges" in text.lower():
            return "Complete estes desafios baseados em jogadores para ganhar recompensas."

        # Ex: "Complete these Puzzle-based challenges to earn rewards."
        if "complete these puzzle-based challenges" in text.lower():
            return "Complete estes desafios baseados em quebra-cabeças para ganhar recompensas."

        # Ex: "Complete these Upgrade-based challenges to earn rewards."
        if "complete these upgrade-based challenges" in text.lower():
            return "Complete estes desafios baseados em melhorias para ganhar recompensas."

        # Ex: "Min. 1 Players from: Premier League"
        m = re.match(r"Min\.\s*(\d+)\s*Players\s*from:\s*(.+)", text, re.IGNORECASE)
        if m:
            return f"Mín. {m.group(1)} jogadores de: {self._translate_league_nation(m.group(2))}"

        # Ex: "Max. 1 Players from: Premier League"
        m = re.match(r"Max\.\s*(\d+)\s*Players\s*from:\s*(.+)", text, re.IGNORECASE)
        if m:
            return f"Máx. {m.group(1)} jogadores de: {self._translate_league_nation(m.group(2))}"

        # Ex: "Any TOTW or TOTS"
        if text.lower() == "any totw or tots":
            return "Qualquer TOTW ou TOTS"

        # Ex: "exchange a squad" (comumente em descrições de challenges)
        # "Exchange a squad featuring players from..."
        if "exchange a squad" in text.lower():
            # Tradução literal de futebol comum: "Envie um elenco..."
            text_translated = text.replace("Exchange a squad", "Envie um elenco")
            text_translated = text_translated.replace("exchange a squad", "envie um elenco")
            text_translated = text_translated.replace("featuring players from", "com jogadores de")
            text_translated = text_translated.replace("featuring", "com")
            text_translated = text_translated.replace("to earn a", "para ganhar um")
            text_translated = text_translated.replace("to earn", "para ganhar")
            text_translated = text_translated.replace("players", "jogadores")
            text_translated = text_translated.replace("player", "jogador")
            # Traduzir ligas/nacionalidades conhecidas que sobram
            return self._local_fallback_translate(text_translated)

        return None

    def _translate_league_nation(self, text: str) -> str:
        """Traduz ligas ou nacionalidades no texto de forma dinâmica usando limites de palavras."""
        # Nomes de países em EN para PT
        nations = {
            "Spain": "Espanha", "Brazil": "Brasil", "France": "França",
            "Germany": "Alemanha", "England": "Inglaterra", "Italy": "Itália",
            "Argentina": "Argentina", "Portugal": "Portugal", "Netherlands": "Holanda",
            "Belgium": "Bélgica", "Uruguay": "Uruguai", "Colombia": "Colômbia",
            "Sweden": "Suécia", "Norway": "Noruega", "Denmark": "Dinamarca",
            "Poland": "Polônia", "Mexico": "México", "USA": "EUA",
            "United States": "Estados Unidos", "Croatia": "Croácia", "Morocco": "Marrocos",
            "Senegal": "Senegal", "Japan": "Japão", "Korea Republic": "Coreia do Sul",
        }
        translated = text
        for en_n, pt_n in nations.items():
            translated = re.sub(r"\b" + re.escape(en_n) + r"\b", pt_n, translated, flags=re.IGNORECASE)
        return translated

    def _post_process_translation(self, text: str) -> str:
        """Corrige desvios e erros da tradução genérica da API para termos FIFA/EA FC."""
        # Ex: "Pacote de dois jogadores de ouro raro" -> "Pacote de Dois Jogadores de Ouro Raros"
        corrected = text
        
        # Correções de substantivos e termos de pacotes
        replacements = {
            "Pacote de Jogadores Ouro": "Pacote de Jogadores de Ouro",
            "Pacote de Ouro Raros": "Pacote de Ouro Raro",
            "Pacote de ouro raro": "Pacote de Ouro Raro",
            "Pacote de dois jogadores": "Pacote de Dois Jogadores",
            "Pacote de ouro premium": "Pacote de Ouro Premium",
            "Pacote Ouro Premium": "Pacote de Ouro Premium",
            "Pacote de ouro": "Pacote de Ouro",
            "Escolha do jogador": "Escolha de Jogador",
            "Escolha do Jogador": "Escolha de Jogador",
            "Escolha de jogador": "Escolha de Jogador",
            "Desafio de Montagem de Elenco": "Desafio de Montagem de Elenco (DME)",
            "Classificação do time": "Classificação do Elenco",
            "Classificação do Time": "Classificação do Elenco",
            "Química do time": "Entrosamento do Elenco",
            "Química do Time": "Entrosamento do Elenco",
            "Química": "Entrosamento",
            "Melhoria de Ouro Diário": "Melhoria de Ouro Diária",
            "Melhoria do ouro": "Melhoria de Ouro",
            "Melhoria de ouro": "Melhoria de Ouro",
            "Melhoria de prata": "Melhoria de Prata",
            "Melhoria de bronze": "Melhoria de Bronze",
            "Troca de": "Troca de",
            "Ícone": "Ídolo",
            "Ícones": "Ídolos",
        }
        
        for en_t, pt_t in replacements.items():
            # Substituição insensível a maiúsculas/minúsculas, mas preservando o padrão correto
            corrected = re.sub(re.escape(en_t), pt_t, corrected, flags=re.IGNORECASE)

        # Corrigir traduções errôneas da API do Google para termos de classificação "85+"
        # Ex: "com mais de 85 anos" -> "85+"
        corrected = re.sub(r"com mais de (\d+) anos(?: de idade)?", r"\1+", corrected, flags=re.IGNORECASE)
        corrected = re.sub(r"com mais de (\d+) anos", r"\1+", corrected, flags=re.IGNORECASE)
        corrected = re.sub(r"mais de (\d+) anos", r"\1+", corrected, flags=re.IGNORECASE)
        corrected = re.sub(r"com mais de (\d+) de classificação", r"\1+", corrected, flags=re.IGNORECASE)
        
        # Correção do nome da Eredivisie
        corrected = corrected.replace("Eredivisia", "Eredivisie")
        corrected = corrected.replace("eredivisia", "Eredivisie")

        return corrected

    def _local_fallback_translate(self, text: str) -> str:
        """Fallback local rápido por substituição de palavras chaves do EA FC."""
        translated = text
        # Substituições simples ordenadas por complexidade
        for en_term, pt_term in sorted(FIFA_DICTIONARY.items(), key=lambda x: len(x[0]), reverse=True):
            if len(en_term) > 3: # Evita substituir letras isoladas
                translated = re.sub(re.escape(en_term), pt_term, translated, flags=re.IGNORECASE)
        
        # Traduzir nacionalidades comuns
        translated = self._translate_league_nation(translated)
        return translated


# Instância global single-source of truth para o projeto
translator = TranslationService()
