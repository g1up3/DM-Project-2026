# DM 2025/26 — Confronto sperimentale PostgreSQL vs Neo4j

Progetto di Data Management 2025/26, Sapienza Università di Roma.
Tutor: Roberto Maria Delfino.

**Autori**:
- Giuseppe D'Angelica — [github.com/g1up3](https://github.com/g1up3)
- Nicolas Leone — [github.com/theunick](https://github.com/theunick)

## Repository

- Repository GitHub del progetto: [github.com/g1up3/DM-Project-2026](https://github.com/g1up3/DM-Project-2026)
- Branch principale: `main`
- Per collaborare in modo ordinato, lavora su branch separati e usa pull request prima di unire le modifiche in `main`.

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

Per garantire un confronto **fair** sulle query graph-native (Q08, Q09, Q10),
Postgres precomputa una materialized view `mv_played_for(player, team, season)`
equivalente alla relazione derivata `:PLAYED_FOR` di Neo4j (vedere
`schema/postgres_schema.sql`). Senza questo accorgimento, Neo4j avrebbe un
vantaggio strutturale dovuto al modello di carico.

I risultati confermano l'aspettativa teorica: **Postgres vince sulle query
relazionali "OLAP-like"** (aggregazioni semplici, join 2-3 tabelle), **Neo4j
vince nettamente sulle query di tipo graph traversal** (multi-hop e shortest
path). Il caso più drammatico è la query di shortest-path tra due giocatori
(Messi → Pirlo): **12 ms su Neo4j contro 621 ms su Postgres** (53x), con il
codice Cypher 10 volte più corto del CTE ricorsivo SQL.

## Struttura del repository

```
.
├── schema/                       # Schemi: concettuale ER + DDL Postgres + Cypher Neo4j
│   ├── conceptual_er.md
│   ├── postgres_schema.sql       #  DDL + mv_played_for + viste analitiche
│   ├── neo4j_schema.md
│   ├── schema_ER_mermaidpng.png  #  diagramma ER renderizzato
│   ├── schema_ER_dbdiagram.pdf
│   └── visualisation.png         #  visualizzazione del grafo Neo4j
├── etl/                          # Pipeline di estrazione/trasformazione/caricamento
│   ├── transform.py              #  parsing XML, esplosione di Match
│   ├── load_postgres.py          #  applica DDL + COPY dei CSV + REFRESH MV
│   ├── load_neo4j.py             #  vincoli + LOAD CSV + relazione derivata PLAYED_FOR
│   ├── explore_dataset.py        #  produce reports/dataset_exploration.md
│   ├── README.md                 #  istruzioni operative ETL
│   └── requirements.txt
├── queries/                      # 12 query equivalenti in SQL e Cypher
│   ├── sql/Q01..Q12.sql          #  Q01-Q10 read, Q11-Q12 write
│   ├── cypher/Q01..Q12.cypher
│   └── README.md
├── benchmark/                    # Harness di misura e report
│   ├── queries.py                #  definizione delle 12 query con parametri
│   ├── run_benchmark.py          #  warm-up + N run + verifica risultati (read+write)
│   ├── verbosity.py              #  calcolo LOC + cognitive verbosity (simmetrico)
│   ├── index_ablation.py         #  drop/restore di un indice + ri-esecuzione
│   ├── generate_report.py        #  Markdown + 5 grafici PNG
│   ├── results/run_<ts>/         #  CSV di output per ciascuna run
│   ├── results/index_ablation/   #  output di index_ablation.py
│   └── README.md
├── reports/                      # Output finali
│   ├── dataset_exploration.md
│   ├── engineering_challenges.md #  storia delle 3 sfide ingegneristiche risolte
│   ├── benchmark_report.md       #  report con setup, risultati, limitations, bibliografia
│   └── figures/*.png             #  loc, verbosity, perf_by_query, speedup, qr_github
├── Presentation_DM_DAngelica_Leone.pptx   # Slide deck (20 slide)
├── Live_Demo_Script.md           # Sceneggiatura della demo live (~5 min)
├── clean/                        # CSV puliti generati da transform.py (non committati)
└── database/database.sqlite      # Sorgente Kaggle (non committato)
```

## Risultati di sintesi

Run di riferimento: `run_20260505_114833` (MacBook Air M-series).

| ID  | Query                                | Categoria         | Postgres (ms) | Neo4j (ms) | Vincitore   | Speedup |
| --- | ------------------------------------ | ----------------- | ------------: | ---------: | ----------- | ------: |
| Q01 | Top scorers by season                | A — Relational    |          11.7 |       12.1 | **Postgres**|   1.03x |
| Q02 | League standings by season           | A — Relational    |           5.5 |        7.3 | **Postgres**|   1.33x |
| Q03 | Goals per match by league            | A — Relational    |           4.4 |        8.1 | **Postgres**|   1.84x |
| Q04 | Home win % by team                   | A — Relational    |          16.3 |       28.7 | **Postgres**|   1.76x |
| Q05 | Goal-assist partnerships             | B — Multi-hop     |          62.9 |       42.6 | **Neo4j**   |   1.48x |
| Q06 | Cards vs Real Madrid                 | B — Multi-hop     |          21.5 |        6.8 | **Neo4j**   |   3.17x |
| Q07 | Players in all 8 seasons             | B — Multi-hop     |        1277.7 |      255.5 | **Neo4j**   |   5.00x |
| Q08 | Teammates of Messi 2015/16           | C — Graph-native  |           6.3 |        3.9 | **Neo4j**   |   1.61x |
| Q09 | 2-hop teammates of Messi             | C — Graph-native  |         145.8 |       93.8 | **Neo4j**   |   1.55x |
| Q10 | Shortest path Messi → Pirlo          | C — Graph-native  |         621.1 |       11.7 | **Neo4j**   | **53.21x** |
| Q11 | Bulk UPDATE on event subtype         | D — Write         |         435.7 |      178.0 | **Neo4j**   |   2.45x |
| Q12 | Schema evolution: add totalGoals     | D — Write         |         429.4 |       31.6 | **Neo4j**   |  13.59x |

Tutte e 10 le query read (Q01-Q10) restituiscono risultati semanticamente
equivalenti nei due sistemi (verificato automaticamente come set di tuple
normalizzate). Vedere `reports/benchmark_report.md` per il report completo
con setup hardware, grafici, limitations e bibliografia.

**Nota**: le query SQL Q08/Q09/Q10 sono state aggiornate per usare la
materialized view `mv_played_for` invece di ricostruire la relazione via CTE
ad ogni esecuzione. Le query Cypher Q05 e Q10 sono state allineate
semanticamente alle controparti SQL (gestione NULL `sourceEventId` per Q05;
range di hop equivalente a 6 player-hop per Q10). Dopo queste modifiche al
codice **il benchmark va rieseguito** per ottenere numeri aggiornati: i
valori riportati sopra corrispondono alla run precedente le modifiche.

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
   python3 etl/load_postgres.py    # carica Postgres + REFRESH mv_played_for
   python3 etl/load_neo4j.py       # carica Neo4j + deriva PLAYED_FOR
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
- `schema/postgres_schema.sql` — DDL con vincoli, indici, viste analitiche e
  materialized view `mv_played_for` per il confronto fair su query graph-native.
- `schema/neo4j_schema.md` — modello a grafo, vincoli e indici Cypher.
- `reports/dataset_exploration.md` — analisi preliminare del sorgente
  (qualità, NULL, struttura XML degli eventi, integrità referenziale).
- `reports/engineering_challenges.md` — tre sfide reali risolte durante l'ETL.

In particolare, la struttura *wide* della tabella `Match` (115 colonne) del
sorgente SQLite è stata esplosa in 4 entità separate: `match` (anagrafica
partita), `match_lineup` (542k righe, una per giocatore in formazione),
`match_event` (917k righe, dal parsing dei campi XML), e i dati delle quote
scommesse esclusi dallo scope.
