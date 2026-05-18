# Benchmark — guida operativa

Cuore "scientifico" del progetto: confronta PostgreSQL e Neo4j su 12 query
parametrizzate (10 read + 2 write), misura tempi di esecuzione, verifica la
consistenza dei risultati, e produce un report con grafici.

## Struttura

```
benchmark/
  queries.py            # definizione delle 12 query con parametri
  run_benchmark.py      # esegue il benchmark, registra hardware/versioni DB
  verbosity.py          # calcolo LOC + cognitive verbosity (keyword list simmetrica)
  index_ablation.py     # drop/restore di un indice critico + ri-esecuzione
  generate_report.py    # produce il report Markdown + 5 grafici PNG
  results/              # output di ogni run (timestamped)
  results/index_ablation/  # output dell'esperimento di index ablation
  README.md
```

Le query (file SQL e Cypher equivalenti) sono in `queries/sql/` e
`queries/cypher/`. Vedi `queries/README.md` per il dettaglio.

## Pre-requisiti

I due database popolati (Postgres + Neo4j) come descritto in `etl/README.md`.

Le dipendenze Python sono nello stesso `requirements.txt` dell'ETL
(`matplotlib` e' la sola in piu' rispetto al load):

```bash
source etl/.venv/bin/activate
pip install -r etl/requirements.txt
```

## Esecuzione

```bash
python3 benchmark/run_benchmark.py            # 5 esecuzioni misurate per query (default)
python3 benchmark/run_benchmark.py --runs 10  # piu' run = stime piu' robuste
```

Output (salvato in `benchmark/results/run_YYYYMMDD_HHMMSS/`):

| File | Cosa contiene |
|---|---|
| `timings.csv` | una riga per ogni esecuzione (warm-up escluso) |
| `summary.csv` | mediana / min / max / IQR per (query, sistema) |
| `run_metadata.json` | host, platform, CPU, RAM, versioni Postgres/Neo4j, Python, runs |

A schermo viene anche stampata una tabella riassuntiva con il vincitore
per ogni query e lo speedup.

## Index ablation

```bash
python3 benchmark/index_ablation.py --runs 5
```

Esegue Q08 in tre fasi: con indice (`ix_lineup_player` su Postgres,
`player_name_idx` su Neo4j), dopo `DROP INDEX`, e dopo `CREATE INDEX` di nuovo.
Output: `benchmark/results/index_ablation/<timestamp>.csv` con la mediana per
fase. Mostra che gli indici dello schema non sono decorativi.

## Generazione del report

```bash
python3 benchmark/generate_report.py            # usa l'ultima run
python3 benchmark/generate_report.py --run run_20260101_120000   # run specifica
```

Output:
- `reports/benchmark_report.md` — report completo Markdown con setup, sintesi,
  conclusioni, limitations e bibliografia.
- `reports/figures/perf_by_query.png` — tempi mediani per ogni query.
- `reports/figures/perf_by_category.png` — confronto per categoria di query.
- `reports/figures/speedup.png` — speedup Neo4j vs Postgres.
- `reports/figures/loc.png` — LOC SQL vs Cypher.
- `reports/figures/verbosity.png` — cognitive verbosity SQL vs Cypher.

Sia il Markdown sia le figure sono pronti per essere inseriti nelle slide
della presentazione (le figure sono in PNG ad alta risoluzione, 140 dpi).

## Metodologia

Per ciascuna query e ciascun sistema:
1. **Warm-up**: una prima esecuzione viene scartata (riempie le cache dei
   piani di esecuzione e il buffer dei dati).
2. **N esecuzioni misurate** (default 5).
3. Tempo misurato tramite `time.perf_counter()` attorno alla `execute` +
   fetch completo dei risultati.
4. Statistiche: mediana, min, max, IQR (interquartile range) per robustezza
   anti-outlier.
5. **Verifica risultati**: i set di tuple restituiti dai due sistemi vengono
   normalizzati (cast di Decimal/float, arrotondamento a 4 decimali, cast
   di date a stringa) e confrontati come `set`. Se differiscono, il report
   lo segnala esplicitamente.
6. **Query di scrittura (Q11/Q12)**: eseguite in transazione esplicita e
   rolled-back dopo ogni run, in modo che ogni misurazione lavori su stato
   pulito e nessuna modifica resti persistente.

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
