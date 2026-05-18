"""
Harness di benchmark SQL vs Cypher.

Esegue ogni query (definita in benchmark/queries.py) N volte su PostgreSQL e
N volte su Neo4j. Scarta la prima esecuzione (warm-up della cache), e per le
restanti calcola statistiche robuste: mediana, min, max, IQR.

Confronta inoltre i risultati nei due sistemi (set logici di tuple) per
verificare la consistenza dei dati.

Output:
    benchmark/results/run_<timestamp>/
        timings.csv         righe = (query_id, system, run_idx, time_ms, n_rows)
        summary.csv         righe = (query_id, name, category, system,
                                     median_ms, min_ms, max_ms, iqr_ms,
                                     n_rows, equal_results)
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

import psycopg2
import psycopg2.extras
from neo4j import GraphDatabase

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


# ----------------------------------------------------------------------------
#  Connessioni
# ----------------------------------------------------------------------------

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
    """Estrae versioni dei due DBMS in modo da garantirne la riproducibilita'."""
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


def collect_hardware_info() -> dict:
    """Profilo hardware sintetico — utile per la riproducibilita' del benchmark."""
    info = {
        "host":         platform.node(),
        "platform":     platform.platform(),
        "machine":      platform.machine(),
        "processor":    platform.processor() or "unknown",
        "python":       platform.python_version(),
        "cpu_count":    os.cpu_count(),
    }
    # macOS: rileva modello CPU dettagliato e RAM
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


# ----------------------------------------------------------------------------
#  Esecuzione
# ----------------------------------------------------------------------------

def run_pg(conn, sql: str, params: dict, is_write: bool = False) -> tuple[float, list[tuple]]:
    """Restituisce (tempo in ms, lista di tuple del risultato).
    Per query di scrittura (is_write=True) la transazione viene rolled back
    dopo l'esecuzione, in modo che ogni run misuri su stato pulito.
    """
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
        # Esplicita transazione per poter fare rollback alla fine.
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
    """
    Normalizza i risultati per il confronto:
    - cast di Decimal/float a float arrotondato a 4 cifre per evitare
      mismatch dovuti a precisione differente fra Postgres e Neo4j;
    - cast di date/datetime a stringa ISO troncata al giorno;
    - confronto come set di tuple (ordine irrilevante per equivalenza logica).
    """
    out = []
    for r in rows:
        norm = []
        for v in r:
            if v is None:
                norm.append(None)
            elif hasattr(v, "isoformat"):  # date/datetime
                norm.append(v.isoformat()[:10])
            elif isinstance(v, (int, str)):
                norm.append(v)
            else:
                # numeric (Decimal, float)
                try:
                    norm.append(round(float(v), 4))
                except (TypeError, ValueError):
                    norm.append(str(v))
        out.append(tuple(norm))
    return set(out)


# ----------------------------------------------------------------------------
#  Statistiche
# ----------------------------------------------------------------------------

def summarize(times_ms: list[float]) -> dict:
    if not times_ms:
        return {"median_ms": None, "min_ms": None, "max_ms": None, "iqr_ms": None}
    s = sorted(times_ms)
    return {
        "median_ms": statistics.median(s),
        "min_ms":    s[0],
        "max_ms":    s[-1],
        "iqr_ms":    (statistics.quantiles(s, n=4)[2] - statistics.quantiles(s, n=4)[0])
                     if len(s) >= 4 else 0.0,
    }


# ----------------------------------------------------------------------------
#  Main
# ----------------------------------------------------------------------------

