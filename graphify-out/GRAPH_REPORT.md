# Graph Report - Socorro DMEs  (2026-05-08)

## Corpus Check
- 62 files · ~138,296 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 448 nodes · 584 edges · 34 communities (26 shown, 8 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 91 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2d5f2133`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]

## God Nodes (most connected - your core abstractions)
1. `parse_requirement_text()` - 13 edges
2. `Base` - 13 edges
3. `calculate_optimal_path()` - 11 edges
4. `AppSetting` - 11 edges
5. `useApi()` - 11 edges
6. `_process_sbc()` - 10 edges
7. `_sbc_to_detail_response()` - 9 edges
8. `analyze_sbc()` - 8 edges
9. `scrape_all_sbcs_futnext()` - 8 edges
10. `SBCSet` - 8 edges

## Surprising Connections (you probably didn't know these)
- `App()` --calls--> `useApi()`  [INFERRED]
  Prote-o/app/src/App.tsx → frontend/src/hooks/useApi.js
- `Wrapper que mede a velocidade, executa a função e notifica via WebSocket.` --rationale_for--> `import_squad()`  [EXTRACTED]
  Prote-o/app/backend/main.py → backend/main.py
- `import_squad()` --calls--> `SquadImportResponse`  [INFERRED]
  backend/main.py → backend/schemas/schemas.py
- `squad_stats()` --calls--> `SquadStatsResponse`  [INFERRED]
  backend/main.py → backend/schemas/schemas.py
- `start_scraping()` --calls--> `ScrapeStartResponse`  [INFERRED]
  backend/main.py → backend/schemas/schemas.py

## Communities (34 total, 8 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (41): Help DMEs — Seed Data ====================== Dados iniciais populados automatica, Popula dados iniciais no banco (idempotente).     Só insere registros que ainda, seed_initial_data(), DeclarativeBase, Base, ChallengeRequirement, PlayerCard, PositionMapping (+33 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (40): Converte SBCSet ORM → schema Pydantic detalhado., _sbc_to_detail_response(), BaseModel, AnalysisResponse, AppSettingUpdateRequest, BulkExcludeRequest, CalculatePathResponse, ChallengeRequirementResponse (+32 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (36): analyze_sbc(), bulk_exclude_players(), bulk_include_players(), calculate_optimal_path(), get_sbc_detail(), health_check(), list_sbcs(), list_scrape_sources() (+28 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (36): api_cancelar(), api_executar(), api_velocidade(), ComandoExecutar, _executar_e_notificar(), handle_sigterm(), health(), import_squad() (+28 more)

### Community 4 - "Community 4"
Cohesion: 0.07
Nodes (18): Loading26Props, OPCOES, OptionsProps, iconeStatus, PackageListProps, Progress(), ProgressProps, Status (+10 more)

### Community 5 - "Community 5"
Cohesion: 0.08
Nodes (21): AppSetting, Configurações globais do sistema.     Persistidas em banco para sobreviver reini, get_all_settings(), get_setting(), get_setting_bool(), Help DMEs — Settings Service ============================== CRUD de configuraçõe, Retorna todas as configurações do sistema., Busca uma configuração pela chave. Retorna None se não existir. (+13 more)

### Community 6 - "Community 6"
Cohesion: 0.11
Nodes (9): useApi(), HERO_IMAGES, NAV_ITEMS, CalculatorPage(), SbcsPage(), SettingsPage(), SquadPage(), tdStyle (+1 more)

### Community 7 - "Community 7"
Cohesion: 0.11
Nodes (23): Inicia o scraping em background. Fonte: fut.gg (padrão) ou futnext., Status atual do scraping., Executa scraping em background com fallback., Executa scraping FutNext em background., _run_futnext_background(), _run_scraping_background(), scrape_status(), start_scraping() (+15 more)

### Community 8 - "Community 8"
Cohesion: 0.1
Nodes (18): _coletar_info_sistema(), configurar_logs(), _get_cmd_output(), _limpar_logs_antigos(), Sistema de Logging Acumulativo — Proteção GUI  Regras:   - Cada abertura do prog, Garante que o diretório tenha no máximo MAX_LOGS arquivos com o prefixo dado., Configura o sistema de logs acumulativos.     Logs são salvos em: Prote-o/logs/l, Invoca um comando de sistema e retorna sua saída limpa. (+10 more)

### Community 9 - "Community 9"
Cohesion: 0.1
Nodes (23): bulk_exclude(), bulk_include(), exclude_player(), get_available_for_sbc(), get_squad(), get_squad_stats(), import_csv(), _parse_bool() (+15 more)

### Community 10 - "Community 10"
Cohesion: 0.12
Nodes (21): test_scraper(), create_stealth_context(), normalize_category(), parse_cost_text(), parse_expiry_text(), parse_requirement_text(), Limpa strings de preço e converte para inteiro.     Ex: "10,000" -> 10000, Normaliza textos de expiração (ex: "7 days", "23 hours"). (+13 more)

### Community 11 - "Community 11"
Cohesion: 0.14
Nodes (21): analyze_sbc(), calculate_optimal_path(), _estimate_card_cost(), estimate_cost(), _get_sbc_with_relations(), _load_position_mappings(), _load_rarity_mappings(), _meets_requirement() (+13 more)

### Community 12 - "Community 12"
Cohesion: 0.17
Nodes (11): Added, Added, Added, Changed, CHANGELOG, Fixed, Notes, Removed (+3 more)

### Community 13 - "Community 13"
Cohesion: 0.2
Nodes (9): lifespan(), Inicializa o banco de dados ao iniciar a aplicação., drop_db(), get_session_dependency(), init_db(), Help DMEs — Database Engine & Session ======================================= SQ, Dependency injection para FastAPI endpoints., Inicializa o banco:       1. Cria diretório database/       2. Cria tabelas (CRE (+1 more)

### Community 14 - "Community 14"
Cohesion: 0.2
Nodes (9): code:mermaid (graph TD), code:bash (git clone https://github.com/Higherever/Prote-o.git && cd Pr), 🚀 Comece em Segundos, 🌟 Por que usar o Proteção?, 🛡️ Proteção Completa — CachyOS (Gaming Safe), 🗺️ Seu Mapa de Proteção (Como Funciona?), Sinta-se em casa, sinta-se seguro.🎮, 📊 Transparência Total (Logs) (+1 more)

### Community 15 - "Community 15"
Cohesion: 0.5
Nodes (3): Help DMEs — Fixtures de Teste ================================ Banco SQLite em m, Cria sessão de teste com banco SQLite em memória., test_session()

### Community 16 - "Community 16"
Cohesion: 0.5
Nodes (3): Expanding the ESLint configuration, React Compiler, React + Vite

## Knowledge Gaps
- **185 isolated node(s):** `Inicializa o banco de dados ao iniciar a aplicação.`, `Retorna todas as configurações do sistema.`, `Atualiza uma configuração (ex: toggle do time titular).`, `Lista o elenco com filtros opcionais.`, `Estatísticas do elenco (total, por posição, por liga, etc.).` (+180 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `_run_scraping_background()` connect `Community 7` to `Community 0`, `Community 2`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Why does `calculate_optimal_path()` connect `Community 11` to `Community 9`, `Community 1`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Why does `get_available_for_sbc()` connect `Community 9` to `Community 11`, `Community 5`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `parse_requirement_text()` (e.g. with `_process_sbc()` and `_extract_sbc_details()`) actually correct?**
  _`parse_requirement_text()` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `calculate_optimal_path()` (e.g. with `get_available_for_sbc()` and `SuggestedPlayerResponse`) actually correct?**
  _`calculate_optimal_path()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `AppSetting` (e.g. with `seed_initial_data()` and `test_create_and_get_setting()`) actually correct?**
  _`AppSetting` has 7 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Inicializa o banco de dados ao iniciar a aplicação.`, `Retorna todas as configurações do sistema.`, `Atualiza uma configuração (ex: toggle do time titular).` to the rest of the system?**
  _185 weakly-connected nodes found - possible documentation gaps or missing edges._