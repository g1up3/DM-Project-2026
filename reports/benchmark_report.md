# Benchmark SQL vs Cypher — Report

Run: `run_20260916_183215`


## 1. Experimental setup

| Item | Value |
|---|---|
| Host | `MacBook-Air-di-Peppe.local` |
| Platform | `macOS-27.0-arm64-arm-64bit` |
| CPU | `Apple M2` (8 cores) |
| Memory | 8.0 GB |
| Python | `3.12.3` |
| PostgreSQL | `PostgreSQL 18.6 (Homebrew) on aarch64-apple-darwin25.6.0, compiled by Apple clang version 21.0.0 (clang-2100.1.1.101), 64-bit` |
| Neo4j | `Neo4j Kernel 2026.04.0 (enterprise)` |
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

| ID | Query | Categoria | PG (ms) | Neo4j (ms) | CI 95% PG | CI 95% Neo4j | Vincitore | Speedup | p-value | Effect r | Sig | Risultati |
|---|---|---|---:|---:| :---: | :---: |---|---:|---:|---:|:---:|:---:|
| Q01 | Top scorers by season | A_relational | 10.3 | 5.8 | [10.078, 10.732] | [5.391, 5.918] | **Neo4j** | 1.78x | 3e-06 | 1.0 | Yes | OK |
| Q02 | League standings by season | A_relational | 5.2 | 4.9 | [4.906, 6.604] | [2.901, 5.396] | Neo4j (ns) | 1.07x | 0.12486 | 0.3333 | No | OK |
| Q03 | Goals per match by league | A_relational | 6.3 | 5.4 | [5.75, 7.41] | [4.109, 5.772] | **Neo4j** | 1.17x | 0.046487 | 0.4311 | Yes | OK |
| Q04 | Home win percentage by team | A_relational | 13.6 | 14.8 | [12.025, 15.522] | [13.907, 16.064] | Postgres (ns) | 1.09x | 0.114987 | 0.3422 | No | OK |
| Q05 | Goal-assist partnerships | B_multihop | 55.1 | 41.1 | [54.69, 55.816] | [39.827, 41.486] | **Neo4j** | 1.34x | 3e-06 | 1.0 | Yes | OK |
| Q06 | Cards received vs Real Madrid | B_multihop | 19.1 | 5.5 | [18.35, 19.157] | [4.25, 7.677] | **Neo4j** | 3.50x | 3e-06 | 1.0 | Yes | OK |
| Q07 | Players in all 8 seasons | B_multihop | 1432.1 | 194.3 | [1374.605, 1462.831] | [191.967, 195.793] | **Neo4j** | 7.37x | 3e-06 | 1.0 | Yes | OK |
| Q08 | Teammates of Messi 2015/16 | C_graph_native | 7.1 | 4.1 | [5.617, 7.843] | [3.247, 5.574] | **Neo4j** | 1.75x | 0.00105 | 0.7067 | Yes | OK |
| Q09 | 2-hop teammates of Messi | C_graph_native | 37.4 | 72.0 | [31.896, 38.578] | [70.678, 72.518] | **Postgres** | 1.92x | 5.7e-05 | 0.8667 | Yes | OK |
| Q10 | Shortest path Messi -> Pirlo | C_graph_native | 800.6 | 11.8 | [773.513, 835.566] | [11.215, 12.3] | **Neo4j** | 68.12x | 3e-06 | 1.0 | Yes | OK |
| Q11 | Bulk UPDATE on event subtype | D_write | 363.5 | 163.9 | [356.606, 378.681] | [159.245, 166.721] | **Neo4j** | 2.22x | 3e-06 | 1.0 | Yes | OK |
| Q12 | Schema evolution: add totalGoals | D_write | 399.9 | 30.0 | [346.368, 410.46] | [29.001, 31.369] | **Neo4j** | 13.32x | 3e-06 | 1.0 | Yes | OK |

Legenda: **grassetto** = differenza statisticamente significativa (p < 0.05, Mann-Whitney U); (ns) = non significativa. **Effect r** = correlazione rank-biserial (0 = distribuzioni indistinguibili, 1 = separazione completa): misura la *magnitudine* della differenza, complementare al p-value che ne misura l'affidabilita'.


10 confronti su 12 sono statisticamente significativi; 8 hanno effect size molto grande (r >= 0.8).


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
| Q05 | 11 | 8 | 1.38x | 10 | 11 | 0.91x |
| Q06 | 17 | 11 | 1.55x | 16 | 13 | 1.23x |
| Q07 | 8 | 6 | 1.33x | 7 | 7 | 1.00x |
| Q08 | 15 | 7 | 2.14x | 13 | 8 | 1.62x |
| Q09 | 26 | 12 | 2.17x | 25 | 17 | 1.47x |
| Q10 | 21 | 5 | 4.20x | 26 | 5 | 5.20x |
| Q11 | 4 | 3 | 1.33x | 3 | 4 | 0.75x |
| Q12 | 5 | 2 | 2.50x | 2 | 3 | 0.67x |

### Nota metodologica sulla verbosity

La metrica cattura il numero di *step logici* che il lettore deve tracciare mentalmente. SQL e Cypher esprimono lo stesso concetto con meccanismi diversi: un pattern Cypher multi-nodo (es. `(a)-[:R]->(b)<-[:R]-(c)`) sussume cio' che in SQL richiede piu' JOIN espliciti. Questa asimmetria e' intrinseca ai linguaggi, non un artefatto della misurazione — la metrica la cattura intenzionalmente.


