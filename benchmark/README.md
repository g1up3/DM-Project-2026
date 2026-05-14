# Benchmark — guida operativa

Cuore "scientifico" del progetto: confronta PostgreSQL e Neo4j su 10 query
parametrizzate, misura tempi di esecuzione, verifica la consistenza dei
risultati, e produce un report con grafici.

## Struttura

```
benchmark/
  queries.py            # definizione delle 10 query con parametri
  run_benchmark.py      # esegue il benchmark e salva CSV
  generate_report.py    # produce il report Markdown + grafici
  results/              # output di ogni run (timestamped)
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
| `run_metadata.json` | host, platform, python, runs |

A schermo viene anche stampata una tabella riassuntiva con il vincitore
per ogni query e lo speedup.

## Generazione del report

```bash
python3 benchmark/generate_report.py            # usa l'ultima run
python3 benchmark/generate_report.py --run run_20260101_120000   # run specifica
```

Output:
- `reports/benchmark_report.md` — report completo Markdown.
- `reports/figures/perf_by_query.png` — tempi mediani per ogni query.
- `reports/figures/perf_by_category.png` — confronto per categoria di query.
- `reports/figures/speedup.png` — speedup Neo4j vs Postgres.
- `reports/figures/loc.png` — verbosita' (LOC) di SQL vs Cypher.

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

## Categorie delle query

| Categoria | Cosa testa | Aspettativa |
|---|---|---|
| **A — Relational** | aggregazioni, join 2-3 tabelle, filtri | Postgres dovrebbe essere competitivo o vincente: ottimizzatore maturo, gli indici B-tree sono perfetti per questi casi. |
| **B — Multi-hop** | join su molte tabelle, self-join, EXISTS | Pareggio o leggero vantaggio Neo4j. SQL inizia a soffrire la verbosita'. |
| **C — Graph-native** | network traversal, "amici degli amici", shortest path | Neo4j dovrebbe vincere nettamente. La query Cypher e' anche molto piu' breve e leggibile. |

Questa suddivisione e' un'**ipotesi di lavoro**, non un risultato: il
benchmark serve proprio a verificare se l'aspettativa si conferma.

## Cosa raccontare nelle slide

Tre dimensioni chiave del confronto, a partire dai dati prodotti:
1. **Performance**: usare il grafico `perf_by_query` (scala log) e
   `perf_by_category` per mostrare dove ciascun sistema vince.
2. **Espressivita'**: `loc.png` per quantificare la verbosita', con uno o
   due esempi di codice affiancato (Q01 vs Q10 sono i casi piu' istruttivi).
3. **Correttezza**: la colonna "Risultati" in tabella di sintesi: tutte OK
   = i due sistemi forniscono la stessa risposta, quindi il confronto di
   performance e' fra implementazioni semanticamente equivalenti.
