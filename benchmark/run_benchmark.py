"""
Harness di benchmark SQL vs Cypher.

Esegue ogni query (definita in benchmark/queries.py) N volte su PostgreSQL e
N volte su Neo4j. Scarta la prima esecuzione (warm-up della cache), e per le
restanti calcola statistiche robuste: mediana, min, max, IQR, intervalli di
confidenza bootstrap al 95%, e test di significativita' (Mann-Whitney U).

Cattura inoltre:
  - EXPLAIN ANALYZE (Postgres) e PROFILE (Neo4j) per ogni query
  - Configurazione runtime dei due DBMS
  - Confronto dei risultati nei due sistemi (set logici di tuple)

Output:
    benchmark/results/run_<timestamp>/
        timings.csv         righe = (query_id, system, run_idx, time_ms, n_rows)
        summary.csv         righe = (query_id, name, category, system,
                                     median_ms, min_ms, max_ms, iqr_ms,
                                     ci95_lo, ci95_hi,
                                     n_rows, equal_results)
        significance.csv    righe = (query_id, u_stat, p_value, significant,
                                     effect_size, winner, speedup)
        plans/              EXPLAIN ANALYZE e PROFILE per ogni query
        db_config.json      parametri di configurazione runtime
        run_metadata.json   info di run (host, versioni, ecc.)

Uso:
    python3 run_benchmark.py [--runs N]

Variabili d'ambiente: stesse di etl/load_*.py (PGHOST, NEO4J_URI, ecc.).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import statistics
import subprocess
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import numpy as np
import psycopg2
import psycopg2.extras
from neo4j import GraphDatabase
from scipy import stats as sp_stats

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / "etl" / ".env")
except ImportError:
    pass

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from queries import QUERIES, QueryDef  # noqa: E402

HERE         = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
SQL_DIR      = PROJECT_ROOT / "queries" / "sql"
CYPHER_DIR   = PROJECT_ROOT / "queries" / "cypher"
RESULTS_DIR  = HERE / "results"


# ---------------------------------------------------------------------------
#  Connessioni
# ---------------------------------------------------------------------------

def pg_connect():
    return psycopg2.connect(
        host     = os.getenv("PGHOST",     "localhost"),
        port     = os.getenv("PGPORT",     "5432"),
        user     = os.getenv("PGUSER",     "postgres"),
        password = os.getenv("PGPASSWORD", "postgres"),
        dbname   = os.getenv("PGDATABASE", "soccer_db"),
    )


def neo4j_driver():
    return GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(
            os.getenv("NEO4J_USER",     "neo4j"),
            os.getenv("NEO4J_PASSWORD", "password"),
        ),
    )


def collect_db_versions(pg_conn, neo_session) -> dict:
    versions = {}
    try:
        with pg_conn.cursor() as cur:
            cur.execute("SELECT version()")
            versions["postgres_version"] = cur.fetchone()[0]
    except Exception as e:
        versions["postgres_version"] = f"unknown ({e})"
    try:
        rec = neo_session.run(
            "CALL dbms.components() YIELD name, versions, edition "
            "RETURN name, versions[0] AS version, edition"
        ).single()
        if rec:
            versions["neo4j_version"] = f"{rec['name']} {rec['version']} ({rec['edition']})"
    except Exception as e:
        versions["neo4j_version"] = f"unknown ({e})"
    return versions


def collect_db_config(pg_conn, neo_session) -> dict:
    """Cattura i parametri di configurazione runtime rilevanti per la riproducibilita'."""
    config = {"postgres": {}, "neo4j": {}}

    pg_params = [
        "shared_buffers", "work_mem", "maintenance_work_mem",
        "effective_cache_size", "random_page_cost", "seq_page_cost",
        "max_parallel_workers_per_gather", "jit",
        "enable_hashjoin", "enable_mergejoin", "enable_nestloop",
        "enable_seqscan", "enable_indexscan",
    ]
    try:
        with pg_conn.cursor() as cur:
            for p in pg_params:
                try:
                    cur.execute(f"SHOW {p}")
                    config["postgres"][p] = cur.fetchone()[0]
                except Exception:
                    pass
    except Exception:
        pass

    try:
        neo4j_params = [
            "server.memory.heap.initial_size",
            "server.memory.heap.max_size",
            "server.memory.pagecache.size",
            "db.tx_log.rotation.retention_policy",
        ]
        for p in neo4j_params:
            try:
                rec = neo_session.run(
                    "CALL dbms.listConfig($name) YIELD name, value RETURN value",
                    name=p,
                ).single()
                if rec:
                    config["neo4j"][p] = rec["value"]
            except Exception:
                pass
        if not config["neo4j"]:
            try:
                recs = neo_session.run(
                    "CALL dbms.listConfig() YIELD name, value "
                    "WHERE name STARTS WITH 'server.memory' OR name STARTS WITH 'db.tx_log' "
                    "RETURN name, value"
                ).data()
                for r in recs:
                    config["neo4j"][r["name"]] = r["value"]
            except Exception:
                pass
    except Exception:
        pass

    return config


