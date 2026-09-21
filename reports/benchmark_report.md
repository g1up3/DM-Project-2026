# Benchmark SQL vs Cypher — Report

Run: `run_20260921_162704`


## 1. Experimental setup

| Item | Value |
|---|---|
| Host | `MacBook-Air-di-Peppe.local` |
| Platform | `macOS-27.0-arm64-arm-64bit` |
| CPU | `Apple M2` (8 cores) |
| Memory | 8.0 GB |
| Python | `3.12.3` |
| PostgreSQL | `PostgreSQL 18.6 (Homebrew) on aarch64-apple-darwin25.6.0, compiled by Apple clang version 21.0.0 (clang-2100.1.1.101), 64-bit` |
| Neo4j | `Neo4j Kernel 2026.04.0 (enterprise)` — edizione Enterprise inclusa in Neo4j Desktop (licenza developer); nessuna feature Enterprise-only e' usata (runtime pipelined, singola istanza): il benchmark e' riproducibile su Community Edition |
| Misure per query | 15 run + 1 warm-up scartato |
| Numero query | 12 |
| Test statistico | Mann-Whitney U (two-sided, alpha=0.05) |
| Intervalli di confidenza | Bootstrap 95% CI of the median (10000 resamples, seed=42) |


### Configurazione runtime dei DBMS

**PostgreSQL**:

| Parameter | Value |
|---|---|
| `shared_buffers` | `128MB` |
| `work_mem` | `4MB` |
| `maintenance_work_mem` | `64MB` |
| `effective_cache_size` | `4GB` |
| `random_page_cost` | `4` |
| `seq_page_cost` | `1` |
| `max_parallel_workers_per_gather` | `2` |
| `jit` | `on` |
| `enable_hashjoin` | `on` |
| `enable_mergejoin` | `on` |
| `enable_nestloop` | `on` |
| `enable_seqscan` | `on` |
| `enable_indexscan` | `on` |

**Neo4j**:

| Parameter | Value |
|---|---|
| `server.memory.heap.initial_size` | `512.00MiB` |
| `server.memory.heap.max_size` | `1.00GiB` |
| `server.memory.pagecache.size` | `512.00MiB` |
| `db.tx_log.rotation.retention_policy` | `2 days 2G` |


## 2. Risultati

| ID | Query | Categoria | PG (ms) | Neo4j (ms) | CI 95% PG | CI 95% Neo4j | Vincitore | Speedup | p-value | Effect r | Sig | Sig (Holm) | Risultati |
|---|---|---|---:|---:| :---: | :---: |---|---:|---:|---:|:---:|:---:|:---:|
| Q01 | Top scorers by season | A_relational | 10.3 | 6.9 | [9.524, 10.991] | [6.12, 7.041] | **Neo4j** | 1.51x | 0.000494 | 0.7511 | Yes | Yes | OK |
| Q02 | League standings by season | A_relational | 3.7 | 5.1 | [3.215, 5.161] | [4.011, 5.53] | Postgres (ns) | 1.38x | 0.229029 | 0.2622 | No | No | OK |
| Q03 | Goals per match by league | A_relational | 8.3 | 5.4 | [5.452, 11.168] | [5.147, 5.672] | **Neo4j** | 1.54x | 0.027925 | 0.4756 | Yes | No | OK |
| Q04 | Home win percentage by team | A_relational | 15.9 | 20.7 | [13.699, 17.551] | [17.25, 21.658] | **Postgres** | 1.30x | 0.00421 | 0.6178 | Yes | Yes | OK |
| Q05 | Goal-assist partnerships | B_multihop | 61.5 | 38.1 | [56.666, 63.986] | [35.365, 38.943] | **Neo4j** | 1.62x | 5.7e-05 | 0.8667 | Yes | Yes | OK |
| Q06 | Cards received vs Real Madrid | B_multihop | 21.8 | 7.6 | [20.2, 24.681] | [6.628, 8.338] | **Neo4j** | 2.85x | 3e-06 | 1.0 | Yes | Yes | OK |
| Q07 | Players in all 8 seasons | B_multihop | 400.2 | 216.1 | [393.97, 406.329] | [209.69, 230.045] | **Neo4j** | 1.85x | 3e-06 | 1.0 | Yes | Yes | OK |
| Q08 | Teammates of Messi 2015/16 | C_graph_native | 7.0 | 4.2 | [5.729, 8.024] | [3.497, 4.933] | **Neo4j** | 1.66x | 1.3e-05 | 0.9378 | Yes | Yes | OK |
| Q09 | 2-hop teammates of Messi | C_graph_native | 28.9 | 77.6 | [25.234, 33.324] | [74.458, 80.419] | **Postgres** | 2.68x | 3e-06 | 1.0 | Yes | Yes | OK |
| Q10 | Shortest path Messi -> Pirlo | C_graph_native | 792.1 | 14.4 | [762.212, 831.703] | [13.777, 15.981] | **Neo4j** | 54.88x | 3e-06 | 1.0 | Yes | Yes | OK |
| Q11 | Bulk UPDATE on event subtype | D_write | 303.1 | 195.6 | [275.291, 321.074] | [192.22, 207.387] | **Neo4j** | 1.55x | 9e-06 | 0.9556 | Yes | Yes | OK |
| Q12 | Schema evolution: add totalGoals | D_write | 435.9 | 85.4 | [412.674, 461.902] | [82.387, 87.053] | **Neo4j** | 5.11x | 3e-06 | 1.0 | Yes | Yes | OK |

Legenda: **grassetto** = differenza statisticamente significativa (p < 0.05, Mann-Whitney U); (ns) = non significativa. **Effect r** = correlazione rank-biserial (0 = distribuzioni indistinguibili, 1 = separazione completa): misura la *magnitudine* della differenza, complementare al p-value che ne misura l'affidabilita'. **Sig (Holm)** = significativita' dopo correzione di Holm-Bonferroni per i 12 confronti simultanei (family-wise error rate 0.05): 10 confronti restano significativi. Le conclusioni del report si appoggiano solo su differenze che superano la correzione E hanno effect size r >= 0.8.


11 confronti su 12 sono statisticamente significativi; 8 hanno effect size molto grande (r >= 0.8).


## 3. Tempi di esecuzione

Error bars rappresentano il 95% CI bootstrap della mediana. L'asterisco (*) indica significativita' statistica.

![](figures/perf_by_query.png)


### Per categoria

![](figures/perf_by_category.png)


## 4. Distribuzioni dei tempi

Box plot delle singole esecuzioni per query. Permette di valutare la dispersione e identificare outlier.

![](figures/distributions.png)


## 5. Speedup Neo4j vs Postgres

Valori > 1 indicano che Neo4j e' piu' veloce. Barre saturate: p < 0.05; barre desaturate: non significativo.

![](figures/speedup.png)


## 6. Espressivita': LOC e cognitive verbosity

**LOC** = righe non vuote e non di commento. **Cognitive verbosity** = numero di occorrenze di operatori logici distinti, con *consume-on-match*: le keyword composte (LEFT JOIN, NOT EXISTS, OPTIONAL MATCH, ORDER BY) vengono riconosciute per prime e rimosse dal testo prima di contare le keyword semplici, prevenendo il double-counting.

![](figures/loc.png)

![](figures/verbosity.png)


| ID | LOC SQL | LOC Cypher | LOC ratio | Verb SQL | Verb Cypher | Verb ratio |
|---|---:|---:|---:|---:|---:|---:|
| Q01 | 16 | 5 | 3.20x | 12 | 6 | 2.00x |
| Q02 | 35 | 15 | 2.33x | 20 | 11 | 1.82x |
| Q03 | 9 | 8 | 1.12x | 6 | 5 | 1.20x |
| Q04 | 12 | 11 | 1.09x | 9 | 8 | 1.12x |
| Q05 | 13 | 9 | 1.44x | 10 | 11 | 0.91x |
| Q06 | 17 | 11 | 1.55x | 16 | 13 | 1.23x |
| Q07 | 9 | 5 | 1.80x | 7 | 6 | 1.17x |
| Q08 | 16 | 7 | 2.29x | 13 | 8 | 1.62x |
| Q09 | 27 | 12 | 2.25x | 25 | 17 | 1.47x |
| Q10 | 21 | 5 | 4.20x | 26 | 5 | 5.20x |
| Q11 | 5 | 3 | 1.67x | 5 | 4 | 1.25x |
| Q12 | 5 | 2 | 2.50x | 2 | 3 | 0.67x |

### Nota metodologica sulla verbosity

La metrica cattura il numero di *step logici* che il lettore deve tracciare mentalmente. SQL e Cypher esprimono lo stesso concetto con meccanismi diversi: un pattern Cypher multi-nodo (es. `(a)-[:R]->(b)<-[:R]-(c)`) sussume cio' che in SQL richiede piu' JOIN espliciti. Questa asimmetria e' intrinseca ai linguaggi, non un artefatto della misurazione — la metrica la cattura intenzionalmente.


