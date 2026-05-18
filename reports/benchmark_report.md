# Benchmark SQL vs Cypher — Report

Run: `run_20260518_194104`


## Experimental setup

| Item | Value |
|---|---|
| Host | `192.168.1.52` |
| Platform | `macOS-26.5-arm64-arm-64bit` |
| CPU | `Apple M2` (8 cores) |
| Memory | 8.0 GB |
| Python | `3.12.3` |
| PostgreSQL | `PostgreSQL 18.3 (Homebrew) on aarch64-apple-darwin25.2.0, compiled by Apple clang version 17.0.0 (clang-1700.6.3.2), 64-bit` |
| Neo4j | `Neo4j Kernel 2026.04.0 (enterprise)` |
| Misure per query | 5 run + 1 warm-up scartato |
| Numero query | 12 |


## Sintesi

| ID | Query | Categoria | Postgres (ms) | Neo4j (ms) | Vincitore | Speedup | Risultati |
|---|---|---|---:|---:|---|---:|:---:|
| Q01 | Top scorers by season | A_relational | 15.6 | 9.1 | **Neo4j** | 1.71x | OK |
| Q02 | League standings by season | A_relational | 3.8 | 5.7 | **Postgres** | 1.52x | OK |
| Q03 | Goals per match by league | A_relational | 3.9 | 5.6 | **Postgres** | 1.45x | OK |
| Q04 | Home win percentage by team | A_relational | 16.8 | 24.5 | **Postgres** | 1.46x | OK |
| Q05 | Goal-assist partnerships | B_multihop | 27.6 | 52.3 | **Postgres** | 1.89x | OK |
| Q06 | Cards received vs Real Madrid | B_multihop | 24.4 | 8.8 | **Neo4j** | 2.78x | OK |
| Q07 | Players in all 8 seasons | B_multihop | 1283.5 | 201.0 | **Neo4j** | 6.39x | OK |
| Q08 | Teammates of Messi 2015/16 | C_graph_native | 5.6 | 3.5 | **Neo4j** | 1.61x | OK |
| Q09 | 2-hop teammates of Messi | C_graph_native | 36.3 | 66.9 | **Postgres** | 1.84x | OK |
| Q10 | Shortest path Messi -> Pirlo | C_graph_native | 749.6 | 9.9 | **Neo4j** | 75.91x | OK |
| Q11 | Bulk UPDATE on event subtype | D_write | 363.9 | 155.2 | **Neo4j** | 2.34x | OK |
| Q12 | Schema evolution: add totalGoals | D_write | 390.8 | 33.2 | **Neo4j** | 11.77x | OK |

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
| Q01 | 16 | 5 | 3.20x | 12 | 6 | 2.00x |
| Q02 | 35 | 15 | 2.33x | 21 | 11 | 1.91x |
| Q03 | 9 | 8 | 1.12x | 6 | 5 | 1.20x |
| Q04 | 12 | 11 | 1.09x | 9 | 8 | 1.12x |
| Q05 | 11 | 8 | 1.38x | 10 | 11 | 0.91x |
| Q06 | 17 | 11 | 1.55x | 16 | 13 | 1.23x |
| Q07 | 8 | 6 | 1.33x | 7 | 7 | 1.00x |
| Q08 | 15 | 7 | 2.14x | 13 | 8 | 1.62x |
| Q09 | 26 | 12 | 2.17x | 26 | 17 | 1.53x |
| Q10 | 21 | 3 | 7.00x | 26 | 3 | 8.67x |
| Q11 | 4 | 3 | 1.33x | 3 | 4 | 0.75x |
| Q12 | 5 | 2 | 2.50x | 3 | 3 | 1.00x |

## Verifica risultati

Tutte le 10 query restituiscono risultati equivalenti nei due sistemi.


## Conclusioni — quando usare cosa

Quattro takeaway emersi dai dati di questa run:


1. **Postgres regge il confronto sulle aggregazioni e OLAP-light** (categoria A: 3 query su 4 a favore di Postgres). L'ottimizzatore relazionale maturo e gli indici B-tree sono perfetti per query con piccoli join e aggregazioni semplici. Vantaggi modesti (1.45x-1.52x) ma sistematici.


2. **Neo4j domina sul shortest-path generico** (Q10): **75.9x piu' veloce** di Postgres. Il vantaggio del traversal nativo diventa drammatico quando la profondita' del path non e' nota a priori. Anche su Q07 (giocatori in tutte le 8 stagioni), che NON e' una query intrinsecamente "grafica", Neo4j vince 6.4x grazie al traversal diretto via LINEUP_OF.


