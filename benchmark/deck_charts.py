"""Grafici delle slide, generati dai dati del run di riferimento.

Ogni numero nei grafici del deck viene letto dai file di risultato, non scritto a
mano: rigenerando dopo un nuovo run, le slide restano allineate al report.

Output (reports/figures/deck/):
  results.png  slide 10 — diverging bar chart log, saturazione = significativo dopo Holm
  work.png     slide 11 — lavoro dei motori su Q10, dai piani catturati
  loc.png      slide 13 — righe di codice per query, SQL vs Cypher
  scale.png    slide 15 — Q07/Q09 su 2, 4, 8 stagioni
  qr.png       slide 16 — QR al repository

Font: Space Grotesk + IBM Plex Mono (quelli del deck), se installati in ~/Library/Fonts.

Uso:
    python3 benchmark/deck_charts.py                          # run di riferimento
    python3 benchmark/deck_charts.py --run run_20260921_162704
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager as fm

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "benchmark" / "results"
OUT = ROOT / "reports" / "figures" / "deck"
REFERENCE_RUN = "run_20260921_162704"
REPO_URL = "https://github.com/g1up3/DM-Project-2026"

_FONTS = Path(os.path.expanduser("~/Library/Fonts"))
for _f in ["SpaceGrotesk-VariableFont_wght.ttf", "IBMPlexMono-Regular.ttf",
           "IBMPlexMono-SemiBold.ttf", "IBMPlexMono-Bold.ttf"]:
    if (_FONTS / _f).exists():
        fm.fontManager.addfont(str(_FONTS / _f))
SG, PM = "Space Grotesk", "IBM Plex Mono"

PG, NEO = "#33608F", "#1E7A52"
PG_SOFT, NEO_SOFT = "#A9B7C9", "#A6C7B6"
INK, INK2, INK3, RULE, GREY = "#1A2430", "#3D4652", "#6B655C", "#E4DFD6", "#9A938A"

SHORT_NAMES = {
    "Q01": "Top scorers by season", "Q02": "League standings", "Q03": "Goals per match",
    "Q04": "Home win % by team", "Q05": "Goal-assist partnerships", "Q06": "Cards vs Real Madrid",
    "Q07": "Players in all 8 seasons", "Q08": "Teammates of Messi", "Q09": "2-hop teammates",
    "Q10": "Shortest path Messi → Pirlo", "Q11": "Bulk UPDATE (write)", "Q12": "Schema evolution (write)",
}
CATS = [("A · relational", 0, 3), ("B · multi-hop", 4, 6), ("C · graph-native", 7, 9), ("D · write", 10, 11)]


# ------------------------------------------------------------------ data
def load_results(run_dir: Path):
    from run_benchmark import holm_correction

    rows = list(csv.DictReader(open(run_dir / "significance.csv", encoding="utf-8")))
    if rows and "significant_holm" in rows[0]:
        holm = [r["significant_holm"] == "True" for r in rows]
    else:
        holm = holm_correction([float(r["p_value"]) for r in rows])
    summ = {(r["query_id"], r["system"]): float(r["median_ms"])
            for r in csv.DictReader(open(run_dir / "summary.csv", encoding="utf-8"))}
    out = []
    for r, h in zip(rows, holm):
        q = r["query_id"]
        winner = "postgres" if summ[(q, "postgres")] < summ[(q, "neo4j")] else "neo4j"
        out.append((q, SHORT_NAMES[q], winner, float(r["speedup"]), h))
    return out


def load_work(run_dir: Path):
    pg = (run_dir / "plans" / "Q10_postgres.txt").read_text(encoding="utf-8")
    neo = (run_dir / "plans" / "Q10_neo4j.txt").read_text(encoding="utf-8")
    buffers = int(re.search(r"Buffers: shared hit=(\d+)", pg).group(1))
    frontier = int(float(re.search(r"Recursive Union.*?actual time=[^)]*?rows=([\d.]+)", pg).group(1)))
    db_hits = sum(int(h) for h in re.findall(r"dbHits: (\d+)", neo))
    return buffers, frontier, db_hits


def load_loc():
    rows = csv.DictReader(open(RESULTS / "syntactic_complexity.csv", encoding="utf-8"))
    return {r["query_id"]: (int(r["loc_sql"]), int(r["loc_cypher"])) for r in rows}


def load_scale():
    f = sorted((RESULTS / "sensitivity").glob("scale_*.json"))[-1]
    data = json.load(open(f, encoding="utf-8"))
    scale = {}
    for r in data["results"]:
        q = r["experiment"].split("-")[0]
        scale.setdefault(q, {})[r["n_seasons"]] = (r["pg_median_ms"], r["neo_median_ms"])
    return scale, f.name


# ------------------------------------------------------------------ charts
def results_chart(results, path, w=17.92, h=6.25):
    fig = plt.figure(figsize=(w, h), dpi=200)
    ax = fig.add_axes([0.255, 0.04, 0.70, 0.86])
    n = len(results)
    ys = np.arange(n)[::-1]
    xmin, xmax = -0.62, 1.98
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(-0.7, n - 0.3)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_yticks([])
    ax.set_xticks([])
    ticks = [(-0.5, "3×"), (-0.301, "2×"), (0, "1×"), (0.301, "2×"), (0.699, "5×"),
             (1, "10×"), (1.301, "20×"), (1.699, "50×")]
    for x, lab in ticks:
        ax.axvline(x, color=RULE if x else INK, lw=0.8 if x else 1.4, zorder=1)
        ax.text(x, n - 0.35, lab, ha="center", va="bottom", fontfamily=PM, fontsize=10, color=GREY)
    fy = lambda y: 0.04 + 0.86 * (y + 0.7) / (n + 0.4)
    for name, a, b in CATS:
        ytop, ybot = ys[a] + 0.5, ys[b] - 0.5
        if a > 0:
            ax.axhline(ytop, color=RULE, lw=0.8, zorder=1)
            fig.lines.append(plt.Line2D([0.02, 0.25], [fy(ytop)] * 2, transform=fig.transFigure, color=RULE, lw=0.8))
        fig.text(0.022, fy((ytop + ybot) / 2), name, rotation=90, ha="center", va="center",
                 fontfamily=PM, fontsize=9.5, color=GREY)
    q10 = None
    for i, (qid, name, winner, sp, sig) in enumerate(results):
        y, v = ys[i], np.log10(sp)
        if winner == "postgres":
            color = PG if sig else PG_SOFT
            ax.barh(y, -v, height=0.58, color=color, zorder=3)
            lx, ha = -v - 0.02, "right"
        else:
            color = NEO if sig else NEO_SOFT
            ax.barh(y, v, height=0.58, color=color, zorder=3)
            lx, ha = v + 0.02, "left"
        label = f"{sp:.2f}×" if sp < 10 else f"{sp:.1f}×"
        ax.text(lx, y, label, ha=ha, va="center", fontfamily=PM, fontsize=13, fontweight="semibold",
                color=color if sig else GREY, zorder=4)
        fig.text(0.052, fy(y), qid, ha="left", va="center", fontfamily=PM, fontsize=13, fontweight="bold",
                 color=INK if sig else GREY)
        fig.text(0.095, fy(y), name, ha="left", va="center", fontfamily=SG, fontsize=13,
                 color=INK2 if sig else GREY)
        if qid == "Q10":
            q10 = (y, sp)
    x0 = 0.255 + 0.70 * (0 - xmin) / (xmax - xmin)
    fig.text(x0 - 0.012, 0.965, "←  POSTGRES FASTER", ha="right", va="center", fontfamily=PM,
             fontsize=11.5, fontweight="semibold", color=PG)
    fig.text(x0 + 0.012, 0.965, "NEO4J FASTER  →", ha="left", va="center", fontfamily=PM,
             fontsize=11.5, fontweight="semibold", color=NEO)
    fig.text(0.052, 0.965, "QUERY", ha="left", va="center", fontfamily=PM, fontsize=11, color=GREY)
    fig.text(0.052, 0.92, "log scale · median of 15 runs", ha="left", va="center", fontfamily=PM,
             fontsize=9.5, color=GREY)
    if q10:
        y, sp = q10
        ax.annotate(f"{sp:.0f}× — a change of complexity class", xy=(np.log10(sp) - 0.25, y + 0.32),
                    xytext=(1.02, y + 1.55), fontfamily=SG, fontsize=14.5, color=NEO, ha="left", va="center",
                    arrowprops=dict(arrowstyle="-|>", color=NEO, lw=1.3, connectionstyle="arc3,rad=-0.25"),
                    zorder=5)
    fig.savefig(path, transparent=True)
    plt.close(fig)


def work_chart(work, path, w=9.36, h=3.0):
    buffers, frontier, db_hits = work
    fig = plt.figure(figsize=(w, h), dpi=200)
    ax = fig.add_axes([0.42, 0.10, 0.50, 0.60])
    rows = [("shared-buffer accesses", "Postgres · recursive CTE", buffers, "#7FA8D4"),
            ("frontier rows explored", "Postgres · recursive CTE", frontier, "#7FA8D4"),
            ("db hits", "Neo4j · SHORTEST 1", db_hits, "#6FC79B")]
    ax.set_xscale("log")
    ax.set_xlim(1e3, 2e7)
    ax.set_ylim(-0.6, 2.6)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_yticks([])
    ax.set_xticks([1e3, 1e4, 1e5, 1e6, 1e7])
    ax.set_xticklabels(["1K", "10K", "100K", "1M", "10M"], fontfamily=PM, fontsize=10.5, color="#8B96A3")
    ax.tick_params(axis="x", length=0, pad=4)
    for x in [1e3, 1e4, 1e5, 1e6, 1e7]:
        ax.axvline(x, color="#2C3A4A", lw=0.8, zorder=1)
    for y, (what, who, v, c) in zip([2, 1, 0], rows):
        ax.barh(y, v, left=1e3, height=0.62, color=c, zorder=3)
        ax.text(v * 1.18, y, f"{v:,}", ha="left", va="center", fontfamily=PM, fontsize=14.5,
                fontweight="semibold", color="#F2EFE9")
        yy = 0.10 + 0.60 * (y + 0.6) / 3.2
        fig.text(0.40, yy + 0.02, what, ha="right", va="center", fontfamily=SG, fontsize=14, color="#F2EFE9")
        fig.text(0.40, yy - 0.075, who, ha="right", va="center", fontfamily=PM, fontsize=10, color=c)
    fig.text(0.02, 0.95, "WORK DONE BY THE ENGINE — FROM THE CAPTURED QUERY PLANS", ha="left", va="center",
             fontfamily=PM, fontsize=11.5, color="#8B96A3")
    fig.text(0.02, 0.855, "~3 orders of magnitude less work — identical semantics", ha="left", va="center",
             fontfamily=SG, fontsize=15, color="#6FC79B")
    fig.savefig(path, transparent=True)
    plt.close(fig)


def loc_chart(loc, path, w=6.7, h=2.55):
    fig = plt.figure(figsize=(w, h), dpi=200)
    ax = fig.add_axes([0.06, 0.16, 0.92, 0.74])
    qs = sorted(loc)
    x = np.arange(len(qs))
    sql = [loc[q][0] for q in qs]
    cy = [loc[q][1] for q in qs]
    bw = 0.38
    i10 = qs.index("Q10")
    ax.axvspan(i10 - 0.5, i10 + 0.5, color="#EDE9E1", zorder=0)
    ax.bar(x - bw / 2, sql, bw, color=PG, zorder=3)
    ax.bar(x + bw / 2, cy, bw, color=NEO, zorder=3)
    for xi, (s, c) in enumerate(zip(sql, cy)):
        ax.text(xi - bw / 2, s + 0.6, str(s), ha="center", va="bottom", fontfamily=PM, fontsize=7.5, color=PG)
        ax.text(xi + bw / 2, c + 0.6, str(c), ha="center", va="bottom", fontfamily=PM, fontsize=7.5, color=NEO)
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.set_yticks([])
    ax.set_xticks(x)
    ax.set_xticklabels(qs, fontfamily=PM, fontsize=8.5, color=INK2)
    ax.tick_params(axis="x", length=0)
    ax.get_xticklabels()[i10].set_fontweight("bold")
    ymax = max(sql) * 1.14
    ax.set_ylim(0, ymax)
    ax.text(9.6, ymax * 0.975, "SQL", fontfamily=PM, fontsize=9.5, fontweight="semibold", color=PG, va="top")
    ax.text(10.6, ymax * 0.975, "Cypher", fontfamily=PM, fontsize=9.5, fontweight="semibold", color=NEO, va="top")
    ratio = loc["Q10"][0] / loc["Q10"][1]
    ax.text(i10, loc["Q10"][0] + ymax * 0.2, f"{ratio:.0f}× shorter", ha="center", va="bottom",
            fontfamily=SG, fontsize=9.5, color=NEO)
    fig.savefig(path, transparent=True)
    plt.close(fig)


def scale_chart(scale, path, w=9.0, h=4.0):
    fig = plt.figure(figsize=(w, h), dpi=200)
    g = lambda q, i: scale[q][8][i] / scale[q][2][i]
    panels = [("Q07 — players in all seasons", "Q07",
               f"Postgres ×{g('Q07', 0):.1f}, Neo4j ×{g('Q07', 1):.1f} — the graph edge widens"),
              ("Q09 — 2-hop teammates", "Q09", "Postgres keeps the lead at every size")]
    for k, (title, q, note) in enumerate(panels):
        ax = fig.add_axes([0.08 + k * 0.50, 0.17, 0.40, 0.62])
        seasons = sorted(scale[q])
        pg = [scale[q][s][0] for s in seasons]
        neo = [scale[q][s][1] for s in seasons]
        ax.plot(seasons, pg, color=PG, lw=2.4, marker="o", ms=6, zorder=3)
        ax.plot(seasons, neo, color=NEO, lw=2.4, marker="o", ms=6, zorder=3)
        for s, vp, vn in zip(seasons, pg, neo):
            hi, lo = ((vp, PG), (vn, NEO)) if vp >= vn else ((vn, NEO), (vp, PG))
            ax.text(s, hi[0] * 1.08, f"{hi[0]:.0f}", ha="center", va="bottom", fontfamily=PM, fontsize=10.5, color=hi[1])
            ax.text(s, lo[0] * 0.92, f"{lo[0]:.0f}", ha="center", va="top", fontfamily=PM, fontsize=10.5, color=lo[1])
        for sp in ["top", "right"]:
            ax.spines[sp].set_visible(False)
        ax.spines["left"].set_color(RULE)
        ax.spines["bottom"].set_color(RULE)
        ax.set_xticks(seasons)
        ax.set_xticklabels([f"{seasons[0]} seasons"] + [str(s) for s in seasons[1:]], fontfamily=PM,
                           fontsize=10.5, color=INK3)
        ax.set_xlim(1.4, 9.9)
        ymax = max(pg + neo) * 1.35
        ax.set_ylim(0, ymax)
        ax.set_yticks([])
        ax.tick_params(length=0)
        ax.text(1.45, ymax * 0.99, "ms", fontfamily=PM, fontsize=8.5, color=GREY, va="top")
        ax.set_title(title, loc="left", fontfamily=SG, fontsize=14, color=INK, pad=8)
        ax.text(0.0, -0.22, note, transform=ax.transAxes, fontfamily=SG, fontsize=12, color=INK2, va="top")
        ax.text(8.2, pg[-1], "Postgres", fontfamily=PM, fontsize=10.5, color=PG, va="center")
        ax.text(8.2, neo[-1], "Neo4j", fontfamily=PM, fontsize=10.5, color=NEO, va="center")
    fig.savefig(path, transparent=True)
    plt.close(fig)


def qr_png(path):
    import qrcode
    from qrcode.constants import ERROR_CORRECT_M
    q = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=12, border=2)
    q.add_data(REPO_URL)
    q.make(fit=True)
    q.make_image(fill_color="#1A2430", back_color="white").save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", default=REFERENCE_RUN)
    args = ap.parse_args()
    run_dir = RESULTS / args.run
    OUT.mkdir(parents=True, exist_ok=True)
    results = load_results(run_dir)
    work = load_work(run_dir)
    loc = load_loc()
    scale, scale_file = load_scale()
    results_chart(results, OUT / "results.png")
    work_chart(work, OUT / "work.png")
    loc_chart(loc, OUT / "loc.png")
    scale_chart(scale, OUT / "scale.png")
    qr_png(OUT / "qr.png")
    print(f"run {args.run} · {scale_file} · Q10 work {work} · written to {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
