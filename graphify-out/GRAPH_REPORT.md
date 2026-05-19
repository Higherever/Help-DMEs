# Graph Report - Socorro DMEs  (2026-05-19)

## Corpus Check
- 68 files · ~511,097 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 509 nodes · 663 edges · 53 communities (44 shown, 9 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 100 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5851e8fa`
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
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]

## God Nodes (most connected - your core abstractions)
1. `parse_requirement_text()` - 13 edges
2. `Base` - 13 edges
3. `_process_single_sbc()` - 12 edges
4. `calculate_optimal_path()` - 11 edges
5. `AppSetting` - 11 edges
6. `useApi()` - 11 edges
7. `_sbc_to_detail_response()` - 10 edges
8. `_process_sbc()` - 10 edges
9. `SBCSet` - 9 edges
10. `SBCChallenge` - 9 edges

## Surprising Connections (you probably didn't know these)
- `App()` --calls--> `useApi()`  [INFERRED]
  Prote-o/app/src/App.tsx → frontend/src/hooks/useApi.js
- `WebSocket para streaming de progresso em tempo real.` --rationale_for--> `list_squad()`  [EXTRACTED]
  Prote-o/app/backend/main.py → backend/main.py
- `test_get_available_for_sbc()` --calls--> `AppSetting`  [INFERRED]
  backend/tests/test_squad_service.py → backend/models/models.py
- `import_squad()` --calls--> `SquadImportResponse`  [INFERRED]
  backend/main.py → backend/schemas/schemas.py
- `Wrapper que mede a velocidade, executa a função e notifica via WebSocket.` --rationale_for--> `import_squad()`  [EXTRACTED]
  Prote-o/app/backend/main.py → backend/main.py

## Communities (53 total, 9 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (45): Help DMEs — Seed Data ====================== Dados iniciais populados automatica, Popula dados iniciais no banco (idempotente).     Só insere registros que ainda, seed_initial_data(), DeclarativeBase, AppSetting, Base, ChallengeRequirement, PlayerCard (+37 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (41): Converte SBCSet ORM → schema Pydantic detalhado., Converte SBCSet ORM → schema Pydantic detalhado., _sbc_to_detail_response(), BaseModel, AnalysisResponse, AppSettingUpdateRequest, BulkExcludeRequest, CalculatePathResponse (+33 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (39): api_cancelar(), api_executar(), api_velocidade(), ComandoExecutar, _executar_e_notificar(), handle_sigterm(), health(), import_squad() (+31 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (18): Loading26Props, OPCOES, OptionsProps, iconeStatus, PackageListProps, Progress(), ProgressProps, Status (+10 more)

### Community 4 - "Community 4"
Cohesion: 0.09
Nodes (27): Inicia o scraping em background. Fonte: fut.gg (padrão) ou futnext., Inicia o scraping em background via Futbin., Status atual do scraping., Status atual do scraping., Executa scraping Futbin em background., Executa scraping em background com fallback., Executa scraping FutNext em background., _run_futnext_background() (+19 more)

### Community 5 - "Community 5"
Cohesion: 0.1
Nodes (27): _download_image(), _extract_challenges(), _fetch(), _fetch_binary(), _get_total_pages(), _map_category(), _parse_cost(), _parse_requirement_line() (+19 more)

### Community 6 - "Community 6"
Cohesion: 0.11
Nodes (9): useApi(), HERO_IMAGES, NAV_ITEMS, CalculatorPage(), SbcsPage(), SettingsPage(), SquadPage(), tdStyle (+1 more)

### Community 7 - "Community 7"
Cohesion: 0.1
Nodes (18): _coletar_info_sistema(), configurar_logs(), _get_cmd_output(), _limpar_logs_antigos(), Sistema de Logging Acumulativo — Proteção GUI  Regras:   - Cada abertura do prog, Garante que o diretório tenha no máximo MAX_LOGS arquivos com o prefixo dado., Configura o sistema de logs acumulativos.     Logs são salvos em: Prote-o/logs/l, Invoca um comando de sistema e retorna sua saída limpa. (+10 more)

### Community 8 - "Community 8"
Cohesion: 0.1
Nodes (23): bulk_exclude(), bulk_include(), exclude_player(), get_available_for_sbc(), get_squad(), get_squad_stats(), import_csv(), _parse_bool() (+15 more)

### Community 9 - "Community 9"
Cohesion: 0.12
Nodes (21): test_scraper(), create_stealth_context(), normalize_category(), parse_cost_text(), parse_expiry_text(), parse_requirement_text(), Limpa strings de preço e converte para inteiro.     Ex: "10,000" -> 10000, Normaliza textos de expiração (ex: "7 days", "23 hours"). (+13 more)

### Community 10 - "Community 10"
Cohesion: 0.14
Nodes (21): analyze_sbc(), calculate_optimal_path(), _estimate_card_cost(), estimate_cost(), _get_sbc_with_relations(), _load_position_mappings(), _load_rarity_mappings(), _meets_requirement() (+13 more)

### Community 11 - "Community 11"
Cohesion: 0.12
Nodes (17): get_all_settings(), get_setting(), get_setting_bool(), Help DMEs — Settings Service ============================== CRUD de configuraçõe, Retorna todas as configurações do sistema., Busca uma configuração pela chave. Retorna None se não existir., Atualiza o valor de uma configuração existente.     Levanta ValueError se a chav, Atalho: busca uma configuração e retorna como bool.     Usa a property .as_bool (+9 more)

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
Cohesion: 0.25
Nodes (8): bulk_exclude_players(), bulk_include_players(), Exclusão em lote por filtro., Exclusão em lote por filtro., Remove exclusão de TODOS os jogadores., Remove exclusão de TODOS os jogadores., BulkActionResponse, Resposta para ações em lote.

### Community 16 - "Community 16"
Cohesion: 0.25
Nodes (8): list_settings(), Atualiza uma configuração (ex: toggle do time titular)., Atualiza uma configuração (ex: toggle do time titular)., Retorna todas as configurações do sistema., Retorna todas as configurações do sistema., update_setting(), AppSettingResponse, Configuração do sistema.

### Community 17 - "Community 17"
Cohesion: 0.33
Nodes (5): list_squad(), _player_to_response(), Lista o elenco com filtros opcionais., Converte UserSquadPlayer ORM → schema Pydantic., Converte UserSquadPlayer ORM → schema Pydantic.

### Community 18 - "Community 18"
Cohesion: 0.33
Nodes (6): list_sbcs(), Lista todos os SBCs coletados, com filtro opcional por categoria., Lista todos os SBCs coletados, com filtro opcional por categoria., Converte SBCSet ORM → schema Pydantic resumido., Converte SBCSet ORM → schema Pydantic resumido., _sbc_to_response()

### Community 20 - "Community 20"
Cohesion: 0.5
Nodes (3): Help DMEs — Fixtures de Teste ================================ Banco SQLite em m, Cria sessão de teste com banco SQLite em memória., test_session()

### Community 21 - "Community 21"
Cohesion: 0.5
Nodes (3): Expanding the ESLint configuration, React Compiler, React + Vite

### Community 22 - "Community 22"
Cohesion: 0.67
Nodes (3): Histórico de sincronizações., Histórico de sincronizações., scrape_logs()

### Community 23 - "Community 23"
Cohesion: 0.67
Nodes (3): calculate_optimal_path(), [Fase 4] Calcula a rota ótima para completar um SBC., [Fase 4] Calcula a rota ótima para completar um SBC.

### Community 24 - "Community 24"
Cohesion: 0.67
Nodes (3): get_sbc_detail(), Detalhes completos de um SBC com challenges, requisitos e rewards., Detalhes completos de um SBC com challenges, requisitos e rewards.

### Community 25 - "Community 25"
Cohesion: 0.67
Nodes (3): analyze_sbc(), [Fase 4] Análise de viabilidade de um SBC., [Fase 4] Análise de viabilidade de um SBC.

### Community 26 - "Community 26"
Cohesion: 0.67
Nodes (3): health_check(), Verifica a saúde do sistema e conexão com banco., Verifica a saúde do sistema e conexão com banco.

### Community 27 - "Community 27"
Cohesion: 0.67
Nodes (3): list_scrape_sources(), Lista as fontes de scraping disponíveis., Lista as fontes de scraping disponíveis.

### Community 28 - "Community 28"
Cohesion: 0.67
Nodes (3): Estatísticas do elenco (total, por posição, por liga, etc.)., Estatísticas do elenco (total, por posição, por liga, etc.)., squad_stats()

## Knowledge Gaps
- **217 isolated node(s):** `Inicializa o banco de dados ao iniciar a aplicação.`, `Retorna todas as configurações do sistema.`, `Atualiza uma configuração (ex: toggle do time titular).`, `Importa o CSV do elenco (reimportação completa — apaga dados anteriores).`, `Estatísticas do elenco (total, por posição, por liga, etc.).` (+212 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `_run_scraping_background()` connect `Community 4` to `Community 0`, `Community 17`, `Community 5`?**
  _High betweenness centrality (0.115) - this node is a cross-community bridge._
- **Why does `calculate_optimal_path()` connect `Community 10` to `Community 8`, `Community 1`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Why does `AppSetting` connect `Community 0` to `Community 19`, `Community 11`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `parse_requirement_text()` (e.g. with `test_parse_team_rating()` and `test_parse_players_from_league()`) actually correct?**
  _`parse_requirement_text()` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `_process_single_sbc()` (e.g. with `SBCSet` and `SBCChallenge`) actually correct?**
  _`_process_single_sbc()` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `calculate_optimal_path()` (e.g. with `get_available_for_sbc()` and `SuggestedPlayerResponse`) actually correct?**
  _`calculate_optimal_path()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Inicializa o banco de dados ao iniciar a aplicação.`, `Retorna todas as configurações do sistema.`, `Atualiza uma configuração (ex: toggle do time titular).` to the rest of the system?**
  _217 weakly-connected nodes found - possible documentation gaps or missing edges._