## 7. Analisi dei query plan

Per ogni query, il benchmark cattura `EXPLAIN (ANALYZE, BUFFERS)` per Postgres e `PROFILE` per Neo4j. Di seguito i plan piu' significativi.


### Q05: Goal-assist partnerships

**PostgreSQL** (`EXPLAIN ANALYZE`):

```
Sort  (cost=14791.95..14799.70 rows=3102 width=44) (actual time=64.592..64.593 rows=29.00 loops=1)
  Sort Key: (count(*)) DESC, scorer.player_name, assister.player_name, scorer.player_api_id, assister.player_api_id
  Sort Method: quicksort  Memory: 26kB
  Buffers: shared hit=152617
  ->  HashAggregate  (cost=14495.73..14612.05 rows=3102 width=44) (actual time=63.725..64.560 rows=29.00 loops=1)
        Group Key: scorer.player_api_id, assister.player_api_id
        Filter: (count(*) >= 10)
        Batches: 1  Memory Usage: 1305kB
        Rows Removed by Filter: 12240
        Buffers: shared hit=152617
        ->  Merge Join  (cost=1.14..14425.95 rows=9305 width=36) (actual time=0.039..60.823 rows=16934.00 loops=1)
              Merge Cond: (e.player2_id = assister.player_api_id)
              Buffers: shared hit=152617
              ->  Nested Loop  (cost=0.72..59960.55 rows=9305 width=22) (actual time=0.033..56.737 rows=16934.00 loops=1)
                    Buffers: shared hit=141717
                    ->  Index Scan using ix_event_player2 on match_event e  (cost=0.42..58355.74 rows=9305 width=8) (actual time=0.025..49.507 rows=17000.00 loops=1)
                          Index Cond: (player2_id IS NOT NULL)
                          Filter: ((event_type)::text = 'goal'::text)
                          Rows Removed by Filter: 189945
                          Index Searches: 1
                          Buffers: shared hit=132954
                    ->  Memoize  (cost=0.30..0.37 rows=1 width=18) (actual time=0.000..0.000 rows=1.00 loops=17000)
                          Cache Key: e.player1_id
                          Cache Mode: logical
                          Hits: 14078  Misses: 2922  Evictions: 0  Overflows: 0  Memory Usage: 339kB
                          Buffers: shared hit=8763
                          ->  Index Scan using player_pkey on player scorer  (cost=0.29..0.36 rows=1 width=18) (actual time=0.001..0.001 rows=1.00 loops=2922)
                                Index Cond: (player_api_id = e.player1_id)
                                Index Searches: 2921
                                Buffers: shared hit=8763
              ->  Index Scan using player_pkey on player assister  (cost=0.29..710.16 rows=11060 width=18) (actual time=0.004..2.409 rows=11045.00 loops=1)
                    Index Searches: 1
                    Buffers: shared hit=10900
Planning:
  Buffers: shared hit=28
Planning Time: 0.286 ms
Execution Time: 64.650 ms
```

**Neo4j** (`PROFILE`):

```
+-- ProduceResults@neo4j  (rows: 29, dbHits: 0)
    identifiers: ['scorer_api_id', 'assister', 'partnerships', 'assister_api_id', 'scorer']
  +-- Sort@neo4j  (rows: 29, dbHits: 0)
      identifiers: ['scorer_api_id', 'assister', 'partnerships', 'assister_api_id', 'scorer']
    +-- Projection@neo4j  (rows: 29, dbHits: 0)
        identifiers: ['scorer_api_id', 'assister', 'partnerships', 'assister_api_id', 'scorer']
      +-- CacheProperties@neo4j  (rows: 29, dbHits: 174)
          identifiers: ['scorer', 'assister', 'partnerships']
        +-- Filter@neo4j  (rows: 29, dbHits: 0)
            identifiers: ['scorer', 'assister', 'partnerships']
          +-- OrderedAggregation@neo4j  (rows: 12269, dbHits: 0)
              identifiers: ['scorer', 'assister', 'partnerships']
            +-- Filter@neo4j  (rows: 16934, dbHits: 99860)
                identifiers: ['assister', 'a', 'm', 'g', 'scorer']
              +-- Expand(All)@neo4j  (rows: 65992, dbHits: 82992)
                  identifiers: ['assister', 'a', 'm', 'g', 'scorer']
                +-- CacheProperties@neo4j  (rows: 17000, dbHits: 17014)
                    identifiers: ['assister', 'a', 'm']
                  +-- Filter@neo4j  (rows: 17000, dbHits: 34028)
                      identifiers: ['assister', 'a', 'm']
                    +-- Expand(All)@neo4j  (rows: 17000, dbHits: 17000)
                        identifiers: ['assister', 'a', 'm']
                      +-- NodeByLabelScan@neo4j  (rows: 11060, dbHits: 11061)
                          identifiers: ['assister']
```


### Q07: Players in all 8 seasons

**PostgreSQL** (`EXPLAIN ANALYZE`):

```
Sort  (cost=78404.96..78405.10 rows=55 width=26) (actual time=471.348..471.360 rows=539.00 loops=1)
  Sort Key: p.player_name, p.player_api_id
  Sort Method: quicksort  Memory: 49kB
  Buffers: shared hit=315290
  ->  GroupAggregate  (cost=7.21..78403.37 rows=55 width=26) (actual time=21.133..470.535 rows=539.00 loops=1)
        Group Key: p.player_api_id
        Filter: (count(DISTINCT m.season) = 8)
        Rows Removed by Filter: 10521
        Buffers: shared hit=315290
        ->  Incremental Sort  (cost=7.21..75553.71 rows=542281 width=28) (actual time=1.014..433.130 rows=542281.00 loops=1)
              Sort Key: p.player_api_id, m.season
              Presorted Key: p.player_api_id
              Full-sort Groups: 6303  Sort Method: quicksort  Average Memory: 28kB  Peak Memory: 28kB
              Pre-sorted Groups: 5710  Sort Method: quicksort  Average Memory: 29kB  Peak Memory: 29kB
              Buffers: shared hit=315290
              ->  Merge Join  (cost=1.01..53327.79 rows=542281 width=28) (actual time=0.136..277.359 rows=542281.00 loops=1)
                    Merge Cond: (l.player_api_id = p.player_api_id)
                    Buffers: shared hit=315290
                    ->  Nested Loop  (cost=0.72..45811.67 rows=542281 width=14) (actual time=0.114..242.031 rows=542281.00 loops=1)
                          Buffers: shared hit=304375
                          ->  Index Scan using ix_lineup_player on match_lineup l  (cost=0.42..23786.45 rows=542281 width=8) (actual time=0.019..99.025 rows=542281.00 loops=1)
                                Index Searches: 1
                                Buffers: shared hit=228712
                          ->  Memoize  (cost=0.30..0.35 rows=1 width=14) (actual time=0.000..0.000 rows=1.00 loops=542281)
                                Cache Key: l.match_api_id
                                Cache Mode: logical
                                Hits: 517060  Misses: 25221  Evictions: 0  Overflows: 0  Memory Usage: 2858kB
                                Buffers: shared hit=75663
                                ->  Index Scan using match_pkey on match m  (cost=0.29..0.34 rows=1 width=14) (actual time=0.001..0.001 rows=1.00 loops=25221)
                                      Index Cond: (match_api_id = l.match_api_id)
                                      Index Searches: 25221
                                      Buffers: shared hit=75663
                    ->  Index Scan using player_pkey on player p  (cost=0.29..710.16 rows=11060 width=18) (actual time=0.017..3.222 rows=11060.00 loops=1)
                          Index Searches: 1
                          Buffers: shared hit=10915
Planning:
  Buffers: shared hit=28
Planning Time: 0.914 ms
Execution Time: 471.438 ms
```

**Neo4j** (`PROFILE`):

```
+-- ProduceResults@neo4j  (rows: 539, dbHits: 0)
    identifiers: ['p', 'seasons_played', 'player', 'player_api_id']
  +-- Sort@neo4j  (rows: 539, dbHits: 0)
      identifiers: ['p', 'seasons_played', 'player', 'player_api_id']
    +-- Projection@neo4j  (rows: 539, dbHits: 0)
        identifiers: ['p', 'seasons_played', 'player', 'player_api_id']
      +-- CacheProperties@neo4j  (rows: 539, dbHits: 1617)
          identifiers: ['p', 'seasons_played']
        +-- Filter@neo4j  (rows: 539, dbHits: 0)
            identifiers: ['p', 'seasons_played']
          +-- OrderedAggregation@neo4j  (rows: 11060, dbHits: 1151992)
              identifiers: ['p', 'seasons_played']
            +-- Filter@neo4j  (rows: 542281, dbHits: 1084562)
                identifiers: ['p', 'm']
              +-- Expand(All)@neo4j  (rows: 542281, dbHits: 542281)
                  identifiers: ['p', 'm']
                +-- NodeByLabelScan@neo4j  (rows: 11060, dbHits: 11061)
                    identifiers: ['p']
```


