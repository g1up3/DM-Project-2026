"""
Analisi di sensibilita': scalabilita' con la dimensione dei dati.

Il benchmark gira su un solo dataset. Per osservare come i costi crescono con i
dati senza ricaricare i DB, due query vengono rieseguite su sottoinsiemi
crescenti di stagioni (ultime 2, ultime 4, tutte le 8), con la stessa struttura
in entrambi i sistemi:

  Q07-scaled  aggregazione full-scan: giocatori presenti in TUTTE le N stagioni
              del sottoinsieme (COUNT(DISTINCT season) = N)
  Q09-scaled  traversal a profondita' fissa (2 hop) sul grafo ristretto alle
              stagioni del sottoinsieme (mv_played_for / PLAYED_FOR filtrati)

Per ogni (query, N, sistema): mediana e CI bootstrap su --runs esecuzioni
(+1 warm-up), piu' le righe restituite (per verificare che i due sistemi
concordino anche sui sottoinsiemi).

Output: benchmark/results/sensitivity/scale_<timestamp>.json
Il report (generate_report.py) include automaticamente l'ultimo file (sez. 12).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_benchmark import pg_connect, neo4j_driver, run_pg, run_neo4j, summarize, normalize_rows  # noqa: E402

OUT_DIR = HERE / "results" / "sensitivity"
ALL_SEASONS = ["2008/2009", "2009/2010", "2010/2011", "2011/2012",
               "2012/2013", "2013/2014", "2014/2015", "2015/2016"]
SUBSETS = {2: ALL_SEASONS[-2:], 4: ALL_SEASONS[-4:], 8: ALL_SEASONS}

Q07_SQL = """
SELECT p.player_api_id, p.player_name, COUNT(DISTINCT m.season) AS seasons_played
FROM   soccer.match_lineup l
JOIN   soccer.match  m ON m.match_api_id = l.match_api_id
JOIN   soccer.player p ON p.player_api_id = l.player_api_id
WHERE  m.season = ANY(%(seasons)s)
GROUP  BY p.player_api_id, p.player_name
HAVING COUNT(DISTINCT m.season) = %(n)s
ORDER  BY p.player_name, p.player_api_id"""
Q07_CY = """
MATCH (p:Player)-[:LINEUP_OF]->(m:Match)
WHERE m.season IN $seasons
WITH p, count(DISTINCT m.season) AS seasons_played
WHERE seasons_played = $n
RETURN p.playerApiId AS player_api_id, p.name AS player, seasons_played
ORDER BY player, player_api_id"""

Q09_SQL = """
WITH pf AS (SELECT * FROM soccer.mv_played_for WHERE season = ANY(%(seasons)s)),
x_history AS (
    SELECT pf.team_api_id, pf.season
    FROM   pf JOIN soccer.player p ON p.player_api_id = pf.player_api_id
    WHERE  p.player_name = %(player_name)s),
direct_teammates AS (
    SELECT DISTINCT pf.player_api_id
    FROM   pf JOIN x_history h ON h.team_api_id = pf.team_api_id AND h.season = pf.season),
teams_of_direct AS (
    SELECT DISTINCT pf.team_api_id, pf.season
    FROM   pf JOIN direct_teammates d ON d.player_api_id = pf.player_api_id)
SELECT p.player_name AS player_2hop, COUNT(*) AS connection_strength
FROM   pf
JOIN   teams_of_direct td ON td.team_api_id = pf.team_api_id AND td.season = pf.season
JOIN   soccer.player p ON p.player_api_id = pf.player_api_id
WHERE  pf.player_api_id NOT IN (SELECT player_api_id FROM direct_teammates)
  AND  p.player_name <> %(player_name)s
GROUP  BY p.player_name
ORDER  BY connection_strength DESC, player_2hop
LIMIT  %(top_n)s"""
Q09_CY = """
MATCH (x:Player {name: $player_name})-[r1:PLAYED_FOR]->(t:Team)<-[r2:PLAYED_FOR]-(direct:Player)
WHERE r1.season = r2.season AND r1.season IN $seasons
WITH x, collect(DISTINCT direct) AS direct_set
MATCH (d:Player)-[r3:PLAYED_FOR]->(t2:Team)
WHERE d IN direct_set AND r3.season IN $seasons
WITH x, direct_set, collect(DISTINCT [t2.teamApiId, r3.season]) AS covered_pairs
MATCH (p2:Player)-[r4:PLAYED_FOR]->(t3:Team)
WHERE p2 <> x AND NOT p2 IN direct_set AND r4.season IN $seasons
  AND [t3.teamApiId, r4.season] IN covered_pairs
RETURN p2.name AS player_2hop, count(*) AS connection_strength
ORDER BY connection_strength DESC, player_2hop
LIMIT $top_n"""

EXPERIMENTS = {
    "Q07-scaled": (Q07_SQL, Q07_CY, lambda n, seasons: {"seasons": seasons, "n": n}),
    "Q09-scaled": (Q09_SQL, Q09_CY, lambda n, seasons: {"seasons": seasons,
                                                         "player_name": "Lionel Messi", "top_n": 20}),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=10)
    args = ap.parse_args()
    pg = pg_connect()
    drv = neo4j_driver()
    out = {"timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"), "runs": args.runs, "results": []}
    try:
        with drv.session(database=os.getenv("NEO4J_DATABASE", "neo4j")) as s:
            for name, (sql, cy, mk) in EXPERIMENTS.items():
                for n, seasons in SUBSETS.items():
                    params = mk(n, seasons)
                    pg_t, ne_t = [], []
                    pg_rows = ne_rows = None
                    for i in range(args.runs + 1):
                        t1, pg_rows, _ = run_pg(pg, sql, params)
                        t2, ne_rows, _ = run_neo4j(s, cy, params)
                        if i:
                            pg_t.append(t1); ne_t.append(t2)
                    sp, sn = summarize(pg_t), summarize(ne_t)
                    equal = normalize_rows(pg_rows) == normalize_rows(ne_rows)
                    rec = {"experiment": name, "n_seasons": n,
                           "pg_median_ms": round(sp["median_ms"], 2), "pg_ci": [round(sp["ci95_lo"], 2), round(sp["ci95_hi"], 2)],
                           "neo_median_ms": round(sn["median_ms"], 2), "neo_ci": [round(sn["ci95_lo"], 2), round(sn["ci95_hi"], 2)],
                           "n_rows": len(pg_rows), "equal_results": equal}
                    out["results"].append(rec)
                    print(f"[{name} | {n} stagioni] PG {rec['pg_median_ms']:.1f} ms  Neo4j {rec['neo_median_ms']:.1f} ms  "
                          f"righe={rec['n_rows']}  uguali={equal}", flush=True)
    finally:
        pg.close(); drv.close()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"scale_{out['timestamp']}.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Scritto: {path}")


if __name__ == "__main__":
    main()
