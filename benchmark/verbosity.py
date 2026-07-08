"""
Compute syntactic complexity of each query in two dimensions:

  - LOC               : non-blank, non-comment lines.
  - Cognitive Verbosity: count of logical operator occurrences.

Methodology:

  Each occurrence of a logical operator keyword (JOIN, WHERE, GROUP BY, etc.)
  is counted exactly once. Compound keywords are matched first and consumed
  so that e.g. LEFT JOIN counts as one operator, not as both LEFT JOIN and
  JOIN.  The SQL and Cypher keyword lists are designed to be *conceptually
  symmetric*: each maps to equivalent categories of logical operations
  (retrieval, filtering, aggregation, set logic, mutation, conditionals).

  The metric captures "how many distinct logical steps the reader must track"
  rather than raw character count. A query with 3 JOINs has higher cognitive
  load than one with 1 JOIN, so we count occurrences, not just presence.

Limitations (documented for transparency):

  - SQL and Cypher express the same concept differently (a Cypher MATCH with a
    multi-node pattern subsumes what SQL needs multiple JOINs for). This is an
    inherent asymmetry of the *languages*, not a measurement error — the metric
    intentionally captures it.
  - The metric does not capture *semantic* complexity (e.g. a self-join is
    harder to reason about than a FK join, but both count as one JOIN).
  - Aggregate functions (COUNT, SUM, AVG) are not counted as operators in
    either language to keep the lists symmetric.

Usage:
    python3 benchmark/verbosity.py
    python3 benchmark/verbosity.py --json
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

HERE         = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
SQL_DIR      = PROJECT_ROOT / "queries" / "sql"
CYPHER_DIR   = PROJECT_ROOT / "queries" / "cypher"
OUT_CSV      = HERE / "results" / "syntactic_complexity.csv"

# --- Keyword lists ---
# Compound patterns MUST come before their simple counterparts so that
# "LEFT JOIN" is consumed before "JOIN" can match it.

SQL_KEYWORDS_ORDERED = [
    # compounds first
    r"\bLEFT\s+JOIN\b",
    r"\bRIGHT\s+JOIN\b",
    r"\bINNER\s+JOIN\b",
    r"\bCROSS\s+JOIN\b",
    r"\bUNION\s+ALL\b",
    r"\bNOT\s+EXISTS\b",
    r"\bNOT\s+IN\b",
    r"\bGROUP\s+BY\b",
    r"\bORDER\s+BY\b",
    # simple keywords (only match if not already consumed by a compound)
    r"\bSELECT\b",
    r"\bFROM\b",
    r"\bWHERE\b",
    r"\bJOIN\b",
    r"\bHAVING\b",
    r"\bLIMIT\b",
    r"\bUNION\b",
    r"\bINTERSECT\b",
    r"\bEXCEPT\b",
    r"\bEXISTS\b",
    r"\bIN\b",
    r"\bCASE\b",
    r"\bWITH\b",
    r"\bRECURSIVE\b",
    r"\bAND\b",
    r"\bOR\b",
    r"\bNOT\b",
]

CYPHER_KEYWORDS_ORDERED = [
    # compounds first
    r"\bOPTIONAL\s+MATCH\b",
    r"\bORDER\s+BY\b",
    # simple keywords
    r"\bMATCH\b",
    r"\bWHERE\b",
    r"\bWITH\b",
    r"\bRETURN\b",
    r"\bLIMIT\b",
    r"\bUNWIND\b",
    r"\bCALL\b",
    r"\bCASE\b",
    r"\bSET\b",
    r"\bMERGE\b",
    r"\bCREATE\b",
    r"\bDELETE\b",
    r"\bIN\b",
    r"\bAND\b",
    r"\bOR\b",
    r"\bNOT\b",
]


def loc(path: Path) -> int:
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("--") or s.startswith("//"):
            continue
        n += 1
    return n


def strip_comments(text: str, kind: str) -> str:
    out = []
    for line in text.splitlines():
        if kind == "sql":
            i = line.find("--")
        else:
            i = line.find("//")
        if i >= 0:
            line = line[:i]
        out.append(line)
    return "\n".join(out)


def cognitive_verbosity(path: Path, kind: str) -> int:
    """
    Count operator keyword occurrences with consume-on-match to prevent
    double-counting of compound keywords (e.g. LEFT JOIN).
    """
    text = strip_comments(path.read_text(encoding="utf-8"), kind)
    keywords = SQL_KEYWORDS_ORDERED if kind == "sql" else CYPHER_KEYWORDS_ORDERED

    total = 0
    for kw in keywords:
        matches = list(re.finditer(kw, text, flags=re.IGNORECASE))
        total += len(matches)
        # consume matched spans so subsequent simpler patterns can't re-match
        for m in reversed(matches):
            text = text[:m.start()] + (" " * (m.end() - m.start())) + text[m.end():]

    return total


def collect() -> list[dict]:
    rows = []
    sql_files    = sorted(SQL_DIR.glob("Q*.sql"))
    cypher_files = sorted(CYPHER_DIR.glob("Q*.cypher"))
    by_id_sql    = {f.name.split("_", 1)[0]: f for f in sql_files}
    by_id_cypher = {f.name.split("_", 1)[0]: f for f in cypher_files}
    qids = sorted(set(by_id_sql) | set(by_id_cypher))
    for qid in qids:
        ps = by_id_sql.get(qid)
        pc = by_id_cypher.get(qid)
        rows.append({
            "query_id":         qid,
            "loc_sql":          loc(ps) if ps else 0,
            "loc_cypher":       loc(pc) if pc else 0,
            "verbosity_sql":    cognitive_verbosity(ps, "sql")    if ps else 0,
            "verbosity_cypher": cognitive_verbosity(pc, "cypher") if pc else 0,
        })
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    rows = collect()

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        print(f"{'ID':<4} {'LOC SQL':>8} {'LOC Cyp':>8} "
              f"{'Verb SQL':>9} {'Verb Cyp':>9} "
              f"{'LOC ratio':>10} {'Verb ratio':>10}")
        for r in rows:
            lr = r["loc_sql"] / r["loc_cypher"] if r["loc_cypher"] else 0
            vr = r["verbosity_sql"] / r["verbosity_cypher"] if r["verbosity_cypher"] else 0
            print(f"{r['query_id']:<4} {r['loc_sql']:>8} {r['loc_cypher']:>8} "
                  f"{r['verbosity_sql']:>9} {r['verbosity_cypher']:>9} "
                  f"{lr:>9.2f}x {vr:>9.2f}x")
        print(f"\nWritten: {OUT_CSV}")


if __name__ == "__main__":
    main()
