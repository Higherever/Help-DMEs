#!/usr/bin/env python3
"""
================================================================================
🎨 UI COOLHUNTER - Agente Inteligente de Pesquisa Estética & Animações
================================================================================
Este script utiliza a biblioteca 'browser-use' (https://github.com/browser-use/browser-use)
para navegar autonomamente pela web (CodePen, Dribbble, GitHub, Awwwards), 
buscando animações interativas, efeitos visuais premium (Wow Factor) e códigos-fonte
para inspirar e enriquecer a interface do ecossistema Help DMEs.

Desenvolvido para o ambiente Socorro DMEs.
================================================================================
"""

import os
import sys
import asyncio
import argparse
from datetime import datetime

# Cores para saída amigável no terminal
class Cores:
    VERDE = '\033[92m'
    AMARELO = '\033[93m'
    AZUL = '\033[94m'
    MAGENTA = '\033[95m'
    VERMELHO = '\033[91m'
    RESET = '\033[0m'
    NEGRITO = '\033[1m'

def verificar_dependencias():
    """Verifica se os pacotes necessários estão instalados e instrui o usuário se faltarem."""
    dependencias_faltando = []
    
    try:
        import browser_use
    except ImportError:
        dependencias_faltando.append("browser-use")
        
    try:
        import langchain_google_genai
    except ImportError:
        try:
            import langchain_openai
        except ImportError:
            dependencias_faltando.append("langchain-google-genai (ou langchain-openai)")

    if dependencias_faltando:
        print(f"\n{Cores.VERMELHO}{Cores.NEGRITO}⚠️  Erro: Dependências ausentes no ambiente!{Cores.RESET}")
        print(f"Para executar o UI Coolhunter, por favor instale as dependências executando:")
        print(f"\n  {Cores.AZUL}pip install browser-use langchain-google-genai playwrite{Cores.RESET}")
        print(f"  {Cores.AZUL}playwright install{Cores.RESET}\n")
        print("Certifique-se de executar esses comandos com o seu ambiente virtual (.venv) ativo.")
        sys.exit(1)

async def executar_pesquisa(prompt_busca, engine, limite_passos):
    """Executa o agente browser-use para pesquisar na web e trazer inspirações."""
    # Importações dinâmicas após validação para evitar quebra de import global
    from browser_use import Agent
    
    print(f"\n{Cores.AZUL}🚀 Inicializando Agente de Pesquisa Estética...{Cores.RESET}")
    print(f"🎯 {Cores.NEGRITO}Objetivo:{Cores.RESET} {prompt_busca}")
    
    # 1. Configurando o Modelo de Linguagem (LLM)
    llm = None
    if engine == "gemini":
        if not os.environ.get("GEMINI_API_KEY"):
            print(f"\n{Cores.VERMELHO}❌ Erro: Variável de ambiente GEMINI_API_KEY não definida!{Cores.RESET}")
            print("Configure a sua chave do Gemini antes de rodar:")
            print(f"  {Cores.AMARELO}export GEMINI_API_KEY='sua_chave_aqui'{Cores.RESET}")
            sys.exit(1)
            
        from langchain_google_genai import ChatGoogleGenerativeAI
        print(f"🧠 Usando Modelo: {Cores.VERDE}Gemini (Google){Cores.RESET}")
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
        
    elif engine == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            print(f"\n{Cores.VERMELHO}❌ Erro: Variável de ambiente OPENAI_API_KEY não definida!{Cores.RESET}")
            print("Configure a sua chave da OpenAI antes de rodar:")
            print(f"  {Cores.AMARELO}export OPENAI_API_KEY='sua_chave_aqui'{Cores.RESET}")
            sys.exit(1)
            
        from langchain_openai import ChatOpenAI
        print(f"🧠 Usando Modelo: {Cores.VERDE}GPT-4o (OpenAI){Cores.RESET}")
        llm = ChatOpenAI(model="gpt-4o-mini")

    # 2. Construindo a instrução estrita de pesquisa para o browser-use
    instrucao_completa = (
        f"Você é o UI Coolhunter, um agente de pesquisa estética de altíssimo nível. "
        f"Seu objetivo é navegar na web para buscar inspiração de design premium e códigos de animação para o projeto Help DMEs. "
        f"INSTRUÇÃO DE BUSCA: {prompt_busca}. "
        f"Visite sites como codepen.io, dribbble.com ou repositórios do GitHub que correspondam ao termo. "
        f"Quando encontrar uma animação ou conceito visual excelente, faça o seguinte: "
        f"1. Extraia a URL direta da demonstração ou do repositório. "
        f"2. Extraia o trecho de código principal (HTML/CSS/JS) se estiver disponível (especialmente em CodePens ou gists do GitHub). "
        f"3. Descreva os aspectos de design que tornam essa animação premium (ex: transições, física, sombras, cores). "
        f"4. Retorne um relatório markdown muito detalhado no final da sua execução."
    )

    # 3. Inicializando e executando o agente browser-use
    agent = Agent(
        task=instrucao_completa,
        llm=llm,
    )
    
    print(f"🌐 Navegador em execução via Playwright. O agente irá operar de forma autônoma.")
    print(f"⏳ Processando passos (limite configurado: {limite_passos} ações)... Aguarde.")
    
    try:
        resultado = await agent.run(max_steps=limite_passos)
        return resultado
    except Exception as e:
        print(f"\n{Cores.VERMELHO}❌ Ocorreu um erro durante a navegação do agente: {e}{Cores.RESET}")
        sys.exit(1)