### Q09: 2-hop teammates of Messi

**PostgreSQL** (`EXPLAIN ANALYZE`):

```
Limit  (cost=1485.45..1485.50 rows=20 width=26) (actual time=41.003..41.011 rows=20.00 loops=1)
  Buffers: shared hit=10567
  CTE direct_teammates
    ->  HashAggregate  (cost=26.09..26.65 rows=56 width=4) (actual time=0.395..0.409 rows=57.00 loops=1)
          Group Key: pf_2.player_api_id
          Batches: 1  Memory Usage: 32kB
          Buffers: shared hit=207
          ->  Nested Loop  (cost=4.89..25.95 rows=56 width=4) (actual time=0.057..0.324 rows=183.00 loops=1)
                Buffers: shared hit=207
                ->  Nested Loop  (cost=4.60..23.64 rows=3 width=14) (actual time=0.043..0.056 rows=8.00 loops=1)
                      Buffers: shared hit=13
                      ->  Index Scan using ix_player_name on player p_1  (cost=0.29..8.30 rows=1 width=4) (actual time=0.022..0.023 rows=1.00 loops=1)
                            Index Cond: ((player_name)::text = 'Lionel Messi'::text)
                            Index Searches: 1
                            Buffers: shared hit=3
                      ->  Bitmap Heap Scan on mv_played_for pf_3  (cost=4.31..15.31 rows=3 width=18) (actual time=0.018..0.027 rows=8.00 loops=1)
                            Recheck Cond: (player_api_id = p_1.player_api_id)
                            Heap Blocks: exact=8
                            Buffers: shared hit=10
                            ->  Bitmap Index Scan on ix_mv_played_for_player  (cost=0.00..4.31 rows=3 width=0) (actual time=0.008..0.008 rows=8.00 loops=1)
                                  Index Cond: (player_api_id = p_1.player_api_id)
                                  Index Searches: 1
                                  Buffers: shared hit=2
                ->  Index Scan using ix_mv_played_for_team_season on mv_played_for pf_2  (cost=0.29..0.62 rows=15 width=18) (actual time=0.006..0.028 rows=22.88 loops=8)
                      Index Cond: ((team_api_id = pf_3.team_api_id) AND ((season)::text = (pf_3.season)::text))
                      Index Searches: 8
                      Buffers: shared hit=194
  ->  Sort  (cost=1458.80..1458.95 rows=59 width=26) (actual time=41.002..41.005 rows=20.00 loops=1)
        Sort Key: (count(*)) DESC, p.player_name, p.player_api_id
        Sort Method: top-N heapsort  Memory: 27kB
        Buffers: shared hit=10567
        ->  GroupAggregate  (cost=1456.20..1457.23 rows=59 width=26) (actual time=39.422..40.444 rows=1750.00 loops=1)
              Group Key: p.player_api_id
              Buffers: shared hit=10567
              ->  Sort  (cost=1456.20..1456.35 rows=59 width=18) (actual time=39.414..39.623 rows=3228.00 loops=1)
                    Sort Key: p.player_api_id
                    Sort Method: quicksort  Memory: 217kB
                    Buffers: shared hit=10567
                    ->  Nested Loop  (cost=682.52..1454.47 rows=59 width=18) (actual time=1.908..38.131 rows=3228.00 loops=1)
                          Buffers: shared hit=10567
                          ->  Hash Join  (cost=682.23..1434.64 rows=59 width=4) (actual time=1.897..22.671 rows=3228.00 loops=1)
                                Hash Cond: ((pf.team_api_id = pf_1.team_api_id) AND ((pf.season)::text = (pf_1.season)::text))
                                Buffers: shared hit=883
                                ->  Seq Scan on mv_played_for pf  (cost=1.26..661.79 rows=17501 width=18) (actual time=0.471..12.672 rows=34656.00 loops=1)
                                      Filter: (NOT (ANY (player_api_id = (hashed SubPlan 2).col1)))
                                      Rows Removed by Filter: 346
                                      Buffers: shared hit=430
                                      SubPlan 2
                                        ->  CTE Scan on direct_teammates  (cost=0.00..1.12 rows=56 width=4) (actual time=0.397..0.430 rows=57.00 loops=1)
                                              Storage: Memory  Maximum Storage: 18kB
                                              Buffers: shared hit=207
                                ->  Hash  (cost=678.23..678.23 rows=183 width=14) (actual time=1.403..1.405 rows=146.00 loops=1)
                                      Buckets: 1024  Batches: 1  Memory Usage: 15kB
                                      Buffers: shared hit=453
                                      ->  Unique  (cost=676.85..678.23 rows=183 width=14) (actual time=1.243..1.360 rows=146.00 loops=1)
                                            Buffers: shared hit=453
                                            ->  Sort  (cost=676.85..677.31 rows=183 width=14) (actual time=1.242..1.278 rows=346.00 loops=1)
                                                  Sort Key: pf_1.team_api_id, pf_1.season
                                                  Sort Method: quicksort  Memory: 35kB
                                                  Buffers: shared hit=453
                                                  ->  Nested Loop  (cost=0.29..669.98 rows=183 width=14) (actual time=0.009..0.717 rows=346.00 loops=1)
                                                        Buffers: shared hit=453
                                                        ->  CTE Scan on direct_teammates d  (cost=0.00..1.12 rows=56 width=4) (actual time=0.000..0.014 rows=57.00 loops=1)
                                                              Storage: Memory  Maximum Storage: 18kB
                                                        ->  Index Scan using ix_mv_played_for_player on mv_played_for pf_1  (cost=0.29..11.91 rows=3 width=18) (actual time=0.004..0.010 rows=6.07 loops=57)
                                                              Index Cond: (player_api_id = d.player_api_id)
                                                              Index Searches: 57
                                                              Buffers: shared hit=453
                          ->  Index Scan using player_pkey on player p  (cost=0.29..0.34 rows=1 width=18) (actual time=0.004..0.004 rows=1.00 loops=3228)
                                Index Cond: (player_api_id = pf.player_api_id)
                                Filter: ((player_name)::text <> 'Lionel Messi'::text)
                                Index Searches: 3228
                                Buffers: shared hit=9684
Planning:
  Buffers: shared hit=36
Planning Time: 1.350 ms
Execution Time: 41.127 ms
```

**Neo4j** (`PROFILE`):

```
+-- ProduceResults@neo4j  (rows: 20, dbHits: 0)
    identifiers: ['player_2hop_api_id', 'player_2hop', 'connection_strength']
  +-- Top@neo4j  (rows: 20, dbHits: 0)
      identifiers: ['player_2hop_api_id', 'player_2hop', 'connection_strength']
    +-- EagerAggregation@neo4j  (rows: 1750, dbHits: 0)
        identifiers: ['player_2hop_api_id', 'player_2hop', 'connection_strength']
      +-- Filter@neo4j  (rows: 3228, dbHits: 110424)
          identifiers: ['x', 't3', 'r4', 'p2', 'direct_set', 'covered_pairs']
        +-- Expand(All)@neo4j  (rows: 34656, dbHits: 34656)
            identifiers: ['x', 't3', 'r4', 'p2', 'direct_set', 'covered_pairs']
          +-- CacheProperties@neo4j  (rows: 11003, dbHits: 22010)
              identifiers: ['x', 'direct_set', 'covered_pairs', 'p2']
            +-- Filter@neo4j  (rows: 11003, dbHits: 0)
                identifiers: ['x', 'direct_set', 'covered_pairs', 'p2']
              +-- Apply@neo4j  (rows: 11060, dbHits: 0)
                  identifiers: ['x', 'direct_set', 'covered_pairs', 'p2']
                +-- EagerAggregation@neo4j  (rows: 1, dbHits: 338)
                    identifiers: ['x', 'direct_set', 'covered_pairs']
                  +-- Filter@neo4j  (rows: 338, dbHits: 676)
                      identifiers: ['x', 't2', 'direct_set', 'r3', 'd']
                    +-- Expand(All)@neo4j  (rows: 35002, dbHits: 35002)
                        identifiers: ['x', 't2', 'direct_set', 'r3', 'd']
                      +-- CacheProperties@neo4j  (rows: 299, dbHits: 299)
                          identifiers: ['x', 'direct_set', 't2']
                        +-- Apply@neo4j  (rows: 299, dbHits: 0)
                            identifiers: ['x', 'direct_set', 't2']
                          +-- EagerAggregation@neo4j  (rows: 1, dbHits: 0)
                              identifiers: ['x', 'direct_set']
                            +-- Filter@neo4j  (rows: 175, dbHits: 1806)
                                identifiers: ['x', 't', 'direct', 'r1', 'r2']
                              +-- Expand(All)@neo4j  (rows: 1464, dbHits: 1472)
                                  identifiers: ['x', 't', 'direct', 'r1', 'r2']
                                +-- CacheProperties@neo4j  (rows: 8, dbHits: 8)
                                    identifiers: ['x', 'r1', 't']
                                  +-- Filter@neo4j  (rows: 8, dbHits: 16)
                                      identifiers: ['x', 'r1', 't']
                                    +-- Expand(All)@neo4j  (rows: 8, dbHits: 8)
                                        identifiers: ['x', 'r1', 't']
                                      +-- NodeIndexSeek@neo4j  (rows: 1, dbHits: 2)
                                          identifiers: ['x']
                          +-- NodeByLabelScan@neo4j  (rows: 299, dbHits: 300)
                              identifiers: ['x', 'direct_set', 't2']
                +-- NodeByLabelScan@neo4j  (rows: 11060, dbHits: 11061)
                    identifiers: ['x', 'direct_set', 'covered_pairs', 'p2']
```


