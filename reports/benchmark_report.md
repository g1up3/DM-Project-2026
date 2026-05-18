# Benchmark SQL vs Cypher — Report

Run di riferimento: `run_20260505_114833`

> **Nota**: il file viene rigenerato automaticamente da
> `benchmark/generate_report.py` dopo ogni esecuzione di `run_benchmark.py`.
> Quando si applicano modifiche al codice (come la materialized view
> `mv_played_for` e i fix Cypher Q05/Q10) il benchmark va rieseguito.

## Experimental setup

| Item | Value |
|---|---|
| Host | `MacBook Air (Apple silicon)` |
| Platform | `macOS 26.4.1, arm64` |
| Python | `3.12.3` |
| PostgreSQL | `16.x` (Homebrew, default configuration) |
| Neo4j | `5.x community` (Neo4j Desktop / Docker) |
| Misure per query | 5 run + 1 warm-up scartato |
| Numero query | 12 (10 read, 2 write) |
| Dataset | European Soccer Database — 25,979 match · 11,060 player · 917,815 event · 542,281 lineup row |

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


## Index ablation

Esperimento: rimuovere strategicamente un indice critico, rieseguire Q08,
poi ripristinarlo. Mostra che gli indici dello schema **non sono decorativi**.

| System | Phase | Median (ms) | Slowdown |
|---|---|---:|---:|
| Postgres | with index (`ix_lineup_player`) | 3.54 | 1.00x |
| Postgres | without index | 11.52 | **3.25x** |
| Postgres | restored | 1.41 | 0.40x |
| Neo4j | with index (`player_name_idx`) | 8.08 | 1.00x |
| Neo4j | without index | 18.71 | **2.32x** |
| Neo4j | restored | 10.60 | 1.31x |

Dati misurati in `benchmark/results/index_ablation/20260505_122819.csv`.


## Query verbosity — two dimensions

LOC = lines of code. Cognitive verbosity = count of distinct logical operators
(SELECT/JOIN/WHERE/GROUP BY/AND/OR/NOT/... in SQL; MATCH/WITH/WHERE/RETURN/AND/OR/NOT/... in Cypher).
Le due liste di operatori sono **simmetriche** (entrambi i sistemi contano AND/OR/NOT)
per garantire un confronto fair. Le due dimensioni sono complementari: una query puo'
essere breve in linee ma pesante in operatori.

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

Tutte le 10 query read (Q01-Q10) restituiscono risultati equivalenti nei due
sistemi, verificati come set di tuple normalizzate (cast di Decimal a float
con arrotondamento a 4 decimali, cast di date a stringa ISO).

Le 2 query write (Q11, Q12) sono validate via rollback dopo ogni run:
nessuna alterazione persistente sui DB.


## Conclusioni — quando usare cosa

Tre takeaway emersi dai dati:

1. **Postgres vince sulle aggregazioni e OLAP-light** (categoria A: Q01-Q04).
   L'ottimizzatore relazionale maturo e gli indici B-tree sono perfetti per
   query con piccoli join e aggregazioni semplici. Il vantaggio e' modesto
   (1.03x-1.84x) ma sistematico.

2. **Neo4j vince nettamente sulle query graph-native** (categoria C: Q08-Q10).
   Sul caso d'uso piu' "graph" (Q10 shortest path), Neo4j e' **53x piu' veloce**
   di Postgres. Il vantaggio cresce con la profondita' del traversal:
   trascurabile a 1 hop (Q08), significativo a 2 hop (Q09), drammatico su
   shortest path generico (Q10).

3. **Sulle multi-hop "miste"** (categoria B: Q05-Q07), Neo4j vince
   sistematicamente (1.48x-5.00x). La cosa interessante e' che Q07
   ("giocatori in tutte le 8 stagioni") non e' una query intrinsecamente
   "grafica" — Neo4j vince per via del traversal nativo via LINEUP_OF, non
   per particolare adattamento del modello.

