"""
Genera un report di confronto SQL vs Cypher a partire da una run di benchmark.

Input:
    benchmark/results/run_<timestamp>/summary.csv
    benchmark/results/run_<timestamp>/timings.csv

Output:
    reports/benchmark_report.md          report Markdown completo
    reports/figures/perf_by_query.png    grafico tempi mediani per query
    reports/figures/perf_by_category.png grafico tempi mediani per categoria
    reports/figures/speedup.png          grafico speedup Neo4j vs Postgres
    reports/figures/loc.png              grafico LOC delle query

Uso:
    python3 generate_report.py [--run run_<timestamp>]   (default: ultima)
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from statistics import median

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE         = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
RESULTS_DIR  = HERE / "results"
SQL_DIR      = PROJECT_ROOT / "queries" / "sql"
CYPHER_DIR   = PROJECT_ROOT / "queries" / "cypher"
REPORT_DIR   = PROJECT_ROOT / "reports"
FIG_DIR      = REPORT_DIR  / "figures"


def loc(path: Path) -> int:
    """Linee non vuote e non di solo commento."""
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("--") or s.startswith("//"):
            continue
        n += 1
    return n


# Cognitive verbosity: count of distinct logical operators in a query.
import re as _re

_SQL_KEYWORDS = [
    r"\bSELECT\b", r"\bFROM\b", r"\bWHERE\b",
    r"\bJOIN\b", r"\bLEFT\s+JOIN\b", r"\bRIGHT\s+JOIN\b", r"\bINNER\s+JOIN\b",
    r"\bGROUP\s+BY\b", r"\bHAVING\b", r"\bORDER\s+BY\b", r"\bLIMIT\b",
    r"\bUNION\s+ALL\b", r"\bUNION\b", r"\bEXISTS\b", r"\bIN\b",
    r"\bCASE\b", r"\bWITH\b", r"\bRECURSIVE\b",
    # Logical connectives — symmetrical with Cypher list below.
    r"\bAND\b", r"\bOR\b", r"\bNOT\b",
]
_CYPHER_KEYWORDS = [
    r"\bMATCH\b", r"\bOPTIONAL\s+MATCH\b", r"\bWHERE\b",
    r"\bWITH\b", r"\bRETURN\b", r"\bORDER\s+BY\b", r"\bLIMIT\b",
    r"\bUNWIND\b", r"\bCALL\b", r"\bCASE\b",
    r"\bSET\b", r"\bMERGE\b", r"\bCREATE\b", r"\bDELETE\b",
    r"\bIN\b", r"\bAND\b", r"\bOR\b", r"\bNOT\b",
]


def cognitive_verbosity(path: Path, kind: str) -> int:
    text = path.read_text(encoding="utf-8")
    # strip line comments
    out = []
    for line in text.splitlines():
        i = line.find("--" if kind == "sql" else "//")
        if i >= 0:
            line = line[:i]
        out.append(line)
    text = "\n".join(out)
    keywords = _SQL_KEYWORDS if kind == "sql" else _CYPHER_KEYWORDS
    return sum(len(_re.findall(kw, text, _re.IGNORECASE)) for kw in keywords)


def latest_run() -> Path:
    runs = sorted([p for p in RESULTS_DIR.glob("run_*") if p.is_dir()])
    if not runs:
        raise SystemExit("Nessuna run trovata in benchmark/results/. Esegui prima run_benchmark.py.")
    return runs[-1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=str, default=None,
                        help="Nome della run (es. 'run_20260101_120000'). Default: ultima.")
    args = parser.parse_args()

    run_dir = (RESULTS_DIR / args.run) if args.run else latest_run()
    print(f"Uso la run: {run_dir.name}")

    summary_path = run_dir / "summary.csv"
    timings_path = run_dir / "timings.csv"
    if not summary_path.exists():
        raise SystemExit(f"summary.csv non trovato in {run_dir}")

    # ---- carico summary
    summary = list(csv.DictReader(open(summary_path, encoding="utf-8")))

    # ---- pivot: per ogni query abbiamo postgres + neo4j
    pivot: dict[str, dict] = defaultdict(dict)
    for row in summary:
        pivot[row["query_id"]][row["system"]] = row

    # ---- LOC e cognitive verbosity delle query
    sql_loc, cyp_loc = {}, {}
    sql_verb, cyp_verb = {}, {}
    for q_id in pivot:
        for p in SQL_DIR.glob(f"{q_id}_*.sql"):
            sql_loc[q_id]  = loc(p)
            sql_verb[q_id] = cognitive_verbosity(p, "sql")
            break
        for p in CYPHER_DIR.glob(f"{q_id}_*.cypher"):
            cyp_loc[q_id]  = loc(p)
            cyp_verb[q_id] = cognitive_verbosity(p, "cypher")
            break

    # ---- grafici
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    qids       = sorted(pivot.keys())
    pg_medians = [float(pivot[q]["postgres"]["median_ms"])  for q in qids]
    ne_medians = [float(pivot[q]["neo4j"]["median_ms"])     for q in qids]

    # tempi per query
    fig, ax = plt.subplots(figsize=(10, 5))
    width = 0.4
    x = range(len(qids))
    ax.bar([i - width/2 for i in x], pg_medians, width, label="PostgreSQL", color="#336791")
    ax.bar([i + width/2 for i in x], ne_medians, width, label="Neo4j",      color="#018BFF")
    ax.set_xticks(list(x))
    ax.set_xticklabels(qids)
    ax.set_ylabel("Median execution time (ms)")
    ax.set_title("Median execution time per query")
    ax.set_yscale("log")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "perf_by_query.png", dpi=140)
    plt.close(fig)

    # tempi mediani per categoria (media sulle query della categoria)
    cats = defaultdict(lambda: {"pg": [], "ne": []})
    for q in qids:
        cats[pivot[q]["postgres"]["category"]]["pg"].append(float(pivot[q]["postgres"]["median_ms"]))
        cats[pivot[q]["postgres"]["category"]]["ne"].append(float(pivot[q]["neo4j"]["median_ms"]))
    cat_names = sorted(cats.keys())
    pg_vals = [median(cats[c]["pg"]) for c in cat_names]
    ne_vals = [median(cats[c]["ne"]) for c in cat_names]
    fig, ax = plt.subplots(figsize=(8, 5))
    x = range(len(cat_names))
    ax.bar([i - 0.2 for i in x], pg_vals, 0.4, label="PostgreSQL", color="#336791")
    ax.bar([i + 0.2 for i in x], ne_vals, 0.4, label="Neo4j",      color="#018BFF")
    ax.set_xticks(list(x))
    ax.set_xticklabels([c.replace("_", " ") for c in cat_names])
    ax.set_ylabel("Median execution time (ms)")
    ax.set_title("Comparison by query category")
    ax.set_yscale("log")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "perf_by_category.png", dpi=140)
    plt.close(fig)

    # speedup Neo4j vs Postgres (>1 = Neo4j piu' veloce, <1 = Postgres piu' veloce)
    speedups = [pg / ne for pg, ne in zip(pg_medians, ne_medians)]
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(qids, speedups, color=["#018BFF" if s > 1 else "#336791" for s in speedups])
    ax.axhline(1.0, color="black", linestyle="--", linewidth=0.8)
    ax.set_ylabel("Speedup (Postgres time / Neo4j time)")
    ax.set_title("Speedup Neo4j vs PostgreSQL  ( >1 = Neo4j is faster )")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "speedup.png", dpi=140)
    plt.close(fig)

    # LOC
    sql_vals = [sql_loc.get(q, 0) for q in qids]
    cyp_vals = [cyp_loc.get(q, 0) for q in qids]
    fig, ax = plt.subplots(figsize=(10, 5))
    x = range(len(qids))
    ax.bar([i - 0.2 for i in x], sql_vals, 0.4, label="SQL",    color="#336791")
    ax.bar([i + 0.2 for i in x], cyp_vals, 0.4, label="Cypher", color="#018BFF")
    ax.set_xticks(list(x))
    ax.set_xticklabels(qids)
    ax.set_ylabel("Lines of code (excluding blanks/comments)")
    ax.set_title("Query verbosity: SQL vs Cypher")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "loc.png", dpi=140)
    plt.close(fig)

    # Cognitive verbosity (number of logical operators)
    sql_v = [sql_verb.get(q, 0) for q in qids]
    cyp_v = [cyp_verb.get(q, 0) for q in qids]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar([i - 0.2 for i in x], sql_v, 0.4, label="SQL",    color="#336791")
    ax.bar([i + 0.2 for i in x], cyp_v, 0.4, label="Cypher", color="#018BFF")
    ax.set_xticks(list(x))
    ax.set_xticklabels(qids)
    ax.set_ylabel("Number of logical operators")
    ax.set_title("Cognitive verbosity: SQL vs Cypher")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "verbosity.png", dpi=140)
    plt.close(fig)

    # ---- testo del report
    md = []
    md.append("# Benchmark SQL vs Cypher — Report\n")
    md.append(f"Run: `{run_dir.name}`\n")
    metadata_path = run_dir / "run_metadata.json"
    if metadata_path.exists():
        meta = json.loads(metadata_path.read_text())
        md.append("\n## Experimental setup\n")
        md.append("| Item | Value |")
        md.append("|---|---|")
        md.append(f"| Host | `{meta.get('host', '?')}` |")
        md.append(f"| Platform | `{meta.get('platform', '?')}` |")
        if meta.get("cpu_model"):
            md.append(f"| CPU | `{meta.get('cpu_model')}` ({meta.get('cpu_count', '?')} cores) |")
        else:
            md.append(f"| CPU | `{meta.get('processor', '?')}` ({meta.get('cpu_count', '?')} cores) |")
        if meta.get("memory_gb"):
            md.append(f"| Memory | {meta.get('memory_gb')} GB |")
        md.append(f"| Python | `{meta.get('python', '?')}` |")
        md.append(f"| PostgreSQL | `{meta.get('postgres_version', 'unknown')}` |")
        md.append(f"| Neo4j | `{meta.get('neo4j_version', 'unknown')}` |")
        md.append(f"| Misure per query | {meta.get('runs', '?')} run + 1 warm-up scartato |")
        md.append(f"| Numero query | {meta.get('n_queries', '?')} |")
        md.append("")

    md.append("\n## Sintesi\n")
    md.append("| ID | Query | Categoria | Postgres (ms) | Neo4j (ms) | Vincitore | Speedup | Risultati |")
    md.append("|---|---|---|---:|---:|---|---:|:---:|")
    for q in qids:
        pg = float(pivot[q]["postgres"]["median_ms"])
        ne = float(pivot[q]["neo4j"]["median_ms"])
        winner = "Neo4j" if ne < pg else "Postgres"
        ratio = pg / ne if ne < pg else ne / pg
        eq = "OK" if pivot[q]["postgres"]["equal_results"].lower() == "true" else "DIFF"
        md.append(f"| {q} | {pivot[q]['postgres']['name']} | "
                  f"{pivot[q]['postgres']['category']} | "
                  f"{pg:.1f} | {ne:.1f} | **{winner}** | {ratio:.2f}x | {eq} |")

    md.append("\n## Tempi di esecuzione\n")
    md.append("![](figures/perf_by_query.png)\n")
    md.append("\n### Per categoria\n")
    md.append("![](figures/perf_by_category.png)\n")

    md.append("\n## Speedup Neo4j vs Postgres\n")
    md.append("Valori > 1 indicano che Neo4j e' piu' veloce su quella query.\n")
    md.append("![](figures/speedup.png)\n")

    md.append("\n## Query verbosity — two dimensions\n")
    md.append("LOC = lines of code. Cognitive verbosity = count of distinct "
              "logical operators (SELECT/JOIN/WHERE/GROUP BY/... in SQL; "
              "MATCH/WITH/WHERE/RETURN/... in Cypher). The two dimensions are "
              "complementary: a query can be short in lines but heavy in operators.\n")
    md.append("![](figures/loc.png)\n")
    md.append("![](figures/verbosity.png)\n")
    md.append("\n| ID | LOC SQL | LOC Cypher | LOC ratio | Verb SQL | Verb Cypher | Verb ratio |")
    md.append("|---|---:|---:|---:|---:|---:|---:|")
    for q in qids:
        s, c   = sql_loc.get(q, 0),  cyp_loc.get(q, 0)
        sv, cv = sql_verb.get(q, 0), cyp_verb.get(q, 0)
        loc_ratio  = (s / c)   if c  else 0
        verb_ratio = (sv / cv) if cv else 0
        md.append(f"| {q} | {s} | {c} | {loc_ratio:.2f}x | {sv} | {cv} | {verb_ratio:.2f}x |")

    md.append("\n## Verifica risultati\n")
    bad = [q for q in qids if pivot[q]['postgres']['equal_results'].lower() != "true"]
    if not bad:
        md.append("Tutte le 10 query restituiscono risultati equivalenti nei due sistemi.\n")
    else:
        md.append("Le seguenti query mostrano risultati discordanti tra i due sistemi:\n")
        for q in bad:
            md.append(f"- {q}: {pivot[q]['postgres']['name']}")

    md.append("\n## Note metodologiche\n")
    md.append("- Ogni query e' stata eseguita con un ciclo di warm-up scartato + N esecuzioni misurate.\n")
    md.append("- I tempi riportati sono mediani; min, max e IQR sono in `summary.csv`.\n")
    md.append("- I risultati nei due sistemi sono confrontati come *insiemi* di tuple, "
              "con normalizzazione di tipi (Decimal, date) e arrotondamento a 4 decimali "
              "per evitare falsi positivi dovuti a differenze di precisione.\n")
    md.append("- Per garantire un confronto **fair** su Q08/Q09/Q10, Postgres precomputa la "
              "materialized view `mv_played_for(player, team, season)` (vedere "
              "`schema/postgres_schema.sql`), che corrisponde esattamente alla relazione "
              "derivata `:PLAYED_FOR` di Neo4j.\n")
    md.append("- I conteggi di **cognitive verbosity** usano un insieme simmetrico di "
              "operatori logici (`AND`, `OR`, `NOT` inclusi sia per SQL sia per Cypher).\n")

    md.append("\n## Limitations\n")
    md.append("Il benchmark misura performance **single-node, single-user, in-memory** su "
              "un dataset di dimensione media (917k eventi, 542k lineup rows, 26k match). "
              "Restano fuori dallo scope di questo lavoro:\n")
    md.append("- carico **concorrente** (write contention, lock, MVCC vs lock-free traversal);\n")
    md.append("- carico **OLTP intensivo** (insert rate, transazioni distribuite);\n")
    md.append("- scaling **orizzontale** (sharding Postgres con Citus vs Neo4j Fabric);\n")
    md.append("- benchmark **standardizzati** su dataset grafo (LDBC SNB, vedere bibliografia);\n")
    md.append("- tuning dei sistemi: entrambi usano configurazione di default; il delta "
              "potrebbe ridursi (o ampliarsi) con tuning specifico (shared_buffers per "
              "Postgres, pagecache size per Neo4j).\n")

    md.append("\n## Riferimenti\n")
    md.append("- Angles, R., Gutierrez, C. (2008). *Survey of Graph Database Models*. "
              "ACM Computing Surveys, 40(1).\n")
    md.append("- Vicknair, C. et al. (2010). *A Comparison of a Graph Database and a "
              "Relational Database*. ACM SE 2010.\n")
    md.append("- Holzschuher, F., Peinl, R. (2013). *Performance of Graph Query Languages: "
              "Comparison of Cypher, Gremlin and Native Access in Neo4j*. EDBT/ICDT Workshops.\n")
    md.append("- Erling, O. et al. (2015). *The LDBC Social Network Benchmark: "
              "Interactive Workload*. SIGMOD 2015.\n")
    md.append("- Robinson, I., Webber, J., Eifrem, E. (2015). *Graph Databases* (2nd ed.). "
              "O'Reilly Media.\n")

    out = REPORT_DIR / "benchmark_report.md"
    out.write_text("\n".join(md), encoding="utf-8")
    print(f"Report scritto in: {out}")
    print(f"Figure in: {FIG_DIR}")


if __name__ == "__main__":
    main()
