# DM 2025/26 — Confronto sperimentale PostgreSQL vs Neo4j

Progetto di Data Management 2025/26, Sapienza Università di Roma.
Tutor: Roberto Maria Delfino.

**Autori**:
- Giuseppe D'Angelica — [github.com/g1up3](https://github.com/g1up3)
- Nicolas Leone — [github.com/theunick](https://github.com/theunick)

## Sintesi

Confronto fra un DBMS relazionale (**PostgreSQL**) e un graph database
(**Neo4j**) sul dataset *European Soccer Database* (Hugo Mathien, Kaggle):
~26k partite di campionato delle 11 leghe top europee dal 2008 al 2016, con
formazioni, eventi (gol, assist, cartellini, ...), giocatori e squadre.

L'analisi misura, su **12 query parametrizzate** equivalenti nelle due tecnologie
(10 read-only + 2 di scrittura), su tre dimensioni indipendenti:
- **performance** (mediana di 5 esecuzioni con warm-up scartato),
- **espressività** (LOC + cognitive verbosity = numero di operatori logici),
- **flessibilità** (schema evolution: ALTER+UPDATE in SQL vs SET in Cypher),

più una verifica automatica di **correttezza** (i risultati coincidono nei due sistemi)
e un **index ablation benchmark** che misura il costo di rimuovere un indice critico.

I risultati confermano l'aspettativa teorica: PostgreSQL vince sulle query
relazionali "OLAP-like" (aggregazioni semplici), Neo4j vince nettamente sulle
query di tipo *graph traversal*. Il caso più drammatico è la query di
shortest-path tra due giocatori (Messi → Pirlo): **8 ms su Neo4j contro 601 ms
su Postgres**, con il codice Cypher che è 10 volte più corto del CTE ricorsivo.

## Struttura del repository

```
.
├── schema/                       # Schemi: concettuale ER + DDL Postgres + Cypher Neo4j
│   ├── conceptual_er.md
│   ├── postgres_schema.sql
│   └── neo4j_schema.md
├── etl/                          # Pipeline di estrazione/trasformazione/caricamento
│   ├── transform.py              #  parsing XML, esplosione di Match
│   ├── load_postgres.py          #  applica DDL + COPY dei CSV puliti
│   ├── load_neo4j.py             #  vincoli + LOAD CSV + relazione derivata PLAYED_FOR
│   ├── explore_dataset.py        #  produce reports/dataset_exploration.md
│   ├── README.md                 #  istruzioni operative ETL
│   └── requirements.txt
├── queries/                      # 12 query equivalenti in SQL e Cypher
│   ├── sql/Q01..Q12.sql           #  Q01-Q10 read, Q11-Q12 write
│   ├── cypher/Q01..Q12.cypher
│   └── README.md
├── benchmark/                    # Harness di misura e report
│   ├── queries.py                #  definizione delle 12 query con parametri
│   ├── run_benchmark.py          #  warm-up + N run + verifica risultati (read+write)
│   ├── verbosity.py              #  calcolo LOC + cognitive verbosity
│   ├── index_ablation.py         #  drop/restore di un indice + ri-esecuzione
│   ├── generate_report.py        #  Markdown + 5 grafici PNG
│   ├── results/run_<ts>/         #  CSV di output per ciascuna run
│   └── README.md
├── reports/                      # Output finali
│   ├── dataset_exploration.md
│   ├── engineering_challenges.md #  storia delle 3 sfide ingegneristiche risolte
│   ├── benchmark_report.md
│   └── figures/*.png             #  loc, verbosity, perf_by_query, speedup, qr_github
├── Presentation_DM_DAngelica_Leone.pptx   # Slide deck (20 slide)
├── Live_Demo_Script.md           # Sceneggiatura della demo live (~5 min)
├── clean/                        # CSV puliti generati da transform.py (non committati)
└── database/database.sqlite      # Sorgente Kaggle (non committato)
```

## Risultati di sintesi

| ID | Query | Categoria | Postgres | Neo4j | Vincitore | Speedup |
|---|---|---|---:|---:|---|---:|
| Q01 | Top scorers by season | A — Relational | 14.5 ms | 6.6 ms | Neo4j | 2.19x |
| Q02 | League standings by season | A — Relational | 1.7 ms | 10.2 ms | **Postgres** | 6.14x |
| Q03 | Goals per match by league | A — Relational | 3.2 ms | 8.1 ms | **Postgres** | 2.54x |
| Q04 | Home win % by team | A — Relational | 18.1 ms | 18.5 ms | Pari | 1.02x |
| Q05 | Goal-assist partnerships | B — Multi-hop | 64.0 ms | 47.7 ms | Neo4j | 1.34x |
| Q06 | Cards vs Real Madrid | B — Multi-hop | 22.6 ms | 7.5 ms | Neo4j | 2.99x |
| Q07 | Players in all 8 seasons | B — Multi-hop | 1313.4 ms | 195.9 ms | Neo4j | 6.70x |
| Q08 | Teammates of Messi 2015/16 | C — Graph-native | 3.3 ms | 3.0 ms | Pari | 1.09x |
| Q09 | 2-hop teammates of Messi | C — Graph-native | 145.9 ms | 91.8 ms | Neo4j | 1.59x |
| Q10 | Shortest path Messi → Pirlo | C — Graph-native | 601.5 ms | 8.5 ms | **Neo4j** | **71.10x** |

Tutte e 10 le query restituiscono risultati semanticamente equivalenti nei
due sistemi (verificato automaticamente).

Vedi `reports/benchmark_report.md` per il report completo con grafici.

## Come riprodurre

Pre-requisiti: Python 3.10+, PostgreSQL 16+, Neo4j 5+ (Desktop o Docker),
file `database.sqlite` da Kaggle (https://www.kaggle.com/datasets/hugomathien/soccer).

1. Scaricare il dataset e posizionarlo in `database/database.sqlite`.
2. Configurare `etl/.env` (vedi `etl/README.md`) con le credenziali di entrambi i DB.
3. Setup ambiente:
   ```bash
   cd etl
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. Pipeline:
   ```bash
   python3 etl/transform.py        # estrae + parsa XML + produce CSV
   python3 etl/load_postgres.py    # carica Postgres
   python3 etl/load_neo4j.py       # carica Neo4j
   ```
5. Benchmark:
   ```bash
   python3 benchmark/run_benchmark.py        # 12 query × 5 run + warm-up
   python3 benchmark/verbosity.py            # LOC + cognitive verbosity
   python3 benchmark/index_ablation.py       # drop/restore di un indice critico
   python3 benchmark/generate_report.py      # Markdown + grafici
   ```

## Scelte progettuali

Le scelte di modellazione e i trade-off sono documentati in:
- `schema/conceptual_er.md` — modello concettuale e ipotesi.
- `schema/postgres_schema.sql` — DDL con vincoli e indici, viste analitiche.
- `schema/neo4j_schema.md` — modello a grafo, vincoli e indici Cypher.
- `reports/dataset_exploration.md` — analisi preliminare del sorgente
  (qualità, NULL, struttura XML degli eventi, integrità referenziale).

In particolare, la struttura *wide* della tabella `Match` (115 colonne) del
sorgente SQLite è stata esplosa in 4 entità separate: `match` (anagrafica
partita), `match_lineup` (542k righe, una per giocatore in formazione),
`match_event` (917k righe, dal parsing dei campi XML), e i dati delle quote
scommesse esclusi dallo scope.
