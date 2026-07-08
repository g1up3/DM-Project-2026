"""
Analisi di sensibilita': quanto del gap Postgres/Neo4j su Q07 dipende da work_mem?

Il piano di Q07 su Postgres (config default, work_mem=4MB) mostra un sort
"external merge" che spilla ~18 MB su disco: parte del tempo misurato e'
quindi un effetto di *tuning*, non del modello relazionale in se'.
Questo script quantifica la decomposizione: riesegue Q07 (solo Postgres)
con valori crescenti di work_mem impostati a livello di sessione, e per
ogni configurazione registra mediana, CI bootstrap e il Sort Method
effettivo estratto da EXPLAIN ANALYZE.

Output:
    benchmark/results/sensitivity/q07_workmem_<timestamp>.json

Il report (generate_report.py) include automaticamente l'ultimo file di
sensitivity trovato, confrontando le mediane con quella di Neo4j nella run
di riferimento.

Uso:
    python3 benchmark/sensitivity_q07.py [--runs N] [--work-mem 4MB 64MB 256MB]
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from statistics import median

HERE = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(HERE))
from run_benchmark import pg_connect, run_pg, summarize  # noqa: E402

SQL_FILE = HERE.parent / "queries" / "sql" / "Q07_players_in_all_seasons.sql"
OUT_DIR = HERE / "results" / "sensitivity"


def sort_method(conn, sql: str) -> str:
    """Estrae la riga 'Sort Method' da EXPLAIN ANALYZE (evidenza dello spill)."""
    with conn.cursor() as cur:
        cur.execute(f"EXPLAIN (ANALYZE, BUFFERS) {sql}")
        plan = "\n".join(r[0] for r in cur.fetchall())
    m = re.search(r"Sort Method: (.+)", plan)
    return m.group(1).strip() if m else "n/a"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=15,
                        help="Esecuzioni misurate per configurazione (default 15)")
    parser.add_argument("--work-mem", nargs="+", default=["4MB", "64MB"],
                        help="Valori di work_mem da testare (default: 4MB 64MB)")
    args = parser.parse_args()

    sql = SQL_FILE.read_text(encoding="utf-8")
    conn = pg_connect()
    configs = []
    try:
        for wm in args.work_mem:
            with conn.cursor() as cur:
                cur.execute("SET work_mem = %s", (wm,))
            conn.commit()

            times = []
            for i in range(args.runs + 1):
                t, _rows = run_pg(conn, sql, {})
                if i == 0:
                    print(f"[work_mem={wm}] warmup {t:.1f}ms (scartato)")
                    continue
                times.append(t)
            method = sort_method(conn, sql)
            s = summarize(times)
            print(f"[work_mem={wm}] mediana {s['median_ms']:.1f}ms  "
                  f"CI95 [{s['ci95_lo']:.1f}, {s['ci95_hi']:.1f}]  sort: {method}")
            configs.append({
                "work_mem":   wm,
                "median_ms":  round(s["median_ms"], 3),
                "min_ms":     round(s["min_ms"], 3),
                "max_ms":     round(s["max_ms"], 3),
                "iqr_ms":     round(s["iqr_ms"], 3),
                "ci95_lo":    round(s["ci95_lo"], 3),
                "ci95_hi":    round(s["ci95_hi"], 3),
                "sort_method": method,
            })
    finally:
        conn.close()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = OUT_DIR / f"q07_workmem_{ts}.json"
    out.write_text(json.dumps({
        "timestamp": ts,
        "query_id":  "Q07",
        "system":    "postgres",
        "runs":      args.runs,
        "note":      "work_mem impostato con SET a livello di sessione; "
                     "il resto della configurazione e' identico alla run di riferimento.",
        "configs":   configs,
    }, indent=2), encoding="utf-8")
    print(f"\nScritto: {out}")


if __name__ == "__main__":
    main()