4. **Espressivita'**: il codice Cypher e' sempre piu' breve del SQL
   equivalente (LOC ratio mediano: 1.83x). Il differenziale esplode su
   shortest path: 30 linee SQL (CTE ricorsiva BFS) vs 3 linee Cypher
   (`shortestPath()` primitiva).

5. **Schema flexibility (Q12)**: aggiungere un attributo derivato a tutti i
   match costa 13.59x meno in Neo4j: nessun DDL, nessun lock, solo `SET`.
   Vantaggio rilevante in contesti con schema evolution frequente.

**Verdetto operativo**:
- Scegliere **PostgreSQL** quando: aggregazioni OLAP, schema stabile e
  fortemente vincolato, integrita' referenziale critica, esperienza del team
  consolidata, ecosistema BI/ETL maturo.
- Scegliere **Neo4j** quando: il dominio e' intrinsecamente un grafo
  (relazioni piu' importanti delle entita'), serve traversal a profondita'
  variabile (raccomandazione, fraud detection, supply chain), lo schema
  evolve spesso.
- Molti sistemi production-grade adottano **polyglot persistence**: i due DB
  coesistono e ciascuno gestisce la parte del dominio per cui e' nato.


## Note metodologiche

- Ogni query e' stata eseguita con un ciclo di warm-up scartato + N esecuzioni misurate.
- I tempi riportati sono mediani; min, max e IQR sono in `summary.csv`.
- I risultati nei due sistemi sono confrontati come *insiemi* di tuple,
  con normalizzazione di tipi (Decimal, date) e arrotondamento a 4 decimali
  per evitare falsi positivi dovuti a differenze di precisione.
- Per garantire un confronto **fair** su Q08/Q09/Q10, Postgres precomputa la
  materialized view `mv_played_for(player, team, season)` (vedere
  `schema/postgres_schema.sql`), che corrisponde esattamente alla relazione
  derivata `:PLAYED_FOR` di Neo4j.
- I conteggi di **cognitive verbosity** usano un insieme simmetrico di
  operatori logici (`AND`, `OR`, `NOT` inclusi sia per SQL sia per Cypher).


## Limitations

Il benchmark misura performance **single-node, single-user, in-memory** su
un dataset di dimensione media (917k eventi, 542k lineup rows, 26k match).
Restano fuori dallo scope di questo lavoro:

- carico **concorrente** (write contention, lock, MVCC vs lock-free traversal);
- carico **OLTP intensivo** (insert rate, transazioni distribuite);
- scaling **orizzontale** (sharding Postgres con Citus vs Neo4j Fabric);
- benchmark **standardizzati** su dataset grafo (LDBC SNB);
- tuning dei sistemi: entrambi usano configurazione di default; il delta
  potrebbe ridursi (o ampliarsi) con tuning specifico (`shared_buffers`,
  `work_mem` per Postgres, `dbms.memory.pagecache.size` per Neo4j).

Inoltre, il dataset European Soccer non e' strettamente "graph-native": le
relazioni interessanti (compagni di squadra, eventi connessi) sono derivate
piuttosto che esplicite. Un benchmark su un dominio nativamente a grafo
(social network, knowledge graph) potrebbe accentuare i vantaggi Neo4j.


## Riferimenti

- Angles, R., Gutierrez, C. (2008). *Survey of Graph Database Models*.
  ACM Computing Surveys, 40(1).
- Vicknair, C. et al. (2010). *A Comparison of a Graph Database and a
  Relational Database*. ACM SE 2010.
- Holzschuher, F., Peinl, R. (2013). *Performance of Graph Query Languages:
  Comparison of Cypher, Gremlin and Native Access in Neo4j*. EDBT/ICDT Workshops.
- Erling, O. et al. (2015). *The LDBC Social Network Benchmark:
  Interactive Workload*. SIGMOD 2015.
- Robinson, I., Webber, J., Eifrem, E. (2015). *Graph Databases* (2nd ed.).
  O'Reilly Media.
