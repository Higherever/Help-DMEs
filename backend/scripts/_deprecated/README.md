# ⚠️ Scripts Deprecados

Estes scripts foram **substituídos** pelo orquestrador unificado [`scrape_master.py`](../scrape_master.py).

**NÃO USE** estes scripts para coleta de jogadores. Eles são mantidos apenas como referência histórica.

## Comando Atual (Novo)

```bash
cd "/home/gambeta/Projetos/Socorro DMEs/Socorro DMEs"
source backend/.venv/bin/activate
python backend/scripts/scrape_master.py                    # Raspa tudo, pula o já feito
python backend/scripts/scrape_master.py --pages 1-50       # Só páginas 1 a 50
python backend/scripts/scrape_master.py --pages 1-2 --test # Modo teste
python backend/scripts/scrape_master.py --force             # Ignora skip, reprocessa tudo
```

## Scripts Deprecados e o que faziam

| Script | Função Original | Substituído por |
|---|---|---|
| `scrape_players_v2.py` | Coleta por páginas (sem skip) | `scrape_master.py` |
| `scrape_all_players.py` | Coleta global resiliente | `scrape_master.py` |
| `update_missing_substats.py` | Preencher lacunas de sub-atributos | `scrape_master.py` (integrado no pipeline) |
| `scrape_ea_ratings.py` | Ratings da EA | `scrape_master.py` |
| `scrape_full_db.py` | Coleta completa | `scrape_master.py` |
| `maintain_players_db.py` | Manutenção do banco | `scrape_master.py` |
| `resolve_failed_players.py` | Reprocessar falhas | `scrape_master.py --force` |

## Data da Deprecação

2026-06-01 — Consolidados no `scrape_master.py` v3.0