def run_one_query(q: QueryDef, pg_conn, neo_session, runs: int) -> dict:
    sql_text    = (SQL_DIR    / q.sql_file).read_text(encoding="utf-8")
    cypher_text = (CYPHER_DIR / q.cypher_file).read_text(encoding="utf-8")
    is_write    = q.category.startswith("D_")  # D_write categories use rollback

    pg_times, neo_times = [], []
    pg_rows = neo_rows = None

    print(f"\n--- {q.id}: {q.name}  [{q.category}] ---")

    # warm-up + N esecuzioni
    for i in range(runs + 1):
        t_pg, pg_rows = run_pg(pg_conn, sql_text, q.params, is_write=is_write)
        t_neo, neo_rows = run_neo4j(neo_session, cypher_text, q.params, is_write=is_write)
        if i == 0:
            print(f"  [warmup] pg={t_pg:.1f}ms  neo={t_neo:.1f}ms  (scartato)")
        else:
            pg_times.append(t_pg)
            neo_times.append(t_neo)
            print(f"  [run {i}] pg={t_pg:.1f}ms  neo={t_neo:.1f}ms")

    # confronto risultati (normalizzato)
    pg_set  = normalize_rows(pg_rows or [])
    neo_set = normalize_rows(neo_rows or [])
    equal   = (pg_set == neo_set)
    if not equal:
        only_pg  = len(pg_set - neo_set)
        only_neo = len(neo_set - pg_set)
        print(f"  [WARN] risultati DIFFERENTI: solo-pg={only_pg}, solo-neo={only_neo}")

    return {
        "query":    q,
        "pg_times": pg_times,
        "neo_times": neo_times,
        "pg_n_rows":  len(pg_rows or []),
        "neo_n_rows": len(neo_rows or []),
        "equal":      equal,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=5,
                        help="Numero di esecuzioni misurate per query (default 5)")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = RESULTS_DIR / f"run_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Benchmark SQL vs Cypher ===")
    print(f"Output: {out_dir}")
    print(f"Esecuzioni misurate per query: {args.runs} (+ 1 warm-up)")

    pg_conn = pg_connect()
    driver  = neo4j_driver()
    timings_rows = []
    summary_rows = []

    db_versions = {}
    try:
        with driver.session(database=os.getenv("NEO4J_DATABASE", "neo4j")) as neo_session:
            db_versions = collect_db_versions(pg_conn, neo_session)
            for q in QUERIES:
                try:
                    res = run_one_query(q, pg_conn, neo_session, args.runs)
                except Exception as e:
                    print(f"  [ERRORE] {q.id}: {e}")
                    continue

                # timings dettagliati
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

                # summary per sistema
                for sys_name, times, n_rows in [
                    ("postgres", res["pg_times"],  res["pg_n_rows"]),
                    ("neo4j",    res["neo_times"], res["neo_n_rows"]),
                ]:
                    s = summarize(times)
                    summary_rows.append({
                        "query_id":     q.id,
                        "name":         q.name,
                        "category":     q.category,
                        "system":       sys_name,
                        "median_ms":    None if s["median_ms"] is None else round(s["median_ms"], 3),
                        "min_ms":       None if s["min_ms"]    is None else round(s["min_ms"],    3),
                        "max_ms":       None if s["max_ms"]    is None else round(s["max_ms"],    3),
                        "iqr_ms":       None if s["iqr_ms"]    is None else round(s["iqr_ms"],    3),
                        "n_rows":       n_rows,
                        "equal_results": res["equal"],
                    })
    finally:
        pg_conn.close()
        driver.close()

    # scrivo CSV
    timings_path = out_dir / "timings.csv"
    summary_path = out_dir / "summary.csv"
    with open(timings_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["query_id", "system", "run_idx", "time_ms", "n_rows"])
        w.writeheader()
        w.writerows(timings_rows)
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "query_id", "name", "category", "system",
            "median_ms", "min_ms", "max_ms", "iqr_ms", "n_rows", "equal_results"
        ])
        w.writeheader()
        w.writerows(summary_rows)

    metadata = {
        "timestamp":  timestamp,
        "runs":       args.runs,
        "n_queries":  len(QUERIES),
        **collect_hardware_info(),
        **db_versions,
    }
    (out_dir / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )

    print(f"\nRisultati scritti in {out_dir}")
    print(f"  - {timings_path.name} ({len(timings_rows)} righe)")
    print(f"  - {summary_path.name} ({len(summary_rows)} righe)")

    # tabella riassuntiva a video
    print("\n=== SUMMARY (tempi mediani in ms) ===")
    print(f"{'ID':<5} {'Query':<35} {'Postgres':>10} {'Neo4j':>10} {'Speedup':>10} {'OK':>4}")
    by_query = {}
    for s in summary_rows:
        by_query.setdefault(s["query_id"], {})[s["system"]] = s
    for qid in [q.id for q in QUERIES]:
        if qid not in by_query:
            continue
        rec = by_query[qid]
        pg = rec.get("postgres", {}).get("median_ms")
        ne = rec.get("neo4j", {}).get("median_ms")
        if pg is None or ne is None:
            continue
        winner = "neo4j" if ne < pg else "pg"
        ratio = (pg / ne) if winner == "neo4j" else (ne / pg)
        ok = "OK" if rec["postgres"]["equal_results"] else "DIFF"
        print(f"{qid:<5} {rec['postgres']['name'][:34]:<35} {pg:>10.1f} {ne:>10.1f} "
              f"{ratio:>9.2f}x ({winner}) {ok:>4}")


if __name__ == "__main__":
    main()
