# Live demo script — 5 minutes

Companion to the slides. The demo runs after slide 15 (Verdict); slides 16-18 are backup.
Total time: **~5 minutes**. Speak in English.

## Setup before the talk

Have ready, on screen (Cmd+Tab between them):

1. **Terminal window** in `~/Desktop/Data/Progetto_Data/` with the Python venv
   activated (`source etl/.venv/bin/activate`).
2. **Neo4j Browser** open at `http://localhost:7474` with the soccer DB selected.
3. **psql session** open (`psql -d soccer_db`) with the `soccer` schema set
   (`\timing on; SET search_path TO soccer;`).
4. The **slide deck** still open in presenter mode (so you can flip back).

Pre-warm both DBs by running each demo query once in advance — the first
execution after a cold start is always slower and ruins the on-stage timing.

Project repository (tag `v1.0-submission`): https://github.com/g1up3/DM-Project-2026
- Giuseppe: https://github.com/g1up3
- Nicolas:  https://github.com/theunick

---

## Act 1 — A graph question, two languages (~90 s)

> "Let's pick one of our queries, run it on both databases, and see what
>  happens. The query is **Q10: how many degrees of separation between
>  Lionel Messi and Andrea Pirlo** if we walk along teammate relationships?"

### 1A — Show the Postgres version (30 s)

Open `queries/sql/Q10_shortest_path_between_players.sql` in the editor
beside the terminal. Scroll through it briefly.

> "In SQL, this is a recursive CTE doing a breadth-first search up to depth 6.
>  Two players are linked only if they wore the same shirt **in the same
>  season** — that's the `pf2.season = pf1.season` join condition.
>  Twenty-one lines of code, twenty-six logical operators."

Switch to the psql terminal and run:

```sql
\i queries/demo/Q10_shortest_path.sql
```

Expected: ~750-850 ms, single result row showing the hop count (**2**).

> "About eight hundred milliseconds, two hops between them."

### 1B — Show the Neo4j version (30 s)

Switch to **Neo4j Browser**. Paste:

```cypher
:param player_a => 'Lionel Messi';
:param player_b => 'Andrea Pirlo';

MATCH (a:Player {name: $player_a}), (b:Player {name: $player_b})
MATCH path = SHORTEST 1 (a)
  ((x:Player)-[r1:PLAYED_FOR]->(:Team)<-[r2:PLAYED_FOR]-(y:Player) WHERE r1.season = r2.season){1,6}
  (b)
RETURN length(path) / 2 AS hops;
```

Run.

> "Same answer. **Two hops**. Notice the `WHERE r1.season = r2.season`
>  *inside* the repeated group: that is the SQL join condition, written as a
>  pattern. Same semantics, guaranteed. Now look at the time."

Point at the *Started streaming N records after X ms* line at the bottom of
the result panel.

> "**About twelve milliseconds.** Same data, same question, same answer.
>  **Almost seventy times faster**, **five lines** of code instead of twenty-one,
>  **five operators** instead of twenty-six."

If asked *"why not the classic `shortestPath()`?"*: it doesn't constrain the
season between consecutive edges — on Ibrahimović → Neuer it answers 2 hops
where the true teammate distance is 3. We found it, measured it, fixed it
(report, section 10.2).

### 1C — Visualise the actual path (30 s)

To make it visual, run:

```cypher
MATCH (a:Player {name: 'Lionel Messi'}), (b:Player {name: 'Andrea Pirlo'})
MATCH path = SHORTEST 1 (a)
  ((x:Player)-[r1:PLAYED_FOR]->(:Team)<-[r2:PLAYED_FOR]-(y:Player) WHERE r1.season = r2.season){1,6}
  (b)
RETURN path;
```

Click on the **graph view** icon. The path lights up: a chain of players and
teams connecting Messi to Pirlo through one or two intermediaries.

> "And this is what you actually see — the chain of teammates connecting
>  Messi to Pirlo through whoever they had in common. The graph database
>  doesn't compute this; it just *follows* the relationships."

---

## Act 2 — Where Postgres wins (~45 s)

> "It is not always Neo4j's game. Let me show you a *graph* query where
>  Postgres flips the result: the teammates-of-teammates of Messi — two hops,
>  but a **fixed** depth."

Switch to psql:

```sql
\i queries/demo/Q09_two_hop_teammates.sql
```

