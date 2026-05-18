"""
Carica i CSV puliti (cartella clean/) nello schema PostgreSQL definito in
schema/postgres_schema.sql.

Pre-requisiti:
    1. PostgreSQL in esecuzione localmente (vedi etl/README.md).
    2. Variabili d'ambiente di connessione (oppure file .env nella stessa cartella):
            PGHOST     (default: localhost)
            PGPORT     (default: 5432)
            PGUSER     (default: postgres)
            PGPASSWORD (default: postgres)
            PGDATABASE (default: soccer_db)
    3. Pacchetti Python: psycopg2-binary, python-dotenv (opzionale).

Cosa fa lo script:
    1. Si connette al DB indicato e applica schema/postgres_schema.sql
       (DROP SCHEMA IF EXISTS soccer CASCADE + CREATE SCHEMA + DDL).
    2. Carica i CSV via COPY in ordine di dipendenze FK.
    3. Esegue una query di smoke test alla fine.

Uso:
    python3 load_postgres.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg2
from psycopg2 import sql

try:
    from dotenv import load_dotenv  # opzionale
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

HERE = Path(__file__).resolve().parent
CLEAN_DIR  = HERE.parent / "clean"
SCHEMA_SQL = HERE.parent / "schema" / "postgres_schema.sql"

# Ordine di caricamento: prima le tabelle senza FK, poi le altre.
LOAD_ORDER = [
    # (nome tabella nello schema soccer, file CSV, lista colonne)
    ("country",       "country.csv",       ["country_id", "name"]),
    ("league",        "league.csv",        ["league_id", "country_id", "name"]),
    ("team",          "team.csv",          ["team_api_id", "team_fifa_api_id",
                                             "team_long_name", "team_short_name"]),
    ("player",        "player.csv",        ["player_api_id", "player_fifa_api_id",
                                             "player_name", "birthday", "height", "weight"]),
    ("match",         "match.csv",         ["match_api_id", "league_id", "season",
                                             "stage", "match_date",
                                             "home_team_api_id", "away_team_api_id",
                                             "home_team_goal", "away_team_goal"]),
    ("match_lineup",  "match_lineup.csv",  ["match_api_id", "player_api_id", "side",
                                             "position_idx", "pos_x", "pos_y"]),
    ("match_event",   "match_event.csv",   ["match_api_id", "event_type", "subtype",
                                             "elapsed_minute", "team_api_id",
                                             "player1_id", "player2_id",
                                             "card_type", "goal_type", "sort_order",
                                             "source_event_id"]),
    ("player_stats",  "player_stats.csv",  None,  True),   # tutte le colonne nell'header
    ("team_stats",    "team_stats.csv",    None,  True),
]


def get_conn():
    return psycopg2.connect(
        host     = os.getenv("PGHOST",     "localhost"),
        port     = os.getenv("PGPORT",     "5432"),
        user     = os.getenv("PGUSER",     "postgres"),
        password = os.getenv("PGPASSWORD", "postgres"),
        dbname   = os.getenv("PGDATABASE", "soccer_db"),
    )


def apply_schema(conn) -> None:
    print(f"[1/3] Applico schema da {SCHEMA_SQL.name}")
    with conn.cursor() as cur, open(SCHEMA_SQL, "r", encoding="utf-8") as f:
        cur.execute(f.read())
    conn.commit()


def copy_csv(conn, table: str, csv_path: Path, columns: list[str] | None,
             skip_conflicts: bool = False) -> int:
    full_table = f"soccer.{table}"
    cols_part  = ("(" + ", ".join(columns) + ")") if columns else ""

    if not skip_conflicts:
        copy_sql = f"COPY {full_table} {cols_part} FROM STDIN WITH (FORMAT csv, HEADER true, NULL '')"
        with conn.cursor() as cur, open(csv_path, "r", encoding="utf-8") as f:
            cur.copy_expert(copy_sql, f)
            cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier("soccer", table)))
            n = cur.fetchone()[0]
        conn.commit()
    else:
        # Carica in una tabella temporanea, poi inserisce ignorando i duplicati.
        tmp = f"_tmp_{table}"
        with conn.cursor() as cur:
            # LIKE senza INCLUDING ALL: solo colonne, nessun vincolo/indice
            cur.execute(f"CREATE TEMP TABLE {tmp} (LIKE {full_table}) ON COMMIT DROP")
            with open(csv_path, "r", encoding="utf-8") as f:
                copy_sql = f"COPY {tmp} {cols_part} FROM STDIN WITH (FORMAT csv, HEADER true, NULL '')"
                cur.copy_expert(copy_sql, f)
            cur.execute(f"INSERT INTO {full_table} SELECT * FROM {tmp} ON CONFLICT DO NOTHING")
            cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier("soccer", table)))
            n = cur.fetchone()[0]
        conn.commit()
    return n


def refresh_materialized_views(conn) -> None:
    """
    La MV soccer.mv_played_for e' creata dal DDL ma resta vuota finche' le
    tabelle sorgente non sono popolate. Va materializzata DOPO il load di
    match + match_lineup.
    """
    print("\n[2.5/3] Refresh materialized views")
    with conn.cursor() as cur:
        cur.execute("REFRESH MATERIALIZED VIEW soccer.mv_played_for")
        cur.execute("SELECT COUNT(*) FROM soccer.mv_played_for")
        n = cur.fetchone()[0]
        print(f"  [ok]   mv_played_for refreshed. Rows: {n:,}")
    conn.commit()


def smoke_test(conn) -> None:
    print("\n[3/3] Smoke test:")
    queries = [
        ("Match per stagione",
         "SELECT season, COUNT(*) AS n FROM soccer.match GROUP BY season ORDER BY season"),
        ("Top 5 marcatori storici",
         """
         SELECT p.player_name, COUNT(*) AS goals
         FROM soccer.match_event e
         JOIN soccer.player p ON p.player_api_id = e.player1_id
         WHERE e.event_type = 'goal'
         GROUP BY p.player_name ORDER BY goals DESC LIMIT 5
         """),
    ]
    with conn.cursor() as cur:
        for label, q in queries:
            print(f"\n-- {label} --")
            cur.execute(q)
            rows = cur.fetchall()
            for r in rows:
                print(" ", r)


def main() -> None:
    if not SCHEMA_SQL.exists():
        sys.exit(f"Schema mancante: {SCHEMA_SQL}")
    if not CLEAN_DIR.exists():
        sys.exit(f"Cartella clean/ non trovata. Eseguire prima transform.py.")

    conn = get_conn()
    try:
        apply_schema(conn)
        print("[2/3] Caricamento CSV via COPY")
        for entry in LOAD_ORDER:
            table, fname, cols = entry[0], entry[1], entry[2]
            skip_conflicts = entry[3] if len(entry) > 3 else False
            path = CLEAN_DIR / fname
            if not path.exists():
                print(f"  [skip] {table}: file non trovato {path}")
                continue
            n = copy_csv(conn, table, path, cols, skip_conflicts)
            print(f"  [ok]   {table:<14} caricato. Righe in tabella: {n:,}")

        refresh_materialized_views(conn)
        smoke_test(conn)
    finally:
        conn.close()
    print("\nFatto.")


if __name__ == "__main__":
    main()
