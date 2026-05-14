# Benchmark SQL vs Cypher — Report

Run: `run_20260505_114833`

Host: `MacBook-Air-di-Peppe-2.local`  ·  Platform: `macOS-26.4.1-arm64-arm-64bit`  ·  Python: `3.12.3`  ·  Esecuzioni misurate per query: 5


## Sintesi

| ID | Query | Categoria | Postgres (ms) | Neo4j (ms) | Vincitore | Speedup | Risultati |
|---|---|---|---:|---:|---|---:|:---:|
| Q01 | Top scorers by season | A_relational | 11.7 | 12.1 | **Postgres** | 1.03x | OK |
| Q02 | League standings by season | A_relational | 5.5 | 7.3 | **Postgres** | 1.33x | OK |
| Q03 | Goals per match by league | A_relational | 4.4 | 8.1 | **Postgres** | 1.84x | OK |
| Q04 | Home win percentage by team | A_relational | 16.3 | 28.7 | **Postgres** | 1.76x | OK |
| Q05 | Goal-assist partnerships | B_multihop | 62.9 | 42.6 | **Neo4j** | 1.48x | OK |
| Q06 | Cards received vs Real Madrid | B_multihop | 21.5 | 6.8 | **Neo4j** | 3.17x | OK |
| Q07 | Players in all 8 seasons | B_multihop | 1277.7 | 255.5 | **Neo4j** | 5.00x | OK |
| Q08 | Teammates of Messi 2015/16 | C_graph_native | 6.3 | 3.9 | **Neo4j** | 1.61x | OK |
| Q09 | 2-hop teammates of Messi | C_graph_native | 145.8 | 93.8 | **Neo4j** | 1.55x | OK |
| Q10 | Shortest path Messi -> Pirlo | C_graph_native | 621.1 | 11.7 | **Neo4j** | 53.21x | OK |
| Q11 | Bulk UPDATE on event subtype | D_write | 435.7 | 178.0 | **Neo4j** | 2.45x | OK |
| Q12 | Schema evolution: add totalGoals | D_write | 429.4 | 31.6 | **Neo4j** | 13.59x | OK |

## Tempi di esecuzione

![](figures/perf_by_query.png)


### Per categoria

![](figures/perf_by_category.png)


## Speedup Neo4j vs Postgres

Valori > 1 indicano che Neo4j e' piu' veloce su quella query.

![](figures/speedup.png)


## Query verbosity — two dimensions

LOC = lines of code. Cognitive verbosity = count of distinct logical operators (SELECT/JOIN/WHERE/GROUP BY/... in SQL; MATCH/WITH/WHERE/RETURN/... in Cypher). The two dimensions are complementary: a query can be short in lines but heavy in operators.

![](figures/loc.png)

![](figures/verbosity.png)


| ID | LOC SQL | LOC Cypher | LOC ratio | Verb SQL | Verb Cypher | Verb ratio |
|---|---:|---:|---:|---:|---:|---:|
| Q01 | 16 | 5 | 3.20x | 11 | 6 | 1.83x |
| Q02 | 35 | 15 | 2.33x | 20 | 11 | 1.82x |
| Q03 | 9 | 8 | 1.12x | 6 | 5 | 1.20x |
| Q04 | 12 | 11 | 1.09x | 9 | 8 | 1.12x |
| Q05 | 11 | 6 | 1.83x | 8 | 7 | 1.14x |
| Q06 | 17 | 11 | 1.55x | 12 | 13 | 0.92x |
| Q07 | 8 | 6 | 1.33x | 7 | 7 | 1.00x |
| Q08 | 15 | 7 | 2.14x | 10 | 8 | 1.25x |
| Q09 | 34 | 12 | 2.83x | 26 | 17 | 1.53x |
| Q10 | 30 | 3 | 10.00x | 28 | 3 | 9.33x |
| Q11 | 4 | 3 | 1.33x | 1 | 4 | 0.25x |
| Q12 | 5 | 2 | 2.50x | 2 | 3 | 0.67x |

## Verifica risultati

Tutte le 10 query restituiscono risultati equivalenti nei due sistemi.


## Note metodologiche

- Ogni query e' stata eseguita con un ciclo di warm-up scartato + N esecuzioni misurate.

- I tempi riportati sono mediani; min, max e IQR sono in `summary.csv`.

- I risultati nei due sistemi sono confrontati come *insiemi* di tuple, con normalizzazione di tipi (Decimal, date) e arrotondamento a 4 decimali per evitare falsi positivi dovuti a differenze di precisione.