Expected: ~35-40 ms (first run after idle may take ~100 ms — that's why we
pre-warm), 20 rows.

> "Under forty milliseconds. Twenty players, ranked by how many shared
>  team-seasons connect them to Messi."

Switch to Neo4j Browser and run the equivalent Cypher (paste from
`queries/cypher/Q09_two_hop_teammates.cypher`, with
`:param player_name => 'Lionel Messi'; :param top_n => 20;`).

> "Around seventy. Postgres wins by almost two to one — and it's one of the
>  most stable results we have: effect size 0.87, same winner in every run."

> "Why? Because we gave Postgres a fair fight: `mv_played_for` is a
>  materialized view that precomputes exactly the `PLAYED_FOR` relationship
>  Neo4j builds at load time. With the same precomputation, a fixed two-hop
>  join on B-tree indexes beats the traversal. The graph advantage is not
>  'hops' — it's *variable-depth* search, like the shortest path we just saw."

(Do **not** use Q02 for this act: at ~5 ms on both engines it is inside the
noise band and the winner changes between runs — report, section 10.3.)

---

## Act 3 — Schema evolution: Q12 live (~60 s)

> "Now I want to show you a dimension that performance benchmarks usually
>  ignore: **what happens when the schema changes?** Suppose we want to add
>  a new attribute `total_goals` to every match."

### Postgres (30 s)

```sql
\timing on
ALTER TABLE soccer.match ADD COLUMN total_goals SMALLINT;
UPDATE soccer.match SET total_goals = home_team_goal + away_team_goal;
```

> "Two statements. ALTER TABLE took the lock, UPDATE backfilled the column."

Show the timing — ~400 ms across both (benchmark median).

> "Cleanup..."

```sql
ALTER TABLE soccer.match DROP COLUMN total_goals;
```

### Neo4j (30 s)

```cypher
MATCH (m:Match)
SET   m.totalGoals = m.homeGoals + m.awayGoals;
```

> "**One statement, about thirty milliseconds.** No DDL. No migration step. Just SET the property —
>  same logical operation, same semantics, but the schema is *implicit*.
>  This is the trade-off NoSQL was designed for: **flexibility is part of
>  the data model**, not a separate concern."

Cleanup:

```cypher
MATCH (m:Match) REMOVE m.totalGoals;
```

---

## Act 4 — Closing (~30 s)

Switch back to the slides (slide 15 — Verdict).

> "So, the verdict. **PostgreSQL** when the workload is OLAP, integrity is
>  paramount, and the schema is stable. **Neo4j** when the data is naturally
>  a graph, the questions are about connections, and the schema evolves.
>  Most production systems will use both, each for what it does best.
>  Thank you."

→ Hand over to **Q&A**.

---

## Bonus query (only if there's time, e.g. for a long Q&A)

### Index ablation — show the cost of dropping a critical index

```sql
DROP INDEX soccer.ix_lineup_player;
\i queries/demo/Q08_teammates_messi.sql
-- ~3.5x slower (3.2 ms -> 11.2 ms in the ablation run)
CREATE INDEX ix_lineup_player ON soccer.match_lineup(player_api_id);
```

> "The few milliseconds we saw on Q08 aren't free. Drop one index and Postgres goes
>  from 3.2 ms to 11.2 ms — a 3.5x slowdown. The whole engineering story is in those numbers."

Use this only if the audience seems engaged on engineering details.

---

## Backup queries (in case something breaks)

If the Neo4j Browser fails, fall back to the terminal bundled with Neo4j
Desktop (DBMS card → ⋯ → *Terminal*), which has `cypher-shell` on its PATH:

```bash
cypher-shell -u neo4j -p <password> --param "player_a => 'Lionel Messi'" --param "player_b => 'Andrea Pirlo'" < queries/cypher/Q10_shortest_path_between_players.cypher
```

(`cypher-shell` is NOT on the macOS PATH outside that terminal.)

If the Neo4j Browser gets stuck on a long query, just say *"the query is
returning a path that you've seen on slide 11 — let's continue"* and move
on. Do not let any demo issue eat more than 30 seconds of stage time.

**Ultimate fallback**: the numbers are all in `reports/benchmark_report.md`
(section 2) and the query plans in `benchmark/results/run_20260916_183215/plans/`
— if a database is down, show the captured plan instead of running live.
