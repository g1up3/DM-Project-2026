"""
Analisi di sensibilita': la semantica dello shortest path in Cypher (Q10).

La BFS SQL di Q10 collega due giocatori solo se hanno vestito la stessa maglia
nella STESSA stagione (pf2.season = pf1.season). In Cypher esistono tre
formulazioni con costo e garanzie diverse:

  V0  shortestPath((a)-[:PLAYED_FOR*..12]-(b))
      Semantica lasca: attraversa un Team senza vincolare la stagione dei due
      archi. Puo' dare risposte DIVERSE dal SQL.
  V1  shortestPath + predicato di path (stessa stagione su archi consecutivi)
      Semantica esatta, ma se il cammino lasco piu' corto viola il predicato
      Neo4j ripiega su un'enumerazione esaustiva (VarLengthExpand): tempo non
      limitato. Misurata SOLO sulla coppia di riferimento, con timeout.
  V2  quantified path pattern + SHORTEST 1 con predicato inline
      Semantica esatta per costruzione (StatefulShortestPath). E' la Q10
      adottata dal benchmark.

Lo script produce:
  1. per la coppia di riferimento (Messi -> Pirlo): hop, mediana/CI su N run,
     operatore e db hits da PROFILE per V0, V1, V2;
  2. su una lista di coppie: hop secondo SQL, V0 e V2, per contare i casi
     in cui la semantica lasca diverge dal SQL.

Output: benchmark/results/sensitivity/q10_semantics_<timestamp>.json
Il report (generate_report.py) include automaticamente l'ultimo file.

Uso:
    python3 benchmark/sensitivity_q10.py [--runs N] [--timeout SEC]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from neo4j.exceptions import ClientError, TransientError

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_benchmark import pg_connect, neo4j_driver, run_pg, summarize  # noqa: E402

SQL_FILE = HERE.parent / "queries" / "sql" / "Q10_shortest_path_between_players.sql"
OUT_DIR = HERE / "results" / "sensitivity"

REFERENCE_PAIR = ("Lionel Messi", "Andrea Pirlo")
PAIRS = [
    ("Lionel Messi", "Andrea Pirlo"),
    ("Lionel Messi", "Gianluigi Buffon"),
    ("Cristiano Ronaldo", "Francesco Totti"),
    ("Zlatan Ibrahimovic", "Manuel Neuer"),
    ("Luis Suarez", "Robert Lewandowski"),
    ("Wayne Rooney", "Giorgio Chiellini"),
    ("Neymar", "Antonio Di Natale"),
    ("Sergio Ramos", "Eden Hazard"),
]

VARIANTS = {
    "V0_shortestPath_loose": """
MATCH (a:Player {name: $player_a}), (b:Player {name: $player_b})
MATCH path = shortestPath((a)-[:PLAYED_FOR*..12]-(b))
RETURN length(path) / 2 AS hops""",
    "V1_shortestPath_path_predicate": """
MATCH (a:Player {name: $player_a}), (b:Player {name: $player_b})
MATCH path = shortestPath((a)-[:PLAYED_FOR*..12]-(b))
WHERE all(i IN range(0, size(relationships(path)) - 2, 2)
          WHERE relationships(path)[i].season = relationships(path)[i+1].season)
RETURN length(path) / 2 AS hops""",
    "V2_qpp_shortest_exact": """
MATCH (a:Player {name: $player_a}), (b:Player {name: $player_b})
MATCH path = SHORTEST 1 (a)
  ((x:Player)-[r1:PLAYED_FOR]->(:Team)<-[r2:PLAYED_FOR]-(y:Player) WHERE r1.season = r2.season){1,6}
  (b)