def vacuum_postgres(conn) -> dict:
    """VACUUM (ANALYZE) delle tabelle dello schema prima delle misure.

    Le query write Q11/Q12 vengono rolled back, ma in Postgres il rollback non
    rimuove le versioni di tupla create dall'UPDATE (MVCC): ogni run lascia
    ~40k tuple morte su match_event e ~26k su match, che degradano le letture
    dei run successivi finche' l'autovacuum non interviene (vedere report,
    sez. 10.3). Il VACUUM esplicito rende ogni run indipendente dalla storia.
    """
    stats = {}
    old_autocommit = conn.autocommit
    conn.autocommit = True                     # VACUUM non puo' girare in transazione
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT relname, n_dead_tup FROM pg_stat_user_tables "
                        "WHERE schemaname = 'soccer' AND n_dead_tup > 0")
            stats["dead_tuples_before"] = {r[0]: r[1] for r in cur.fetchall()}
            cur.execute("VACUUM (ANALYZE) soccer.match_event")
            cur.execute("VACUUM (ANALYZE) soccer.match")
            cur.execute("VACUUM (ANALYZE) soccer.match_lineup")
            cur.execute("VACUUM (ANALYZE) soccer.player")
        stats["vacuumed"] = ["match_event", "match", "match_lineup", "player"]
    except Exception as e:
        stats["error"] = str(e)
    finally:
        conn.autocommit = old_autocommit
    return stats


def collect_hardware_info() -> dict:
    info = {
        "host":         platform.node(),
        "platform":     platform.platform(),
        "machine":      platform.machine(),
        "processor":    platform.processor() or "unknown",
        "python":       platform.python_version(),
        "cpu_count":    os.cpu_count(),
    }
    if platform.system() == "Darwin":
        try:
            cpu = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                stderr=subprocess.DEVNULL, timeout=2,
            ).decode().strip()
            if cpu:
                info["cpu_model"] = cpu
        except Exception:
            pass
        try:
            mem_bytes = int(subprocess.check_output(
                ["sysctl", "-n", "hw.memsize"],
                stderr=subprocess.DEVNULL, timeout=2,
            ).decode().strip())
            info["memory_gb"] = round(mem_bytes / (1024 ** 3), 1)
        except Exception:
            pass
    return info


# ---------------------------------------------------------------------------
#  Query plan capture
# ---------------------------------------------------------------------------

def capture_pg_plan(conn, sql: str, params: dict, is_write: bool) -> str:
    """Cattura EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) per una query Postgres."""
    explain_sql = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {sql}"
    try:
        with conn.cursor() as cur:
            cur.execute(explain_sql, params)
            plan_rows = cur.fetchall()
        if is_write:
            conn.rollback()
        return "\n".join(row[0] for row in plan_rows)
    except Exception as e:
        if is_write:
            conn.rollback()
        return f"-- EXPLAIN failed: {e}"


