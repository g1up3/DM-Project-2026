"""
Index ablation benchmark — measure the impact of strategically removing
indexes across multiple queries.

For each (index, query) pair, runs the query three ways:

  (1) WITH index    : baseline (indexed schema)
  (2) WITHOUT index : drop the index, re-run
  (3) RESTORED      : recreate the index, verify recovery

This demonstrates that the indexes in our schemas are concrete engineering
choices with measurable impact, not decoration.

Test matrix:

  PostgreSQL:
    ix_lineup_player           x Q08 (teammates via lineup)
    ix_mv_played_for_player    x Q09 (2-hop teammates via MV)
    ix_mv_played_for_player    x Q10 (shortest path via MV)
    ix_event_player1           x Q05 (goal-assist partnerships)

  Neo4j:
    player_name_idx            x Q08 (teammates lookup by name)
    match_season_idx           x Q03 (goals per match by league+season)
    team_name_idx              x Q06 (cards received vs team)

Output:
    benchmark/results/index_ablation/<timestamp>.csv
    benchmark/results/index_ablation/<timestamp>.json

Usage:
    python3 benchmark/index_ablation.py [--runs N]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import psycopg2
from neo4j import GraphDatabase

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / "etl" / ".env")
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from queries import QUERIES  # noqa: E402

HERE       = Path(__file__).resolve().parent
SQL_DIR    = HERE.parent / "queries" / "sql"
CYPHER_DIR = HERE.parent / "queries" / "cypher"
OUT_DIR    = HERE / "results" / "index_ablation"


@dataclass
class AblationTarget:
    system: str
    index_name: str
    drop_stmt: str
    create_stmt: str
    query_id: str
    rationale: str


TARGETS: list[AblationTarget] = [
    # --- PostgreSQL ---
    AblationTarget(
        system="postgres",
        index_name="ix_lineup_player",
        drop_stmt="DROP INDEX IF EXISTS soccer.ix_lineup_player",
        create_stmt="CREATE INDEX IF NOT EXISTS ix_lineup_player ON soccer.match_lineup(player_api_id)",
        query_id="Q08",
        rationale="Q08 joins match_lineup on player_api_id to find teammates",
    ),
    AblationTarget(
        system="postgres",
        index_name="ix_mv_played_for_player",
        drop_stmt="DROP INDEX IF EXISTS soccer.ix_mv_played_for_player",
        create_stmt="CREATE INDEX IF NOT EXISTS ix_mv_played_for_player ON soccer.mv_played_for(player_api_id)",
        query_id="Q09",
        rationale="Q09 starts BFS from player_api_id in the materialized view",
    ),
    AblationTarget(
        system="postgres",
        index_name="ix_mv_played_for_player",
        drop_stmt="DROP INDEX IF EXISTS soccer.ix_mv_played_for_player",
        create_stmt="CREATE INDEX IF NOT EXISTS ix_mv_played_for_player ON soccer.mv_played_for(player_api_id)",
        query_id="Q10",
        rationale="Q10 recursive CTE pivots on player_api_id in each BFS step",
    ),
    AblationTarget(
        system="postgres",
        index_name="ix_event_player1",
        drop_stmt="DROP INDEX IF EXISTS soccer.ix_event_player1",
        create_stmt="CREATE INDEX IF NOT EXISTS ix_event_player1 ON soccer.match_event(player1_id)",
        query_id="Q05",
        rationale="Q05 joins match_event on player1_id for goal-assist pairs",
    ),
    # --- Neo4j ---
    AblationTarget(
        system="neo4j",
        index_name="player_name_idx",
        drop_stmt="DROP INDEX player_name_idx IF EXISTS",
        create_stmt="CREATE INDEX player_name_idx IF NOT EXISTS FOR (p:Player) ON (p.name)",
        query_id="Q08",
        rationale="Q08 starts with Player lookup by name",
    ),
    AblationTarget(
        system="neo4j",
        index_name="match_season_idx",
        drop_stmt="DROP INDEX match_season_idx IF EXISTS",
        create_stmt="CREATE INDEX match_season_idx IF NOT EXISTS FOR (m:Match) ON (m.season)",
        query_id="Q03",
        rationale="Q03 filters Match nodes by season",
    ),
    AblationTarget(
        system="neo4j",
        index_name="team_name_idx",
        drop_stmt="DROP INDEX team_name_idx IF EXISTS",
        create_stmt="CREATE INDEX team_name_idx IF NOT EXISTS FOR (t:Team) ON (t.name)",
        query_id="Q06",
        rationale="Q06 starts with Team lookup by name",
    ),
]


def pg_connect():
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", "postgres"),
        dbname=os.getenv("PGDATABASE", "soccer_db"),
    )


def neo4j_driver():
    return GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(
            os.getenv("NEO4J_USER", "neo4j"),
            os.getenv("NEO4J_PASSWORD", "password"),
        ),
    )


def time_pg(conn, sql, params, repeats):
    times = []
    with conn.cursor() as cur:
        for _ in range(repeats + 1):
            t0 = time.perf_counter()
            cur.execute(sql, params)
            cur.fetchall()
            t1 = time.perf_counter()
            times.append((t1 - t0) * 1000)
    return times[1:]


def time_neo(session, cypher, params, repeats):
    times = []
    for _ in range(repeats + 1):
        t0 = time.perf_counter()
        list(session.run(cypher, **params))
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000)
    return times[1:]


def run_ablation(target: AblationTarget, pg_conn, neo_session, repeats: int) -> list[dict]:
    query_def = next((q for q in QUERIES if q.id == target.query_id), None)
    if not query_def:
        print(f"  [SKIP] Query {target.query_id} not found")
        return []

    if target.system == "postgres":
        sql_text = (SQL_DIR / query_def.sql_file).read_text()
        params = query_def.params

        def measure():
            return time_pg(pg_conn, sql_text, params, repeats)
        def exec_ddl(stmt):
            with pg_conn.cursor() as cur:
                cur.execute(stmt)
            pg_conn.commit()
    else:
        cypher_text = (CYPHER_DIR / query_def.cypher_file).read_text()
        params = query_def.params

        def measure():
            return time_neo(neo_session, cypher_text, params, repeats)
        def exec_ddl(stmt):
            neo_session.run(stmt).consume()

    rows = []
    print(f"\n  [{target.system}] {target.index_name} x {target.query_id}: {target.rationale}")

    for phase, setup_stmt in [
        ("with_index",    None),
        ("without_index", target.drop_stmt),
        ("restored",      target.create_stmt),
    ]:
        if setup_stmt:
            exec_ddl(setup_stmt)
            time.sleep(0.3)

        times = measure()
        med = statistics.median(times)
        rows.append({
            "system":     target.system,
            "index_name": target.index_name,
            "query_id":   target.query_id,
            "phase":      phase,
            "median_ms":  round(med, 3),
            "min_ms":     round(min(times), 3),
            "max_ms":     round(max(times), 3),
        })
        print(f"    {phase:<14} median={med:>9.2f} ms")

    # always restore
    exec_ddl(target.create_stmt)
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--runs", type=int, default=10,
                   help="Measured runs per phase (default 10)")
    args = p.parse_args()
    repeats = args.runs

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_rows = []

    print(f"=== Index ablation matrix ===")
    print(f"Runs per phase: {repeats}")
    print(f"Targets: {len(TARGETS)} (index, query) pairs\n")

    pg = pg_connect()
    drv = neo4j_driver()
    try:
        with drv.session(database=os.getenv("NEO4J_DATABASE", "neo4j")) as sess:
            for target in TARGETS:
                try:
                    rows = run_ablation(target, pg, sess, repeats)
                    all_rows.extend(rows)
                except Exception as e:
                    print(f"    [ERROR] {e}")
                    # safety: restore index
                    try:
                        if target.system == "postgres":
                            with pg.cursor() as cur:
                                cur.execute(target.create_stmt)
                            pg.commit()
                        else:
                            sess.run(target.create_stmt).consume()
                    except Exception:
                        pass
    finally:
        pg.close()
        drv.close()

    if not all_rows:
        print("No results collected.")
        return

    csv_path = OUT_DIR / f"{ts}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        w.writeheader()
        w.writerows(all_rows)

    (OUT_DIR / f"{ts}.json").write_text(
        json.dumps({
            "timestamp": ts,
            "runs_per_phase": repeats,
            "n_targets": len(TARGETS),
            "targets": [
                {"system": t.system, "index": t.index_name,
                 "query": t.query_id, "rationale": t.rationale}
                for t in TARGETS
            ],
        }, indent=2)
    )

    print(f"\nResults saved to {csv_path}")

    # summary
    print(f"\n{'='*80}")
    print(f"{'System':<10} {'Index':<30} {'Query':<5} {'Phase':<14} {'Median':>9} {'Slowdown':>9}")
    print(f"{'='*80}")

    baselines = {}
    for r in all_rows:
        key = (r["system"], r["index_name"], r["query_id"])
        if r["phase"] == "with_index":
            baselines[key] = r["median_ms"]

    for r in all_rows:
        key = (r["system"], r["index_name"], r["query_id"])
        base = baselines.get(key, r["median_ms"])
        slow = r["median_ms"] / base if base > 0 else 0
        mark = " **" if r["phase"] == "without_index" and slow > 1.5 else ""
        print(f"{r['system']:<10} {r['index_name']:<30} {r['query_id']:<5} "
              f"{r['phase']:<14} {r['median_ms']:>8.2f}ms {slow:>8.2f}x{mark}")


if __name__ == "__main__":
    main()