def salvar_nota_obsidian(prompt, relatorio_conteudo):
    """Salva a inspiração encontrada como uma nova Nota de Inteligência no Obsidian."""
    diretorio_obsidian = "/home/gambeta/Documentos/Socorro DMEs/DMEs"
    if not os.path.exists(diretorio_obsidian):
        # Fallback local se o caminho não for encontrado
        diretorio_obsidian = "./DMEs"
        os.makedirs(diretorio_obsidian, exist_ok=True)
        
    data_str = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Criar um título amigável de arquivo
    titulo_limpo = prompt.replace(" ", "_").replace("/", "_").replace("\\", "_")
    titulo_limpo = "".join([c for c in titulo_limpo if c.isalnum() or c in ("_", "-")])[:40]
    nome_arquivo = f"Inteligência - Inspiração UI - {titulo_limpo}_{timestamp}.md"
    caminho_completo = os.path.join(diretorio_obsidian, nome_arquivo)
    
    # Cabeçalho Frontmatter do Obsidian
    conteudo_nota = f"""---
titulo: Inspiração UI - {prompt}
data: {data_str}
tags: [inspiracao, design, frontend, browser-use, animacao, help-dmes]
---

# 🎨 Inspiração de UI & Animação: {prompt}

> **Nota gerada pelo Agente Automático UI Coolhunter** com suporte do *browser-use*.
> **Data de Captura:** {data_str}
> **Objetivo de Busca:** *{prompt}*

---

## 🔬 Relatório da Pesquisa e Códigos Coletados

{relatorio_conteudo}

---

## 🔗 Sinapses (Conexões)
- **MOC Central de Inteligências:** [[🧠 MOC - Cérebro de Inteligências]]
- **Estudos Estéticos:** [[Inteligencia - Estudo de UX, Layout e Animacoes SBC]] | [[Inteligência - Barra Lateral Elástica SVG com Física de Mola (Blob Sidebar)]] | [[Inteligência - Janela de Pesquisa Gooey Search e Efeitos de Transição Líquida]]
- **Configuração da Skill:** [[Skill - UI Coolhunter com Browser-Use]]

"""
    
    with open(caminho_completo, "w", encoding="utf-8") as f:
        f.write(conteudo_nota)
        
    print(f"\n{Cores.VERDE}{Cores.NEGRITO}✅ Inteligência registrada no Obsidian!{Cores.RESET}")
    print(f"📄 Arquivo criado em: {Cores.AZUL}{caminho_completo}{Cores.RESET}")
    print(f"🔗 Nota linkada ao seu segundo cérebro do Obsidian. Atualize o seu Graph View!")

def main():
    parser = argparse.ArgumentParser(
        description="UI Coolhunter - Buscador Autônomo de Referências de Animação e Design Premium para o Help DMEs.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "busca",
        type=str,
        help="O que o agente deve buscar (ex: 'efeito holográfico de cartas 3D css')"
    )
    parser.add_argument(
        "--engine",
        choices=["gemini", "openai"],
        default="gemini",
        help="Qual LLM utilizar para conduzir a navegação (padrão: gemini)"
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=15,
        help="Limite máximo de ações/cliques que o agente pode realizar (padrão: 15)"
    )
    parser.add_argument(
        "--verificar",
        action="store_true",
        help="Apenas valida se as dependências do browser-use estão instaladas"
    )

    args = parser.parse_args()

    if args.verificar:
        verificar_dependencias()
        print(f"{Cores.VERDE}✓ Todas as dependências básicas estão presentes no ambiente!{Cores.RESET}")
        sys.exit(0)

    # Executa a checagem das dependências antes de iniciar
    verificar_dependencias()

    # Loop de eventos assíncrono para rodar o browser-use
    loop = asyncio.get_event_loop()
    resultado_agente = loop.run_until_complete(
        executar_pesquisa(args.busca, args.engine, args.steps)
    )

    # Processamento do relatório gerado
    if resultado_agente:
        # Extrai o relatório de texto das ações ou histórico do agente
        # O browser-use retorna um histórico onde a última resposta contém o resultado
        relatorio_texto = ""
        try:
            # Tenta pegar a mensagem final de conclusão do agente
            relatorio_texto = resultado_agente.final_result()
        except AttributeError:
            relatorio_texto = str(resultado_agente)
            
        salvar_nota_obsidian(args.busca, relatorio_texto)
    else:
        print(f"\n{Cores.AMARELO}⚠️  Nenhum relatório foi retornado pelo agente de automação.{Cores.RESET}")

if __name__ == "__main__":
    main()