def capture_neo4j_plan(session, cypher: str, params: dict, is_write: bool) -> str:
    """Cattura PROFILE per una query Neo4j."""
    profile_cypher = f"PROFILE {cypher}"
    try:
        if is_write:
            tx = session.begin_transaction()
            result = tx.run(profile_cypher, **params)
            summary = result.consume()
            tx.rollback()
        else:
            result = session.run(profile_cypher, **params)
            summary = result.consume()

        lines = []
        plan = summary.profile
        if plan:
            _format_neo4j_plan(plan, lines, indent=0)
        return "\n".join(lines) if lines else "-- No profile data available"
    except Exception as e:
        return f"-- PROFILE failed: {e}"


def _format_neo4j_plan(plan, lines: list, indent: int):
    """Formatta ricorsivamente il plan tree di Neo4j."""
    prefix = "  " * indent
    op = plan.operator_type if hasattr(plan, "operator_type") else str(plan.get("operatorType", "?"))

    rows_val = ""
    if hasattr(plan, "rows"):
        rows_val = plan.rows
    elif isinstance(plan, dict) and "rows" in plan:
        rows_val = plan["rows"]

    db_hits_val = ""
    if hasattr(plan, "db_hits"):
        db_hits_val = plan.db_hits
    elif isinstance(plan, dict) and "dbHits" in plan:
        db_hits_val = plan["dbHits"]

    lines.append(f"{prefix}+-- {op}  (rows: {rows_val}, dbHits: {db_hits_val})")

    identifiers = None
    if hasattr(plan, "identifiers"):
        identifiers = plan.identifiers
    elif isinstance(plan, dict) and "identifiers" in plan:
        identifiers = plan["identifiers"]
    if identifiers:
        lines.append(f"{prefix}    identifiers: {identifiers}")

    children = []
    if hasattr(plan, "children"):
        children = plan.children
    elif isinstance(plan, dict) and "children" in plan:
        children = plan["children"]
    for child in children:
        _format_neo4j_plan(child, lines, indent + 1)


# ---------------------------------------------------------------------------
#  Esecuzione
# ---------------------------------------------------------------------------

def run_pg(conn, sql: str, params: dict, is_write: bool = False) -> tuple[float, list[tuple]]:
    with conn.cursor() as cur:
        t0 = time.perf_counter()
        cur.execute(sql, params)
        rows = cur.fetchall() if cur.description else []
        t1 = time.perf_counter()
    if is_write:
        conn.rollback()
    return (t1 - t0) * 1000.0, rows


def run_neo4j(session, cypher: str, params: dict, is_write: bool = False) -> tuple[float, list[tuple]]:
    if is_write:
        tx = session.begin_transaction()
        t0 = time.perf_counter()
        result = tx.run(cypher, **params)
        rows = [tuple(r.values()) for r in result]
        t1 = time.perf_counter()
        tx.rollback()
        return (t1 - t0) * 1000.0, rows
    t0 = time.perf_counter()
    result = session.run(cypher, **params)
    rows = [tuple(r.values()) for r in result]
    t1 = time.perf_counter()
    return (t1 - t0) * 1000.0, rows


def normalize_rows(rows: list[tuple]) -> set:
    out = []
    for r in rows:
        norm = []
        for v in r:
            if v is None:
                norm.append(None)
            elif hasattr(v, "isoformat"):
                norm.append(v.isoformat()[:10])
            elif isinstance(v, (int, str)):
                norm.append(v)
            else:
                try:
                    norm.append(round(float(v), 4))
                except (TypeError, ValueError):
                    norm.append(str(v))
        out.append(tuple(norm))
    return set(out)


# ---------------------------------------------------------------------------
#  Statistiche
# ---------------------------------------------------------------------------