RETURN length(path) / 2 AS hops""",
}
SWEEP_VARIANTS = ("V0_shortestPath_loose", "V2_qpp_shortest_exact")   # V1 esclusa: fallback esaustivo


def run_cypher(session, query: str, params: dict, timeout_s: float):
    """Esegue in una transazione con timeout server-side. Ritorna (hops, ms) o (None, ms) su timeout."""
    t0 = time.perf_counter()
    try:
        with session.begin_transaction(timeout=timeout_s) as tx:
            rec = tx.run(query, **params).single()
            hops = rec["hops"] if rec else None
        return hops, (time.perf_counter() - t0) * 1000.0
    except (ClientError, TransientError) as e:
        return f"timeout:{type(e).__name__}", (time.perf_counter() - t0) * 1000.0


def profile_summary(session, query: str, params: dict, timeout_s: float) -> dict:
    """Operatore radice del path search + db hits totali del piano."""
    def walk(plan, acc):
        acc["db_hits"] += int(plan.get("args", {}).get("DbHits", 0) or 0)
        op = plan["operatorType"]
        if "ShortestPath" in op or "VarLengthExpand" in op:
            acc["ops"].append(op)
        for c in plan.get("children", []):
            walk(c, acc)
    try:
        with session.begin_transaction(timeout=timeout_s) as tx:
            prof = tx.run("PROFILE " + query, **params).consume().profile
        acc = {"db_hits": 0, "ops": []}
        walk(prof, acc)
        return {"db_hits": acc["db_hits"], "path_operators": sorted(set(acc["ops"]))}
    except (ClientError, TransientError) as e:
        return {"db_hits": None, "path_operators": [f"timeout:{type(e).__name__}"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=15, help="run misurate per variante (default 15)")
    ap.add_argument("--timeout", type=float, default=20.0, help="timeout server-side per query Cypher, s (default 20)")
    args = ap.parse_args()

    sql = SQL_FILE.read_text(encoding="utf-8")
    pg = pg_connect()
    drv = neo4j_driver()
    out = {"timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"), "query_id": "Q10",
           "runs": args.runs, "timeout_s": args.timeout,
           "reference_pair": list(REFERENCE_PAIR), "variants": {}, "pairs": []}
    try:
        with drv.session(database=os.getenv("NEO4J_DATABASE", "neo4j")) as s:
            # --- 1. tre varianti sulla coppia di riferimento ---
            p = {"player_a": REFERENCE_PAIR[0], "player_b": REFERENCE_PAIR[1]}
            for name, q in VARIANTS.items():
                hops, _ = run_cypher(s, q, p, args.timeout)   # warm-up
                times = []
                for _ in range(args.runs):
                    h, t = run_cypher(s, q, p, args.timeout)
                    if isinstance(h, str):
                        break
                    times.append(t)
                st = summarize(times) if times else {}
                prof = profile_summary(s, q, p, args.timeout)
                out["variants"][name] = {
                    "hops": hops, "n": len(times),
                    "median_ms": round(st["median_ms"], 3) if times else None,
                    "ci95_lo": round(st["ci95_lo"], 3) if times else None,
                    "ci95_hi": round(st["ci95_hi"], 3) if times else None,
                    **prof,
                }
                print(f"[{name}] hops={hops} median={out['variants'][name]['median_ms']} ms "
                      f"dbHits={prof['db_hits']} ops={prof['path_operators']}")

            # --- 2. sweep semantico su piu' coppie (SQL vs V0 vs V2) ---
            for a, b in PAIRS:
                params = {"player_a": a, "player_b": b}
                _, sql_rows = run_pg(pg, sql, params)
                sql_hops = sql_rows[0][0] if sql_rows else None
                row = {"pair": [a, b], "sql_hops": sql_hops}
                for name in SWEEP_VARIANTS:
                    run_cypher(s, VARIANTS[name], params, args.timeout)      # warm-up
                    h, t = run_cypher(s, VARIANTS[name], params, args.timeout)
                    row[name] = {"hops": h, "ms": round(t, 2)}
                row["loose_diverges"] = row["V0_shortestPath_loose"]["hops"] != sql_hops
                row["exact_matches"] = row["V2_qpp_shortest_exact"]["hops"] == sql_hops
                out["pairs"].append(row)
                print(f"[{a} -> {b}] sql={sql_hops} V0={row['V0_shortestPath_loose']['hops']} "
                      f"V2={row['V2_qpp_shortest_exact']['hops']}"
                      f"{'  <-- V0 diverge' if row['loose_diverges'] else ''}")
    finally:
        pg.close()
        drv.close()

    out["n_pairs"] = len(out["pairs"])
    out["n_loose_diverges"] = sum(1 for r in out["pairs"] if r["loose_diverges"])
    out["n_exact_matches"] = sum(1 for r in out["pairs"] if r["exact_matches"])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"q10_semantics_{out['timestamp']}.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nV0 diverge dal SQL su {out['n_loose_diverges']}/{out['n_pairs']} coppie; "
          f"V2 coincide su {out['n_exact_matches']}/{out['n_pairs']}.\nScritto: {path}")


if __name__ == "__main__":
    main()