3. **La materialized view cambia le carte** sulle query intermedie (Q09): Postgres con `mv_played_for` ora vince. Questo conferma che lavorando su strutture precomputate equivalenti, il vantaggio Neo4j si concentra esattamente dove ha senso teoricamente: il traversal a profondita' variabile, non l'iterazione su join precomputati.


4. **Espressivita'**: il codice Cypher e' quasi sempre piu' breve del SQL equivalente. Il differenziale esplode su shortest path: ~20-30 linee SQL (CTE ricorsiva BFS) vs 3 linee Cypher (`shortestPath()` primitiva).


5. **Schema flexibility (Q12)**: aggiungere un attributo derivato a tutti i match costa molto meno in Neo4j (~33 ms vs ~391 ms): nessun DDL, nessun lock, solo `SET`. Vantaggio rilevante in contesti con schema evolution frequente.


**Verdetto operativo**:

- Scegliere **PostgreSQL** quando: aggregazioni OLAP, schema stabile e fortemente vincolato, integrita' referenziale critica, esperienza del team consolidata, ecosistema BI/ETL maturo.

- Scegliere **Neo4j** quando: il dominio e' intrinsecamente un grafo (relazioni piu' importanti delle entita'), serve traversal a profondita' variabile (raccomandazione, fraud detection, supply chain), lo schema evolve spesso.

- Molti sistemi production-grade adottano **polyglot persistence**: i due DB coesistono e ciascuno gestisce la parte del dominio per cui e' nato.


## Index ablation

Esperimento separato (vedere `benchmark/index_ablation.py`): rimuovere strategicamente un indice critico, rieseguire Q08, poi ripristinarlo. Mostra che gli indici dello schema non sono decorativi.


| System | Phase | Median (ms) | Slowdown |
|---|---|---:|---:|
| Postgres | with index (`ix_lineup_player`) | 3.6 | 1.00x |
| Postgres | without index | 11.3 | **3.18x** |
| Neo4j | with index (`player_name_idx`) | 5.1 | 1.00x |
| Neo4j | without index | 7.8 | **1.55x** |

Valori reali misurati in `benchmark/results/index_ablation/`.


## Note metodologiche

- Ogni query e' stata eseguita con un ciclo di warm-up scartato + N esecuzioni misurate.

- I tempi riportati sono mediani; min, max e IQR sono in `summary.csv`.

- I risultati nei due sistemi sono confrontati come *insiemi* di tuple, con normalizzazione di tipi (Decimal, date) e arrotondamento a 4 decimali per evitare falsi positivi dovuti a differenze di precisione.

- Per garantire un confronto **fair** su Q08/Q09/Q10, Postgres precomputa la materialized view `mv_played_for(player, team, season)` (vedere `schema/postgres_schema.sql`), che corrisponde esattamente alla relazione derivata `:PLAYED_FOR` di Neo4j.

- I conteggi di **cognitive verbosity** usano un insieme simmetrico di operatori logici (`AND`, `OR`, `NOT` inclusi sia per SQL sia per Cypher).


## Limitations

Il benchmark misura performance **single-node, single-user, in-memory** su un dataset di dimensione media (917k eventi, 542k lineup rows, 26k match). Restano fuori dallo scope di questo lavoro:

- carico **concorrente** (write contention, lock, MVCC vs lock-free traversal);

- carico **OLTP intensivo** (insert rate, transazioni distribuite);

- scaling **orizzontale** (sharding Postgres con Citus vs Neo4j Fabric);

- benchmark **standardizzati** su dataset grafo (LDBC SNB, vedere bibliografia);

- tuning dei sistemi: entrambi usano configurazione di default; il delta potrebbe ridursi (o ampliarsi) con tuning specifico (shared_buffers per Postgres, pagecache size per Neo4j).


## Riferimenti

- Angles, R., Gutierrez, C. (2008). *Survey of Graph Database Models*. ACM Computing Surveys, 40(1).

- Vicknair, C. et al. (2010). *A Comparison of a Graph Database and a Relational Database*. ACM SE 2010.

- Holzschuher, F., Peinl, R. (2013). *Performance of Graph Query Languages: Comparison of Cypher, Gremlin and Native Access in Neo4j*. EDBT/ICDT Workshops.

- Erling, O. et al. (2015). *The LDBC Social Network Benchmark: Interactive Workload*. SIGMOD 2015.

- Robinson, I., Webber, J., Eifrem, E. (2015). *Graph Databases* (2nd ed.). O'Reilly Media.