## 7. Analisi dei query plan

Per ogni query, il benchmark cattura `EXPLAIN (ANALYZE, BUFFERS)` per Postgres e `PROFILE` per Neo4j. Di seguito i plan piu' significativi.


### Q05: Goal-assist partnerships

**PostgreSQL** (`EXPLAIN ANALYZE`):

```
Sort  (cost=10841.90..10849.33 rows=2972 width=36) (actual time=57.733..57.734 rows=29.00 loops=1)
  Sort Key: (count(*)) DESC, scorer.player_name, assister.player_name
  Sort Method: quicksort  Memory: 26kB
  Buffers: shared hit=148480
  ->  HashAggregate  (cost=10559.01..10670.46 rows=2972 width=36) (actual time=56.888..57.717 rows=29.00 loops=1)
        Group Key: scorer.player_name, assister.player_name
        Filter: (count(*) >= 10)
        Batches: 1  Memory Usage: 1305kB
        Rows Removed by Filter: 12240
        Buffers: shared hit=148480
        ->  Merge Join  (cost=1.14..10492.14 rows=8916 width=28) (actual time=0.029..53.825 rows=16934.00 loops=1)
              Merge Cond: (e.player2_id = assister.player_api_id)
              Buffers: shared hit=148480
              ->  Nested Loop  (cost=0.72..42455.68 rows=8916 width=18) (actual time=0.024..50.185 rows=16934.00 loops=1)
                    Buffers: shared hit=137580
                    ->  Index Scan using ix_event_player2 on match_event e  (cost=0.42..40862.54 rows=8916 width=8) (actual time=0.019..43.853 rows=17000.00 loops=1)
                          Index Cond: (player2_id IS NOT NULL)
                          Filter: ((event_type)::text = 'goal'::text)
                          Rows Removed by Filter: 189945
                          Index Searches: 1
                          Buffers: shared hit=128817
                    ->  Memoize  (cost=0.30..0.37 rows=1 width=18) (actual time=0.000..0.000 rows=1.00 loops=17000)
                          Cache Key: e.player1_id
                          Cache Mode: logical
                          Hits: 14078  Misses: 2922  Evictions: 0  Overflows: 0  Memory Usage: 343kB
                          Buffers: shared hit=8763
                          ->  Index Scan using player_pkey on player scorer  (cost=0.29..0.36 rows=1 width=18) (actual time=0.001..0.001 rows=1.00 loops=2922)
                                Index Cond: (player_api_id = e.player1_id)
                                Index Searches: 2921
                                Buffers: shared hit=8763
              ->  Index Scan using player_pkey on player assister  (cost=0.29..710.16 rows=11060 width=18) (actual time=0.003..2.103 rows=11045.00 loops=1)
                    Index Searches: 1
                    Buffers: shared hit=10900
Planning:
  Buffers: shared hit=28
Planning Time: 0.174 ms
Execution Time: 57.759 ms
```

**Neo4j** (`PROFILE`):

```
+-- ProduceResults@neo4j  (rows: 29, dbHits: 0)
    identifiers: ['scorer', 'assister', 'partnerships']
  +-- Sort@neo4j  (rows: 29, dbHits: 0)
      identifiers: ['scorer', 'assister', 'partnerships']
    +-- Filter@neo4j  (rows: 29, dbHits: 0)
        identifiers: ['scorer', 'assister', 'partnerships']
      +-- EagerAggregation@neo4j  (rows: 12269, dbHits: 50802)
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
GroupAggregate  (cost=75627.63..79830.34 rows=54 width=22) (actual time=1334.493..1513.269 rows=550.00 loops=1)
  Group Key: p.player_name
  Filter: (count(DISTINCT m.season) = 8)
  Rows Removed by Filter: 10298
  Buffers: shared hit=3752, temp read=2299 written=2308
  ->  Sort  (cost=75627.63..76983.33 rows=542281 width=24) (actual time=1334.326..1465.387 rows=542281.00 loops=1)
        Sort Key: p.player_name, m.season
        Sort Method: external merge  Disk: 18392kB
        Buffers: shared hit=3752, temp read=2299 written=2308
        ->  Hash Join  (cost=1145.38..12855.94 rows=542281 width=24) (actual time=15.237..174.312 rows=542281.00 loops=1)
              Hash Cond: (l.player_api_id = p.player_api_id)
              Buffers: shared hit=3752
              ->  Hash Join  (cost=801.53..11088.06 rows=542281 width=14) (actual time=10.268..103.108 rows=542281.00 loops=1)
                    Hash Cond: (l.match_api_id = m.match_api_id)
                    Buffers: shared hit=3657
                    ->  Seq Scan on match_lineup l  (cost=0.00..8862.81 rows=542281 width=8) (actual time=0.009..17.326 rows=542281.00 loops=1)
                          Buffers: shared hit=3440
                    ->  Hash  (cost=476.79..476.79 rows=25979 width=14) (actual time=10.245..10.245 rows=25979.00 loops=1)
                          Buckets: 32768  Batches: 1  Memory Usage: 1474kB
                          Buffers: shared hit=217
                          ->  Seq Scan on match m  (cost=0.00..476.79 rows=25979 width=14) (actual time=0.007..4.422 rows=25979.00 loops=1)
                                Buffers: shared hit=217
              ->  Hash  (cost=205.60..205.60 rows=11060 width=18) (actual time=4.933..4.934 rows=11060.00 loops=1)
                    Buckets: 16384  Batches: 1  Memory Usage: 691kB
                    Buffers: shared hit=95
                    ->  Seq Scan on player p  (cost=0.00..205.60 rows=11060 width=18) (actual time=0.016..2.025 rows=11060.00 loops=1)
                          Buffers: shared hit=95
Planning:
  Buffers: shared hit=28
Planning Time: 0.337 ms
Execution Time: 1514.486 ms
```

