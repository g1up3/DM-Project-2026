"""
Index ablation benchmark — show what happens when you drop a strategically
important index, then restore it.

Picks one query per system, runs it three ways:

  (1) WITH index    : the indexed schema we use throughout the project
  (2) WITHOUT index : drop a key index, re-run the same query
  (3) RESTORE       : recreate the index, re-run the query

The idea is to demonstrate that the indexes we put in our schemas are not
decoration — they are concrete engineering choices with measurable impact.

Target queries:

  - PostgreSQL: Q08 (teammates of Messi). Heavily relies on the indexes
    `ix_lineup_player` and `ix_lineup_match` on match_lineup. We drop the
    player index, run the query, restore, and re-run.

  - Neo4j: Q08 (teammates of Messi). Relies on the `player_name_idx` index
    for the initial lookup of (:Player {name: ...}). We drop it, re-run,
    re-create, re-run.

Output:
    benchmark/results/index_ablation/<timestamp>.csv
    benchmark/results/index_ablation/<timestamp>.json (run metadata)

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

HERE = Path(__file__).resolve().parent
SQL_DIR    = HERE.parent / "queries" / "sql"
CYPHER_DIR = HERE.parent / "queries" / "cypher"
OUT_DIR    = HERE / "results" / "index_ablation"

# Query under test — Q08 is the right scale for this experiment:
# small enough to run many times, but heavy enough that index loss is visible.
TARGET_QID = "Q08"

PG_INDEX_NAME = "ix_lineup_player"
PG_INDEX_DROP = "DROP INDEX IF EXISTS soccer.ix_lineup_player"
PG_INDEX_CREATE = (
    "CREATE INDEX IF NOT EXISTS ix_lineup_player "
    "ON soccer.match_lineup(player_api_id)"
)

NEO4J_INDEX_NAME = "player_name_idx"
NEO4J_INDEX_DROP = f"DROP INDEX {NEO4J_INDEX_NAME} IF EXISTS"
NEO4J_INDEX_CREATE = (
    f"CREATE INDEX {NEO4J_INDEX_NAME} IF NOT EXISTS FOR (p:Player) ON (p.name)"
)


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
        for _ in range(repeats + 1):  # 1 warm-up
            t0 = time.perf_counter()
            cur.execute(sql, params)
            cur.fetchall()
            t1 = time.perf_counter()
            times.append((t1 - t0) * 1000)
    return times[1:]  # drop warm-up


def time_neo(session, cypher, params, repeats):
    times = []
    for _ in range(repeats + 1):
        t0 = time.perf_counter()
        list(session.run(cypher, **params))
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000)
    return times[1:]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--runs", type=int, default=5,
                   help="Measured runs per phase (default 5)")
    args = p.parse_args()
    repeats = args.runs

    # find target query
    target = next((q for q in QUERIES if q.id == TARGET_QID), None)
    if not target:
        sys.exit(f"Query {TARGET_QID} not found in queries.py")

    sql_text    = (SQL_DIR    / target.sql_file).read_text()
    cypher_text = (CYPHER_DIR / target.cypher_file).read_text()
    params      = target.params

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    rows = []

    print(f"=== Index ablation — query {TARGET_QID} ({target.name}) ===")
    print(f"Runs per phase: {repeats}\n")

    # ----- Postgres -----
    pg = pg_connect()
    try:
        for phase, setup_sql in [
            ("with_index",    None),                        # baseline (already indexed)
            ("without_index", PG_INDEX_DROP),
            ("restored",      PG_INDEX_CREATE),
        ]:
            if setup_sql:
                with pg.cursor() as cur:
                    cur.execute(setup_sql)
                pg.commit()
            times = time_pg(pg, sql_text, params, repeats)
            med = statistics.median(times)
            rows.append({"system": "postgres", "phase": phase,
                         "median_ms": round(med, 3),
                         "min_ms": round(min(times), 3),
                         "max_ms": round(max(times), 3)})
            print(f"  postgres {phase:<14} median={med:>9.2f} ms")
    finally:
        # safety: ensure index is always restored
        with pg.cursor() as cur:
            cur.execute(PG_INDEX_CREATE)
        pg.commit()
        pg.close()

    # ----- Neo4j -----
    drv = neo4j_driver()
    try:
        with drv.session(database=os.getenv("NEO4J_DATABASE", "neo4j")) as sess:
            for phase, setup_cy in [
                ("with_index",    None),
                ("without_index", NEO4J_INDEX_DROP),
                ("restored",      NEO4J_INDEX_CREATE),
            ]:
                if setup_cy:
                    sess.run(setup_cy).consume()
                times = time_neo(sess, cypher_text, params, repeats)
                med = statistics.median(times)
                rows.append({"system": "neo4j", "phase": phase,
                             "median_ms": round(med, 3),
                             "min_ms": round(min(times), 3),
                             "max_ms": round(max(times), 3)})
                print(f"  neo4j    {phase:<14} median={med:>9.2f} ms")
            # safety: ensure index restored
            sess.run(NEO4J_INDEX_CREATE).consume()
    finally:
        drv.close()

    # write CSV
    csv_path = OUT_DIR / f"{ts}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # write metadata
    (OUT_DIR / f"{ts}.json").write_text(
        json.dumps({"timestamp": ts, "target_query": TARGET_QID,
                    "runs": repeats}, indent=2)
    )

    print(f"\nResults saved to {csv_path}")

    # summary table
    print("\n=== SUMMARY ===")
    print(f"{'System':<10} {'Phase':<14} {'Median (ms)':>12} {'Slowdown':>10}")
    for sys_name in ("postgres", "neo4j"):
        baseline = next(r["median_ms"] for r in rows
                        if r["system"] == sys_name and r["phase"] == "with_index")
        for r in rows:
            if r["system"] != sys_name:
                continue
            slow = r["median_ms"] / baseline
            print(f"{r['system']:<10} {r['phase']:<14} "
                  f"{r['median_ms']:>12.2f} {slow:>9.2f}x")


if __name__ == "__main__":
    main()
