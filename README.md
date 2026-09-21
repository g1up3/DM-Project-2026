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

*Nota sui volumi*: il sorgente contiene 25.979 match (la proposta scriveva
"approximately 300,000 match records": era una stima sbagliata, corretta
all'esplorazione del dataset — `reports/dataset_exploration.md`), 11.060
giocatori e ~184k snapshot di attributi; il parsing dei campi XML espande i match in **917.815
eventi** e **542.281 righe di formazione**, per ~1.5M righe totali caricate
nei due sistemi.

Inventario dei dati caricati (ogni relazione del grafo coincide con la
popolazione Postgres corrispondente — e' la verifica di consistenza fra i due sistemi):

| PostgreSQL | Righe | Neo4j | Conteggio |
|---|---:|---|---:|
| `match` | 25.979 | `(:Match)`, `HOME`, `AWAY`, `IN_LEAGUE` | 25.979 ciascuno |
| `player` | 11.060 | `(:Player)` | 11.060 |
| `team` / `league` / `country` | 299 / 11 / 11 | `(:Team)` / `(:League)` / `(:Country)` | 299 / 11 / 11 |
| `match_lineup` | 542.281 | `LINEUP_OF` | 542.281 |
| `match_event` — falli con autore | 210.100 | `COMMITTED_FOUL_IN` | 210.100 |
| `match_event` — cartellini con autore | 61.380 | `RECEIVED_CARD_IN` | 61.380 |
| `match_event` — gol con marcatore | 39.665 | `SCORED_IN` | 39.665 |
| `match_event` — gol con assist | 17.000 | `ASSISTED_IN` | 17.000 |
| `mv_played_for` (derivata) | 35.002 | `PLAYED_FOR` (derivata) | 35.002 |
| `player_stats` / `team_stats` | 183.978 / 1.458 | non caricati (scope) | — |
| **Totale** | **~1.75M righe** | **37.360 nodi, 983.376 relazioni** | |

I 917.815 eventi di `match_event` includono anche tiri, cross, corner e
possesso (non modellati nel grafo) e gli eventi con autore ignoto.

L'analisi misura, su **12 query parametrizzate** equivalenti nelle due tecnologie
(10 read-only + 2 di scrittura), su tre dimensioni indipendenti:
- **performance** (mediana di 15 esecuzioni con warm-up scartato, CI bootstrap al 95%,
  significativita' statistica via Mann-Whitney U),
- **espressività** (LOC + cognitive verbosity con consume-on-match counting),
- **flessibilità** (schema evolution: ALTER+UPDATE in SQL vs SET in Cypher),
- **ease-of-use** (proxy oggettivi: LOC della pipeline, dipendenze, DDL,
  pitfall documentati) e **scalabilità** (ragionata sui query plan),

più una verifica automatica di **correttezza** (i risultati coincidono nei due sistemi),
un **index ablation benchmark** a matrice (7 coppie indice x query), e la cattura
automatica dei **query plan** (`EXPLAIN ANALYZE` per Postgres, `PROFILE` per Neo4j).

Per garantire un confronto **fair** sulle query graph-native a piu' hop (Q09, Q10),
Postgres precomputa una materialized view `mv_played_for(player, team, season)`
equivalente alla relazione derivata `:PLAYED_FOR` di Neo4j (vedere
`schema/postgres_schema.sql`). Senza questo accorgimento, Neo4j avrebbe un
vantaggio strutturale dovuto al modello di carico.

I risultati raffinano l'aspettativa teorica: sulle **aggregazioni "OLAP-like"
leggere** (categoria A, mediane sotto i 25 ms) i due sistemi sono in **parita'
operativa** — il vincitore cambia da un run all'altro; il vantaggio netto di
**Postgres** emerge dove il join su indici B-tree batte il traversal a
profondita' *fissa* (Q09, 2-hop con materialized view, 2.7x, e il divario cresce
con i dati); **Neo4j vince nettamente sui traversal a profondita' variabile**
(Q10) e in modo netto ma piu' contenuto sulle aggregazioni full-scan sulle
relazioni (Q07, 1.9x — il gap si allarga con la taglia dei dati) e sulla schema
evolution (Q12, 5.1x). Il caso più drammatico è lo shortest path tra due
giocatori (Messi → Pirlo): **14 ms su Neo4j contro 792 ms su Postgres**
(**55x**, p < 0.001) con semantica *identica* (vincolo di stagione dentro il
quantified path pattern) e codice Cypher 4 volte più corto del CTE ricorsivo SQL.

Quattro analisi di sensibilita' (sez. 10 e 12 del report) mettono alla prova i
risultati: `work_mem` non spiegava il gap di Q07 — lo spiegava un `GROUP BY` per
nome (163 omonimi nel dataset) che forzava un sort su testo con spill su disco:
corretto, il gap scende da 7.4x a 1.9x; la formulazione `shortestPath`
"naturale" di Q10 dava risposte **diverse dal SQL** su 1 coppia su 8 ed e' stata
sostituita da una semanticamente esatta; le scritture del benchmark gonfiavano
Postgres via MVCC (Q01 da 10 a 23 ms) finche' l'harness non ha adottato
`VACUUM (ANALYZE)` prima di ogni run e la misura fino al commit (con il solo
rollback Q12 risultava 11x invece di ~5x); su 2/4/8 stagioni il vantaggio di
Neo4j su Q07 si allarga e quello di Postgres su Q09 pure.

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
│   ├── sensitivity_q10.py        #  sensitivity semantica shortest path (3 varianti, 8 coppie)
│   ├── sensitivity_scale.py      #  scalabilita' misurata: Q07/Q09 su 2, 4, 8 stagioni
│   ├── generate_report.py        #  Markdown + 6 grafici PNG + threats to validity
│   ├── results/run_<ts>/         #  CSV, significance, plans/, db_config
│   ├── results/index_ablation/   #  output matrice di ablazione
│   ├── results/sensitivity/      #  output analisi di sensibilita'
│   └── README.md
├── reports/                      # Output finali
│   ├── dataset_exploration.md
│   ├── engineering_challenges.md #  storia delle 3 sfide ingegneristiche risolte
│   ├── benchmark_report.md       #  report completo (17 sezioni: perf, plans, ease-of-use, scalabilita', threats)
│   └── figures/*.png             #  6 grafici: perf, category, speedup, distributions, loc, verbosity
├── tests/                        # Test unitari dell'harness (pytest)
├── Makefile                      # Entry-point unico: make benchmark / report / test
├── LICENSE                       # MIT (codice); il dataset resta ODbL, non ridistribuito
├── PostgreSQL_vs_Neo4j_DAngelica_Leone.pptx   # Slide deck della presentazione (16 slide + 6 di backup)
├── PostgreSQL_vs_Neo4j_DAngelica_Leone.pdf    # Lo stesso deck in PDF, font incorporati
├── Live_Demo_Script.md           # Sceneggiatura della demo live (~5 min)
├── clean/                        # CSV puliti generati da transform.py (non committati)
└── database/database.sqlite      # Sorgente Kaggle (non committato)
```

## Risultati di sintesi

Run di riferimento: `run_20260921_162704` (MacBook Air M2, 8 GB, PostgreSQL 18.6, Neo4j 2026.04.0).
15 esecuzioni misurate + 1 warm-up scartato, `VACUUM (ANALYZE)` prima delle misure, query write
misurate fino al `COMMIT`. Significativita' via Mann-Whitney U (alpha = 0.05), effect size rank-biserial.

| ID  | Query                                | Categoria         | Postgres (ms) | Neo4j (ms) | Vincitore    | Speedup | p-value  | r    | Sig | Holm |
| --- | ------------------------------------ | ----------------- | ------------: | ---------: | ------------ | ------: | -------: | ---: | --- | ---- |
| Q01 | Top scorers by season                | A — Relational    |          10.3 |        6.9 | **Neo4j**    |   1.51x | < 0.001  | 0.75 | Yes | Yes  |
| Q02 | League standings by season           | A — Relational    |           3.7 |        5.1 | Postgres     |   1.38x | 0.229    | 0.26 | No  | No  |
| Q03 | Goals per match by league            | A — Relational    |           8.3 |        5.4 | **Neo4j**    |   1.54x | 0.028    | 0.48 | Yes | No  |
| Q04 | Home win % by team                   | A — Relational    |          15.9 |       20.7 | **Postgres** |   1.30x | 0.004    | 0.62 | Yes | Yes  |
| Q05 | Goal-assist partnerships             | B — Multi-hop     |          61.5 |       38.1 | **Neo4j**    |   1.62x | < 0.001  | 0.87 | Yes | Yes  |
| Q06 | Cards vs Real Madrid                 | B — Multi-hop     |          21.8 |        7.6 | **Neo4j**    |   2.85x | < 0.001  | 1.00 | Yes | Yes  |
| Q07 | Players in all 8 seasons             | B — Multi-hop     |         400.2 |      216.1 | **Neo4j**    |   1.85x | < 0.001  | 1.00 | Yes | Yes  |
| Q08 | Teammates of Messi 2015/16           | C — Graph-native  |           7.0 |        4.2 | **Neo4j**    |   1.66x | < 0.001  | 0.94 | Yes | Yes  |
| Q09 | 2-hop teammates of Messi             | C — Graph-native  |          28.9 |       77.6 | **Postgres** |   2.68x | < 0.001  | 1.00 | Yes | Yes  |
| Q10 | Shortest path Messi → Pirlo          | C — Graph-native  |         792.1 |       14.4 | **Neo4j**    | **54.9x** | < 0.001  | 1.00 | Yes | Yes  |
| Q11 | Bulk UPDATE on event subtype         | D — Write         |         303.1 |      195.6 | **Neo4j**    |   1.55x | < 0.001  | 0.96 | Yes | Yes  |
| Q12 | Schema evolution: add totalGoals     | D — Write         |         435.9 |       85.4 | **Neo4j**    |   5.11x | < 0.001  | 1.00 | Yes | Yes  |

Tutte e 10 le query read (Q01-Q10) restituiscono risultati equivalenti nei due
sistemi (verificato automaticamente come **multiset** di tuple normalizzate; per
Q10 anche su 8 coppie di giocatori, per Q02 su tutte le 88 coppie lega-stagione);
le 2 write modificano lo stesso numero di righe (21.442 e 25.979, verificato dai
contatori dei driver). 11 confronti su 12 sono significativi al livello nominale,
10 dopo la correzione di Holm per confronti multipli (cadono Q02 e Q03); 8 hanno
effect size rank-biserial >= 0.8. Le quattro query di categoria A stanno tutte
sotto i 25 ms: e' il regime in cui il vincitore cambia fra run (sez. 10.3 del
report) e va letto come parita'.

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
   python3 benchmark/run_benchmark.py        # VACUUM ANALYZE + 12 query × 15 run + warm-up, write fino al COMMIT
   python3 benchmark/verbosity.py            # LOC + cognitive verbosity
   python3 benchmark/index_ablation.py       # matrice (indice × query), 10 run per fase
   python3 benchmark/sensitivity_q07.py      # sensitivity work_mem su Q07 (solo Postgres)
   python3 benchmark/sensitivity_q10.py      # sensitivity semantica Q10 (3 varianti Cypher, 8 coppie)
   python3 benchmark/sensitivity_scale.py    # scalabilita': Q07 e Q09 su 2/4/8 stagioni
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
