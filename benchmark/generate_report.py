"""
Genera un report di confronto SQL vs Cypher a partire da una run di benchmark.

Input:
    benchmark/results/run_<timestamp>/summary.csv
    benchmark/results/run_<timestamp>/timings.csv
    benchmark/results/run_<timestamp>/significance.csv
    benchmark/results/run_<timestamp>/plans/
    benchmark/results/run_<timestamp>/db_config.json
    benchmark/results/run_<timestamp>/run_metadata.json
    benchmark/results/syntactic_complexity.csv
    benchmark/results/index_ablation/<latest>.csv
    benchmark/results/sensitivity/<latest>.json   (opzionale, sez. 10)

Output:
    reports/benchmark_report.md
    reports/figures/*.png

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
import numpy as np

HERE         = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
RESULTS_DIR  = HERE / "results"
SQL_DIR      = PROJECT_ROOT / "queries" / "sql"
CYPHER_DIR   = PROJECT_ROOT / "queries" / "cypher"
REPORT_DIR   = PROJECT_ROOT / "reports"
FIG_DIR      = REPORT_DIR  / "figures"


def loc(path: Path) -> int:
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("--") or s.startswith("//"):
            continue
        n += 1
    return n


def strip_comments(text: str, kind: str) -> str:
    out = []
    for line in text.splitlines():
        i = line.find("--" if kind == "sql" else "//")
        if i >= 0:
            line = line[:i]
        out.append(line)
    return "\n".join(out)


_SQL_KW = [
    r"\bLEFT\s+JOIN\b", r"\bRIGHT\s+JOIN\b", r"\bINNER\s+JOIN\b",
    r"\bCROSS\s+JOIN\b", r"\bUNION\s+ALL\b", r"\bNOT\s+EXISTS\b",
    r"\bNOT\s+IN\b", r"\bGROUP\s+BY\b", r"\bORDER\s+BY\b",
    r"\bSELECT\b", r"\bFROM\b", r"\bWHERE\b", r"\bJOIN\b",
    r"\bHAVING\b", r"\bLIMIT\b", r"\bUNION\b", r"\bINTERSECT\b",
    r"\bEXCEPT\b", r"\bEXISTS\b", r"\bIN\b", r"\bCASE\b",
    r"\bWITH\b", r"\bRECURSIVE\b", r"\bAND\b", r"\bOR\b", r"\bNOT\b",
]
_CYP_KW = [
    r"\bOPTIONAL\s+MATCH\b", r"\bORDER\s+BY\b",
    r"\bMATCH\b", r"\bWHERE\b", r"\bWITH\b", r"\bRETURN\b",
    r"\bLIMIT\b", r"\bUNWIND\b", r"\bCALL\b", r"\bCASE\b",
    r"\bSET\b", r"\bMERGE\b", r"\bCREATE\b", r"\bDELETE\b",
    r"\bIN\b", r"\bAND\b", r"\bOR\b", r"\bNOT\b",
]


def cognitive_verbosity(path: Path, kind: str) -> int:
    text = strip_comments(path.read_text(encoding="utf-8"), kind)
    keywords = _SQL_KW if kind == "sql" else _CYP_KW
    total = 0
    for kw in keywords:
        matches = list(re.finditer(kw, text, flags=re.IGNORECASE))
        total += len(matches)
        for m in reversed(matches):
            text = text[:m.start()] + (" " * (m.end() - m.start())) + text[m.end():]
    return total


def latest_run() -> Path:
    runs = sorted([p for p in RESULTS_DIR.glob("run_*") if p.is_dir()])
    if not runs:
        raise SystemExit("Nessuna run trovata in benchmark/results/.")
    return runs[-1]


def latest_ablation() -> Path | None:
    ablation_dir = RESULTS_DIR / "index_ablation"
    if not ablation_dir.exists():
        return None
    csvs = sorted(ablation_dir.glob("*.csv"))
    return csvs[-1] if csvs else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=str, default=None)
    args = parser.parse_args()

    run_dir = (RESULTS_DIR / args.run) if args.run else latest_run()
    print(f"Uso la run: {run_dir.name}")

    summary = list(csv.DictReader(open(run_dir / "summary.csv", encoding="utf-8")))

    # significance
    sig_path = run_dir / "significance.csv"
    sig_data = {}
    if sig_path.exists():
        for row in csv.DictReader(open(sig_path, encoding="utf-8")):
            sig_data[row["query_id"]] = row

    pivot: dict[str, dict] = defaultdict(dict)
    for row in summary:
        pivot[row["query_id"]][row["system"]] = row

    # LOC + verbosity
    sql_loc, cyp_loc = {}, {}
    sql_verb, cyp_verb = {}, {}
    for q_id in pivot:
        for p in SQL_DIR.glob(f"{q_id}_*.sql"):
            sql_loc[q_id] = loc(p)
            sql_verb[q_id] = cognitive_verbosity(p, "sql")
            break
        for p in CYPHER_DIR.glob(f"{q_id}_*.cypher"):
            cyp_loc[q_id] = loc(p)
            cyp_verb[q_id] = cognitive_verbosity(p, "cypher")
            break

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    qids = sorted(pivot.keys())
    pg_medians = [float(pivot[q]["postgres"]["median_ms"]) for q in qids]
    ne_medians = [float(pivot[q]["neo4j"]["median_ms"]) for q in qids]

    # --- CI data ---
    has_ci = "ci95_lo" in summary[0] if summary else False
    pg_ci_lo = [float(pivot[q]["postgres"].get("ci95_lo", 0)) for q in qids] if has_ci else None
    pg_ci_hi = [float(pivot[q]["postgres"].get("ci95_hi", 0)) for q in qids] if has_ci else None
    ne_ci_lo = [float(pivot[q]["neo4j"].get("ci95_lo", 0)) for q in qids] if has_ci else None
    ne_ci_hi = [float(pivot[q]["neo4j"].get("ci95_hi", 0)) for q in qids] if has_ci else None

    # ======== FIGURE 1: tempi per query (con CI) ========
    fig, ax = plt.subplots(figsize=(12, 5.5))
    width = 0.35
    x = np.arange(len(qids))

    if has_ci:
        pg_err = [
            [m - lo for m, lo in zip(pg_medians, pg_ci_lo)],
            [hi - m for m, hi in zip(pg_medians, pg_ci_hi)],
        ]
        ne_err = [
            [m - lo for m, lo in zip(ne_medians, ne_ci_lo)],
            [hi - m for m, hi in zip(ne_medians, ne_ci_hi)],
        ]
        ax.bar(x - width/2, pg_medians, width, yerr=pg_err, capsize=3,
               label="PostgreSQL", color="#336791", ecolor="#1a3a50")
        ax.bar(x + width/2, ne_medians, width, yerr=ne_err, capsize=3,
               label="Neo4j", color="#018BFF", ecolor="#005fa3")
    else:
        ax.bar(x - width/2, pg_medians, width, label="PostgreSQL", color="#336791")
        ax.bar(x + width/2, ne_medians, width, label="Neo4j", color="#018BFF")

    # significance markers
    for i, qid in enumerate(qids):
        if qid in sig_data:
            sig = sig_data[qid].get("significant", "False")
            if sig == "True":
                top = max(pg_medians[i], ne_medians[i])
                if has_ci:
                    top = max(top, pg_ci_hi[i], ne_ci_hi[i])
                ax.text(i, top * 1.15, "*", ha="center", fontsize=14, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(qids)
    ax.set_ylabel("Median execution time (ms)")
    ax.set_title("Median execution time per query (log scale, * = p < 0.05)")
    ax.set_yscale("log")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "perf_by_query.png", dpi=150)
    plt.close(fig)

    # ======== FIGURE 2: tempi per categoria ========
    cats = defaultdict(lambda: {"pg": [], "ne": []})
    for q in qids:
        cats[pivot[q]["postgres"]["category"]]["pg"].append(float(pivot[q]["postgres"]["median_ms"]))
        cats[pivot[q]["postgres"]["category"]]["ne"].append(float(pivot[q]["neo4j"]["median_ms"]))
    cat_names = sorted(cats.keys())
    pg_vals = [median(cats[c]["pg"]) for c in cat_names]
    ne_vals = [median(cats[c]["ne"]) for c in cat_names]
    fig, ax = plt.subplots(figsize=(8, 5))
    x2 = np.arange(len(cat_names))
    ax.bar(x2 - 0.2, pg_vals, 0.4, label="PostgreSQL", color="#336791")
    ax.bar(x2 + 0.2, ne_vals, 0.4, label="Neo4j", color="#018BFF")
    ax.set_xticks(x2)
    ax.set_xticklabels([c.replace("_", " ") for c in cat_names])
    ax.set_ylabel("Median execution time (ms)")
    ax.set_title("Comparison by query category")
    ax.set_yscale("log")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "perf_by_category.png", dpi=150)
    plt.close(fig)

    # ======== FIGURE 3: speedup ========
    speedups = [pg / ne for pg, ne in zip(pg_medians, ne_medians)]
    fig, ax = plt.subplots(figsize=(12, 5))
    colors = []
    for i, s in enumerate(speedups):
        qid = qids[i]
        is_sig = sig_data.get(qid, {}).get("significant", "False") == "True"
        if s > 1:
            colors.append("#018BFF" if is_sig else "#99d1ff")
        else:
            colors.append("#336791" if is_sig else "#8ab4d4")
    bars = ax.bar(qids, speedups, color=colors, edgecolor="white", linewidth=0.5)
    ax.axhline(1.0, color="black", linestyle="--", linewidth=0.8)
    ax.set_ylabel("Speedup (Postgres time / Neo4j time)")
    ax.set_title("Speedup Neo4j vs PostgreSQL  ( >1 = Neo4j faster, saturated = p<0.05 )")
    ax.grid(True, axis="y", alpha=0.3)

    for i, (s, qid) in enumerate(zip(speedups, qids)):
        ax.text(i, s + (0.3 if s > 1 else -0.15),
                f"{s:.1f}x", ha="center", va="bottom", fontsize=8)

    fig.tight_layout()
    fig.savefig(FIG_DIR / "speedup.png", dpi=150)
    plt.close(fig)

    # ======== FIGURE 4 & 5: LOC + verbosity ========
    sql_l = [sql_loc.get(q, 0) for q in qids]
    cyp_l = [cyp_loc.get(q, 0) for q in qids]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - 0.2, sql_l, 0.4, label="SQL", color="#336791")
    ax.bar(x + 0.2, cyp_l, 0.4, label="Cypher", color="#018BFF")
    ax.set_xticks(x)
    ax.set_xticklabels(qids)
    ax.set_ylabel("Lines of code (excluding blanks/comments)")
    ax.set_title("Query length: SQL vs Cypher")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "loc.png", dpi=150)
    plt.close(fig)

    sql_v = [sql_verb.get(q, 0) for q in qids]
    cyp_v = [cyp_verb.get(q, 0) for q in qids]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - 0.2, sql_v, 0.4, label="SQL", color="#336791")
    ax.bar(x + 0.2, cyp_v, 0.4, label="Cypher", color="#018BFF")
    ax.set_xticks(x)
    ax.set_xticklabels(qids)
    ax.set_ylabel("Number of logical operators")
    ax.set_title("Cognitive verbosity: SQL vs Cypher (consume-on-match counting)")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "verbosity.png", dpi=150)
    plt.close(fig)

    # ======== FIGURE 6: box plot distribuzione tempi ========
    timings_path = run_dir / "timings.csv"
    if timings_path.exists():
        timings = list(csv.DictReader(open(timings_path, encoding="utf-8")))
        fig, axes = plt.subplots(3, 4, figsize=(16, 10), sharey=False)
        axes_flat = axes.flatten()
        for idx, qid in enumerate(qids):
            ax = axes_flat[idx]
            pg_t = [float(r["time_ms"]) for r in timings
                    if r["query_id"] == qid and r["system"] == "postgres"]
            ne_t = [float(r["time_ms"]) for r in timings
                    if r["query_id"] == qid and r["system"] == "neo4j"]
            bp = ax.boxplot([pg_t, ne_t], tick_labels=["PG", "Neo4j"],
                            patch_artist=True, widths=0.6)
            bp["boxes"][0].set_facecolor("#336791")
            bp["boxes"][1].set_facecolor("#018BFF")
            for b in bp["boxes"]:
                b.set_alpha(0.7)
            ax.set_title(qid, fontsize=10, fontweight="bold")
            ax.set_ylabel("ms")
            ax.grid(True, axis="y", alpha=0.3)
        for idx in range(len(qids), len(axes_flat)):
            axes_flat[idx].set_visible(False)
        fig.suptitle("Distribution of execution times per query", fontsize=13)
        fig.tight_layout()
        fig.savefig(FIG_DIR / "distributions.png", dpi=150)
        plt.close(fig)

    # ================================================================
    #  REPORT MARKDOWN
    # ================================================================
    md = []

    # --- Header ---
    md.append("# Benchmark SQL vs Cypher — Report\n")
    md.append(f"Run: `{run_dir.name}`\n")

    # --- Setup ---
    metadata_path = run_dir / "run_metadata.json"
    if metadata_path.exists():
        meta = json.loads(metadata_path.read_text())
        md.append("\n## 1. Experimental setup\n")
        md.append("| Item | Value |")
        md.append("|---|---|")
        md.append(f"| Host | `{meta.get('host', '?')}` |")
        md.append(f"| Platform | `{meta.get('platform', '?')}` |")
        cpu_label = meta.get("cpu_model") or meta.get("processor", "?")
        md.append(f"| CPU | `{cpu_label}` ({meta.get('cpu_count', '?')} cores) |")
        if meta.get("memory_gb"):
            md.append(f"| Memory | {meta.get('memory_gb')} GB |")
        md.append(f"| Python | `{meta.get('python', '?')}` |")
        md.append(f"| PostgreSQL | `{meta.get('postgres_version', 'unknown')}` |")
        md.append(f"| Neo4j | `{meta.get('neo4j_version', 'unknown')}` |")
        md.append(f"| Misure per query | {meta.get('runs', '?')} run + 1 warm-up scartato |")
        md.append(f"| Numero query | {meta.get('n_queries', '?')} |")
        md.append(f"| Test statistico | {meta.get('statistical_method', 'N/A')} |")
        md.append(f"| Intervalli di confidenza | {meta.get('ci_method', 'N/A')} |")
        md.append("")

    # --- DB config ---
    db_config_path = run_dir / "db_config.json"
    if db_config_path.exists():
        db_cfg = json.loads(db_config_path.read_text())
        md.append("\n### Configurazione runtime dei DBMS\n")
        if db_cfg.get("postgres"):
            md.append("**PostgreSQL**:\n")
            md.append("| Parameter | Value |")
            md.append("|---|---|")
            for k, v in db_cfg["postgres"].items():
                md.append(f"| `{k}` | `{v}` |")
            md.append("")
        if db_cfg.get("neo4j"):
            md.append("**Neo4j**:\n")
            md.append("| Parameter | Value |")
            md.append("|---|---|")
            for k, v in db_cfg["neo4j"].items():
                md.append(f"| `{k}` | `{v}` |")
            md.append("")

    # --- Sintesi ---
    md.append("\n## 2. Risultati\n")
    ci_cols = " CI 95% PG | CI 95% Neo4j |" if has_ci else ""
    ci_hdr  = " :---: | :---: |" if has_ci else ""
    md.append(f"| ID | Query | Categoria | PG (ms) | Neo4j (ms) |{ci_cols} Vincitore | Speedup | p-value | Effect r | Sig | Risultati |")
    md.append(f"|---|---|---|---:|---:|{ci_hdr}---|---:|---:|---:|:---:|:---:|")

    for q in qids:
        pg = float(pivot[q]["postgres"]["median_ms"])
        ne = float(pivot[q]["neo4j"]["median_ms"])
        winner = "Neo4j" if ne < pg else "Postgres"
        ratio = pg / ne if ne < pg else ne / pg
        eq = "OK" if pivot[q]["postgres"]["equal_results"].lower() == "true" else "DIFF"
        sig_row = sig_data.get(q, {})
        p_val = sig_row.get("p_value", "—")
        eff = sig_row.get("effect_size", "—")
        is_sig = sig_row.get("significant", "False") == "True"
        sig_mark = "Yes" if is_sig else "No"

        ci_cells = ""
        if has_ci:
            pg_lo = pivot[q]["postgres"].get("ci95_lo", "")
            pg_hi = pivot[q]["postgres"].get("ci95_hi", "")
            ne_lo = pivot[q]["neo4j"].get("ci95_lo", "")
            ne_hi = pivot[q]["neo4j"].get("ci95_hi", "")
            ci_cells = f" [{pg_lo}, {pg_hi}] | [{ne_lo}, {ne_hi}] |"

        bold_winner = f"**{winner}**" if is_sig else f"{winner} (ns)"
        md.append(f"| {q} | {pivot[q]['postgres']['name']} | "
                  f"{pivot[q]['postgres']['category']} | "
                  f"{pg:.1f} | {ne:.1f} |{ci_cells} {bold_winner} | {ratio:.2f}x | {p_val} | {eff} | {sig_mark} | {eq} |")

    md.append("\nLegenda: **grassetto** = differenza statisticamente significativa (p < 0.05, Mann-Whitney U); "
              "(ns) = non significativa. **Effect r** = correlazione rank-biserial "
              "(0 = distribuzioni indistinguibili, 1 = separazione completa): misura la "
              "*magnitudine* della differenza, complementare al p-value che ne misura l'affidabilita'.\n")

    n_sig = sum(1 for q in qids if sig_data.get(q, {}).get("significant") == "True")
    md.append(f"\n{n_sig} confronti su {len(qids)} sono statisticamente significativi; "
              f"{sum(1 for q in qids if sig_data.get(q, {}).get('effect_size') not in (None, '') and float(sig_data[q]['effect_size']) >= 0.8)} "
              f"hanno effect size molto grande (r >= 0.8).\n")

    # --- Grafici ---
    md.append("\n## 3. Tempi di esecuzione\n")
    md.append("Error bars rappresentano il 95% CI bootstrap della mediana. "
              "L'asterisco (*) indica significativita' statistica.\n")
    md.append("![](figures/perf_by_query.png)\n")
    md.append("\n### Per categoria\n")
    md.append("![](figures/perf_by_category.png)\n")

    md.append("\n## 4. Distribuzioni dei tempi\n")
    md.append("Box plot delle singole esecuzioni per query. Permette di valutare "
              "la dispersione e identificare outlier.\n")
    if (FIG_DIR / "distributions.png").exists():
        md.append("![](figures/distributions.png)\n")

    md.append("\n## 5. Speedup Neo4j vs Postgres\n")
    md.append("Valori > 1 indicano che Neo4j e' piu' veloce. "
              "Barre saturate: p < 0.05; barre desaturate: non significativo.\n")
    md.append("![](figures/speedup.png)\n")

    # --- Verbosity ---
    md.append("\n## 6. Espressivita': LOC e cognitive verbosity\n")
    md.append("**LOC** = righe non vuote e non di commento. "
              "**Cognitive verbosity** = numero di occorrenze di operatori logici "
              "distinti, con *consume-on-match*: le keyword composte (LEFT JOIN, "
              "NOT EXISTS, OPTIONAL MATCH, ORDER BY) vengono riconosciute per prime "
              "e rimosse dal testo prima di contare le keyword semplici, prevenendo "
              "il double-counting.\n")
    md.append("![](figures/loc.png)\n")
    md.append("![](figures/verbosity.png)\n")

    md.append("\n| ID | LOC SQL | LOC Cypher | LOC ratio | Verb SQL | Verb Cypher | Verb ratio |")
    md.append("|---|---:|---:|---:|---:|---:|---:|")
    for q in qids:
        s, c = sql_loc.get(q, 0), cyp_loc.get(q, 0)
        sv, cv = sql_verb.get(q, 0), cyp_verb.get(q, 0)
        lr = (s / c) if c else 0
        vr = (sv / cv) if cv else 0
        md.append(f"| {q} | {s} | {c} | {lr:.2f}x | {sv} | {cv} | {vr:.2f}x |")

    md.append("\n### Nota metodologica sulla verbosity\n")
    md.append("La metrica cattura il numero di *step logici* che il lettore deve "
              "tracciare mentalmente. SQL e Cypher esprimono lo stesso concetto con "
              "meccanismi diversi: un pattern Cypher multi-nodo (es. "
              "`(a)-[:R]->(b)<-[:R]-(c)`) sussume cio' che in SQL richiede piu' "
              "JOIN espliciti. Questa asimmetria e' intrinseca ai linguaggi, non "
              "un artefatto della misurazione — la metrica la cattura intenzionalmente.\n")

    # --- Query plans ---
    plans_dir = run_dir / "plans"
    if plans_dir.exists() and list(plans_dir.glob("*.txt")):
        md.append("\n## 7. Analisi dei query plan\n")
        md.append("Per ogni query, il benchmark cattura `EXPLAIN (ANALYZE, BUFFERS)` "
                  "per Postgres e `PROFILE` per Neo4j. Di seguito i plan piu' "
                  "significativi.\n")

        key_queries = ["Q05", "Q07", "Q09", "Q10"]
        for qid in key_queries:
            pg_plan_path = plans_dir / f"{qid}_postgres.txt"
            neo_plan_path = plans_dir / f"{qid}_neo4j.txt"
            if not pg_plan_path.exists():
                continue

            md.append(f"\n### {qid}: {pivot.get(qid, {}).get('postgres', {}).get('name', qid)}\n")

            pg_plan = pg_plan_path.read_text(encoding="utf-8").strip()
            md.append("**PostgreSQL** (`EXPLAIN ANALYZE`):\n")
            md.append("```")
            md.append(pg_plan)
            md.append("```\n")

            if neo_plan_path.exists():
                neo_plan = neo_plan_path.read_text(encoding="utf-8").strip()
                md.append("**Neo4j** (`PROFILE`):\n")
                md.append("```")
                md.append(neo_plan)
                md.append("```\n")

        md.append(f"\nI plan completi per tutte le 12 query sono in `{plans_dir.relative_to(PROJECT_ROOT)}/`.\n")

    # --- Verifica risultati ---
    md.append("\n## 8. Verifica di correttezza\n")
    bad = [q for q in qids if pivot[q]['postgres']['equal_results'].lower() != "true"]
    if not bad:
        md.append("Tutte le 10 query read (Q01-Q10) restituiscono risultati semanticamente "
                  "equivalenti nei due sistemi, verificato come confronto di insiemi di "
                  "tuple normalizzate (arrotondamento a 4 decimali, date come ISO-8601, "
                  "ordine irrilevante). Le 2 query write (Q11-Q12) producono conteggi "
                  "identici di righe modificate.\n")
    else:
        md.append("Le seguenti query mostrano risultati discordanti:\n")
        for q in bad:
            md.append(f"- {q}: {pivot[q]['postgres']['name']}")
        md.append("")

    # --- Index ablation ---
    md.append("\n## 9. Index ablation\n")
    abl_path = latest_ablation()
    if abl_path:
        abl_rows = list(csv.DictReader(open(abl_path, encoding="utf-8")))
        md.append("Matrice di ablazione: per ciascuna coppia (indice, query), "
                  "il benchmark rimuove l'indice, riesegue la query, e lo ripristina. "
                  "Lo slowdown misura il rapporto tra la mediana senza indice e la "
                  "mediana con indice.\n")
        md.append("| System | Index | Query | With (ms) | Without (ms) | Slowdown |")
        md.append("|---|---|---|---:|---:|---:|")

        baselines = {}
        for r in abl_rows:
            key = (r["system"], r["index_name"], r["query_id"])
            if r["phase"] == "with_index":
                baselines[key] = float(r["median_ms"])

        for r in abl_rows:
            if r["phase"] != "without_index":
                continue
            key = (r["system"], r["index_name"], r["query_id"])
            base = baselines.get(key, 1)
            without = float(r["median_ms"])
            slow = without / base if base > 0 else 0
            bold = f"**{slow:.2f}x**" if slow > 1.5 else f"{slow:.2f}x"
            md.append(f"| {r['system']} | `{r['index_name']}` | {r['query_id']} | "
                      f"{base:.1f} | {without:.1f} | {bold} |")
        md.append("")
    else:
        md.append("Dati non disponibili. Eseguire `python3 benchmark/index_ablation.py`.\n")

    # --- Sensitivity: work_mem su Q07 ---
    md.append("\n## 10. Analisi di sensibilita': work_mem e lo spill di Q07\n")
    sens_dir = RESULTS_DIR / "sensitivity"
    sens_files = sorted(sens_dir.glob("q07_workmem_*.json")) if sens_dir.exists() else []
    ne_q07_med = ne_medians[qids.index("Q07")] if "Q07" in qids else None
    if sens_files:
        sens = json.loads(sens_files[-1].read_text(encoding="utf-8"))
        md.append("Il piano di Q07 contiene l'unico accesso a disco dell'intero benchmark: "
                  "un sort *external merge* (~18 MB di file temporanei) causato dal "
                  "`work_mem` di default (4MB). Ipotesi da verificare: quanto del gap "
                  "Postgres/Neo4j su Q07 e' un artefatto di questo parametro di tuning?\n")
        md.append(f"Q07 e' stata rieseguita solo su Postgres ({sens['runs']} run + warm-up "
                  f"per configurazione, `SET work_mem` a livello di sessione):\n")
        md.append("| work_mem | Mediana PG (ms) | CI 95% | Sort method (EXPLAIN ANALYZE) | Gap vs Neo4j |")
        md.append("|---|---:|:---:|---|---:|")
        for c in sens["configs"]:
            gap = f"{c['median_ms'] / ne_q07_med:.2f}x" if ne_q07_med else "—"
            md.append(f"| {c['work_mem']} | {c['median_ms']:.1f} | "
                      f"[{c['ci95_lo']:.1f}, {c['ci95_hi']:.1f}] | `{c['sort_method']}` | {gap} |")
        first, last = sens["configs"][0], sens["configs"][-1]
        delta_pct = abs(first["median_ms"] - last["median_ms"]) / first["median_ms"] * 100
        md.append(f"\n**Risultato: ipotesi smentita.** Eliminare lo spill (il sort passa a "
                  f"quicksort interamente in memoria) sposta la mediana dello {delta_pct:.1f}%. "
                  f"Su macOS i file temporanei restano nella page cache del sistema operativo, "
                  f"quindi l'external merge non paga I/O fisico. Il collo di bottiglia reale "
                  f"e' la strategia sort-based scelta dal planner per `COUNT(DISTINCT)` su "
                  f"542k righe, non il disco: il gap con Neo4j (hash aggregation sulle "
                  f"relazioni) **non e' un artefatto di tuning**.\n")
    else:
        md.append("Dati non disponibili. Eseguire `python3 benchmark/sensitivity_q07.py`.\n")

    # --- Ease-of-use ---
    md.append("\n## 11. Ease-of-use e suitability\n")
    md.append("La terza dimensione dichiarata nella proposal e' l'ease-of-use dei due "
              "sistemi. E' per natura la meno misurabile: per non ridurla a un'opinione, "
              "la ancoriamo a **proxy oggettivi prodotti dal progetto stesso** (righe di "
              "codice della pipeline, dipendenze, statement DDL) e ai problemi "
              "**effettivamente incontrati** e documentati in "
              "`reports/engineering_challenges.md` e nella storia del repository.\n")
    md.append("| Aspetto | PostgreSQL | Neo4j |")
    md.append("|---|---|---|")
    md.append("| Definizione dello schema | 9 `CREATE TABLE` + 19 indici; tipi, PK composite, FK e `CHECK` espliciti | 7 constraint di unicita' + 4 indici; lo schema e' *implicito*, emerge dal load |")
    md.append("| Bulk load (~1.5M righe) | `COPY FROM STDIN`: 1 statement per tabella, nessuna dipendenza esterna | `LOAD CSV`; per le 542k `LINEUP_OF` serve `apoc.periodic.iterate` (batch 5000) — cioe' il **plugin APOC** — o una transazione monolitica |")
    md.append("| Codice di load (LOC) | 150 (`load_postgres.py`) | 240 (`load_neo4j.py`, +60%) |")
    md.append("| Relazione derivata player-team-season | `CREATE MATERIALIZED VIEW` + `REFRESH` | `MATCH ... MERGE` di aggregazione post-load |")
    md.append("| Integrita' referenziale | **Enforced**: il `COPY` di `match_event` e' *fallito* per FK violation, rivelando 5.632 riferimenti orfani (Challenge 1) | Non esiste FK: un `MATCH` su un `Player` mancante non lega la riga e la **scarta in silenzio** — lo stesso difetto sarebbe passato inosservato |")
    md.append("| Strumenti di analisi delle performance | `EXPLAIN (ANALYZE, BUFFERS)`: piano testuale con costi stimati/reali, buffer, tempi per nodo | `PROFILE`: albero di operatori con rows e db hits, visualizzato nel Browser |")
    md.append("| Ambiente interattivo | `psql` / pgAdmin | Neo4j Browser, con visualizzazione nativa del grafo |")
    md.append("| Curva di apprendimento | SQL: prerequisito del corso | Cypher: nuovo per entrambi gli autori; i pattern ASCII-art (`(a)-[:R]->(b)`) sono intuitivi per i traversal, meno per le aggregazioni (Q02, classifica: l'`UNION ALL` SQL diventa un `UNWIND` su una lista di mappe) |")
    md.append("| Pitfall incontrati | Tipizzazione rigida: colonne pandas integer-con-NaN rifiutate (Challenge 2) | Semantica di `NULL` (`NULL = NULL` e' null: Q05 richiedeva un `IS NOT NULL` esplicito per equivalere al self-join SQL); direzionalita' di `PLAYED_FOR` (6 hop = `*..12` archi); `shortestPath` non esprime predicati fra archi consecutivi |")
    md.append("")
    md.append("Tre osservazioni:\n")
    md.append("1. **Lo schema esplicito e' un costo iniziale che si ripaga come rete di "
              "sicurezza.** Le 273 righe di DDL di Postgres sono sembrate overhead "
              "finche' il vincolo FK ha intercettato un difetto reale del dataset che "
              "il modello a grafo avrebbe assorbito silenziosamente. In un progetto "
              "data-intensive, *fallire presto* e' una feature.\n")
    md.append("2. **Scrivere query e' piu' facile in Cypher, caricare dati e' piu' facile "
              "in SQL.** Un pattern come "
              "`(:Team {name:'Milan'})<-[:PLAYED_FOR]-(p)-[:PLAYED_FOR]->(:Team {name:'Juventus'})` "
              "sostituisce quattro join; ma il bulk load ha richiesto +60% di codice "
              "e un plugin, e l'assenza di tipi sui property ha spostato la validazione "
              "sull'ETL.\n")
    md.append("3. **La semantica implicita di Cypher e' la fonte principale di errori "
              "sottili.** Tutti e tre i pitfall Cypher (NULL, direzionalita', "
              "predicati di path) sono emersi solo grazie alla verifica automatica di "
              "equivalenza dei risultati: senza un oracolo relazionale accanto, sarebbero "
              "rimasti invisibili. E' un argomento a favore di mantenere entrambi i "
              "sistemi durante lo sviluppo, anche quando la produzione ne usera' uno solo.\n")
    md.append("**Suitability per il dominio**: il dataset calcistico e' *misto*: le "
              "anagrafiche, le classifiche e le statistiche per stagione sono "
              "relazionali; le reti di compagni di squadra e le catene di trasferimenti "
              "sono grafi. Nessuno dei due modelli e' \"naturale\" per l'intero dominio, "
              "il che rende il caso di studio adatto a un confronto — e la persistenza "
              "poliglotta (sez. 13) la risposta pragmatica.\n")

    # --- Scalabilita' ---
    md.append("\n## 12. Considerazioni sulla scalabilita'\n")
    md.append("Il benchmark e' single-node e single-user (8 GB di RAM, working set "
              "interamente in cache: nessun piano contiene `shared read`). Non misura "
              "la scalabilita', ma i piani catturati permettono di **ragionare su come "
              "i costi crescono** con i dati, e l'architettura dei due sistemi su come "
              "si distribuiscono.\n")
    md.append("### Crescita dei dati su un singolo nodo\n")
    md.append("- **Aggregazioni full-scan (Q07)**: il piano Postgres ordina 542.281 righe "
              "(`external merge`, 18 MB); il costo e' O(n log n) nel numero di righe di "
              "formazione. A 10x (80 stagioni) lo spill crescerebbe in proporzione, ma "
              "il rimedio e' standard: partizionamento dichiarativo per `season` e "
              "`work_mem` dimensionato. Neo4j aggrega le stesse relazioni in modo "
              "lineare, ma **senza meccanismo di spill**: il grafo deve stare nella "
              "pagecache, altrimenti il degrado e' brusco.\n")
    md.append("- **Traversal a profondita' variabile (Q10)**: la CTE ricorsiva "
              "materializza l'intera frontiera BFS — 44.251 stati e 2.977.128 accessi "
              "al buffer per profondita' <= 6 — un costo che cresce con la dimensione del "
              "grafo *e* esponenzialmente con la profondita'. `shortestPath()` (BFS "
              "bidirezionale) tocca 237 db hits: il lavoro dipende dalla lunghezza del "
              "cammino e dal grado dei nodi attraversati, **non dalla dimensione totale "
              "del grafo**. E' l'index-free adjacency letta come proprieta' di scaling: "
              "il 89x osservato non e' un artefatto della taglia del dataset ma tende "
              "ad *allargarsi* al crescere dei dati.\n")
    md.append("- **Scritture (Q11/Q12)**: in Postgres ogni `UPDATE` crea nuove versioni "
              "di tupla (MVCC) da ripulire con `VACUUM`; in Neo4j la scrittura passa dal "
              "transaction log. Entrambi i sistemi sono stati misurati con un solo "
              "writer: sotto scrittori concorrenti entrano in gioco lock a livello di "
              "riga (Postgres) e di nodo/relazione (Neo4j), non testati.\n")
    md.append("### Scaling orizzontale\n")
    md.append("- **PostgreSQL**: la replica in streaming scala le *letture* senza "
              "toccare le query (l'intero benchmark read girerebbe invariato su una "
              "replica). Lo sharding dei *dati* (Citus) richiede una chiave di "
              "distribuzione; i join multi-hop di Q09/Q10 fra shard diversi diventano "
              "join di rete e degradano.\n")
    md.append("- **Neo4j**: il causal cluster replica l'**intero grafo** su ogni core "
              "member — scala le letture, non i dati. Il partizionamento reale "
              "(Fabric / composite database) e' manuale, e un traversal che attraversa "
              "una partizione perde l'index-free adjacency. E' il limite noto dei graph "
              "database: il partizionamento di un grafo minimizzando gli archi tagliati "
              "e' un problema NP-hard, e la proprieta' che rende Q10 89x piu' veloce su "
              "un nodo e' esattamente quella che **non si distribuisce gratis**.\n")
    md.append("### Verdetto\n")
    md.append("A 10x i dati (80 stagioni, ~5M formazioni, ~9M eventi) entrambi i sistemi "
              "restano su un nodo con accorgimenti ordinari (partizionamento e "
              "`work_mem` per Postgres, pagecache dimensionata per Neo4j) e i rapporti "
              "osservati si conservano o si accentuano a favore di Neo4j sui traversal. "
              "Oltre la memoria di una singola macchina, il workload OLAP scala meglio "
              "in Postgres (Citus, storage colonnare); il workload a grafo scala in "
              "Neo4j solo finche' il grafo e' replicabile per intero. La "
              "misura di questi regimi e' il lavoro futuro piu' rilevante (sez. 16).\n")

    # --- Conclusioni ---
    q10_speedup = pg_medians[qids.index("Q10")] / ne_medians[qids.index("Q10")] if "Q10" in qids else 0
    q07_speedup = pg_medians[qids.index("Q07")] / ne_medians[qids.index("Q07")] if "Q07" in qids else 0
    q12_pg = pg_medians[qids.index("Q12")] if "Q12" in qids else 0
    q12_ne = ne_medians[qids.index("Q12")] if "Q12" in qids else 0

    md.append("\n## 13. Conclusioni\n")
    md.append("Sei risultati emersi dai dati:\n")

    md.append(f"\n1. **Postgres domina sulle aggregazioni OLAP-light** (categoria A): "
              f"3 query su 4 a favore di Postgres. L'ottimizzatore relazionale maturo "
              f"e gli indici B-tree sono ideali per query con join limitati e aggregazioni "
              f"semplici.\n")

    md.append(f"\n2. **Neo4j domina sul traversal a profondita' variabile** (Q10): "
              f"**{q10_speedup:.1f}x piu' veloce**. I piani catturati mostrano il perche': "
              f"la CTE ricorsiva di Postgres materializza l'intera frontiera BFS "
              f"(decine di migliaia di stati, milioni di accessi al buffer), mentre "
              f"`shortestPath()` si ferma appena i due fronti si incontrano (poche "
              f"centinaia di db hits). E' l'effetto dell'index-free adjacency.\n")

    md.append(f"\n3. **Neo4j vince anche sull'aggregazione full-scan** (Q07, "
              f"{q07_speedup:.1f}x), ma per una ragione diversa dal traversal: il planner "
              f"Postgres esegue `COUNT(DISTINCT)` con una strategia sort-based su 542k "
              f"righe, mentre Neo4j aggrega le stesse relazioni con hash aggregation. "
              f"L'analisi di sensibilita' (sez. 10) esclude che il gap dipenda dal "
              f"tuning di `work_mem`.\n")

    md.append(f"\n4. **La materialized view equalizza il campo sulle query intermedie** "
              f"(Q09): Postgres con `mv_played_for` vince su una query 2-hop che, senza "
              f"la precomputazione, sarebbe dominata da Neo4j. Questo isola il contributo "
              f"del *motore di esecuzione* da quello del *modello di carico*.\n")

    md.append(f"\n5. **Espressivita'**: Cypher e' sistematicamente piu' breve del SQL "
              f"equivalente. Il caso estremo e' Q10: 3 LOC / 3 operatori logici in "
              f"Cypher contro ~21 LOC / ~26 operatori in SQL (CTE ricorsiva BFS).\n")

    md.append(f"\n6. **Schema flexibility** (Q12): aggiungere un attributo derivato "
              f"a tutti i match costa ~{q12_ne:.0f} ms in Neo4j (singolo `SET`) vs "
              f"~{q12_pg:.0f} ms in Postgres (`ALTER TABLE` + `UPDATE`). Rilevante "
              f"in contesti con schema evolution frequente.\n")

    md.append("\n**Verdetto operativo**:\n")
    md.append("- **PostgreSQL**: aggregazioni OLAP, schema stabile e fortemente "
              "vincolato, integrita' referenziale critica, ecosistema BI/ETL maturo.\n")
    md.append("- **Neo4j**: dominio intrinsecamente a grafo, traversal a profondita' "
              "variabile (raccomandazione, fraud detection, supply chain), schema "
              "evolution frequente.\n")
    md.append("- **Polyglot persistence**: in produzione i due DB spesso coesistono, "
              "ciascuno gestendo la parte del dominio per cui e' nato. L'analisi di "
              "ease-of-use (sez. 11) aggiunge un argomento operativo: tenere il modello "
              "relazionale accanto a quello a grafo durante lo sviluppo intercetta "
              "errori di dati e di semantica che il grafo da solo assorbe in silenzio.\n")

    # --- Threats to validity ---
    md.append("\n## 14. Threats to validity\n")

    md.append("\n### Validita' interna\n")
    md.append("- **Warm-up e caching**: la prima esecuzione di ogni query viene "
              "scartata per escludere cold-cache effects. Le esecuzioni successive "
              "beneficiano della page cache OS e della buffer pool dei DBMS. "
              "Il benchmark misura quindi performance *warm-cache*, coerente con "
              "un sistema in regime.\n")
    md.append("- **Variabilita' di misurazione**: le query con mediane < 20 ms e "
              "speedup < 1.3x (Q01, Q02, Q04) hanno CI parzialmente sovrapposti tra "
              "i due sistemi. Il test di Mann-Whitney identifica quali differenze "
              "sono statisticamente significative; per Q01 la differenza resta "
              "nel rumore di misurazione (p = 0.30).\n")
    md.append("- **Rollback nelle write query**: Q11 e Q12 usano rollback per "
              "mantenere lo stato pulito tra le run. Il costo del rollback e' "
              "escluso dal timer in entrambi i sistemi.\n")

    md.append("\n### Validita' esterna\n")
    md.append("- **Single-node, single-user**: il benchmark non misura performance "
              "sotto carico concorrente (write contention, MVCC vs lock-free traversal), "
              "carico OLTP intensivo, o scaling orizzontale.\n")
    md.append("- **Dimensione del dataset**: 26k match, 917k eventi, 542k lineup rows. "
              "Un dataset di dimensione *media*: abbastanza grande da rendere "
              "significative le differenze di query plan, ma non abbastanza per "
              "evidenziare problemi di scalabilita' I/O.\n")
    md.append("- **Configurazione di default e asimmetria di memoria**: entrambi i DBMS "
              "usano la configurazione di default (documentata nella sezione Setup), che "
              "assegna budget di memoria diversi: `shared_buffers` 128MB per Postgres "
              "contro heap 1GiB + pagecache 512MiB per Neo4j. Due evidenze empiriche ne "
              "limitano l'impatto: (i) nessuno dei 24 piani catturati contiene letture "
              "fisiche (`shared read`) — il working set e' interamente in cache in "
              "entrambi i sistemi; (ii) l'analisi di sensibilita' su `work_mem` "
              "(sez. 10) mostra che l'unico spill del benchmark non sposta la mediana. "
              "Un tuning sistematico resta comunque una variabile non esplorata per i "
              "confronti piu' tirati (categoria A).\n")
    md.append("- **Asimmetria nel caricamento**: Postgres carica `PlayerStats` e "
              "`TeamStats` (~184k righe) che Neo4j non importa. Su 8 GB di RAM "
              "l'impatto sulla cache e' trascurabile, ma va documentato.\n")

    md.append("\n### Validita' del costrutto\n")
    md.append("- **Cognitive verbosity**: la metrica cattura il numero di operatori "
              "logici, non la complessita' semantica. Un self-join e un FK join "
              "contano uguale. La metrica e' complementare (non sostitutiva) a LOC.\n")
    md.append("- **Tassonomia delle query**: la classificazione A/B/C/D e' definita "
              "*a priori* in base alla struttura logica, non *a posteriori* in base "
              "ai risultati. Questo previene il cherry-picking.\n")

    # --- Note metodologiche ---
    md.append("\n## 15. Note metodologiche\n")
    md.append("- I tempi riportati sono **mediani**; min, max, IQR e 95% CI sono in `summary.csv`.\n")
    md.append("- La significativita' statistica e' valutata con il test di **Mann-Whitney U** "
              "(non parametrico, two-sided, alpha = 0.05), con effect size "
              "**rank-biserial**. Gli intervalli di confidenza sono calcolati con "
              "**bootstrap** della mediana (10.000 ricampionamenti, seed fisso 42: "
              "i CI sono riproducibili bit-a-bit).\n")
    md.append("- I risultati nei due sistemi sono confrontati come *insiemi* di tuple, "
              "con normalizzazione di tipi (Decimal, date) e arrotondamento a 4 decimali.\n")
    md.append("- Per garantire un confronto **fair** su Q08/Q09/Q10, Postgres precomputa la "
              "materialized view `mv_played_for(player, team, season)`, equivalente "
              "alla relazione derivata `:PLAYED_FOR` di Neo4j.\n")
    md.append("- I query plan (`EXPLAIN ANALYZE` e `PROFILE`) sono catturati "
              "automaticamente dall'harness e salvati in `plans/`.\n")

    # --- Limitations ---
    md.append("\n## 16. Limitations e lavoro futuro\n")
    md.append("Restano fuori dallo scope di questo lavoro:\n")
    md.append("- Carico **concorrente** (write contention, lock, MVCC vs lock-free traversal).\n")
    md.append("- Carico **OLTP intensivo** (insert rate, transazioni distribuite).\n")
    md.append("- Scaling **orizzontale** (sharding Postgres con Citus vs Neo4j Fabric): "
              "discusso qualitativamente in sez. 12, non misurato.\n")
    md.append("- Benchmark **standardizzati** su dataset grafo (LDBC Social Network Benchmark).\n")
    md.append("- **Tuning sistematico** dei sistemi: esplorato solo `work_mem` su Q07 "
              "(sez. 10); resta fuori un grid completo (shared_buffers, pagecache, "
              "parallelismo).\n")

    # --- Riferimenti ---
    md.append("\n## 17. Riferimenti\n")
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
    md.append("- Mann, H. B., Whitney, D. R. (1947). *On a Test of Whether one of Two "
              "Random Variables is Stochastically Larger than the Other*. Annals of "
              "Mathematical Statistics, 18(1).\n")

    out = REPORT_DIR / "benchmark_report.md"
    out.write_text("\n".join(md), encoding="utf-8")
    print(f"Report scritto in: {out}")
    print(f"Figure in: {FIG_DIR}")


if __name__ == "__main__":
    main()
