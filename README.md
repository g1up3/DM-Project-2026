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

*Nota sui volumi*: il sorgente contiene 25.979 match, 11.060 giocatori e ~184k
snapshot di attributi; il parsing dei campi XML espande i match in **917.815
eventi** e **542.281 righe di formazione**, per ~1.5M righe totali caricate
nei due sistemi.

L'analisi misura, su **12 query parametrizzate** equivalenti nelle due tecnologie
(10 read-only + 2 di scrittura), su tre dimensioni indipendenti:
- **performance** (mediana di 15 esecuzioni con warm-up scartato, CI bootstrap al 95%,
  significativita' statistica via Mann-Whitney U),
- **espressività** (LOC + cognitive verbosity con consume-on-match counting),
- **flessibilità** (schema evolution: ALTER+UPDATE in SQL vs SET in Cypher),

più una verifica automatica di **correttezza** (i risultati coincidono nei due sistemi),
un **index ablation benchmark** a matrice (7 coppie indice x query), e la cattura
automatica dei **query plan** (`EXPLAIN ANALYZE` per Postgres, `PROFILE` per Neo4j).

Per garantire un confronto **fair** sulle query graph-native (Q08, Q09, Q10),
Postgres precomputa una materialized view `mv_played_for(player, team, season)`
equivalente alla relazione derivata `:PLAYED_FOR` di Neo4j (vedere
`schema/postgres_schema.sql`). Senza questo accorgimento, Neo4j avrebbe un
vantaggio strutturale dovuto al modello di carico.

I risultati confermano l'aspettativa teorica: **Postgres vince sulle query
relazionali "OLAP-like"** (aggregazioni semplici, join 2-3 tabelle, e — grazie
alla materialized view — anche la query 2-hop Q09), **Neo4j vince nettamente
sulle query di tipo graph traversal a profondita' variabile** (Q07 multi-hop
e Q10 shortest path). Il caso più drammatico è la query di shortest-path tra
due giocatori (Messi → Pirlo): **8 ms su Neo4j contro 712 ms su Postgres**
(**89x**, p < 0.001), con il codice Cypher 7 volte più corto del CTE ricorsivo SQL.
11 differenze su 12 sono statisticamente significative (p < 0.05).

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
│   ├── run_benchmark.py          #  15 run + warm-up + stats + EXPLAIN/PROFILE
│   ├── verbosity.py              #  LOC + cognitive verbosity (consume-on-match)
│   ├── index_ablation.py         #  matrice 7 coppie (indice, query)
│   ├── sensitivity_q07.py        #  sensitivity work_mem su Q07 (spill analysis)
│   ├── generate_report.py        #  Markdown + 6 grafici PNG + threats to validity
│   ├── results/run_<ts>/         #  CSV, significance, plans/, db_config
│   ├── results/index_ablation/   #  output matrice di ablazione
│   ├── results/sensitivity/      #  output analisi di sensibilita'
│   └── README.md
├── reports/                      # Output finali
│   ├── dataset_exploration.md
│   ├── engineering_challenges.md #  storia delle 3 sfide ingegneristiche risolte
│   ├── benchmark_report.md       #  report completo (15 sezioni, threats to validity)
│   └── figures/*.png             #  6 grafici: perf, category, speedup, distributions, loc, verbosity
├── tests/                        # Test unitari dell'harness (pytest)
├── Makefile                      # Entry-point unico: make benchmark / report / test
├── LICENSE                       # MIT (codice); il dataset resta ODbL, non ridistribuito
├── Presentation_DM_DAngelica_Leone.pptx   # Slide deck (23 slide)
├── Live_Demo_Script.md           # Sceneggiatura della demo live (~5 min)
├── clean/                        # CSV puliti generati da transform.py (non committati)
└── database/database.sqlite      # Sorgente Kaggle (non committato)
```

## Risultati di sintesi

Run di riferimento: `run_20260524_230038` (MacBook Air M2, 8 GB, PostgreSQL 18.3, Neo4j 2026.04.0).
15 esecuzioni misurate + 1 warm-up scartato. Significativita' via Mann-Whitney U (alpha = 0.05).

| ID  | Query                                | Categoria         | Postgres (ms) | Neo4j (ms) | Vincitore    | Speedup | p-value  | Sig |
| --- | ------------------------------------ | ----------------- | ------------: | ---------: | ------------ | ------: | -------: | --- |
| Q01 | Top scorers by season                | A — Relational    |          10.8 |       13.2 | Postgres     |   1.23x | 0.300    | No  |
| Q02 | League standings by season           | A — Relational    |           7.4 |        8.8 | **Postgres** |   1.19x | 0.009    | Yes |
| Q03 | Goals per match by league            | A — Relational    |           3.8 |        7.9 | **Postgres** |   2.11x | < 0.001  | Yes |
| Q04 | Home win % by team                   | A — Relational    |          12.5 |       14.7 | **Postgres** |   1.18x | 0.016    | Yes |
| Q05 | Goal-assist partnerships             | B — Multi-hop     |          55.4 |       36.0 | **Neo4j**    |   1.54x | < 0.001  | Yes |
| Q06 | Cards vs Real Madrid                 | B — Multi-hop     |          20.2 |        6.3 | **Neo4j**    |   3.24x | < 0.001  | Yes |
| Q07 | Players in all 8 seasons             | B — Multi-hop     |        1277.1 |      204.9 | **Neo4j**    |   6.23x | < 0.001  | Yes |
| Q08 | Teammates of Messi 2015/16           | C — Graph-native  |           5.9 |        3.5 | **Neo4j**    |   1.69x | 0.002    | Yes |
| Q09 | 2-hop teammates of Messi             | C — Graph-native  |          30.6 |       68.8 | **Postgres** |   2.25x | < 0.001  | Yes |
| Q10 | Shortest path Messi → Pirlo          | C — Graph-native  |         711.7 |        8.0 | **Neo4j**    | **89.3x**| < 0.001 | Yes |
| Q11 | Bulk UPDATE on event subtype         | D — Write         |         411.2 |      168.2 | **Neo4j**    |   2.44x | < 0.001  | Yes |
| Q12 | Schema evolution: add totalGoals     | D — Write         |         443.4 |       32.4 | **Neo4j**    |  13.70x | < 0.001  | Yes |

Tutte e 10 le query read (Q01-Q10) restituiscono risultati semanticamente
equivalenti nei due sistemi (verificato automaticamente come set di tuple
normalizzate). 11 confronti su 12 sono statisticamente significativi; l'unica
eccezione e' Q01 (p = 0.30, differenza nel rumore di misurazione). 8 confronti
hanno effect size rank-biserial >= 0.8 (separazione quasi completa delle
distribuzioni). Un'analisi di sensibilita' su `work_mem` esclude che il gap
di Q07 sia un artefatto di tuning (sez. 10 del report).

Vedere `reports/benchmark_report.md` per il report completo con intervalli di
confidenza, query plan, configurazione dei DBMS, threats to validity, e bibliografia.

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
   python3 benchmark/run_benchmark.py        # 12 query × 15 run + warm-up (default)
   python3 benchmark/verbosity.py            # LOC + cognitive verbosity
   python3 benchmark/index_ablation.py       # matrice (indice × query), 10 run per fase
   python3 benchmark/sensitivity_q07.py      # sensitivity work_mem su Q07 (solo Postgres)
   python3 benchmark/generate_report.py      # Markdown + 6 grafici
   ```
   In alternativa, l'intera sequenza e' orchestrata dal `Makefile`:
   `make benchmark` esegue misure + report, `make test` i test unitari
   dell'harness.

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

## Licenza e attribuzione dei dati

- **Codice** del progetto: licenza MIT (vedi `LICENSE`).
- **Dataset**: *European Soccer Database* di Hugo Mathien (Kaggle), rilasciato
  sotto Open Database License (ODbL). Il file `database.sqlite` **non è
  ridistribuito** in questo repository: va scaricato dalla fonte originale
  (link nella sezione "Come riprodurre").
