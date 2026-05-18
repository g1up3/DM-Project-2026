"""
Debug utility — dumpa tutte le tabelle del file SQLite (European Soccer
Database) in CSV "grezzi", una corrispondenza 1:1 con lo schema sorgente.

NON e' parte della pipeline ETL ufficiale (che e' in etl/transform.py,
load_postgres.py, load_neo4j.py). Va usato solo per:
- ispezionare manualmente il sorgente,
- avere uno snapshot CSV del DB SQLite originale,
- verificare l'integrita' di un dump.

La pipeline ufficiale parte da etl/transform.py, che fa l'esplosione di Match
(115 colonne) in 4 entita' separate e parsa gli XML degli eventi.

Uso:
    python3 sqlite_to_csv.py

Input:  ../database.sqlite
Output: ../csv/<NomeTabella>.csv (uno per tabella)

Note:
- Salta le tabelle interne di SQLite (es. sqlite_sequence).
- Usa la quotazione minima (QUOTE_MINIMAL) e separatore virgola.
- I valori NULL vengono scritti come stringa vuota (default di pandas).
"""

import os
import sqlite3
import csv
from pathlib import Path

import pandas as pd

# Percorsi (relativi alla cartella dello script)
HERE = Path(__file__).resolve().parent
DB_PATH = HERE.parent / "database.sqlite"
OUT_DIR = HERE.parent / "csv"

# Tabelle da non esportare
SKIP_TABLES = {"sqlite_sequence"}


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database non trovato: {DB_PATH}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    try:
        tables = pd.read_sql(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;",
            conn,
        )["name"].tolist()

        print(f"Trovate {len(tables)} tabelle nel database.")
        print(f"Output: {OUT_DIR}\n")

        for t in tables:
            if t in SKIP_TABLES:
                print(f"  [skip] {t}")
                continue

            df = pd.read_sql(f'SELECT * FROM "{t}"', conn)
            out_path = OUT_DIR / f"{t}.csv"
            df.to_csv(
                out_path,
                index=False,
                quoting=csv.QUOTE_MINIMAL,
                encoding="utf-8",
            )
            size_mb = out_path.stat().st_size / (1024 * 1024)
            print(f"  [ok]   {t}: {len(df):>7,} righe, {len(df.columns):>2} colonne -> {out_path.name} ({size_mb:.1f} MB)")
    finally:
        conn.close()

    print("\nFatto.")


if __name__ == "__main__":
    main()