def summarize(times_ms: list[float]) -> dict:
    if not times_ms:
        return {"median_ms": None, "min_ms": None, "max_ms": None,
                "iqr_ms": None, "ci95_lo": None, "ci95_hi": None}
    s = sorted(times_ms)
    med = statistics.median(s)
    iqr = (np.percentile(s, 75) - np.percentile(s, 25)) if len(s) >= 4 else 0.0

    ci_lo, ci_hi = bootstrap_ci(s)

    return {
        "median_ms": med,
        "min_ms":    s[0],
        "max_ms":    s[-1],
        "iqr_ms":    float(iqr),
        "ci95_lo":   ci_lo,
        "ci95_hi":   ci_hi,
    }


def bootstrap_ci(data: list[float], n_boot: int = 10000, alpha: float = 0.05,
                 seed: int = 42) -> tuple[float, float]:
    """Bootstrap 95% CI della mediana. Seed fisso: i CI sono riproducibili bit-a-bit."""
    rng = np.random.default_rng(seed)
    arr = np.array(data)
    boot_medians = np.array([
        np.median(rng.choice(arr, size=len(arr), replace=True))
        for _ in range(n_boot)
    ])
    lo = float(np.percentile(boot_medians, 100 * alpha / 2))
    hi = float(np.percentile(boot_medians, 100 * (1 - alpha / 2)))
    return lo, hi


def significance_test(pg_times: list[float], neo_times: list[float]) -> dict:
    """Mann-Whitney U test + effect size (rapporto mediane)."""
    if len(pg_times) < 3 or len(neo_times) < 3:
        return {"u_stat": None, "p_value": None, "significant": False,
                "effect_size": None, "winner": "inconclusive", "speedup": None}

    u_stat, p_value = sp_stats.mannwhitneyu(
        pg_times, neo_times, alternative="two-sided"
    )

    med_pg = statistics.median(pg_times)
    med_neo = statistics.median(neo_times)

    if med_neo < med_pg:
        winner = "neo4j"
        speedup = med_pg / med_neo
    else:
        winner = "postgres"
        speedup = med_neo / med_pg

    n1, n2 = len(pg_times), len(neo_times)
    r_effect = 1.0 - (2.0 * u_stat) / (n1 * n2)

    significant = p_value < 0.05

    return {
        "u_stat":      round(float(u_stat), 2),
        "p_value":     round(float(p_value), 6),
        "significant": significant,
        "effect_size": round(abs(r_effect), 4),
        "winner":      winner if significant else "not significant",
        "speedup":     round(speedup, 2),
    }


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------

