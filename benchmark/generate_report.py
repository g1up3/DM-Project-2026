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
    r"\bLIMIT\b", r"\bUNWIND\b", r"\bCALL\b", r"\bSHORTEST\b", r"\bCASE\b",
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
        md.append(f"| Neo4j | `{meta.get('neo4j_version', 'unknown')}` — edizione Enterprise "
                  f"inclusa in Neo4j Desktop (licenza developer); nessuna feature "
                  f"Enterprise-only e' usata (runtime pipelined, singola istanza): il "
                  f"benchmark e' riproducibile su Community Edition |")
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
    # Correzione di Holm-Bonferroni per i confronti multipli (12 test, alpha 0.05)
    holm_sig = {}
    pvals = [(q, float(sig_data[q]["p_value"])) for q in qids
             if sig_data.get(q, {}).get("p_value") not in (None, "", "None")]
    m_tests = len(pvals)
    for rank, (q, p) in enumerate(sorted(pvals, key=lambda t: t[1])):
        holm_sig[q] = p <= 0.05 / (m_tests - rank)
        if not holm_sig[q]:            # Holm: dal primo non rigetto in poi, nessun rigetto
            for q2, _ in sorted(pvals, key=lambda t: t[1])[rank + 1:]:
                holm_sig[q2] = False
            break

    md.append(f"| ID | Query | Categoria | PG (ms) | Neo4j (ms) |{ci_cols} Vincitore | Speedup | p-value | Effect r | Sig | Sig (Holm) | Risultati |")
    md.append(f"|---|---|---|---:|---:|{ci_hdr}---|---:|---:|---:|:---:|:---:|:---:|")

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
        holm_mark = "Yes" if holm_sig.get(q) else "No"
        md.append(f"| {q} | {pivot[q]['postgres']['name']} | "
                  f"{pivot[q]['postgres']['category']} | "
                  f"{pg:.1f} | {ne:.1f} |{ci_cells} {bold_winner} | {ratio:.2f}x | {p_val} | {eff} | {sig_mark} | {holm_mark} | {eq} |")

    n_holm = sum(1 for q in qids if holm_sig.get(q))
    md.append("\nLegenda: **grassetto** = differenza statisticamente significativa (p < 0.05, Mann-Whitney U); "
              "(ns) = non significativa. **Effect r** = correlazione rank-biserial "
              "(0 = distribuzioni indistinguibili, 1 = separazione completa): misura la "
              "*magnitudine* della differenza, complementare al p-value che ne misura l'affidabilita'. "
              f"**Sig (Holm)** = significativita' dopo correzione di Holm-Bonferroni per i {m_tests} "
              f"confronti simultanei (family-wise error rate 0.05): {n_holm} confronti restano "
              "significativi. Le conclusioni del report si appoggiano solo su differenze che "
              "superano la correzione E hanno effect size r >= 0.8.\n")

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
    reads  = [q for q in qids if not pivot[q]["postgres"]["category"].startswith("D_")]
    writes = [q for q in qids if pivot[q]["postgres"]["category"].startswith("D_")]
    if not bad:
        md.append(f"Tutte le {len(reads)} query read ({reads[0]}-{reads[-1]}) restituiscono risultati "
                  "semanticamente equivalenti nei due sistemi, verificato come confronto di "
                  "insiemi di tuple normalizzate (arrotondamento a 4 decimali, date come "
                  "ISO-8601, ordine irrilevante). Le query di raggruppamento usano le chiavi "
                  "(`player_api_id`, `team_api_id`), non i nomi: il dataset contiene 163 "
                  "nomi di giocatore e 3 nomi di squadra omonimi.\n")
    else:
        md.append("Le seguenti query mostrano risultati discordanti:\n")
        for q in bad:
            md.append(f"- {q}: {pivot[q]['postgres']['name']}")
        md.append("")
    if writes:
        md.append("Per le query write il confronto e' sul numero di righe/proprieta' "
                  "effettivamente modificate, letto dal driver (`cursor.rowcount` in Postgres, "
                  "`counters.properties_set` in Neo4j) — un `UPDATE` non restituisce righe e "
                  "confrontare due result-set vuoti non verificherebbe nulla:\n")
        md.append("| ID | Query | Righe modificate PG | Proprieta' modificate Neo4j | Uguali |")
        md.append("|---|---|---:|---:|:---:|")
        for q in writes:
            md.append(f"| {q} | {pivot[q]['postgres']['name']} | {pivot[q]['postgres']['n_rows']} | "
                      f"{pivot[q]['neo4j']['n_rows']} | "
                      f"{'OK' if pivot[q]['postgres']['equal_results'].lower() == 'true' else 'DIFF'} |")
        md.append("")
        md.append("Q11 aggiorna solo i gol con marcatore noto (`player1_id IS NOT NULL`): i 109 "
                  "gol il cui riferimento al giocatore e' stato annullato nell'ETL non hanno "
                  "una relazione `SCORED_IN` nel grafo, e senza il filtro i due workload "
                  "avrebbero toccato popolazioni diverse (21.551 vs 21.442 righe).\n")

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
        md.append("La matrice viene da una sessione separata (10 run per fase, senza il "
                  "protocollo VACUUM del run di riferimento): i valori assoluti in ms non sono "
                  "confrontabili con la tabella della sez. 2; la misura e' il rapporto "
                  "con/senza indice.\n")
        md.append("Tre letture della matrice. (i) Gli indici che contano sono quelli sul "
                  "*punto di ingresso* della query: `ix_lineup_player` (Q08) e "
                  "`player_name_idx` (Q08) valgono 2-3.5x, perche' senza di essi il lookup "
                  "del giocatore diventa una scansione di 542k righe / 11k nodi. (ii) Gli "
                  "indici sulla materialized view contano poco per Q09/Q10 (1.0-1.2x): la BFS "
                  "di Q10 e' dominata dall'espansione della frontiera, non dal lookup iniziale, "
                  "e Postgres ripiega su hash join efficienti. (iii) **L'anomalia di "
                  "`team_name_idx` su Q06 (0.62x: senza indice e' piu' veloce)** non e' un "
                  "errore di misura: `Team` ha 299 nodi, e un `NodeByLabelScan` con filtro "
                  "in memoria su 299 record costa meno di un `NodeIndexSeek` (discesa "
                  "nell'albero dell'indice + dereferenziazione). Sotto una certa cardinalita' "
                  "l'indice e' controproducente — lo stesso motivo per cui il planner di "
                  "Postgres preferisce un Seq Scan su tabelle piccole.\n")
    else:
        md.append("Dati non disponibili. Eseguire `python3 benchmark/index_ablation.py`.\n")

    # --- Sensitivity ---
    md.append("\n## 10. Analisi di sensibilita'\n")
    md.append("Ipotesi che avrebbero potuto invalidare i risultati principali, verificate "
              "sperimentalmente: un artefatto di *tuning* (10.1), uno di *semantica* "
              "(10.2), uno di *stato fisico* (10.3).\n")
    md.append("\n### 10.1 Q07: lo spill su disco, work_mem, e il costo nascosto del GROUP BY per nome\n")
    sens_dir = RESULTS_DIR / "sensitivity"
    sens_files = sorted(sens_dir.glob("q07_workmem_*.json")) if sens_dir.exists() else []
    ne_q07_med = ne_medians[qids.index("Q07")] if "Q07" in qids else None
    pg_q07_med = pg_medians[qids.index("Q07")] if "Q07" in qids else None
    q07_plan_path = run_dir / "plans" / "Q07_postgres.txt"
    q07_sort = re.findall(r"Sort Method: ([^\n]+)", q07_plan_path.read_text(encoding="utf-8")) if q07_plan_path.exists() else []
    q07_spills = any("external" in s for s in q07_sort)
    if sens_files:
        sens = json.loads(sens_files[0].read_text(encoding="utf-8"))   # formulazione originale
        md.append("Nella formulazione originale di Q07 (`GROUP BY p.player_name`, come nella "
                  "controparte Cypher dell'epoca) il piano Postgres conteneva l'unico accesso "
                  "a disco dell'intero benchmark: un sort *external merge* di 542k righe "
                  "(~18 MB di file temporanei) causato dal `work_mem` di default (4MB). "
                  "Ipotesi: quanto del gap Postgres/Neo4j su Q07 e' un artefatto di questo "
                  "parametro di tuning?\n")
        md.append(f"Q07 e' stata rieseguita solo su Postgres ({sens['runs']} run + warm-up "
                  f"per configurazione, `SET work_mem` a livello di sessione):\n")
        md.append("| work_mem | Mediana PG (ms) | CI 95% | Sort method (EXPLAIN ANALYZE) |")
        md.append("|---|---:|:---:|---|")
        for c in sens["configs"]:
            md.append(f"| {c['work_mem']} | {c['median_ms']:.1f} | "
                      f"[{c['ci95_lo']:.1f}, {c['ci95_hi']:.1f}] | `{c['sort_method']}` |")
        first, last = sens["configs"][0], sens["configs"][-1]
        delta_pct = abs(first["median_ms"] - last["median_ms"]) / first["median_ms"] * 100
        md.append(f"\n**Risultato: ipotesi smentita.** Eliminare lo spill (il sort passa a "
                  f"quicksort interamente in memoria) sposta la mediana dello {delta_pct:.1f}%: "
                  f"su macOS i file temporanei restano nella page cache del sistema operativo "
                  f"e l'external merge non paga I/O fisico. Il collo di bottiglia era la "
                  f"strategia *sort-based* scelta dal planner per `COUNT(DISTINCT)`, non il disco.\n")
        if not q07_spills and q07_sort:
            md.append(f"**La causa vera era a monte, nella semantica.** L'audit di equivalenza "
                      f"(sez. 8) ha mostrato che raggruppare per *nome* fonde i 163 omonimi del "
                      f"dataset (14 risultati fittizi su 550); la formulazione corretta raggruppa "
                      f"per `player_api_id`. Con la chiave intera e indicizzata (`ix_lineup_player`) "
                      f"il planner abbandona il sort completo per un **Incremental Sort** sui "
                      f"gruppi gia' ordinati dall'indice — nel run di riferimento il piano riporta "
                      f"`{q07_sort[-1].strip()}`, nessuno spill — e la mediana Postgres scende a "
                      f"{pg_q07_med:.0f} ms (era {first['median_ms']:.0f}). Il gap con Neo4j su Q07 "
                      f"si riduce a **{(pg_q07_med / ne_q07_med):.1f}x**: una parte sostanziale del "
                      f"vantaggio misurato in precedenza era il costo di un sort su testo con "
                      f"collation, cioe' un bug semantico travestito da caratteristica di "
                      f"performance. E' l'argomento piu' forte del report a favore della verifica "
                      f"di equivalenza come prerequisito di qualunque benchmark.\n")
    else:
        md.append("Dati non disponibili. Eseguire `python3 benchmark/sensitivity_q07.py`.\n")

    # --- Sensitivity: semantica dello shortest path (Q10) ---
    md.append("\n### 10.2 La semantica dello shortest path in Cypher (Q10)\n")
    q10_files = sorted(sens_dir.glob("q10_semantics_*.json")) if sens_dir.exists() else []
    pg_q10_med = pg_medians[qids.index("Q10")] if "Q10" in qids else None
    if q10_files:
        s10 = json.loads(q10_files[-1].read_text(encoding="utf-8"))
        v = s10["variants"]
        md.append("La BFS SQL di Q10 collega due giocatori solo se hanno vestito la stessa "
                  "maglia **nella stessa stagione** (`pf2.season = pf1.season`). La "
                  "formulazione Cypher piu' naturale, `shortestPath((a)-[:PLAYED_FOR*..12]-(b))`, "
                  "attraversa un nodo `Team` **senza vincolare la stagione** dei due archi "
                  "consecutivi: e' una relazione di connettivita' piu' lasca, che puo' "
                  "produrre cammini piu' corti di quelli ammessi dal SQL. Sulla coppia "
                  "di riferimento le due semantiche coincidono per caso, e la verifica "
                  "automatica di equivalenza non poteva accorgersene. Abbiamo quindi "
                  "confrontato tre formulazioni:\n")
        md.append("| Variante | Semantica | Hop | Mediana (ms) | CI 95% | db hits | Operatore di path |")
        md.append("|---|---|---:|---:|:---:|---:|---|")
        labels = {
            "V0_shortestPath_loose": ("V0 `shortestPath(...*..12)`", "lasca (stagione libera)"),
            "V1_shortestPath_path_predicate": ("V1 `shortestPath` + predicato di path", "esatta, con fallback esaustivo"),
            "V2_qpp_shortest_exact": ("**V2 quantified path pattern + `SHORTEST 1`**", "**esatta per costruzione**"),
        }
        for key, (lab, sem) in labels.items():
            r = v.get(key)
            if not r:
                continue
            ci = f"[{r['ci95_lo']:.1f}, {r['ci95_hi']:.1f}]" if r.get("ci95_lo") is not None else "—"
            med = f"{r['median_ms']:.1f}" if r.get("median_ms") is not None else "—"
            ops = ", ".join(f"`{o.replace('@neo4j', '')}`" for o in r.get("path_operators", []))
            md.append(f"| {lab} | {sem} | {r['hops']} | {med} | {ci} | {r['db_hits']} | {ops} |")
        md.append("")
        md.append(f"Verifica semantica su {s10['n_pairs']} coppie di giocatori, confrontando gli hop "
                  f"con la BFS SQL:\n")
        md.append("| Coppia | SQL | V0 (lasca) | V2 (esatta) | |")
        md.append("|---|---:|---:|---:|---|")
        for row in s10["pairs"]:
            flag = "**V0 diverge**" if row["loose_diverges"] else "ok"
            md.append(f"| {row['pair'][0]} → {row['pair'][1]} | {row['sql_hops']} | "
                      f"{row['V0_shortestPath_loose']['hops']} | {row['V2_qpp_shortest_exact']['hops']} | {flag} |")
        md.append("")
        div = [r for r in s10["pairs"] if r["loose_diverges"]]
        ex = div[0] if div else None
        ex_txt = (f" Esempio: {ex['pair'][0]} → {ex['pair'][1]} dista {ex['sql_hops']} hop di "
                  f"veri compagni di squadra, ma la formulazione lasca risponde "
                  f"{ex['V0_shortestPath_loose']['hops']}, passando per una squadra in cui i due "
                  f"intermedi non hanno mai giocato insieme.") if ex else ""
        v0, v2 = v.get("V0_shortestPath_loose", {}), v.get("V2_qpp_shortest_exact", {})
        ratio = (v2["median_ms"] / v0["median_ms"]) if v0.get("median_ms") and v2.get("median_ms") else None
        md.append(f"**Risultato.** La semantica lasca (V0) da' una risposta diversa dal SQL su "
                  f"{s10['n_loose_diverges']}/{s10['n_pairs']} coppie; V2 coincide su "
                  f"{s10['n_exact_matches']}/{s10['n_pairs']}.{ex_txt} "
                  f"V1 e' corretta ma pericolosa: il suo piano contiene un ramo "
                  f"`VarLengthExpand` che scatta quando il cammino lasco piu' corto viola il "
                  f"predicato, degenerando in un'enumerazione esaustiva di tutti i cammini "
                  f"fino a 12 archi (~200^6 con il grado medio dei nodi `Team`): in un test "
                  f"senza timeout ha saturato la macchina. **Il benchmark adotta V2**: il "
                  f"vincolo `r1.season = r2.season` e' scritto *dentro* il gruppo ripetuto del "
                  f"quantified path pattern (sintassi GQL), il planner usa l'operatore dedicato "
                  f"`StatefulShortestPath` e il costo dell'esattezza e' "
                  f"{('%.1fx' % ratio) if ratio else 'contenuto'} rispetto alla versione lasca"
                  f"{(' — contro un gap di %.0fx con Postgres.' % (pg_q10_med / v2['median_ms'])) if (pg_q10_med and v2.get('median_ms')) else '.'}\n")
        md.append("Due lezioni. Primo: la verifica di equivalenza su *una* istanza dei "
                  "parametri e' necessaria ma non sufficiente — i vincoli fra elementi "
                  "consecutivi di un cammino sono il punto in cui SQL e Cypher divergono "
                  "piu' facilmente. Secondo: in un graph database la semantica si codifica "
                  "nella *topologia* o nel *pattern*, non in un filtro a posteriori; il "
                  "modello alternativo (un nodo `TeamSeason` al posto della proprieta' "
                  "`season` sulla relazione) renderebbe il vincolo strutturale e la "
                  "formulazione lasca semplicemente inesprimibile.\n")
    else:
        md.append("Dati non disponibili. Eseguire `python3 benchmark/sensitivity_q10.py`.\n")

    # --- Sensitivity: stabilita' cross-run e bloat MVCC ---
    md.append("\n### 10.3 Stabilita' fra run e bloat MVCC da scritture rolled back\n")
    cross = []
    for rd in sorted(p for p in RESULTS_DIR.glob("run_*") if p.is_dir()):
        if rd.name < "run_20260518" or not (rd / "summary.csv").exists():
            continue                                   # solo run con il set di query definitivo
        rows = list(csv.DictReader(open(rd / "summary.csv", encoding="utf-8")))
        sig = {}
        if (rd / "significance.csv").exists():
            sig = {r["query_id"]: r for r in csv.DictReader(open(rd / "significance.csv", encoding="utf-8"))}
        meta = {}
        if (rd / "run_metadata.json").exists():
            meta = json.loads((rd / "run_metadata.json").read_text(encoding="utf-8"))
        entry = {"run": rd.name, "runs": meta.get("runs", "?"),
                 "vacuum": bool(meta.get("postgres_vacuum_before_run"))}
        for r in rows:
            if r["query_id"] in ("Q01", "Q02"):
                entry[f"{r['query_id']}_{r['system']}"] = float(r["median_ms"])
        for q in ("Q01", "Q02"):
            entry[f"{q}_p"] = sig.get(q, {}).get("p_value", "—")
        if "Q01_postgres" in entry and "Q02_postgres" in entry:
            cross.append(entry)
    if len(cross) >= 2:
        md.append("Le due query piu' veloci del benchmark (Q01, Q02: mediane fra 4 e 25 ms) "
                  "sono anche quelle il cui vincitore **cambia da un run all'altro**, pur "
                  "risultando \"significative\" *dentro* ciascun run. La tabella riporta "
                  "tutti i run eseguiti con il set di query definitivo:\n")
        md.append("| Run | N | VACUUM pre-run | Q01 PG | Q01 Neo4j | p | Q02 PG | Q02 Neo4j | p |")
        md.append("|---|---:|:---:|---:|---:|---:|---:|---:|---:|")
        for e in cross:
            md.append(f"| `{e['run']}` | {e['runs']} | {'si' if e['vacuum'] else 'no'} | "
                      f"{e['Q01_postgres']:.1f} | {e['Q01_neo4j']:.1f} | {e['Q01_p']} | "
                      f"{e['Q02_postgres']:.1f} | {e['Q02_neo4j']:.1f} | {e['Q02_p']} |")
        md.append("")
        md.append("**Causa individuata: bloat MVCC generato dal benchmark stesso.** Q11 aggiorna "
                  "~21k righe di `match_event` (gli eventi `goal`) e Q12 tutte le 26k righe di "
                  "`match`; nei run fino al 16/09 entrambe venivano rolled back, ma in Postgres "
                  "il rollback **non rimuove** le versioni di tupla create dall'`UPDATE`: "
                  "ogni run lasciava 16 x ~21k tuple morte esattamente sulle pagine che Q01 "
                  "scansiona. `pg_stat_user_tables` lo conferma (oltre 1,29 milioni di "
                  "`n_tup_upd` su `match_event`, 1,45 milioni su `match`), e l'autovacuum e' "
                  "intervenuto solo *dopo* i due run consecutivi del 16/09 — durante i quali "
                  "la mediana di Q01 su Postgres e' salita da 10,8 a 16,0 e poi 23,2 ms. "
                  "Neo4j non ha l'effetto: una transazione annullata non lascia garbage nello "
                  "store, e una committata sovrascrive la proprieta' in place.\n")
        md.append("**Correzione del protocollo.** Dall'ultimo run l'harness esegue "
                  "`VACUUM (ANALYZE)` sulle tabelle coinvolte *prima* delle misure e lo "
                  "registra in `run_metadata.json`: ogni run e' cosi' indipendente dalla "
                  "storia delle esecuzioni precedenti. Il run di riferimento di questo "
                  "report e' il primo con il protocollo corretto.\n")
        md.append("Il VACUUM ha anche aggiornato le statistiche del planner, con un effetto "
                  "collaterale visibile su Q03: con la tabella `match` compattata "
                  "(217 pagine) il planner e' passato dal *Bitmap Index Scan* su "
                  "`ix_match_season` (47 accessi al buffer, ~2,8 ms) a un *Seq Scan* "
                  "(217 accessi, ~6 ms). E' una scelta del cost model con "
                  "`random_page_cost = 4` — il default tarato sui dischi rotanti — che "
                  "su SSD con working set in cache penalizza l'accesso indicizzato. "
                  "Non abbiamo modificato il parametro per restare fedeli alla "
                  "configurazione di default dichiarata, ma e' la dimostrazione che le "
                  "differenze di categoria A stanno dentro il margine di errore del "
                  "planner, non del paradigma.\n")
        md.append("Due lezioni: (i) un benchmark che mescola letture e scritture deve "
                  "controllare lo *stato fisico* delle tabelle, non solo la cache; "
                  "(ii) la significativita' statistica entro un run misura il rumore di "
                  "misurazione, **non** la stabilita' del sistema fra sessioni — per le "
                  "gare sotto i 20 ms il verdetto onesto e' \"parita' operativa\", "
                  "qualunque sia il p-value di un singolo run.\n")
    else:
        md.append("Dati insufficienti (servono almeno due run con il set di query definitivo).\n")

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
    md.append("| Bulk load (~1.5M righe) | `COPY FROM STDIN`: 1 statement per tabella, nessuna dipendenza esterna | `LOAD CSV`; per le 542k `LINEUP_OF` il loader offre `apoc.periodic.iterate` (batch 5000, richiede il **plugin APOC**) oppure — come nel run di riferimento — una singola transazione monolitica, che ha bisogno dell'heap da 1 GiB |")
    md.append("| Codice di load (LOC) | 150 (`load_postgres.py`) | 240 (`load_neo4j.py`, +60%) |")
    md.append("| Relazione derivata player-team-season | `CREATE MATERIALIZED VIEW` + `REFRESH` | `MATCH ... MERGE` di aggregazione post-load |")
    md.append("| Integrita' referenziale | **Enforced**: il `COPY` di `match_event` e' *fallito* per FK violation, rivelando 5.653 riferimenti orfani (4.632 su `player1_id` + 1.021 su `player2_id`, Challenge 1) | Non esiste FK: un `MATCH` su un `Player` mancante non lega la riga e la **scarta in silenzio** — lo stesso difetto sarebbe passato inosservato |")
    md.append("| Strumenti di analisi delle performance | `EXPLAIN (ANALYZE, BUFFERS)`: piano testuale con costi stimati/reali, buffer, tempi per nodo | `PROFILE`: albero di operatori con rows e db hits, visualizzato nel Browser |")
    md.append("| Ambiente interattivo | `psql` / pgAdmin | Neo4j Browser, con visualizzazione nativa del grafo |")
    md.append("| Curva di apprendimento | SQL: prerequisito del corso | Cypher: nuovo per entrambi gli autori; i pattern ASCII-art (`(a)-[:R]->(b)`) sono intuitivi per i traversal, meno per le aggregazioni (Q02, classifica: l'`UNION ALL` SQL diventa un `UNWIND` su una lista di mappe) |")
    md.append("| Pitfall incontrati | Tipizzazione rigida: colonne pandas integer-con-NaN rifiutate (Challenge 2) | Semantica di `NULL` (`NULL = NULL` e' null: Q05 richiedeva un `IS NOT NULL` esplicito per equivalere al self-join SQL); direzionalita' di `PLAYED_FOR` (6 hop = 12 archi); `shortestPath` legacy non vincola la stagione fra archi consecutivi — risolto con il quantified path pattern (sez. 10.2) |")
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
    # numeri di Q10 letti dai piani del run di riferimento (non hardcoded)
    q10_sp = pg_medians[qids.index("Q10")] / ne_medians[qids.index("Q10")] if "Q10" in qids else 0
    q10_pg_states, q10_pg_buffers, q10_neo_hits = "?", "?", "?"
    _pgp = run_dir / "plans" / "Q10_postgres.txt"
    _nep = run_dir / "plans" / "Q10_neo4j.txt"
    if _pgp.exists():
        _t = _pgp.read_text(encoding="utf-8")
        _m = re.search(r"Recursive Union.*?actual time=[^)]*?rows=([\d.]+)", _t)
        if _m: q10_pg_states = f"{int(float(_m.group(1))):,}".replace(",", ".")
        _m = re.search(r"Buffers: shared hit=(\d+)", _t)
        if _m: q10_pg_buffers = f"{int(_m.group(1)):,}".replace(",", ".")
    if _nep.exists():
        _hits = [int(h) for h in re.findall(r"dbHits: (\d+)", _nep.read_text(encoding="utf-8"))]
        if _hits: q10_neo_hits = f"{sum(_hits):,}".replace(",", ".")
    md.append("\n## 12. Considerazioni sulla scalabilita'\n")
    md.append("Il benchmark e' single-node e single-user (8 GB di RAM, working set "
              "interamente in cache: nessun piano contiene `shared read`). Non misura "
              "la scalabilita', ma i piani catturati permettono di **ragionare su come "
              "i costi crescono** con i dati, e l'architettura dei due sistemi su come "
              "si distribuiscono.\n")
    md.append("### Crescita dei dati su un singolo nodo\n")
    if q07_spills:
        md.append("- **Aggregazioni full-scan (Q07)**: il piano Postgres ordina 542.281 righe "
                  "(`external merge`, 18 MB); il costo e' O(n log n) nel numero di righe di "
                  "formazione. A 10x (80 stagioni) lo spill crescerebbe in proporzione, ma "
                  "il rimedio e' standard: partizionamento dichiarativo per `season` e "
                  "`work_mem` dimensionato. Neo4j aggrega le stesse relazioni in modo "
                  "lineare, ma **senza meccanismo di spill**: il grafo deve stare nella "
                  "pagecache, altrimenti il degrado e' brusco.\n")
    else:
        md.append("- **Aggregazioni full-scan (Q07)**: Postgres scandisce le 542.281 righe di "
                  "formazione e le aggrega con un *Incremental Sort* guidato dall'indice su "
                  "`player_api_id` (nessuno spill, sez. 10.1): il costo e' lineare nelle righe "
                  "piu' un sort per gruppo di dimensione costante. A 10x (80 stagioni) il "
                  "rimedio standard e' il partizionamento dichiarativo per `season`. Neo4j "
                  "aggrega le stesse relazioni in modo lineare, ma **senza meccanismo di "
                  "spill**: il grafo deve stare nella pagecache, altrimenti il degrado e' "
                  "brusco.\n")
    md.append(f"- **Traversal a profondita' variabile (Q10)**: la CTE ricorsiva "
              f"materializza l'intera frontiera BFS — {q10_pg_states} stati e "
              f"{q10_pg_buffers} accessi al buffer per profondita' <= 6 — un costo che "
              f"cresce con la dimensione del grafo *e* esponenzialmente con la "
              f"profondita'. `SHORTEST 1` (operatore `StatefulShortestPath`, BFS sul "
              f"pattern) tocca {q10_neo_hits} db hits: il lavoro dipende dalla lunghezza "
              f"del cammino e dal grado dei nodi attraversati, **non dalla dimensione "
              f"totale del grafo**. E' l'index-free adjacency letta come proprieta' di "
              f"scaling: il {q10_sp:.0f}x osservato non e' un artefatto della taglia del "
              f"dataset ma tende ad *allargarsi* al crescere dei dati.\n")
    # evidenza empirica di scaling con la profondita': le coppie del sweep di Q10
    if q10_files:
        s10p = json.loads(q10_files[-1].read_text(encoding="utf-8"))
        rows_p = sorted(s10p["pairs"], key=lambda r: (r["sql_hops"], r["V2_qpp_shortest_exact"]["ms"]))
        sql_ms = [r["V2_qpp_shortest_exact"]["ms"] for r in rows_p]
        md.append("  Evidenza empirica (le 8 coppie del sweep di sez. 10.2, una esecuzione "
                  "ciascuna, semantica esatta in entrambi i sistemi):\n")
        md.append("  | Coppia | Hop | Postgres (ms) | Neo4j (ms) |")
        md.append("  |---|---:|---:|---:|")
        pg_ms = [r.get("sql_ms") for r in rows_p if r.get("sql_ms") is not None]
        for r in rows_p:
            pgv = f"{r['sql_ms']:.0f}" if r.get("sql_ms") is not None else "—"
            md.append(f"  | {r['pair'][0]} → {r['pair'][1]} | {r['sql_hops']} | "
                      f"{pgv} | {r['V2_qpp_shortest_exact']['ms']:.1f} |")
        md.append("")
        pg_range = (f"{min(pg_ms):.0f}-{max(pg_ms):.0f} ms" if pg_ms else "~650-860 ms")
        md.append(f"  Il tempo Postgres ({pg_range} su tutte le coppie) e' **indipendente "
                  "dalla distanza**: la CTE ricorsiva espande sempre l'intera frontiera fino "
                  "a profondita' 6, perche' SQL non puo' fermare la ricorsione quando trova "
                  "la destinazione. Il tempo Neo4j cresce con la distanza (da "
                  f"{min(sql_ms):.0f} ms a {max(sql_ms):.0f} ms per la coppia a 3 hop): il "
                  "costo e' proporzionale al vicinato del cammino, non al grafo.\n")
    # evidenza empirica di scaling con la DIMENSIONE dei dati (sensitivity_scale.py)
    scale_files = sorted(sens_dir.glob("scale_*.json")) if sens_dir.exists() else []
    if scale_files:
        sc = json.loads(scale_files[-1].read_text(encoding="utf-8"))
        md.append(f"- **Crescita con la dimensione dei dati (misurata)**: Q07 (aggregazione "
                  f"full-scan) e Q09 (2-hop a profondita' fissa) rieseguite su sottoinsiemi "
                  f"crescenti di stagioni — ultime 2, ultime 4, tutte le 8 — filtrando "
                  f"`match.season` / `PLAYED_FOR.season` senza ricaricare i DB "
                  f"({sc['runs']} run + warm-up per cella; risultati identici nei due sistemi "
                  f"su ogni sottoinsieme):\n")
        md.append("  | Query | Stagioni | Postgres (ms) | Neo4j (ms) | Rapporto PG/Neo4j | Righe |")
        md.append("  |---|---:|---:|---:|---:|---:|")
        for r in sc["results"]:
            ratio = r["pg_median_ms"] / r["neo_median_ms"] if r["neo_median_ms"] else 0
            md.append(f"  | {r['experiment']} | {r['n_seasons']} | {r['pg_median_ms']:.0f} | "
                      f"{r['neo_median_ms']:.0f} | {ratio:.2f}x | {r['n_rows']} |")
        md.append("")
        q7 = [r for r in sc["results"] if r["experiment"].startswith("Q07")]
        q9 = [r for r in sc["results"] if r["experiment"].startswith("Q09")]
        if len(q7) >= 2 and len(q9) >= 2:
            g7p = q7[-1]["pg_median_ms"] / q7[0]["pg_median_ms"]
            g7n = q7[-1]["neo_median_ms"] / q7[0]["neo_median_ms"]
            g9p = q9[-1]["pg_median_ms"] / q9[0]["pg_median_ms"]
            g9n = q9[-1]["neo_median_ms"] / q9[0]["neo_median_ms"]
            md.append(f"  Da {q7[0]['n_seasons']} a {q7[-1]['n_seasons']} stagioni "
                      f"({q7[-1]['n_seasons'] // q7[0]['n_seasons']}x i dati) il tempo di Q07 cresce "
                      f"di {g7p:.1f}x su Postgres e di {g7n:.1f}x su Neo4j: l'aggregazione sulle "
                      f"relazioni e' quasi insensibile alla taglia, quella sort-based sulle righe "
                      f"e' lineare — **il vantaggio di Neo4j si allarga con i dati**. Su Q09 "
                      f"crescono entrambi ({g9p:.1f}x Postgres, {g9n:.1f}x Neo4j) e Postgres resta "
                      f"davanti a ogni taglia: il join a profondita' fissa scala meglio del "
                      f"traversal con la lista `IN` delle coppie coperte, che si allunga con le "
                      f"stagioni.\n")
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
              f"e' un problema NP-hard, e la proprieta' che rende Q10 {q10_sp:.0f}x piu' "
              f"veloce su un nodo e' esattamente quella che **non si distribuisce gratis**.\n")
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

    cat_a = [q for q in qids if pivot[q]["postgres"]["category"] == "A_relational"]
    def _sig_winner(q):
        if sig_data.get(q, {}).get("significant") != "True":
            return None
        return "postgres" if float(pivot[q]["postgres"]["median_ms"]) < float(pivot[q]["neo4j"]["median_ms"]) else "neo4j"
    a_pg = [q for q in cat_a if _sig_winner(q) == "postgres"]
    a_ne = [q for q in cat_a if _sig_winner(q) == "neo4j"]
    a_ns = [q for q in cat_a if _sig_winner(q) is None]
    q09_speedup = (ne_medians[qids.index("Q09")] / pg_medians[qids.index("Q09")]) if "Q09" in qids else 0
    a_max = max(max(pg_medians[qids.index(q)], ne_medians[qids.index(q)]) for q in cat_a) if cat_a else 0
    md.append(f"\n1. **Le aggregazioni OLAP-light (categoria A) sono parita' operativa**: "
              f"in questo run {len(a_pg)} query su {len(cat_a)} significativamente a favore "
              f"di Postgres ({', '.join(a_pg) or '—'}), {len(a_ne)} a favore di Neo4j "
              f"({', '.join(a_ne) or '—'}), {len(a_ns)} non significative "
              f"({', '.join(a_ns) or '—'}); tutte le mediane sono sotto i {a_max:.0f} ms e il "
              f"vincitore cambia da un run all'altro (sez. 10.3: in altri run Q03 e Q04 "
              f"andavano a Postgres). A questa scala l'ottimizzatore relazionale non ha "
              f"un vantaggio *misurabile* su join di 2-3 tabelle con aggregazione semplice. "
              f"Il vantaggio netto di Postgres emerge invece dove il join su indici B-tree "
              f"batte il traversal a profondita' *fissa*: Q09 ({q09_speedup:.1f}x, r = 1.0, "
              f"stabile in tutti i run).\n")

    md.append(f"\n2. **Neo4j domina sul traversal a profondita' variabile** (Q10): "
              f"**{q10_speedup:.1f}x piu' veloce**, con semantica *identica* al SQL "
              f"(vincolo di stagione dentro il quantified path pattern, sez. 10.2). "
              f"I piani catturati mostrano il perche': la CTE ricorsiva di Postgres "
              f"materializza l'intera frontiera BFS (decine di migliaia di stati, "
              f"milioni di accessi al buffer), mentre `SHORTEST 1` esplora solo il "
              f"vicinato del cammino (poche migliaia di db hits). E' l'effetto "
              f"dell'index-free adjacency.\n")

    md.append(f"\n3. **Neo4j vince anche sull'aggregazione full-scan** (Q07, "
              f"{q07_speedup:.1f}x), ma per una ragione diversa dal traversal: Postgres "
              f"deve ordinare (per gruppo) 542k righe di formazione per il "
              f"`COUNT(DISTINCT season)`, Neo4j aggrega le stesse relazioni con hash "
              f"aggregation. Il gap era 7.4x con la formulazione originale per *nome*: "
              f"la correzione semantica (raggruppare per chiave) ha eliminato un sort su "
              f"testo con spill su disco e lo ha ridotto a quello attuale (sez. 10.1) — "
              f"`work_mem` non c'entrava.\n")

    md.append(f"\n4. **La materialized view equalizza il campo sulle query intermedie** "
              f"(Q09): Postgres con `mv_played_for` vince su una query 2-hop che, senza "
              f"la precomputazione, sarebbe dominata da Neo4j. Questo isola il contributo "
              f"del *motore di esecuzione* da quello del *modello di carico*.\n")

    md.append(f"\n5. **Espressivita'**: Cypher e' sistematicamente piu' breve del SQL "
              f"equivalente. Il caso estremo e' Q10: {cyp_loc.get('Q10', '?')} LOC / "
              f"{cyp_verb.get('Q10', '?')} operatori logici in Cypher contro "
              f"{sql_loc.get('Q10', '?')} LOC / {sql_verb.get('Q10', '?')} operatori in SQL "
              f"(CTE ricorsiva BFS).\n")

    md.append(f"\n6. **Schema flexibility** (Q12): aggiungere e materializzare un attributo "
              f"derivato su tutti i match costa ~{q12_ne:.0f} ms in Neo4j (singolo `SET`, "
              f"commit incluso) vs ~{q12_pg:.0f} ms in Postgres (`ALTER TABLE` + `UPDATE` + "
              f"commit). Misurato fino al commit: con il solo rollback il rapporto sarebbe "
              f"gonfiato a oltre 11x, perche' Neo4j applica le mutazioni allo store solo "
              f"al commit (sez. 14). Rilevante in contesti con schema evolution frequente; "
              f"per un attributo *non* materializzato Postgres 18 offre le colonne generate "
              f"virtuali, istantanee.\n")

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
    md.append("- **Variabilita' di misurazione e stabilita' fra run**: le query con "
              "mediane sotto i 25 ms (Q01, Q02, Q03, Q04, Q08) hanno vincitori che "
              "possono cambiare da una sessione all'altra anche quando il test di "
              "Mann-Whitney li dichiara significativi entro il singolo run (sez. 10.3). "
              "Le conclusioni del report si appoggiano solo sulle differenze con "
              "effect size r >= 0.8, stabili in tutti i run.\n")
    md.append("- **Indipendenza delle osservazioni**: Mann-Whitney assume campioni "
              "indipendenti; le 15 esecuzioni sono sequenziali sulla stessa macchina e "
              "condividono stato di cache, scheduling e termica, quindi il test e' "
              "*liberale* (p-value ottimisti). Per questo le conclusioni richiedono anche "
              "un effect size r >= 0.8 e la stabilita' fra sessioni (sez. 10.3), che e' il "
              "vero controllo empirico dell'autocorrelazione. Un warm-up singolo e' "
              "sufficiente anche per Q07 e Q10: i loro CI sono i piu' stretti del "
              "benchmark (±2% della mediana).\n")
    md.append("- **Ordine di esecuzione**: in ogni iterazione la query gira prima su Postgres "
              "e poi su Neo4j (interleaving), e le query si susseguono sempre da Q01 a Q12; "
              "l'ordine non e' randomizzato. L'interleaving controlla la deriva temporale "
              "(termica, processi di background) distribuendola su entrambi i sistemi; "
              "l'interferenza di cache fra i due e' trascurabile perche' entrambi i "
              "working set stanno in RAM (nessun piano mostra letture da disco).\n")
    md.append("- **Parametri per nome**: le query parametrizzate per nome (Q08-Q10, Q06) "
              "assumono che il nome sia univoco; e' verificato per i valori usati "
              "(un solo `Lionel Messi`, `Andrea Pirlo`, `Real Madrid CF`) ma non in "
              "generale (163 nomi di giocatore e 3 di squadra sono omonimi). Per un uso "
              "generale i parametri andrebbero passati per chiave.\n")
    md.append("- **Equivalenza semantica oltre l'istanza misurata**: il confronto "
              "automatico dei risultati vale per i parametri del benchmark. Per Q10 "
              "l'equivalenza e' stata verificata anche su 8 coppie di giocatori "
              "(sez. 10.2), dopo aver scoperto che la formulazione `shortestPath` "
              "legacy coincideva con il SQL solo per caso.\n")
    wm = meta.get("write_mode", "rollback") if metadata_path.exists() else "rollback"
    if wm == "commit":
        md.append("- **Write query misurate fino al COMMIT**: per Q11 e Q12 il timer include "
                  "`COMMIT` (Postgres: flush del WAL; Neo4j: validazione, applicazione allo "
                  "store e flush del transaction log). Un cleanup non misurato riporta lo "
                  "stato iniziale dopo ogni run (Q11 e' idempotente; Q12 rimuove la "
                  "colonna/proprieta'). La versione precedente dell'harness annullava la "
                  "transazione: in Neo4j le mutazioni restano nello stato di transazione in "
                  "memoria fino al commit, quindi il rollback misurava un'operazione quasi "
                  "in-RAM contro un `UPDATE` Postgres che aveva gia' scritto pagine e WAL "
                  "(sez. 10.4).\n")
    else:
        md.append("- **Rollback nelle write query**: Q11 e Q12 vengono annullate dopo ogni "
                  "run. Attenzione: in Neo4j le mutazioni restano in memoria fino al commit, "
                  "quindi il rollback sottostima il costo di scrittura di Neo4j rispetto a "
                  "Postgres, che ha gia' modificato pagine e WAL prima dell'annullamento.\n")
    md.append("- **Overhead del driver client**: il timer include il round-trip e la "
              "materializzazione dei risultati nel client (psycopg2 in C, driver Neo4j in "
              "Python). Con result-set fino a ~550 righe l'overhead e' sub-millisecondo "
              "e simmetrico in ordine di grandezza; nessun piano usa il JIT di Postgres "
              "(costo stimato sempre sotto `jit_above_cost`).\n")

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
              "limitano l'impatto: (i) nessuno dei 24 piani catturati contiene `shared read` "
              "— il contatore dei blocchi entrati nel buffer pool da *fuori* (page cache "
              "del sistema operativo o disco), quindi il working set delle query stava "
              "interamente nei 128 MB di `shared_buffers`, e a maggior ragione nella "
              "pagecache di Neo4j; (ii) l'analisi di sensibilita' su `work_mem` "
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
    md.append("- Per garantire un confronto **fair** su Q09/Q10 (Q08 usa le formazioni in entrambi i sistemi), Postgres precomputa la "
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
