# Query benchmark — SQL vs Cypher

Le 10 query usate per il confronto fra PostgreSQL e Neo4j. Sono organizzate
in tre categorie progressive di "graph-friendliness":

| # | Categoria | Nome breve | Cosa misura |
|---|---|---|---|
| Q01 | A — Relazionale | Top scorers by season | aggregazione semplice + join 3 tabelle |
| Q02 | A — Relazionale | League standings by season | UNION ALL + aggregazioni su match |
| Q03 | A — Relazionale | Goals per match per league | aggregazione + GROUP BY |
| Q04 | A — Relazionale | Home win percentage by team | percentuali + filtri |
| Q05 | B — Multi-hop | Goal/assist partnerships | 2 join sullo stesso evento (player1, player2) |
| Q06 | B — Multi-hop | Cards received vs a team | join 4 tabelle con filtro su squadra avversaria |
| Q07 | B — Multi-hop | Players in all 8 seasons | EXISTS su 8 sottoinsiemi |
| Q08 | C — Graph-native | Teammates of X in a season | 1 hop di traversal |
| Q09 | C — Graph-native | "Friends of friends" 2-hop | 2 hop con deduplicazione |
| Q10 | C — Graph-native | Shortest path between two players | path search a profondità variabile |

## Convenzioni

- I file SQL usano placeholder named-style `%(param)s` (psycopg2).
- I file Cypher usano placeholder dollar-style `$param` (driver Neo4j).
- I parametri sono definiti in `benchmark/queries.py` per ciascuna query.
- Ogni query produce lo stesso result-set logico nei due sistemi (verificato
  da `benchmark/run_benchmark.py`).

## Struttura

```
queries/
    sql/      Q01_*.sql ... Q10_*.sql
    cypher/   Q01_*.cypher ... Q10_*.cypher
```
