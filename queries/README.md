# Query benchmark — SQL vs Cypher

Le **12 query** usate per il confronto fra PostgreSQL e Neo4j. Sono organizzate
in quattro categorie progressive: tre di lettura (A, B, C) di "graph-friendliness"
crescente, piu' una di scrittura (D):

| #   | Categoria         | Nome breve                         | Cosa misura                                         |
| --- | ----------------- | ---------------------------------- | --------------------------------------------------- |
| Q01 | A — Relazionale   | Top scorers by season              | aggregazione semplice + join 3 tabelle              |
| Q02 | A — Relazionale   | League standings by season         | UNION ALL + aggregazioni su match                   |
| Q03 | A — Relazionale   | Goals per match per league         | aggregazione + GROUP BY                             |
| Q04 | A — Relazionale   | Home win percentage by team        | percentuali + filtri                                |
| Q05 | B — Multi-hop     | Goal/assist partnerships           | 2 join sullo stesso evento (player1, player2)       |
| Q06 | B — Multi-hop     | Cards received vs a team           | join 4 tabelle con filtro su squadra avversaria     |
| Q07 | B — Multi-hop     | Players in all 8 seasons           | DISTINCT su 8 sottoinsiemi                          |
| Q08 | C — Graph-native  | Teammates of X in a season         | 1 hop di traversal                                  |
| Q09 | C — Graph-native  | "Friends of friends" 2-hop         | 2 hop con deduplicazione                            |
| Q10 | C — Graph-native  | Shortest path between two players  | path search a profondità variabile (max 6 hop)      |
| Q11 | D — Write         | Bulk UPDATE on event subtype       | mass-update workload (~21k righe)                   |
| Q12 | D — Write         | Schema evolution: add totalGoals   | DDL+UPDATE in SQL vs single SET in Cypher           |

## Convenzioni

- I file SQL usano placeholder named-style `%(param)s` (psycopg2).
- I file Cypher usano placeholder dollar-style `$param` (driver Neo4j).
- I parametri sono definiti in `benchmark/queries.py` per ciascuna query.
- Ogni query Q01-Q10 produce lo stesso result-set logico nei due sistemi
  (verificato da `benchmark/run_benchmark.py` come set di tuple normalizzate).
  Le query che raggruppano usano le chiavi (`player_api_id`, `team_api_id`),
  mai i nomi: il dataset ha 163 nomi di giocatore e 3 di squadra omonimi.
- Le query write Q11/Q12 vengono misurate fino al `COMMIT` incluso e poi
  riportate allo stato iniziale da un cleanup non misurato (Q11 e'
  idempotente; Q12 rimuove colonna/proprieta'). L'harness verifica che il
  numero di righe/proprieta' modificate coincida nei due sistemi.

## Note di equivalenza semantica

- **Q09, Q10**: le versioni SQL usano la materialized view
  `soccer.mv_played_for` (vedere `schema/postgres_schema.sql`), che replica
  esattamente la relazione derivata `:PLAYED_FOR` di Neo4j. Senza di essa il
  confronto sarebbe asimmetrico (Neo4j attraverserebbe una struttura
  precomputata mentre Postgres la ricostruirebbe ad ogni esecuzione).
- **Q10**: in SQL la BFS ricorsiva limita la profondita' a 6 hop player-player
  (`WHERE b.distance < 6`) e collega due giocatori solo se compagni **nella
  stessa stagione** (`pf2.season = pf1.season`). In Cypher un hop e' il
  gruppo `(x)-[r1:PLAYED_FOR]->(Team)<-[r2:PLAYED_FOR]-(y) WHERE r1.season =
  r2.season`, ripetuto `{1,6}` volte dentro un quantified path pattern con
  `SHORTEST 1`. La formulazione legacy `shortestPath((a)-[:PLAYED_FOR*..12]-(b))`
  **non** vincola la stagione fra archi consecutivi e da' risposte diverse dal
  SQL (es. Ibrahimovic → Neuer: 2 hop invece di 3): vedere il report, sez. 10.2.
- **Q05**: in SQL marcatore e assistman stanno sulla stessa riga di
  `match_event`; in Cypher l'evento e' spezzato in due relazioni
  (`SCORED_IN`, `ASSISTED_IN`) riaccoppiate tramite `sourceEventId`.
  L'equivalenza poggia su un invariante dei dati, verificato: ogni gol ha un
  `sourceEventId` non nullo e univoco (0 NULL, 0 duplicati). Il guard
  `IS NOT NULL` rende l'assunzione esplicita; e' un limite noto della
  modellazione a due archi rispetto a un nodo `:MatchEvent`.
- **Q11**: il grafo materializza un gol come `SCORED_IN` solo se il marcatore
  e' noto; 109 gol hanno `player1_id` annullato nell'ETL (riferimenti orfani)
  e non hanno controparte in Neo4j. La versione SQL filtra
  `player1_id IS NOT NULL` cosi' che i due workload tocchino le stesse 21.442
  righe logiche (verificato da rowcount vs `properties_set`).
- **Q07 / Q04**: raggruppano per `player_api_id` / `team_api_id`. Raggruppando
  per nome, 14 "giocatori" di Q07 sarebbero omonimi fusi (550 vs 539 reali).

## Struttura

```
queries/
    sql/      Q01_*.sql ... Q12_*.sql
    cypher/   Q01_*.cypher ... Q12_*.cypher
    demo/     versioni hard-coded per la live demo (parametri inline)
```