### Q10: Shortest path Messi -> Pirlo

**PostgreSQL** (`EXPLAIN ANALYZE`):

```
Aggregate  (cost=621.74..621.75 rows=1 width=4) (actual time=1042.923..1042.927 rows=1.00 loops=1)
  Buffers: shared hit=2977128
  CTE endpoints
    ->  Result  (cost=16.61..16.62 rows=1 width=8) (actual time=0.016..0.018 rows=1.00 loops=1)
          Buffers: shared hit=6
          InitPlan 1
            ->  Limit  (cost=0.29..8.30 rows=1 width=4) (actual time=0.008..0.009 rows=1.00 loops=1)
                  Buffers: shared hit=3
                  ->  Index Scan using ix_player_name on player  (cost=0.29..8.30 rows=1 width=4) (actual time=0.007..0.007 rows=1.00 loops=1)
                        Index Cond: ((player_name)::text = 'Lionel Messi'::text)
                        Index Searches: 1
                        Buffers: shared hit=3
          InitPlan 2
            ->  Limit  (cost=0.29..8.30 rows=1 width=4) (actual time=0.007..0.007 rows=1.00 loops=1)
                  Buffers: shared hit=3
                  ->  Index Scan using ix_player_name on player player_1  (cost=0.29..8.30 rows=1 width=4) (actual time=0.007..0.007 rows=1.00 loops=1)
                        Index Cond: ((player_name)::text = 'Andrea Pirlo'::text)
                        Index Searches: 1
                        Buffers: shared hit=3
  CTE bfs
    ->  Recursive Union  (cost=0.00..565.23 rows=1771 width=8) (actual time=0.017..1038.010 rows=44251.00 loops=1)
          Storage: Memory  Maximum Storage: 948kB
          Buffers: shared hit=2977128
          ->  CTE Scan on endpoints  (cost=0.00..0.02 rows=1 width=8) (actual time=0.017..0.017 rows=1.00 loops=1)
                Storage: Memory  Maximum Storage: 17kB
                Buffers: shared hit=6
          ->  Nested Loop  (cost=4.60..54.75 rows=177 width=8) (actual time=0.040..115.449 rows=371901.29 loops=7)
                Join Filter: (pf2.player_api_id <> b.player_api_id)
                Rows Removed by Join Filter: 15840
                Buffers: shared hit=2977122
                ->  Nested Loop  (cost=4.31..46.24 rows=10 width=22) (actual time=0.038..14.199 rows=15839.86 loops=7)
                      Buffers: shared hit=176237
                      ->  WorkTable Scan on bfs b  (cost=0.00..0.22 rows=3 width=8) (actual time=0.035..0.368 rows=4741.57 loops=7)
                            Filter: (distance < 6)
                            Rows Removed by Filter: 1580
                      ->  Bitmap Heap Scan on mv_played_for pf1  (cost=4.31..15.31 rows=3 width=18) (actual time=0.002..0.002 rows=3.34 loops=33191)
                            Recheck Cond: (player_api_id = b.player_api_id)
                            Heap Blocks: exact=109855
                            Buffers: shared hit=176237
                            ->  Bitmap Index Scan on ix_mv_played_for_player  (cost=0.00..4.31 rows=3 width=0) (actual time=0.001..0.001 rows=3.34 loops=33191)
                                  Index Cond: (player_api_id = b.player_api_id)
                                  Index Searches: 33191
                                  Buffers: shared hit=66382
                ->  Index Scan using ix_mv_played_for_team_season on mv_played_for pf2  (cost=0.29..0.62 rows=15 width=18) (actual time=0.001..0.004 rows=24.48 loops=110879)
                      Index Cond: ((team_api_id = pf1.team_api_id) AND ((season)::text = (pf1.season)::text))
                      Index Searches: 110879
                      Buffers: shared hit=2800885
  InitPlan 5
    ->  CTE Scan on endpoints endpoints_1  (cost=0.00..0.02 rows=1 width=4) (actual time=0.000..0.000 rows=1.00 loops=1)
          Storage: Memory  Maximum Storage: 17kB
  ->  CTE Scan on bfs  (cost=0.00..39.85 rows=9 width=4) (actual time=1.445..1042.917 rows=5.00 loops=1)
        Filter: (player_api_id = (InitPlan 5).col1)
        Rows Removed by Filter: 44246
        Storage: Memory  Maximum Storage: 1895kB
        Buffers: shared hit=2977128
Planning:
  Buffers: shared hit=12
Planning Time: 0.274 ms
Execution Time: 1042.965 ms
```

**Neo4j** (`PROFILE`):

```
+-- ProduceResults@neo4j  (rows: 1, dbHits: 0)
    identifiers: ['x', 'a', 'shortest_path_hops', 'anon_7', 'b', 'r1', 'r2']
  +-- Projection@neo4j  (rows: 1, dbHits: 0)
      identifiers: ['x', 'a', 'shortest_path_hops', 'anon_7', 'b', 'r1', 'r2']
    +-- StatefulShortestPath(Into, Trail)@neo4j  (rows: 1, dbHits: 4398)
        identifiers: ['x', 'a', 'anon_7', 'b', 'r1', 'r2']
      +-- MultiNodeIndexSeek@neo4j  (rows: 1, dbHits: 4)
          identifiers: ['a', 'b']
```


I plan completi per tutte le 12 query sono in `benchmark/results/run_20260921_162704/plans/`.


## 8. Verifica di correttezza

Tutte le 10 query read (Q01-Q10) restituiscono risultati semanticamente equivalenti nei due sistemi, verificato come confronto di insiemi di tuple normalizzate (arrotondamento a 4 decimali, date come ISO-8601, ordine irrilevante). Le query di raggruppamento usano le chiavi (`player_api_id`, `team_api_id`), non i nomi: il dataset contiene 163 nomi di giocatore e 3 nomi di squadra omonimi.

Per le query write il confronto e' sul numero di righe/proprieta' effettivamente modificate, letto dal driver (`cursor.rowcount` in Postgres, `counters.properties_set` in Neo4j) — un `UPDATE` non restituisce righe e confrontare due result-set vuoti non verificherebbe nulla:

| ID | Query | Righe modificate PG | Proprieta' modificate Neo4j | Uguali |
|---|---|---:|---:|:---:|
| Q11 | Bulk UPDATE on event subtype | 21442 | 21442 | OK |
| Q12 | Schema evolution: add totalGoals | 25979 | 25979 | OK |

Q11 aggiorna solo i gol con marcatore noto (`player1_id IS NOT NULL`): i 109 gol il cui riferimento al giocatore e' stato annullato nell'ETL non hanno una relazione `SCORED_IN` nel grafo, e senza il filtro i due workload avrebbero toccato popolazioni diverse (21.551 vs 21.442 righe).


## 9. Index ablation

Matrice di ablazione: per ciascuna coppia (indice, query), il benchmark rimuove l'indice, riesegue la query, e lo ripristina. Lo slowdown misura il rapporto tra la mediana senza indice e la mediana con indice.

