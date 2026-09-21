# Benchmark — guida operativa

Cuore "scientifico" del progetto: confronta PostgreSQL e Neo4j su 12 query
parametrizzate (10 read + 2 write), misura tempi di esecuzione, verifica la
consistenza dei risultati, e produce un report con grafici.

## Struttura

```
benchmark/
  queries.py            # definizione delle 12 query con parametri
  run_benchmark.py      # benchmark + statistiche + EXPLAIN/PROFILE + config DBMS
  verbosity.py          # calcolo LOC + cognitive verbosity (keyword list simmetrica)
  index_ablation.py     # matrice (indice, query): drop -> misura -> restore
  sensitivity_q07.py    # analisi di sensibilita': work_mem e lo spill di Q07
  sensitivity_q10.py    # analisi di sensibilita': semantica dello shortest path (Q10)
  sensitivity_scale.py  # scalabilita' misurata: Q07/Q09 su 2, 4, 8 stagioni
  generate_report.py    # produce il report Markdown + 6 grafici PNG
  results/              # output di ogni run (timestamped)
  results/index_ablation/  # output dell'esperimento di index ablation
  results/sensitivity/  # output dell'analisi di sensibilita'
  README.md
```

Le query (file SQL e Cypher equivalenti) sono in `queries/sql/` e
`queries/cypher/`. Vedi `queries/README.md` per il dettaglio.

## Pre-requisiti

I due database popolati (Postgres + Neo4j) come descritto in `etl/README.md`.

Le dipendenze Python sono nello stesso `requirements.txt` dell'ETL
(`matplotlib`, `numpy` e `scipy` sono quelle in piu' rispetto al load;
`pytest` serve solo per i test in `tests/`):

```bash
source etl/.venv/bin/activate
pip install -r etl/requirements.txt
```

## Esecuzione

```bash
python3 benchmark/run_benchmark.py            # 15 esecuzioni misurate per query (default)
python3 benchmark/run_benchmark.py --runs 30  # piu' run = CI piu' stretti
```

Output (salvato in `benchmark/results/run_YYYYMMDD_HHMMSS/`):

| File | Cosa contiene |
|---|---|
| `timings.csv` | una riga per ogni esecuzione (warm-up escluso) |
| `summary.csv` | mediana / min / max / IQR / CI bootstrap 95% per (query, sistema) |
| `significance.csv` | Mann-Whitney U, p-value, effect size rank-biserial, vincitore |
| `plans/` | `EXPLAIN (ANALYZE, BUFFERS)` e `PROFILE` per ognuna delle 12 query |
| `db_config.json` | configurazione runtime dei DBMS (shared_buffers, heap, pagecache, ...) |
| `run_metadata.json` | host, platform, CPU, RAM, versioni Postgres/Neo4j, Python, runs |

A schermo viene anche stampata una tabella riassuntiva con il vincitore
per ogni query e lo speedup.

## Index ablation

```bash
python3 benchmark/index_ablation.py            # 10 run per fase (default)
```