def run_one_query(q: QueryDef, pg_conn, neo_session, runs: int,
                  plans_dir: Path) -> dict:
    sql_text    = (SQL_DIR    / q.sql_file).read_text(encoding="utf-8")
    cypher_text = (CYPHER_DIR / q.cypher_file).read_text(encoding="utf-8")
    is_write    = q.category.startswith("D_")

    pg_times, neo_times = [], []
    pg_rows = neo_rows = None

    print(f"\n--- {q.id}: {q.name}  [{q.category}] ---")

    for i in range(runs + 1):
        t_pg, pg_rows = run_pg(pg_conn, sql_text, q.params, is_write=is_write)
        t_neo, neo_rows = run_neo4j(neo_session, cypher_text, q.params, is_write=is_write)
        if i == 0:
            print(f"  [warmup] pg={t_pg:.1f}ms  neo={t_neo:.1f}ms  (scartato)")
        else:
            pg_times.append(t_pg)
            neo_times.append(t_neo)
            print(f"  [run {i:>2}] pg={t_pg:.1f}ms  neo={t_neo:.1f}ms")

    # cattura query plan
    print(f"  [plan]  capturing EXPLAIN ANALYZE + PROFILE...")
    pg_plan = capture_pg_plan(pg_conn, sql_text, q.params, is_write)
    neo_plan = capture_neo4j_plan(neo_session, cypher_text, q.params, is_write)
    (plans_dir / f"{q.id}_postgres.txt").write_text(pg_plan, encoding="utf-8")
    (plans_dir / f"{q.id}_neo4j.txt").write_text(neo_plan, encoding="utf-8")

    # confronto risultati
    pg_set  = normalize_rows(pg_rows or [])
    neo_set = normalize_rows(neo_rows or [])
    equal   = (pg_set == neo_set)
    if not equal:
        only_pg  = len(pg_set - neo_set)
        only_neo = len(neo_set - pg_set)
        print(f"  [WARN] risultati DIFFERENTI: solo-pg={only_pg}, solo-neo={only_neo}")

    # significativita'
    sig = significance_test(pg_times, neo_times)
    tag = f"p={sig['p_value']:.4f}" if sig['p_value'] is not None else "N/A"
    robust = "ROBUST" if sig['significant'] else "NOISE"
    print(f"  [stat]  {sig['winner']} {sig['speedup']}x  ({tag}, {robust})")

    return {
        "query":      q,
        "pg_times":   pg_times,
        "neo_times":  neo_times,
        "pg_n_rows":  len(pg_rows or []),
        "neo_n_rows": len(neo_rows or []),
        "equal":      equal,
        "significance": sig,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=15,
                        help="Numero di esecuzioni misurate per query (default 15)")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = RESULTS_DIR / f"run_{timestamp}"
    plans_dir = out_dir / "plans"
    out_dir.mkdir(parents=True, exist_ok=True)
    plans_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Benchmark SQL vs Cypher ===")
    print(f"Output: {out_dir}")
    print(f"Esecuzioni misurate per query: {args.runs} (+ 1 warm-up)")

    pg_conn = pg_connect()
    driver  = neo4j_driver()
    timings_rows = []
    summary_rows = []
    significance_rows = []

    db_versions = {}
    db_config = {}
    print("VACUUM (ANALYZE) delle tabelle Postgres (stato pulito, indipendente dai run precedenti)...")
    vacuum_stats = vacuum_postgres(pg_conn)
    if vacuum_stats.get("dead_tuples_before"):
        print(f"  tuple morte rimosse: {vacuum_stats['dead_tuples_before']}")
    try:
        with driver.session(database=os.getenv("NEO4J_DATABASE", "neo4j")) as neo_session:
            db_versions = collect_db_versions(pg_conn, neo_session)
            db_config = collect_db_config(pg_conn, neo_session)

            for q in QUERIES:
                try:
                    res = run_one_query(q, pg_conn, neo_session, args.runs, plans_dir)
                except Exception as e:
                    print(f"  [ERRORE] {q.id}: {e}")
                    continue

                for i, t in enumerate(res["pg_times"], start=1):
                    timings_rows.append({
                        "query_id": q.id, "system": "postgres",
                        "run_idx": i, "time_ms": round(t, 3),
                        "n_rows": res["pg_n_rows"],
                    })
                for i, t in enumerate(res["neo_times"], start=1):
                    timings_rows.append({
                        "query_id": q.id, "system": "neo4j",
                        "run_idx": i, "time_ms": round(t, 3),
                        "n_rows": res["neo_n_rows"],
                    })

                for sys_name, times, n_rows in [
                    ("postgres", res["pg_times"],  res["pg_n_rows"]),
                    ("neo4j",    res["neo_times"], res["neo_n_rows"]),
                ]:
                    s = summarize(times)
                    summary_rows.append({
                        "query_id":      q.id,
                        "name":          q.name,
                        "category":      q.category,
                        "system":        sys_name,
                        "median_ms":     None if s["median_ms"] is None else round(s["median_ms"], 3),
                        "min_ms":        None if s["min_ms"]    is None else round(s["min_ms"],    3),
                        "max_ms":        None if s["max_ms"]    is None else round(s["max_ms"],    3),
                        "iqr_ms":        None if s["iqr_ms"]    is None else round(s["iqr_ms"],    3),
                        "ci95_lo":       None if s["ci95_lo"]   is None else round(s["ci95_lo"],   3),
                        "ci95_hi":       None if s["ci95_hi"]   is None else round(s["ci95_hi"],   3),
                        "n_rows":        n_rows,
                        "equal_results": res["equal"],
                    })

                sig = res["significance"]
                significance_rows.append({
                    "query_id":    q.id,
                    "u_stat":      sig["u_stat"],
                    "p_value":     sig["p_value"],
                    "significant": sig["significant"],
                    "effect_size": sig["effect_size"],
                    "winner":      sig["winner"],
                    "speedup":     sig["speedup"],
                })
    finally:
        pg_conn.close()
        driver.close()

    # --- scrivo CSV ---
    timings_path = out_dir / "timings.csv"
    summary_path = out_dir / "summary.csv"
    sig_path     = out_dir / "significance.csv"

    with open(timings_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["query_id", "system", "run_idx", "time_ms", "n_rows"])
        w.writeheader()
        w.writerows(timings_rows)

    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "query_id", "name", "category", "system",
            "median_ms", "min_ms", "max_ms", "iqr_ms", "ci95_lo", "ci95_hi",
            "n_rows", "equal_results"
        ])
        w.writeheader()
        w.writerows(summary_rows)

    with open(sig_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "query_id", "u_stat", "p_value", "significant",
            "effect_size", "winner", "speedup"
        ])
        w.writeheader()
        w.writerows(significance_rows)

    # --- metadata ---
    metadata = {
        "timestamp":  timestamp,
        "runs":       args.runs,
        "n_queries":  len(QUERIES),
        "statistical_method": "Mann-Whitney U (two-sided, alpha=0.05)",
        "ci_method":  "Bootstrap 95% CI of the median (10000 resamples, seed=42)",
        "postgres_vacuum_before_run": vacuum_stats,
        **collect_hardware_info(),
        **db_versions,
    }
    (out_dir / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    (out_dir / "db_config.json").write_text(
        json.dumps(db_config, indent=2), encoding="utf-8"
    )

    print(f"\nRisultati scritti in {out_dir}")
    print(f"  - {timings_path.name} ({len(timings_rows)} righe)")
    print(f"  - {summary_path.name} ({len(summary_rows)} righe)")
    print(f"  - {sig_path.name} ({len(significance_rows)} righe)")
    print(f"  - plans/ ({len(list(plans_dir.glob('*.txt')))} file)")

    # --- tabella riassuntiva a video ---
    print(f"\n{'='*85}")
    print(f"{'ID':<5} {'Query':<35} {'PG (ms)':>8} {'Neo (ms)':>9} {'Speed':>7} {'p-val':>8} {'Sig':>5}")
    print(f"{'='*85}")
    by_query = {}
    for s in summary_rows:
        by_query.setdefault(s["query_id"], {})[s["system"]] = s
    for i, qid in enumerate(q.id for q in QUERIES):
        if qid not in by_query:
            continue
        rec = by_query[qid]
        pg = rec.get("postgres", {}).get("median_ms")
        ne = rec.get("neo4j", {}).get("median_ms")
        if pg is None or ne is None:
            continue
        sig_row = significance_rows[i] if i < len(significance_rows) else {}
        winner = "neo4j" if ne < pg else "pg"
        ratio = (pg / ne) if winner == "neo4j" else (ne / pg)
        p_val = sig_row.get("p_value", "")
        robust = "Y" if sig_row.get("significant") else "N"
        print(f"{qid:<5} {rec['postgres']['name'][:34]:<35} {pg:>8.1f} {ne:>9.1f} "
              f"{ratio:>6.1f}x {p_val:>8} {robust:>5}")


if __name__ == "__main__":
    main()