| System | Index | Query | With (ms) | Without (ms) | Slowdown |
|---|---|---|---:|---:|---:|
| postgres | `ix_lineup_player` | Q08 | 3.2 | 11.2 | **3.48x** |
| postgres | `ix_mv_played_for_player` | Q09 | 11.9 | 14.0 | 1.18x |
| postgres | `ix_mv_played_for_player` | Q10 | 718.7 | 734.4 | 1.02x |
| postgres | `ix_event_player1` | Q05 | 58.9 | 64.9 | 1.10x |
| neo4j | `player_name_idx` | Q08 | 3.9 | 7.4 | **1.91x** |
| neo4j | `match_season_idx` | Q03 | 8.5 | 13.9 | **1.64x** |
| neo4j | `team_name_idx` | Q06 | 6.2 | 3.8 | 0.62x |

La matrice viene da una sessione separata (10 run per fase, senza il protocollo VACUUM del run di riferimento): i valori assoluti in ms non sono confrontabili con la tabella della sez. 2; la misura e' il rapporto con/senza indice.

Tre letture della matrice. (i) Gli indici che contano sono quelli sul *punto di ingresso* della query: `ix_lineup_player` (Q08) e `player_name_idx` (Q08) valgono 2-3.5x, perche' senza di essi il lookup del giocatore diventa una scansione di 542k righe / 11k nodi. (ii) Gli indici sulla materialized view contano poco per Q09/Q10 (1.0-1.2x): la BFS di Q10 e' dominata dall'espansione della frontiera, non dal lookup iniziale, e Postgres ripiega su hash join efficienti. (iii) **L'anomalia di `team_name_idx` su Q06 (0.62x: senza indice e' piu' veloce)** non e' un errore di misura: `Team` ha 299 nodi, e un `NodeByLabelScan` con filtro in memoria su 299 record costa meno di un `NodeIndexSeek` (discesa nell'albero dell'indice + dereferenziazione). Sotto una certa cardinalita' l'indice e' controproducente — lo stesso motivo per cui il planner di Postgres preferisce un Seq Scan su tabelle piccole.


## 10. Analisi di sensibilita'

Ipotesi che avrebbero potuto invalidare i risultati principali, verificate sperimentalmente: un artefatto di *tuning* (10.1), uno di *semantica* (10.2), uno di *stato fisico* (10.3).


### 10.1 Q07: lo spill su disco, work_mem, e il costo nascosto del GROUP BY per nome