Matrice di ablazione su **7 coppie (indice, query)** — 4 su Postgres, 3 su
Neo4j. Per ogni coppia esegue la query in tre fasi: con indice, dopo
`DROP INDEX`, e dopo il `CREATE INDEX` di ripristino (con verifica che
l'indice sia tornato). Output:
`benchmark/results/index_ablation/<timestamp>.csv` + `.json` con la mediana
per fase e lo slowdown. Mostra quali indici dello schema sono decorativi e
quali no.

## Analisi di sensibilita'

```bash
python3 benchmark/sensitivity_q07.py           # work_mem: 4MB vs 64MB, 15 run
python3 benchmark/sensitivity_q10.py           # semantica Q10: 3 varianti + 8 coppie, timeout 20 s
python3 benchmark/sensitivity_scale.py         # Q07 e Q09 su 2/4/8 stagioni, 10 run per cella
```

`sensitivity_q10.py` confronta tre formulazioni Cypher dello shortest path
(legacy `shortestPath` senza vincolo di stagione, `shortestPath` con predicato
di path, quantified path pattern + `SHORTEST 1`) sulla coppia di riferimento e
verifica su 8 coppie di giocatori quale coincide con la BFS SQL. Ogni query
Cypher gira con timeout server-side: la variante con predicato di path ha un
fallback esaustivo che puo' saturare la macchina, e viene misurata solo sulla
coppia sicura. Il report include automaticamente l'ultimo risultato (sez. 10.2).

### work_mem su Q07

Nella formulazione originale (`GROUP BY player_name`) il piano di Q07
conteneva l'unico spill su disco del benchmark (sort external merge, ~18 MB).
Lo script riesegue Q07 su Postgres con valori crescenti di `work_mem` e
registra mediana, CI e il Sort Method estratto da `EXPLAIN ANALYZE`: lo spill
non spostava la mediana. La causa vera era il raggruppamento per nome (testo
con collation, 163 omonimi): raggruppando per `player_api_id` il planner usa un
Incremental Sort sull'indice e Q07 scende da ~1.2 s a ~0.4 s (report, sez. 10.1).
Il report usa il primo file JSON (formulazione originale) come evidenza storica.

## Generazione del report

```bash
python3 benchmark/generate_report.py            # usa l'ultima run
python3 benchmark/generate_report.py --run run_20260101_120000   # run specifica
```

Output:
- `reports/benchmark_report.md` — report completo Markdown (17 sezioni: setup,
  configurazione DBMS, risultati con CI e significativita', query plan,
  sensitivity, ease-of-use, scalabilita', conclusioni, threats to validity,
  bibliografia).
- `reports/figures/perf_by_query.png` — tempi mediani con error bar (CI 95%).
- `reports/figures/perf_by_category.png` — confronto per categoria di query.
- `reports/figures/speedup.png` — speedup Neo4j vs Postgres (saturazione = significativita').
- `reports/figures/distributions.png` — box plot delle distribuzioni per query.
- `reports/figures/loc.png` — LOC SQL vs Cypher.
- `reports/figures/verbosity.png` — cognitive verbosity SQL vs Cypher.

Sia il Markdown sia le figure sono pronti per essere inseriti nelle slide
della presentazione (le figure sono in PNG ad alta risoluzione, 140 dpi).

## Metodologia

Per ciascuna query e ciascun sistema:
0. **Stato pulito**: `VACUUM (ANALYZE)` sulle tabelle Postgres coinvolte
   prima delle misure. Le write query Q11/Q12 creano in Postgres versioni di
   tupla morte (MVCC) che ne' il rollback ne' il cleanup rimuovono: senza
   VACUUM ogni run degrada le letture del run successivo finche' l'autovacuum
   non interviene (report, sez. 10.3). Registrato in `run_metadata.json`.
1. **Warm-up**: una prima esecuzione viene scartata (riempie le cache dei
   piani di esecuzione e il buffer dei dati).
2. **N esecuzioni misurate** (default 15).
3. Tempo misurato tramite `time.perf_counter()` attorno alla `execute` +
   fetch completo dei risultati.
4. Statistiche robuste: mediana, min, max, IQR, e **CI bootstrap al 95%**
   della mediana (10.000 ricampionamenti, seed fisso 42 per riproducibilita').
5. **Significativita'**: test di **Mann-Whitney U** (non parametrico,
   two-sided, alpha = 0.05) + effect size **rank-biserial** per la
   magnitudine della differenza. La correzione di **Holm-Bonferroni** per i
   12 confronti e' applicata in `generate_report.py` (colonna "Sig (Holm)"
   del report); `significance.csv` riporta il p-value grezzo.
6. **Query plan**: per ogni query vengono catturati `EXPLAIN (ANALYZE,
   BUFFERS)` su Postgres e `PROFILE` su Neo4j, salvati in `plans/`.
7. **Verifica risultati**: i set di tuple restituiti dai due sistemi vengono
   normalizzati (cast di Decimal/float, arrotondamento a 4 decimali, cast
   di date a stringa) e confrontati come **multiset** (stesse tuple, stessa
   molteplicita'). Se differiscono, il report lo segnala esplicitamente.
8. **Query di scrittura (Q11/Q12)**: misurate **fino al COMMIT** (Postgres:
   flush del WAL; Neo4j: applicazione allo store e transaction log), poi un
   cleanup non misurato riporta lo stato iniziale (Q11 e' idempotente, Q12
   rimuove colonna/proprieta'). Il numero di righe/proprieta' modificate e'
   letto dai driver e confrontato fra i due sistemi. `--write-mode rollback`
   riproduce il metodo storico, che sottostima Neo4j (le mutazioni restano in
   memoria fino al commit: Q12 risultava 11x invece di 4.5x).

## Categorie delle query

| Categoria | Cosa testa | Aspettativa |
|---|---|---|
| **A — Relational** | aggregazioni, join 2-3 tabelle, filtri | Postgres dovrebbe essere competitivo o vincente: ottimizzatore maturo, gli indici B-tree sono perfetti per questi casi. |
| **B — Multi-hop** | join su molte tabelle, self-join, condizioni "anti-join" | Pareggio o leggero vantaggio Neo4j. SQL inizia a soffrire la verbosita'. |
| **C — Graph-native** | network traversal, "amici degli amici", shortest path | Neo4j dovrebbe vincere nettamente. La query Cypher e' anche molto piu' breve e leggibile. |
| **D — Write** | bulk UPDATE e schema evolution | Neo4j dovrebbe vincere su schema evolution (schemaless = `SET`). |

Questa suddivisione e' un'**ipotesi di lavoro**, non un risultato: il
benchmark serve proprio a verificare se l'aspettativa si conferma.

## Fair-comparison: la materialized view in Postgres

Per evitare un confronto strutturalmente sbilanciato, Postgres precomputa
una materialized view `soccer.mv_played_for(player_api_id, team_api_id, season)`
che replica esattamente la relazione derivata `:PLAYED_FOR` di Neo4j. Senza
questo accorgimento, Neo4j attraverserebbe una struttura precomputata in
Q08/Q09/Q10 mentre Postgres dovrebbe ricostruirla via CTE ad ogni
esecuzione — il confronto sarebbe asimmetrico per design.

## Cosa raccontare nelle slide

Tre dimensioni chiave del confronto, a partire dai dati prodotti:
1. **Performance**: usare il grafico `perf_by_query` (scala log) e
   `perf_by_category` per mostrare dove ciascun sistema vince.
2. **Espressivita'**: `loc.png` + `verbosity.png` per quantificare la
   verbosita', con uno o due esempi di codice affiancato (Q01 vs Q10 sono i
   casi piu' istruttivi).
3. **Correttezza**: la colonna "Risultati" in tabella di sintesi: tutte OK
   = i due sistemi forniscono la stessa risposta, quindi il confronto di
   performance e' fra implementazioni semanticamente equivalenti.