**Neo4j** (`PROFILE`):

```
+-- ProduceResults@neo4j  (rows: 550, dbHits: 0)
    identifiers: ['player_name', 'seasons_played', 'player']
  +-- Sort@neo4j  (rows: 550, dbHits: 0)
      identifiers: ['player_name', 'seasons_played', 'player']
    +-- Projection@neo4j  (rows: 550, dbHits: 0)
        identifiers: ['player_name', 'seasons_played', 'player']
      +-- Filter@neo4j  (rows: 550, dbHits: 0)
          identifiers: ['player_name', 'seasons_played']
        +-- EagerAggregation@neo4j  (rows: 10848, dbHits: 0)
            identifiers: ['player_name', 'seasons_played']
          +-- Projection@neo4j  (rows: 542281, dbHits: 1084562)
              identifiers: ['p', 'm', 'player_name', 'season']
            +-- Filter@neo4j  (rows: 542281, dbHits: 1084562)
                identifiers: ['p', 'm']
              +-- Expand(All)@neo4j  (rows: 542281, dbHits: 542281)
                  identifiers: ['p', 'm']
                +-- CacheProperties@neo4j  (rows: 11060, dbHits: 11584)
                    identifiers: ['p']
                  +-- NodeByLabelScan@neo4j  (rows: 11060, dbHits: 11061)
                      identifiers: ['p']
```


### Q09: 2-hop teammates of Messi

**PostgreSQL** (`EXPLAIN ANALYZE`):

```
Limit  (cost=1485.45..1485.50 rows=20 width=22) (actual time=40.585..40.589 rows=20.00 loops=1)
  Buffers: shared hit=10567
  CTE direct_teammates
    ->  HashAggregate  (cost=26.09..26.65 rows=56 width=4) (actual time=0.605..0.624 rows=57.00 loops=1)
          Group Key: pf_2.player_api_id
          Batches: 1  Memory Usage: 32kB
          Buffers: shared hit=207
          ->  Nested Loop  (cost=4.89..25.95 rows=56 width=4) (actual time=0.087..0.507 rows=183.00 loops=1)
                Buffers: shared hit=207
                ->  Nested Loop  (cost=4.60..23.64 rows=3 width=14) (actual time=0.065..0.082 rows=8.00 loops=1)
                      Buffers: shared hit=13
                      ->  Index Scan using ix_player_name on player p_1  (cost=0.29..8.30 rows=1 width=4) (actual time=0.038..0.039 rows=1.00 loops=1)
                            Index Cond: ((player_name)::text = 'Lionel Messi'::text)
                            Index Searches: 1
                            Buffers: shared hit=3
                      ->  Bitmap Heap Scan on mv_played_for pf_3  (cost=4.31..15.31 rows=3 width=18) (actual time=0.023..0.036 rows=8.00 loops=1)
                            Recheck Cond: (player_api_id = p_1.player_api_id)
                            Heap Blocks: exact=8
                            Buffers: shared hit=10
                            ->  Bitmap Index Scan on ix_mv_played_for_player  (cost=0.00..4.31 rows=3 width=0) (actual time=0.010..0.010 rows=8.00 loops=1)
                                  Index Cond: (player_api_id = p_1.player_api_id)
                                  Index Searches: 1
                                  Buffers: shared hit=2
                ->  Index Scan using ix_mv_played_for_team_season on mv_played_for pf_2  (cost=0.29..0.62 rows=15 width=18) (actual time=0.010..0.045 rows=22.88 loops=8)
                      Index Cond: ((team_api_id = pf_3.team_api_id) AND ((season)::text = (pf_3.season)::text))
                      Index Searches: 8
                      Buffers: shared hit=194
  ->  Sort  (cost=1458.80..1458.95 rows=59 width=22) (actual time=40.582..40.584 rows=20.00 loops=1)
        Sort Key: (count(*)) DESC, p.player_name
        Sort Method: top-N heapsort  Memory: 27kB
        Buffers: shared hit=10567
        ->  GroupAggregate  (cost=1456.20..1457.23 rows=59 width=22) (actual time=39.910..40.381 rows=1735.00 loops=1)
              Group Key: p.player_name
              Buffers: shared hit=10567
              ->  Sort  (cost=1456.20..1456.35 rows=59 width=14) (actual time=39.906..39.993 rows=3228.00 loops=1)
                    Sort Key: p.player_name
                    Sort Method: quicksort  Memory: 97kB
                    Buffers: shared hit=10567
                    ->  Nested Loop  (cost=682.52..1454.47 rows=59 width=14) (actual time=2.291..27.661 rows=3228.00 loops=1)
                          Buffers: shared hit=10567
                          ->  Hash Join  (cost=682.23..1434.64 rows=59 width=4) (actual time=2.280..19.201 rows=3228.00 loops=1)
                                Hash Cond: ((pf.team_api_id = pf_1.team_api_id) AND ((pf.season)::text = (pf_1.season)::text))
                                Buffers: shared hit=883
                                ->  Seq Scan on mv_played_for pf  (cost=1.26..661.79 rows=17501 width=18) (actual time=0.711..10.588 rows=34656.00 loops=1)
                                      Filter: (NOT (ANY (player_api_id = (hashed SubPlan 2).col1)))
                                      Rows Removed by Filter: 346
                                      Buffers: shared hit=430
                                      SubPlan 2
                                        ->  CTE Scan on direct_teammates  (cost=0.00..1.12 rows=56 width=4) (actual time=0.607..0.654 rows=57.00 loops=1)
                                              Storage: Memory  Maximum Storage: 18kB
                                              Buffers: shared hit=207
                                ->  Hash  (cost=678.23..678.23 rows=183 width=14) (actual time=1.538..1.539 rows=146.00 loops=1)
                                      Buckets: 1024  Batches: 1  Memory Usage: 15kB
                                      Buffers: shared hit=453
                                      ->  Unique  (cost=676.85..678.23 rows=183 width=14) (actual time=1.323..1.485 rows=146.00 loops=1)
                                            Buffers: shared hit=453
                                            ->  Sort  (cost=676.85..677.31 rows=183 width=14) (actual time=1.322..1.371 rows=346.00 loops=1)
                                                  Sort Key: pf_1.team_api_id, pf_1.season
                                                  Sort Method: quicksort  Memory: 35kB
                                                  Buffers: shared hit=453
                                                  ->  Nested Loop  (cost=0.29..669.98 rows=183 width=14) (actual time=0.010..0.756 rows=346.00 loops=1)
                                                        Buffers: shared hit=453
                                                        ->  CTE Scan on direct_teammates d  (cost=0.00..1.12 rows=56 width=4) (actual time=0.000..0.015 rows=57.00 loops=1)
                                                              Storage: Memory  Maximum Storage: 18kB
                                                        ->  Index Scan using ix_mv_played_for_player on mv_played_for pf_1  (cost=0.29..11.91 rows=3 width=18) (actual time=0.005..0.010 rows=6.07 loops=57)
                                                              Index Cond: (player_api_id = d.player_api_id)
                                                              Index Searches: 57
                                                              Buffers: shared hit=453
                          ->  Index Scan using player_pkey on player p  (cost=0.29..0.34 rows=1 width=18) (actual time=0.002..0.002 rows=1.00 loops=3228)
                                Index Cond: (player_api_id = pf.player_api_id)
                                Filter: ((player_name)::text <> 'Lionel Messi'::text)
                                Index Searches: 3228
                                Buffers: shared hit=9684
Planning:
  Buffers: shared hit=36
Planning Time: 0.933 ms
Execution Time: 40.812 ms
```

