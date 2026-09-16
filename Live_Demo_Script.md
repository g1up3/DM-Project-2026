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
>  Twenty-one lines of code, twenty-six logical operators."

Switch to the psql terminal and run:

```sql
\i queries/demo/Q10_shortest_path.sql
```

Expected: ~700-760 ms, single result row showing the hop count (**2**).

> "About seven hundred milliseconds, two hops between them."

### 1B — Show the Neo4j version (30 s)

Switch to **Neo4j Browser**. Paste:

```cypher
:param player_a => 'Lionel Messi';
:param player_b => 'Andrea Pirlo';

MATCH (a:Player {name: $player_a}), (b:Player {name: $player_b})
MATCH path = shortestPath((a)-[:PLAYED_FOR*..12]-(b))
RETURN length(path) / 2 AS hops;
```

Run.

> "Same answer. **Two hops**. But look at the time."

Point at the *Started streaming N records after X ms* line at the bottom of
the result panel.

> "**Eight milliseconds.** Same data, same question, same answer.
>  **Almost ninety times faster**, **three lines** of code instead of twenty-one,
>  **three operators** instead of twenty-six."

### 1C — Visualise the actual path (30 s)

To make it visual, run:

```cypher
MATCH (a:Player {name: 'Lionel Messi'}), (b:Player {name: 'Andrea Pirlo'})
MATCH path = shortestPath((a)-[:PLAYED_FOR*..12]-(b))
RETURN path;
```

Click on the **graph view** icon. The path lights up: a chain of players and
teams connecting Messi to Pirlo through one or two intermediaries.

> "And this is what you actually see — the chain of teammates connecting
>  Messi to Pirlo through whoever they had in common. The graph database
>  doesn't compute this; it just *follows* the relationships."

---

## Act 2 — Where Postgres wins (~45 s)

> "It is not always Neo4j's game. Let me show you a query where Postgres
>  flips the result."

Switch to psql:

```sql
\i queries/demo/Q02_league_standings.sql
```

Expected: ~7 ms.

> "About seven milliseconds. Twenty teams of Serie A 2015/16 with full standings —
>  points, goals for, goals against."

Switch to Neo4j Browser and run the equivalent Cypher (paste from
`queries/cypher/Q02_league_standings.cypher`).

> "Around nine. Postgres wins — classical OLAP territory. Small margin, but
>  statistically significant over fifteen runs."

> "This is the lesson: classical OLAP-style aggregations are exactly what
>  PostgreSQL has been optimised to do for thirty years. The graph paradigm
>  has nothing to add here — and it shows."

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

Show the timing — ~440 ms across both (benchmark median).

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
(section 2) and the query plans in `benchmark/results/run_20260524_230038/plans/`
— if a database is down, show the captured plan instead of running live.