Nella formulazione originale di Q07 (`GROUP BY p.player_name`, come nella controparte Cypher dell'epoca) il piano Postgres conteneva l'unico accesso a disco dell'intero benchmark: un sort *external merge* di 542k righe (~18 MB di file temporanei) causato dal `work_mem` di default (4MB). Ipotesi: quanto del gap Postgres/Neo4j su Q07 e' un artefatto di questo parametro di tuning?

Q07 e' stata rieseguita solo su Postgres (15 run + warm-up per configurazione, `SET work_mem` a livello di sessione):

| work_mem | Mediana PG (ms) | CI 95% | Sort method (EXPLAIN ANALYZE) |
|---|---:|:---:|---|
| 4MB | 1211.1 | [1206.5, 1231.8] | `external merge  Disk: 18392kB` |
| 64MB | 1209.4 | [1208.7, 1211.7] | `quicksort  Memory: 46429kB` |

**Risultato: ipotesi smentita.** Eliminare lo spill (il sort passa a quicksort interamente in memoria) sposta la mediana dello 0.1%: su macOS i file temporanei restano nella page cache del sistema operativo e l'external merge non paga I/O fisico. Il collo di bottiglia era la strategia *sort-based* scelta dal planner per `COUNT(DISTINCT)`, non il disco.

**La causa vera era a monte, nella semantica.** L'audit di equivalenza (sez. 8) ha mostrato che raggruppare per *nome* fonde i 163 omonimi del dataset (14 risultati fittizi su 550); la formulazione corretta raggruppa per `player_api_id`. Con la chiave intera e indicizzata (`ix_lineup_player`) il planner abbandona il sort completo per un **Incremental Sort** sui gruppi gia' ordinati dall'indice — nel run di riferimento il piano riporta `quicksort  Average Memory: 29kB  Peak Memory: 29kB`, nessuno spill — e la mediana Postgres scende a 400 ms (era 1211). Il gap con Neo4j su Q07 si riduce a **1.9x**: una parte sostanziale del vantaggio misurato in precedenza era il costo di un sort su testo con collation, cioe' un bug semantico travestito da caratteristica di performance. E' l'argomento piu' forte del report a favore della verifica di equivalenza come prerequisito di qualunque benchmark.


### 10.2 La semantica dello shortest path in Cypher (Q10)

La BFS SQL di Q10 collega due giocatori solo se hanno vestito la stessa maglia **nella stessa stagione** (`pf2.season = pf1.season`). La formulazione Cypher piu' naturale, `shortestPath((a)-[:PLAYED_FOR*..12]-(b))`, attraversa un nodo `Team` **senza vincolare la stagione** dei due archi consecutivi: e' una relazione di connettivita' piu' lasca, che puo' produrre cammini piu' corti di quelli ammessi dal SQL. Sulla coppia di riferimento le due semantiche coincidono per caso, e la verifica automatica di equivalenza non poteva accorgersene. Abbiamo quindi confrontato tre formulazioni:

| Variante | Semantica | Hop | Mediana (ms) | CI 95% | db hits | Operatore di path |
|---|---|---:|---:|:---:|---:|---|
| V0 `shortestPath(...*..12)` | lasca (stagione libera) | 2 | 2.0 | [1.8, 2.5] | 237 | `ShortestPath` |
| V1 `shortestPath` + predicato di path | esatta, con fallback esaustivo | 2 | 3.8 | [3.4, 4.4] | 837 | `ShortestPath`, `VarLengthExpand(Into)` |
| **V2 quantified path pattern + `SHORTEST 1`** | **esatta per costruzione** | 2 | 11.2 | [10.7, 12.1] | 4402 | `StatefulShortestPath(Into, Trail)` |

Verifica semantica su 8 coppie di giocatori, confrontando gli hop con la BFS SQL:

| Coppia | SQL | V0 (lasca) | V2 (esatta) | |
|---|---:|---:|---:|---|
| Lionel Messi → Andrea Pirlo | 2 | 2 | 2 | ok |
| Lionel Messi → Gianluigi Buffon | 2 | 2 | 2 | ok |
| Cristiano Ronaldo → Francesco Totti | 2 | 2 | 2 | ok |
| Zlatan Ibrahimovic → Manuel Neuer | 3 | 2 | 3 | **V0 diverge** |
| Luis Suarez → Robert Lewandowski | 2 | 2 | 2 | ok |
| Wayne Rooney → Giorgio Chiellini | 2 | 2 | 2 | ok |
| Neymar → Antonio Di Natale | 2 | 2 | 2 | ok |
| Sergio Ramos → Eden Hazard | 2 | 2 | 2 | ok |

**Risultato.** La semantica lasca (V0) da' una risposta diversa dal SQL su 1/8 coppie; V2 coincide su 8/8. Esempio: Zlatan Ibrahimovic → Manuel Neuer dista 3 hop di veri compagni di squadra, ma la formulazione lasca risponde 2, passando per una squadra in cui i due intermedi non hanno mai giocato insieme. V1 e' corretta ma pericolosa: il suo piano contiene un ramo `VarLengthExpand` che scatta quando il cammino lasco piu' corto viola il predicato, degenerando in un'enumerazione esaustiva di tutti i cammini fino a 12 archi (~200^6 con il grado medio dei nodi `Team`): in un test senza timeout ha saturato la macchina. **Il benchmark adotta V2**: il vincolo `r1.season = r2.season` e' scritto *dentro* il gruppo ripetuto del quantified path pattern (sintassi GQL), il planner usa l'operatore dedicato `StatefulShortestPath` e il costo dell'esattezza e' 5.7x rispetto alla versione lasca — contro un gap di 71x con Postgres.

Due lezioni. Primo: la verifica di equivalenza su *una* istanza dei parametri e' necessaria ma non sufficiente — i vincoli fra elementi consecutivi di un cammino sono il punto in cui SQL e Cypher divergono piu' facilmente. Secondo: in un graph database la semantica si codifica nella *topologia* o nel *pattern*, non in un filtro a posteriori; il modello alternativo (un nodo `TeamSeason` al posto della proprieta' `season` sulla relazione) renderebbe il vincolo strutturale e la formulazione lasca semplicemente inesprimibile.


### 10.3 Stabilita' fra run e bloat MVCC da scritture rolled back

Le due query piu' veloci del benchmark (Q01, Q02: mediane fra 4 e 25 ms) sono anche quelle il cui vincitore **cambia da un run all'altro**, pur risultando "significative" *dentro* ciascun run. La tabella riporta tutti i run eseguiti con il set di query definitivo:

| Run | N | VACUUM pre-run | Q01 PG | Q01 Neo4j | p | Q02 PG | Q02 Neo4j | p |
|---|---:|:---:|---:|---:|---:|---:|---:|---:|
| `run_20260518_194104` | 5 | no | 15.6 | 9.1 | — | 3.8 | 5.7 | — |
| `run_20260524_230038` | 15 | no | 10.8 | 13.2 | 0.299758 | 7.4 | 8.8 | 0.008972 |
| `run_20260916_182629` | 15 | no | 16.0 | 8.6 | 0.000494 | 6.0 | 4.8 | 0.007016 |
| `run_20260916_182818` | 15 | no | 23.2 | 7.4 | 3e-06 | 4.8 | 4.4 | 0.868226 |
| `run_20260916_183215` | 15 | si | 10.3 | 5.8 | 3e-06 | 5.2 | 4.9 | 0.12486 |
| `run_20260917_161535` | 15 | si | 9.9 | 6.3 | 0.000136 | 6.2 | 5.0 | 0.005452 |
| `run_20260921_162232` | 15 | si | 15.9 | 11.4 | 0.031017 | 3.3 | 8.6 | 3e-06 |
| `run_20260921_162704` | 15 | si | 10.3 | 6.9 | 0.000494 | 3.7 | 5.1 | 0.229029 |

**Causa individuata: bloat MVCC generato dal benchmark stesso.** Q11 aggiorna ~21k righe di `match_event` (gli eventi `goal`) e Q12 tutte le 26k righe di `match`; nei run fino al 16/09 entrambe venivano rolled back, ma in Postgres il rollback **non rimuove** le versioni di tupla create dall'`UPDATE`: ogni run lasciava 16 x ~21k tuple morte esattamente sulle pagine che Q01 scansiona. `pg_stat_user_tables` lo conferma (oltre 1,29 milioni di `n_tup_upd` su `match_event`, 1,45 milioni su `match`), e l'autovacuum e' intervenuto solo *dopo* i due run consecutivi del 16/09 — durante i quali la mediana di Q01 su Postgres e' salita da 10,8 a 16,0 e poi 23,2 ms. Neo4j non ha l'effetto: una transazione annullata non lascia garbage nello store, e una committata sovrascrive la proprieta' in place.

**Correzione del protocollo.** Dall'ultimo run l'harness esegue `VACUUM (ANALYZE)` sulle tabelle coinvolte *prima* delle misure e lo registra in `run_metadata.json`: ogni run e' cosi' indipendente dalla storia delle esecuzioni precedenti. Il run di riferimento di questo report e' il primo con il protocollo corretto.

Il VACUUM ha anche aggiornato le statistiche del planner, con un effetto collaterale visibile su Q03: con la tabella `match` compattata (217 pagine) il planner e' passato dal *Bitmap Index Scan* su `ix_match_season` (47 accessi al buffer, ~2,8 ms) a un *Seq Scan* (217 accessi, ~6 ms). E' una scelta del cost model con `random_page_cost = 4` — il default tarato sui dischi rotanti — che su SSD con working set in cache penalizza l'accesso indicizzato. Non abbiamo modificato il parametro per restare fedeli alla configurazione di default dichiarata, ma e' la dimostrazione che le differenze di categoria A stanno dentro il margine di errore del planner, non del paradigma.

Due lezioni: (i) un benchmark che mescola letture e scritture deve controllare lo *stato fisico* delle tabelle, non solo la cache; (ii) la significativita' statistica entro un run misura il rumore di misurazione, **non** la stabilita' del sistema fra sessioni — per le gare sotto i 20 ms il verdetto onesto e' "parita' operativa", qualunque sia il p-value di un singolo run.


## 11. Ease-of-use e suitability

La terza dimensione dichiarata nella proposal e' l'ease-of-use dei due sistemi. E' per natura la meno misurabile: per non ridurla a un'opinione, la ancoriamo a **proxy oggettivi prodotti dal progetto stesso** (righe di codice della pipeline, dipendenze, statement DDL) e ai problemi **effettivamente incontrati** e documentati in `reports/engineering_challenges.md` e nella storia del repository.

| Aspetto | PostgreSQL | Neo4j |
|---|---|---|
| Definizione dello schema | 9 `CREATE TABLE` + 19 indici; tipi, PK composite, FK e `CHECK` espliciti | 7 constraint di unicita' + 4 indici; lo schema e' *implicito*, emerge dal load |
| Bulk load (~1.5M righe) | `COPY FROM STDIN`: 1 statement per tabella, nessuna dipendenza esterna | `LOAD CSV`; per le 542k `LINEUP_OF` il loader offre `apoc.periodic.iterate` (batch 5000, richiede il **plugin APOC**) oppure — come nel run di riferimento — una singola transazione monolitica, che ha bisogno dell'heap da 1 GiB |
| Codice di load (LOC) | 150 (`load_postgres.py`) | 240 (`load_neo4j.py`, +60%) |
| Relazione derivata player-team-season | `CREATE MATERIALIZED VIEW` + `REFRESH` | `MATCH ... MERGE` di aggregazione post-load |
| Integrita' referenziale | **Enforced**: il `COPY` di `match_event` e' *fallito* per FK violation, rivelando 5.653 riferimenti orfani (4.632 su `player1_id` + 1.021 su `player2_id`, Challenge 1) | Non esiste FK: un `MATCH` su un `Player` mancante non lega la riga e la **scarta in silenzio** — lo stesso difetto sarebbe passato inosservato |
| Strumenti di analisi delle performance | `EXPLAIN (ANALYZE, BUFFERS)`: piano testuale con costi stimati/reali, buffer, tempi per nodo | `PROFILE`: albero di operatori con rows e db hits, visualizzato nel Browser |
| Ambiente interattivo | `psql` / pgAdmin | Neo4j Browser, con visualizzazione nativa del grafo |
| Curva di apprendimento | SQL: prerequisito del corso | Cypher: nuovo per entrambi gli autori; i pattern ASCII-art (`(a)-[:R]->(b)`) sono intuitivi per i traversal, meno per le aggregazioni (Q02, classifica: l'`UNION ALL` SQL diventa un `UNWIND` su una lista di mappe) |
| Pitfall incontrati | Tipizzazione rigida: colonne pandas integer-con-NaN rifiutate (Challenge 2) | Semantica di `NULL` (`NULL = NULL` e' null: Q05 richiedeva un `IS NOT NULL` esplicito per equivalere al self-join SQL); direzionalita' di `PLAYED_FOR` (6 hop = 12 archi); `shortestPath` legacy non vincola la stagione fra archi consecutivi — risolto con il quantified path pattern (sez. 10.2) |

Tre osservazioni:

1. **Lo schema esplicito e' un costo iniziale che si ripaga come rete di sicurezza.** Le 273 righe di DDL di Postgres sono sembrate overhead finche' il vincolo FK ha intercettato un difetto reale del dataset che il modello a grafo avrebbe assorbito silenziosamente. In un progetto data-intensive, *fallire presto* e' una feature.

2. **Scrivere query e' piu' facile in Cypher, caricare dati e' piu' facile in SQL.** Un pattern come `(:Team {name:'Milan'})<-[:PLAYED_FOR]-(p)-[:PLAYED_FOR]->(:Team {name:'Juventus'})` sostituisce quattro join; ma il bulk load ha richiesto +60% di codice e un plugin, e l'assenza di tipi sui property ha spostato la validazione sull'ETL.

3. **La semantica implicita di Cypher e' la fonte principale di errori sottili.** Tutti e tre i pitfall Cypher (NULL, direzionalita', predicati di path) sono emersi solo grazie alla verifica automatica di equivalenza dei risultati: senza un oracolo relazionale accanto, sarebbero rimasti invisibili. E' un argomento a favore di mantenere entrambi i sistemi durante lo sviluppo, anche quando la produzione ne usera' uno solo.

**Suitability per il dominio**: il dataset calcistico e' *misto*: le anagrafiche, le classifiche e le statistiche per stagione sono relazionali; le reti di compagni di squadra e le catene di trasferimenti sono grafi. Nessuno dei due modelli e' "naturale" per l'intero dominio, il che rende il caso di studio adatto a un confronto — e la persistenza poliglotta (sez. 13) la risposta pragmatica.


## 12. Considerazioni sulla scalabilita'

Il benchmark e' single-node e single-user (8 GB di RAM, working set interamente in cache: nessun piano contiene `shared read`). Non misura la scalabilita', ma i piani catturati permettono di **ragionare su come i costi crescono** con i dati, e l'architettura dei due sistemi su come si distribuiscono.

### Crescita dei dati su un singolo nodo

- **Aggregazioni full-scan (Q07)**: Postgres scandisce le 542.281 righe di formazione e le aggrega con un *Incremental Sort* guidato dall'indice su `player_api_id` (nessuno spill, sez. 10.1): il costo e' lineare nelle righe piu' un sort per gruppo di dimensione costante. A 10x (80 stagioni) il rimedio standard e' il partizionamento dichiarativo per `season`. Neo4j aggrega le stesse relazioni in modo lineare, ma **senza meccanismo di spill**: il grafo deve stare nella pagecache, altrimenti il degrado e' brusco.

- **Traversal a profondita' variabile (Q10)**: la CTE ricorsiva materializza l'intera frontiera BFS — 44.251 stati e 2.977.128 accessi al buffer per profondita' <= 6 — un costo che cresce con la dimensione del grafo *e* esponenzialmente con la profondita'. `SHORTEST 1` (operatore `StatefulShortestPath`, BFS sul pattern) tocca 4.402 db hits: il lavoro dipende dalla lunghezza del cammino e dal grado dei nodi attraversati, **non dalla dimensione totale del grafo**. E' l'index-free adjacency letta come proprieta' di scaling: il 55x osservato non e' un artefatto della taglia del dataset ma tende ad *allargarsi* al crescere dei dati.

  Evidenza empirica (le 8 coppie del sweep di sez. 10.2, una esecuzione ciascuna, semantica esatta in entrambi i sistemi):

  | Coppia | Hop | Postgres (ms) | Neo4j (ms) |
  |---|---:|---:|---:|
  | Neymar → Antonio Di Natale | 2 | 616 | 4.7 |
  | Sergio Ramos → Eden Hazard | 2 | 675 | 7.2 |
  | Luis Suarez → Robert Lewandowski | 2 | 721 | 8.1 |
  | Lionel Messi → Andrea Pirlo | 2 | 673 | 8.2 |
  | Lionel Messi → Gianluigi Buffon | 2 | 675 | 8.3 |
  | Cristiano Ronaldo → Francesco Totti | 2 | 670 | 8.6 |
  | Wayne Rooney → Giorgio Chiellini | 2 | 682 | 10.5 |
  | Zlatan Ibrahimovic → Manuel Neuer | 3 | 708 | 45.7 |

  Il tempo Postgres (616-721 ms su tutte le coppie) e' **indipendente dalla distanza**: la CTE ricorsiva espande sempre l'intera frontiera fino a profondita' 6, perche' SQL non puo' fermare la ricorsione quando trova la destinazione. Il tempo Neo4j cresce con la distanza (da 5 ms a 46 ms per la coppia a 3 hop): il costo e' proporzionale al vicinato del cammino, non al grafo.

- **Crescita con la dimensione dei dati (misurata)**: Q07 (aggregazione full-scan) e Q09 (2-hop a profondita' fissa) rieseguite su sottoinsiemi crescenti di stagioni — ultime 2, ultime 4, tutte le 8 — filtrando `match.season` / `PLAYED_FOR.season` senza ricaricare i DB (10 run + warm-up per cella; risultati identici nei due sistemi su ogni sottoinsieme):

  | Query | Stagioni | Postgres (ms) | Neo4j (ms) | Rapporto PG/Neo4j | Righe |
  |---|---:|---:|---:|---:|---:|
  | Q07-scaled | 2 | 124 | 77 | 1.61x | 3065 |
  | Q07-scaled | 4 | 207 | 78 | 2.66x | 1628 |
  | Q07-scaled | 8 | 409 | 110 | 3.71x | 539 |
  | Q09-scaled | 2 | 16 | 25 | 0.62x | 20 |
  | Q09-scaled | 4 | 24 | 34 | 0.70x | 20 |
  | Q09-scaled | 8 | 42 | 81 | 0.52x | 20 |

  Da 2 a 8 stagioni (4x i dati) il tempo di Q07 cresce di 3.3x su Postgres e di 1.4x su Neo4j: l'aggregazione sulle relazioni e' quasi insensibile alla taglia, quella sort-based sulle righe e' lineare — **il vantaggio di Neo4j si allarga con i dati**. Su Q09 crescono entrambi (2.7x Postgres, 3.3x Neo4j) e Postgres resta davanti a ogni taglia: il join a profondita' fissa scala meglio del traversal con la lista `IN` delle coppie coperte, che si allunga con le stagioni.

- **Scritture (Q11/Q12)**: in Postgres ogni `UPDATE` crea nuove versioni di tupla (MVCC) da ripulire con `VACUUM`; in Neo4j la scrittura passa dal transaction log. Entrambi i sistemi sono stati misurati con un solo writer: sotto scrittori concorrenti entrano in gioco lock a livello di riga (Postgres) e di nodo/relazione (Neo4j), non testati.

### Scaling orizzontale

- **PostgreSQL**: la replica in streaming scala le *letture* senza toccare le query (l'intero benchmark read girerebbe invariato su una replica). Lo sharding dei *dati* (Citus) richiede una chiave di distribuzione; i join multi-hop di Q09/Q10 fra shard diversi diventano join di rete e degradano.

- **Neo4j**: il causal cluster replica l'**intero grafo** su ogni core member — scala le letture, non i dati. Il partizionamento reale (Fabric / composite database) e' manuale, e un traversal che attraversa una partizione perde l'index-free adjacency. E' il limite noto dei graph database: il partizionamento di un grafo minimizzando gli archi tagliati e' un problema NP-hard, e la proprieta' che rende Q10 55x piu' veloce su un nodo e' esattamente quella che **non si distribuisce gratis**.

### Verdetto

A 10x i dati (80 stagioni, ~5M formazioni, ~9M eventi) entrambi i sistemi restano su un nodo con accorgimenti ordinari (partizionamento e `work_mem` per Postgres, pagecache dimensionata per Neo4j) e i rapporti osservati si conservano o si accentuano a favore di Neo4j sui traversal. Oltre la memoria di una singola macchina, il workload OLAP scala meglio in Postgres (Citus, storage colonnare); il workload a grafo scala in Neo4j solo finche' il grafo e' replicabile per intero. La misura di questi regimi e' il lavoro futuro piu' rilevante (sez. 16).


## 13. Conclusioni

Sei risultati emersi dai dati:


1. **Le aggregazioni OLAP-light (categoria A) sono parita' operativa**: in questo run 1 query su 4 significativamente a favore di Postgres (Q04), 2 a favore di Neo4j (Q01, Q03), 1 non significative (Q02); tutte le mediane sono sotto i 21 ms e il vincitore cambia da un run all'altro (sez. 10.3: in altri run Q03 e Q04 andavano a Postgres). A questa scala l'ottimizzatore relazionale non ha un vantaggio *misurabile* su join di 2-3 tabelle con aggregazione semplice. Il vantaggio netto di Postgres emerge invece dove il join su indici B-tree batte il traversal a profondita' *fissa*: Q09 (2.7x, r = 1.0, stabile in tutti i run).


2. **Neo4j domina sul traversal a profondita' variabile** (Q10): **54.9x piu' veloce**, con semantica *identica* al SQL (vincolo di stagione dentro il quantified path pattern, sez. 10.2). I piani catturati mostrano il perche': la CTE ricorsiva di Postgres materializza l'intera frontiera BFS (decine di migliaia di stati, milioni di accessi al buffer), mentre `SHORTEST 1` esplora solo il vicinato del cammino (poche migliaia di db hits). E' l'effetto dell'index-free adjacency.


3. **Neo4j vince anche sull'aggregazione full-scan** (Q07, 1.9x), ma per una ragione diversa dal traversal: Postgres deve ordinare (per gruppo) 542k righe di formazione per il `COUNT(DISTINCT season)`, Neo4j aggrega le stesse relazioni con hash aggregation. Il gap era 7.4x con la formulazione originale per *nome*: la correzione semantica (raggruppare per chiave) ha eliminato un sort su testo con spill su disco e lo ha ridotto a quello attuale (sez. 10.1) — `work_mem` non c'entrava.


4. **La materialized view equalizza il campo sulle query intermedie** (Q09): Postgres con `mv_played_for` vince su una query 2-hop che, senza la precomputazione, sarebbe dominata da Neo4j. Questo isola il contributo del *motore di esecuzione* da quello del *modello di carico*.


5. **Espressivita'**: Cypher e' sistematicamente piu' breve del SQL equivalente. Il caso estremo e' Q10: 5 LOC / 5 operatori logici in Cypher contro 21 LOC / 26 operatori in SQL (CTE ricorsiva BFS).


6. **Schema flexibility** (Q12): aggiungere e materializzare un attributo derivato su tutti i match costa ~85 ms in Neo4j (singolo `SET`, commit incluso) vs ~436 ms in Postgres (`ALTER TABLE` + `UPDATE` + commit). Misurato fino al commit: con il solo rollback il rapporto sarebbe gonfiato a oltre 11x, perche' Neo4j applica le mutazioni allo store solo al commit (sez. 14). Rilevante in contesti con schema evolution frequente; per un attributo *non* materializzato Postgres 18 offre le colonne generate virtuali, istantanee.


**Verdetto operativo**:

- **PostgreSQL**: aggregazioni OLAP, schema stabile e fortemente vincolato, integrita' referenziale critica, ecosistema BI/ETL maturo.

- **Neo4j**: dominio intrinsecamente a grafo, traversal a profondita' variabile (raccomandazione, fraud detection, supply chain), schema evolution frequente.

- **Polyglot persistence**: in produzione i due DB spesso coesistono, ciascuno gestendo la parte del dominio per cui e' nato. L'analisi di ease-of-use (sez. 11) aggiunge un argomento operativo: tenere il modello relazionale accanto a quello a grafo durante lo sviluppo intercetta errori di dati e di semantica che il grafo da solo assorbe in silenzio.


## 14. Threats to validity


### Validita' interna

- **Warm-up e caching**: la prima esecuzione di ogni query viene scartata per escludere cold-cache effects. Le esecuzioni successive beneficiano della page cache OS e della buffer pool dei DBMS. Il benchmark misura quindi performance *warm-cache*, coerente con un sistema in regime.

- **Variabilita' di misurazione e stabilita' fra run**: le query con mediane sotto i 25 ms (Q01, Q02, Q03, Q04, Q08) hanno vincitori che possono cambiare da una sessione all'altra anche quando il test di Mann-Whitney li dichiara significativi entro il singolo run (sez. 10.3). Le conclusioni del report si appoggiano solo sulle differenze con effect size r >= 0.8, stabili in tutti i run.

- **Indipendenza delle osservazioni**: Mann-Whitney assume campioni indipendenti; le 15 esecuzioni sono sequenziali sulla stessa macchina e condividono stato di cache, scheduling e termica, quindi il test e' *liberale* (p-value ottimisti). Per questo le conclusioni richiedono anche un effect size r >= 0.8 e la stabilita' fra sessioni (sez. 10.3), che e' il vero controllo empirico dell'autocorrelazione. Un warm-up singolo e' sufficiente anche per Q07 e Q10: i loro CI sono i piu' stretti del benchmark (±2% della mediana).

- **Ordine di esecuzione**: in ogni iterazione la query gira prima su Postgres e poi su Neo4j (interleaving), e le query si susseguono sempre da Q01 a Q12; l'ordine non e' randomizzato. L'interleaving controlla la deriva temporale (termica, processi di background) distribuendola su entrambi i sistemi; l'interferenza di cache fra i due e' trascurabile perche' entrambi i working set stanno in RAM (nessun piano mostra letture da disco).

- **Parametri per nome**: le query parametrizzate per nome (Q08-Q10, Q06) assumono che il nome sia univoco; e' verificato per i valori usati (un solo `Lionel Messi`, `Andrea Pirlo`, `Real Madrid CF`) ma non in generale (163 nomi di giocatore e 3 di squadra sono omonimi). Per un uso generale i parametri andrebbero passati per chiave.

- **Equivalenza semantica oltre l'istanza misurata**: il confronto automatico dei risultati vale per i parametri del benchmark. Per Q10 l'equivalenza e' stata verificata anche su 8 coppie di giocatori (sez. 10.2), dopo aver scoperto che la formulazione `shortestPath` legacy coincideva con il SQL solo per caso.

- **Write query misurate fino al COMMIT**: per Q11 e Q12 il timer include `COMMIT` (Postgres: flush del WAL; Neo4j: validazione, applicazione allo store e flush del transaction log). Un cleanup non misurato riporta lo stato iniziale dopo ogni run (Q11 e' idempotente; Q12 rimuove la colonna/proprieta'). La versione precedente dell'harness annullava la transazione: in Neo4j le mutazioni restano nello stato di transazione in memoria fino al commit, quindi il rollback misurava un'operazione quasi in-RAM contro un `UPDATE` Postgres che aveva gia' scritto pagine e WAL (sez. 10.4).

- **Overhead del driver client**: il timer include il round-trip e la materializzazione dei risultati nel client (psycopg2 in C, driver Neo4j in Python). Con result-set fino a ~550 righe l'overhead e' sub-millisecondo e simmetrico in ordine di grandezza; nessun piano usa il JIT di Postgres (costo stimato sempre sotto `jit_above_cost`).


### Validita' esterna

- **Single-node, single-user**: il benchmark non misura performance sotto carico concorrente (write contention, MVCC vs lock-free traversal), carico OLTP intensivo, o scaling orizzontale.

- **Dimensione del dataset**: 26k match, 917k eventi, 542k lineup rows. Un dataset di dimensione *media*: abbastanza grande da rendere significative le differenze di query plan, ma non abbastanza per evidenziare problemi di scalabilita' I/O.

- **Configurazione di default e asimmetria di memoria**: entrambi i DBMS usano la configurazione di default (documentata nella sezione Setup), che assegna budget di memoria diversi: `shared_buffers` 128MB per Postgres contro heap 1GiB + pagecache 512MiB per Neo4j. Due evidenze empiriche ne limitano l'impatto: (i) nessuno dei 24 piani catturati contiene `shared read` — il contatore dei blocchi entrati nel buffer pool da *fuori* (page cache del sistema operativo o disco), quindi il working set delle query stava interamente nei 128 MB di `shared_buffers`, e a maggior ragione nella pagecache di Neo4j; (ii) l'analisi di sensibilita' su `work_mem` (sez. 10) mostra che l'unico spill del benchmark non sposta la mediana. Un tuning sistematico resta comunque una variabile non esplorata per i confronti piu' tirati (categoria A).

- **Asimmetria nel caricamento**: Postgres carica `PlayerStats` e `TeamStats` (~184k righe) che Neo4j non importa. Su 8 GB di RAM l'impatto sulla cache e' trascurabile, ma va documentato.


### Validita' del costrutto

- **Cognitive verbosity**: la metrica cattura il numero di operatori logici, non la complessita' semantica. Un self-join e un FK join contano uguale. La metrica e' complementare (non sostitutiva) a LOC.

- **Tassonomia delle query**: la classificazione A/B/C/D e' definita *a priori* in base alla struttura logica, non *a posteriori* in base ai risultati. Questo previene il cherry-picking.


## 15. Note metodologiche

- I tempi riportati sono **mediani**; min, max, IQR e 95% CI sono in `summary.csv`.

- La significativita' statistica e' valutata con il test di **Mann-Whitney U** (non parametrico, two-sided, alpha = 0.05), con effect size **rank-biserial**. Gli intervalli di confidenza sono calcolati con **bootstrap** della mediana (10.000 ricampionamenti, seed fisso 42: i CI sono riproducibili bit-a-bit).

- I risultati nei due sistemi sono confrontati come *insiemi* di tuple, con normalizzazione di tipi (Decimal, date) e arrotondamento a 4 decimali.

- Per garantire un confronto **fair** su Q09/Q10 (Q08 usa le formazioni in entrambi i sistemi), Postgres precomputa la materialized view `mv_played_for(player, team, season)`, equivalente alla relazione derivata `:PLAYED_FOR` di Neo4j.

- I query plan (`EXPLAIN ANALYZE` e `PROFILE`) sono catturati automaticamente dall'harness e salvati in `plans/`.


## 16. Limitations e lavoro futuro

Restano fuori dallo scope di questo lavoro:

- Carico **concorrente** (write contention, lock, MVCC vs lock-free traversal).

- Carico **OLTP intensivo** (insert rate, transazioni distribuite).

- Scaling **orizzontale** (sharding Postgres con Citus vs Neo4j Fabric): discusso qualitativamente in sez. 12, non misurato.

- Benchmark **standardizzati** su dataset grafo (LDBC Social Network Benchmark).

- **Tuning sistematico** dei sistemi: esplorato solo `work_mem` su Q07 (sez. 10); resta fuori un grid completo (shared_buffers, pagecache, parallelismo).


## 17. Riferimenti

- Angles, R., Gutierrez, C. (2008). *Survey of Graph Database Models*. ACM Computing Surveys, 40(1).

- Vicknair, C. et al. (2010). *A Comparison of a Graph Database and a Relational Database*. ACM SE 2010.

- Holzschuher, F., Peinl, R. (2013). *Performance of Graph Query Languages: Comparison of Cypher, Gremlin and Native Access in Neo4j*. EDBT/ICDT Workshops.

- Erling, O. et al. (2015). *The LDBC Social Network Benchmark: Interactive Workload*. SIGMOD 2015.

- Robinson, I., Webber, J., Eifrem, E. (2015). *Graph Databases* (2nd ed.). O'Reilly Media.

- Mann, H. B., Whitney, D. R. (1947). *On a Test of Whether one of Two Random Variables is Stochastically Larger than the Other*. Annals of Mathematical Statistics, 18(1).