**Neo4j** (`PROFILE`):

```
+-- ProduceResults@neo4j  (rows: 20, dbHits: 0)
    identifiers: ['player_2hop', 'connection_strength']
  +-- Top@neo4j  (rows: 20, dbHits: 0)
      identifiers: ['player_2hop', 'connection_strength']
    +-- EagerAggregation@neo4j  (rows: 1735, dbHits: 0)
        identifiers: ['player_2hop', 'connection_strength']
      +-- Filter@neo4j  (rows: 3228, dbHits: 110424)
          identifiers: ['x', 't3', 'r4', 'p2', 'direct_set', 'covered_pairs']
        +-- Expand(All)@neo4j  (rows: 34656, dbHits: 34656)
            identifiers: ['x', 't3', 'r4', 'p2', 'direct_set', 'covered_pairs']
          +-- CacheProperties@neo4j  (rows: 11003, dbHits: 11005)
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
Aggregate  (cost=621.74..621.75 rows=1 width=4) (actual time=1046.891..1046.893 rows=1.00 loops=1)
  Buffers: shared hit=2977128
  CTE endpoints
    ->  Result  (cost=16.61..16.62 rows=1 width=8) (actual time=0.011..0.012 rows=1.00 loops=1)
          Buffers: shared hit=6
          InitPlan 1
            ->  Limit  (cost=0.29..8.30 rows=1 width=4) (actual time=0.006..0.006 rows=1.00 loops=1)
                  Buffers: shared hit=3
                  ->  Index Scan using ix_player_name on player  (cost=0.29..8.30 rows=1 width=4) (actual time=0.005..0.005 rows=1.00 loops=1)
                        Index Cond: ((player_name)::text = 'Lionel Messi'::text)
                        Index Searches: 1
                        Buffers: shared hit=3
          InitPlan 2
            ->  Limit  (cost=0.29..8.30 rows=1 width=4) (actual time=0.004..0.005 rows=1.00 loops=1)
                  Buffers: shared hit=3
                  ->  Index Scan using ix_player_name on player player_1  (cost=0.29..8.30 rows=1 width=4) (actual time=0.004..0.004 rows=1.00 loops=1)
                        Index Cond: ((player_name)::text = 'Andrea Pirlo'::text)
                        Index Searches: 1
                        Buffers: shared hit=3
  CTE bfs
    ->  Recursive Union  (cost=0.00..565.23 rows=1771 width=8) (actual time=0.012..1042.115 rows=44251.00 loops=1)
          Storage: Memory  Maximum Storage: 948kB
          Buffers: shared hit=2977128
          ->  CTE Scan on endpoints  (cost=0.00..0.02 rows=1 width=8) (actual time=0.011..0.011 rows=1.00 loops=1)
                Storage: Memory  Maximum Storage: 17kB
                Buffers: shared hit=6
          ->  Nested Loop  (cost=4.60..54.75 rows=177 width=8) (actual time=0.039..116.343 rows=371901.29 loops=7)
                Join Filter: (pf2.player_api_id <> b.player_api_id)
                Rows Removed by Join Filter: 15840
                Buffers: shared hit=2977122
                ->  Nested Loop  (cost=4.31..46.24 rows=10 width=22) (actual time=0.037..14.423 rows=15839.86 loops=7)
                      Buffers: shared hit=176237
                      ->  WorkTable Scan on bfs b  (cost=0.00..0.22 rows=3 width=8) (actual time=0.034..0.556 rows=4741.57 loops=7)
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
                ->  Index Scan using ix_mv_played_for_team_season on mv_played_for pf2  (cost=0.29..0.62 rows=15 width=18) (actual time=0.001..0.005 rows=24.48 loops=110879)
                      Index Cond: ((team_api_id = pf1.team_api_id) AND ((season)::text = (pf1.season)::text))
                      Index Searches: 110879
                      Buffers: shared hit=2800885
  InitPlan 5
    ->  CTE Scan on endpoints endpoints_1  (cost=0.00..0.02 rows=1 width=4) (actual time=0.000..0.000 rows=1.00 loops=1)
          Storage: Memory  Maximum Storage: 17kB
  ->  CTE Scan on bfs  (cost=0.00..39.85 rows=9 width=4) (actual time=1.407..1046.887 rows=5.00 loops=1)
        Filter: (player_api_id = (InitPlan 5).col1)
        Rows Removed by Filter: 44246
        Storage: Memory  Maximum Storage: 1895kB
        Buffers: shared hit=2977128
Planning:
  Buffers: shared hit=12
Planning Time: 0.185 ms
Execution Time: 1046.929 ms
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


I plan completi per tutte le 12 query sono in `benchmark/results/run_20260916_183215/plans/`.


## 8. Verifica di correttezza

Tutte le 10 query read (Q01-Q10) restituiscono risultati semanticamente equivalenti nei due sistemi, verificato come confronto di insiemi di tuple normalizzate (arrotondamento a 4 decimali, date come ISO-8601, ordine irrilevante). Le 2 query write (Q11-Q12) producono conteggi identici di righe modificate.


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


## 10. Analisi di sensibilita'

Due ipotesi che avrebbero potuto invalidare i risultati principali, verificate sperimentalmente: un artefatto di *tuning* (10.1) e un artefatto di *semantica* (10.2).


### 10.1 work_mem e lo spill di Q07

Il piano di Q07 contiene l'unico accesso a disco dell'intero benchmark: un sort *external merge* (~18 MB di file temporanei) causato dal `work_mem` di default (4MB). Ipotesi da verificare: quanto del gap Postgres/Neo4j su Q07 e' un artefatto di questo parametro di tuning?

Q07 e' stata rieseguita solo su Postgres (15 run + warm-up per configurazione, `SET work_mem` a livello di sessione):

| work_mem | Mediana PG (ms) | CI 95% | Sort method (EXPLAIN ANALYZE) | Gap vs Neo4j |
|---|---:|:---:|---|---:|
| 4MB | 1211.1 | [1206.5, 1231.8] | `external merge  Disk: 18392kB` | 6.23x |
| 64MB | 1209.4 | [1208.7, 1211.7] | `quicksort  Memory: 46429kB` | 6.22x |

**Risultato: ipotesi smentita.** Eliminare lo spill (il sort passa a quicksort interamente in memoria) sposta la mediana dello 0.1%. Su macOS i file temporanei restano nella page cache del sistema operativo, quindi l'external merge non paga I/O fisico. Il collo di bottiglia reale e' la strategia sort-based scelta dal planner per `COUNT(DISTINCT)` su 542k righe, non il disco: il gap con Neo4j (hash aggregation sulle relazioni) **non e' un artefatto di tuning**.


### 10.2 La semantica dello shortest path in Cypher (Q10)

La BFS SQL di Q10 collega due giocatori solo se hanno vestito la stessa maglia **nella stessa stagione** (`pf2.season = pf1.season`). La formulazione Cypher piu' naturale, `shortestPath((a)-[:PLAYED_FOR*..12]-(b))`, attraversa un nodo `Team` **senza vincolare la stagione** dei due archi consecutivi: e' una relazione di connettivita' piu' lasca, che puo' produrre cammini piu' corti di quelli ammessi dal SQL. Sulla coppia di riferimento le due semantiche coincidono per caso, e la verifica automatica di equivalenza non poteva accorgersene. Abbiamo quindi confrontato tre formulazioni:

| Variante | Semantica | Hop | Mediana (ms) | CI 95% | db hits | Operatore di path |
|---|---|---:|---:|:---:|---:|---|
| V0 `shortestPath(...*..12)` | lasca (stagione libera) | 2 | 2.6 | [2.3, 2.8] | 237 | `ShortestPath` |
| V1 `shortestPath` + predicato di path | esatta, con fallback esaustivo | 2 | 5.1 | [3.4, 7.4] | 837 | `ShortestPath`, `VarLengthExpand(Into)` |
| **V2 quantified path pattern + `SHORTEST 1`** | **esatta per costruzione** | 2 | 4.9 | [4.0, 5.8] | 4402 | `StatefulShortestPath(Into, Trail)` |

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

**Risultato.** La semantica lasca (V0) da' una risposta diversa dal SQL su 1/8 coppie; V2 coincide su 8/8. Esempio: Zlatan Ibrahimovic → Manuel Neuer dista 3 hop di veri compagni di squadra, ma la formulazione lasca risponde 2, passando per una squadra in cui i due intermedi non hanno mai giocato insieme. V1 e' corretta ma pericolosa: il suo piano contiene un ramo `VarLengthExpand` che scatta quando il cammino lasco piu' corto viola il predicato, degenerando in un'enumerazione esaustiva di tutti i cammini fino a 12 archi (~200^6 con il grado medio dei nodi `Team`): in un test senza timeout ha saturato la macchina. **Il benchmark adotta V2**: il vincolo `r1.season = r2.season` e' scritto *dentro* il gruppo ripetuto del quantified path pattern (sintassi GQL), il planner usa l'operatore dedicato `StatefulShortestPath` e il costo dell'esattezza e' 1.9x rispetto alla versione lasca — contro un gap di 163x con Postgres.

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

**Causa individuata: bloat MVCC generato dal benchmark stesso.** Q11 aggiorna ~40k righe di `match_event` (gli eventi `goal`) e Q12 tutte le 26k righe di `match`; entrambe vengono rolled back, ma in Postgres il rollback **non rimuove** le versioni di tupla create dall'`UPDATE`: ogni run lascia 16 x 40k tuple morte esattamente sulle pagine che Q01 scansiona. `pg_stat_user_tables` lo conferma (oltre 1,29 milioni di `n_tup_upd` su `match_event`, 1,45 milioni su `match`), e l'autovacuum e' intervenuto solo *dopo* i due run consecutivi del 16/09 — durante i quali la mediana di Q01 su Postgres e' salita da 10,8 a 16,0 e poi 23,2 ms. Neo4j non ha l'effetto: il rollback scarta le modifiche dal transaction log senza lasciare garbage nello store.

**Correzione del protocollo.** Dall'ultimo run l'harness esegue `VACUUM (ANALYZE)` sulle tabelle coinvolte *prima* delle misure e lo registra in `run_metadata.json`: ogni run e' cosi' indipendente dalla storia delle esecuzioni precedenti. Il run di riferimento di questo report e' il primo con il protocollo corretto.

Il VACUUM ha anche aggiornato le statistiche del planner, con un effetto collaterale visibile su Q03: con la tabella `match` compattata (217 pagine) il planner e' passato dal *Bitmap Index Scan* su `ix_match_season` (47 accessi al buffer, ~2,8 ms) a un *Seq Scan* (217 accessi, ~6 ms). E' una scelta del cost model con `random_page_cost = 4` — il default tarato sui dischi rotanti — che su SSD con working set in cache penalizza l'accesso indicizzato. Non abbiamo modificato il parametro per restare fedeli alla configurazione di default dichiarata, ma e' la dimostrazione che le differenze di categoria A stanno dentro il margine di errore del planner, non del paradigma.

Due lezioni: (i) un benchmark che mescola letture e scritture deve controllare lo *stato fisico* delle tabelle, non solo la cache; (ii) la significativita' statistica entro un run misura il rumore di misurazione, **non** la stabilita' del sistema fra sessioni — per le gare sotto i 20 ms il verdetto onesto e' "parita' operativa", qualunque sia il p-value di un singolo run.


## 11. Ease-of-use e suitability

La terza dimensione dichiarata nella proposal e' l'ease-of-use dei due sistemi. E' per natura la meno misurabile: per non ridurla a un'opinione, la ancoriamo a **proxy oggettivi prodotti dal progetto stesso** (righe di codice della pipeline, dipendenze, statement DDL) e ai problemi **effettivamente incontrati** e documentati in `reports/engineering_challenges.md` e nella storia del repository.

| Aspetto | PostgreSQL | Neo4j |
|---|---|---|
| Definizione dello schema | 9 `CREATE TABLE` + 19 indici; tipi, PK composite, FK e `CHECK` espliciti | 7 constraint di unicita' + 4 indici; lo schema e' *implicito*, emerge dal load |
| Bulk load (~1.5M righe) | `COPY FROM STDIN`: 1 statement per tabella, nessuna dipendenza esterna | `LOAD CSV`; per le 542k `LINEUP_OF` serve `apoc.periodic.iterate` (batch 5000) — cioe' il **plugin APOC** — o una transazione monolitica |
| Codice di load (LOC) | 150 (`load_postgres.py`) | 240 (`load_neo4j.py`, +60%) |
| Relazione derivata player-team-season | `CREATE MATERIALIZED VIEW` + `REFRESH` | `MATCH ... MERGE` di aggregazione post-load |
| Integrita' referenziale | **Enforced**: il `COPY` di `match_event` e' *fallito* per FK violation, rivelando 5.632 riferimenti orfani (Challenge 1) | Non esiste FK: un `MATCH` su un `Player` mancante non lega la riga e la **scarta in silenzio** — lo stesso difetto sarebbe passato inosservato |
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

- **Aggregazioni full-scan (Q07)**: il piano Postgres ordina 542.281 righe (`external merge`, 18 MB); il costo e' O(n log n) nel numero di righe di formazione. A 10x (80 stagioni) lo spill crescerebbe in proporzione, ma il rimedio e' standard: partizionamento dichiarativo per `season` e `work_mem` dimensionato. Neo4j aggrega le stesse relazioni in modo lineare, ma **senza meccanismo di spill**: il grafo deve stare nella pagecache, altrimenti il degrado e' brusco.

- **Traversal a profondita' variabile (Q10)**: la CTE ricorsiva materializza l'intera frontiera BFS — 44.251 stati e 2.977.128 accessi al buffer per profondita' <= 6 — un costo che cresce con la dimensione del grafo *e* esponenzialmente con la profondita'. `SHORTEST 1` (operatore `StatefulShortestPath`, BFS sul pattern) tocca 4.402 db hits: il lavoro dipende dalla lunghezza del cammino e dal grado dei nodi attraversati, **non dalla dimensione totale del grafo**. E' l'index-free adjacency letta come proprieta' di scaling: il 68x osservato non e' un artefatto della taglia del dataset ma tende ad *allargarsi* al crescere dei dati.

- **Scritture (Q11/Q12)**: in Postgres ogni `UPDATE` crea nuove versioni di tupla (MVCC) da ripulire con `VACUUM`; in Neo4j la scrittura passa dal transaction log. Entrambi i sistemi sono stati misurati con un solo writer: sotto scrittori concorrenti entrano in gioco lock a livello di riga (Postgres) e di nodo/relazione (Neo4j), non testati.

### Scaling orizzontale

- **PostgreSQL**: la replica in streaming scala le *letture* senza toccare le query (l'intero benchmark read girerebbe invariato su una replica). Lo sharding dei *dati* (Citus) richiede una chiave di distribuzione; i join multi-hop di Q09/Q10 fra shard diversi diventano join di rete e degradano.

- **Neo4j**: il causal cluster replica l'**intero grafo** su ogni core member — scala le letture, non i dati. Il partizionamento reale (Fabric / composite database) e' manuale, e un traversal che attraversa una partizione perde l'index-free adjacency. E' il limite noto dei graph database: il partizionamento di un grafo minimizzando gli archi tagliati e' un problema NP-hard, e la proprieta' che rende Q10 68x piu' veloce su un nodo e' esattamente quella che **non si distribuisce gratis**.

### Verdetto

A 10x i dati (80 stagioni, ~5M formazioni, ~9M eventi) entrambi i sistemi restano su un nodo con accorgimenti ordinari (partizionamento e `work_mem` per Postgres, pagecache dimensionata per Neo4j) e i rapporti osservati si conservano o si accentuano a favore di Neo4j sui traversal. Oltre la memoria di una singola macchina, il workload OLAP scala meglio in Postgres (Citus, storage colonnare); il workload a grafo scala in Neo4j solo finche' il grafo e' replicabile per intero. La misura di questi regimi e' il lavoro futuro piu' rilevante (sez. 16).


## 13. Conclusioni

Sei risultati emersi dai dati:


1. **Le aggregazioni OLAP-light (categoria A) sono parita' operativa**: in questo run 0 query su 4 significativamente a favore di Postgres (—), 2 a favore di Neo4j (Q01, Q03), 2 non significative (Q02, Q04); tutte le mediane sono sotto i 15 ms e il vincitore cambia da un run all'altro (sez. 10.3: in altri run Q03 e Q04 andavano a Postgres). A questa scala l'ottimizzatore relazionale non ha un vantaggio *misurabile* su join di 2-3 tabelle con aggregazione semplice. Il vantaggio netto di Postgres emerge invece dove il join su indici B-tree batte il traversal a profondita' *fissa*: Q09 (1.9x, r = 1.0, stabile in tutti i run).


2. **Neo4j domina sul traversal a profondita' variabile** (Q10): **68.1x piu' veloce**, con semantica *identica* al SQL (vincolo di stagione dentro il quantified path pattern, sez. 10.2). I piani catturati mostrano il perche': la CTE ricorsiva di Postgres materializza l'intera frontiera BFS (decine di migliaia di stati, milioni di accessi al buffer), mentre `SHORTEST 1` esplora solo il vicinato del cammino (poche migliaia di db hits). E' l'effetto dell'index-free adjacency.


3. **Neo4j vince anche sull'aggregazione full-scan** (Q07, 7.4x), ma per una ragione diversa dal traversal: il planner Postgres esegue `COUNT(DISTINCT)` con una strategia sort-based su 542k righe, mentre Neo4j aggrega le stesse relazioni con hash aggregation. L'analisi di sensibilita' (sez. 10) esclude che il gap dipenda dal tuning di `work_mem`.


4. **La materialized view equalizza il campo sulle query intermedie** (Q09): Postgres con `mv_played_for` vince su una query 2-hop che, senza la precomputazione, sarebbe dominata da Neo4j. Questo isola il contributo del *motore di esecuzione* da quello del *modello di carico*.


5. **Espressivita'**: Cypher e' sistematicamente piu' breve del SQL equivalente. Il caso estremo e' Q10: 5 LOC / 5 operatori logici in Cypher contro 21 LOC / 26 operatori in SQL (CTE ricorsiva BFS).


6. **Schema flexibility** (Q12): aggiungere un attributo derivato a tutti i match costa ~30 ms in Neo4j (singolo `SET`) vs ~400 ms in Postgres (`ALTER TABLE` + `UPDATE`). Rilevante in contesti con schema evolution frequente.


**Verdetto operativo**:

- **PostgreSQL**: aggregazioni OLAP, schema stabile e fortemente vincolato, integrita' referenziale critica, ecosistema BI/ETL maturo.

- **Neo4j**: dominio intrinsecamente a grafo, traversal a profondita' variabile (raccomandazione, fraud detection, supply chain), schema evolution frequente.

- **Polyglot persistence**: in produzione i due DB spesso coesistono, ciascuno gestendo la parte del dominio per cui e' nato. L'analisi di ease-of-use (sez. 11) aggiunge un argomento operativo: tenere il modello relazionale accanto a quello a grafo durante lo sviluppo intercetta errori di dati e di semantica che il grafo da solo assorbe in silenzio.


## 14. Threats to validity


### Validita' interna

- **Warm-up e caching**: la prima esecuzione di ogni query viene scartata per escludere cold-cache effects. Le esecuzioni successive beneficiano della page cache OS e della buffer pool dei DBMS. Il benchmark misura quindi performance *warm-cache*, coerente con un sistema in regime.

- **Variabilita' di misurazione e stabilita' fra run**: le query con mediane sotto i 25 ms (Q01, Q02, Q03, Q04, Q08) hanno vincitori che possono cambiare da una sessione all'altra anche quando il test di Mann-Whitney li dichiara significativi entro il singolo run (sez. 10.3). Le conclusioni del report si appoggiano solo sulle differenze con effect size r >= 0.8, stabili in tutti i run.

- **Equivalenza semantica oltre l'istanza misurata**: il confronto automatico dei risultati vale per i parametri del benchmark. Per Q10 l'equivalenza e' stata verificata anche su 8 coppie di giocatori (sez. 10.2), dopo aver scoperto che la formulazione `shortestPath` legacy coincideva con il SQL solo per caso.

- **Rollback nelle write query**: Q11 e Q12 usano rollback per mantenere lo stato pulito tra le run. Il costo del rollback e' escluso dal timer in entrambi i sistemi.


### Validita' esterna

- **Single-node, single-user**: il benchmark non misura performance sotto carico concorrente (write contention, MVCC vs lock-free traversal), carico OLTP intensivo, o scaling orizzontale.

- **Dimensione del dataset**: 26k match, 917k eventi, 542k lineup rows. Un dataset di dimensione *media*: abbastanza grande da rendere significative le differenze di query plan, ma non abbastanza per evidenziare problemi di scalabilita' I/O.

- **Configurazione di default e asimmetria di memoria**: entrambi i DBMS usano la configurazione di default (documentata nella sezione Setup), che assegna budget di memoria diversi: `shared_buffers` 128MB per Postgres contro heap 1GiB + pagecache 512MiB per Neo4j. Due evidenze empiriche ne limitano l'impatto: (i) nessuno dei 24 piani catturati contiene letture fisiche (`shared read`) — il working set e' interamente in cache in entrambi i sistemi; (ii) l'analisi di sensibilita' su `work_mem` (sez. 10) mostra che l'unico spill del benchmark non sposta la mediana. Un tuning sistematico resta comunque una variabile non esplorata per i confronti piu' tirati (categoria A).

- **Asimmetria nel caricamento**: Postgres carica `PlayerStats` e `TeamStats` (~184k righe) che Neo4j non importa. Su 8 GB di RAM l'impatto sulla cache e' trascurabile, ma va documentato.


### Validita' del costrutto

- **Cognitive verbosity**: la metrica cattura il numero di operatori logici, non la complessita' semantica. Un self-join e un FK join contano uguale. La metrica e' complementare (non sostitutiva) a LOC.

- **Tassonomia delle query**: la classificazione A/B/C/D e' definita *a priori* in base alla struttura logica, non *a posteriori* in base ai risultati. Questo previene il cherry-picking.


## 15. Note metodologiche

- I tempi riportati sono **mediani**; min, max, IQR e 95% CI sono in `summary.csv`.

- La significativita' statistica e' valutata con il test di **Mann-Whitney U** (non parametrico, two-sided, alpha = 0.05), con effect size **rank-biserial**. Gli intervalli di confidenza sono calcolati con **bootstrap** della mediana (10.000 ricampionamenti, seed fisso 42: i CI sono riproducibili bit-a-bit).

- I risultati nei due sistemi sono confrontati come *insiemi* di tuple, con normalizzazione di tipi (Decimal, date) e arrotondamento a 4 decimali.

- Per garantire un confronto **fair** su Q08/Q09/Q10, Postgres precomputa la materialized view `mv_played_for(player, team, season)`, equivalente alla relazione derivata `:PLAYED_FOR` di Neo4j.

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
