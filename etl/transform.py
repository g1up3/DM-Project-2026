"""
Transform: estrae i dati dal SQLite, parsa gli XML degli eventi delle partite,
e produce CSV puliti pronti per essere caricati sia in PostgreSQL sia in Neo4j.

Pipeline:

    SQLite (database.sqlite)
        |
        |  --- estrazione e tipizzazione ---
        v
    DataFrame in memoria
        |
        |  --- explode Match (115 col)  ->  match + match_lineup + match_event ---
        v
    CSV in cartella `clean/`:
        country.csv
        league.csv
        team.csv
        player.csv
        match.csv
        match_lineup.csv      (~570k righe)
        match_event.csv       (~1.5M righe — generato dal parsing XML)
        player_stats.csv
        team_stats.csv

I CSV sono nel formato esatto dello schema PostgreSQL definito in
schema/postgres_schema.sql e usabili anche con LOAD CSV di Neo4j.

Uso:
    python3 transform.py
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from xml.etree import ElementTree as ET

import pandas as pd

# ----------------------------------------------------------------------------
#  Percorsi
# ----------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent
_DB_CANDIDATES = [
    HERE.parent / "database.sqlite",
    HERE.parent / "database" / "database.sqlite",
]
DB_PATH = next((p for p in _DB_CANDIDATES if p.exists()), _DB_CANDIDATES[0])
OUT_DIR = HERE.parent / "clean"

# ----------------------------------------------------------------------------
#  Costanti
# ----------------------------------------------------------------------------

XML_COLUMNS = [
    "goal", "shoton", "shotoff", "foulcommit",
    "card", "cross", "corner", "possession",
]

HOME_ID_COLS = [f"home_player_{i}" for i in range(1, 12)]
AWAY_ID_COLS = [f"away_player_{i}" for i in range(1, 12)]
HOME_X_COLS  = [f"home_player_X{i}" for i in range(1, 12)]
AWAY_X_COLS  = [f"away_player_X{i}" for i in range(1, 12)]
HOME_Y_COLS  = [f"home_player_Y{i}" for i in range(1, 12)]
AWAY_Y_COLS  = [f"away_player_Y{i}" for i in range(1, 12)]


# ----------------------------------------------------------------------------
#  Helper
# ----------------------------------------------------------------------------

def _to_int(text: str | None) -> int | None:
    if text is None:
        return None
    text = text.strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _child_text(node: ET.Element, tag: str) -> str | None:
    """Restituisce il testo di un figlio di `node` con tag `tag`, oppure None."""
    el = node.find(tag)
    if el is None or el.text is None:
        return None
    text = el.text.strip()
    return text or None


def parse_event_xml(xml_str: str | None, event_type: str) -> list[dict]:
    """
    Trasforma una stringa XML del campo `event_type` in lista di dict-record
    pronti per essere scritti in match_event.csv.

    Ritorna [] se l'XML è NULL/vuoto/malformato.
    """
    if not xml_str or not xml_str.strip():
        return []
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError:
        return []

    rows = []
    for v in root.findall("value"):
        rows.append({
            "event_type":      event_type,
            "subtype":         _child_text(v, "subtype"),
            "elapsed_minute":  _to_int(_child_text(v, "elapsed")),
            "team_api_id":     _to_int(_child_text(v, "team")),
            "player1_id":      _to_int(_child_text(v, "player1")),
            "player2_id":      _to_int(_child_text(v, "player2")),
            "card_type":       _child_text(v, "card_type") if event_type == "card" else None,
            "goal_type":       _child_text(v, "goal_type") if event_type == "goal" else None,
            "sort_order":      _to_int(_child_text(v, "sortorder")),
            "source_event_id": _to_int(_child_text(v, "id")),
        })
    return rows


# ----------------------------------------------------------------------------
#  Estrazione e trasformazione
# ----------------------------------------------------------------------------

def extract_country(conn) -> pd.DataFrame:
    df = pd.read_sql("SELECT id AS country_id, name FROM Country", conn)
    return df


def extract_league(conn) -> pd.DataFrame:
    df = pd.read_sql(
        "SELECT id AS league_id, country_id, name FROM League",
        conn,
    )
    return df


def extract_team(conn) -> pd.DataFrame:
    df = pd.read_sql(
        """
        SELECT team_api_id,
               team_fifa_api_id,
               team_long_name,
               team_short_name
        FROM Team
        """,
        conn,
    )
    df["team_short_name"] = df["team_short_name"].astype("string").str[:3]
    return df


def extract_player(conn) -> pd.DataFrame:
    df = pd.read_sql(
        """
        SELECT player_api_id,
               player_fifa_api_id,
               player_name,
               substr(birthday, 1, 10) AS birthday,
               height,
               weight
        FROM Player
        """,
        conn,
    )
    return df


def extract_match_basic(conn) -> pd.DataFrame:
    """Estrae solo le colonne base di Match (no XML, no quote, no lineup wide)."""
    return pd.read_sql(
        """
        SELECT match_api_id,
               league_id,
               season,
               stage,
               substr(date, 1, 10) AS match_date,
               home_team_api_id,
               away_team_api_id,
               home_team_goal,
               away_team_goal
        FROM Match
        """,
        conn,
    )


def build_match_lineup(conn) -> pd.DataFrame:
    """
    Esplode le 44 colonne home_player_*/away_player_* (+ X/Y) in una tabella lunga
    con una riga per (match, side, position_idx).
    Le righe in cui il player_api_id è NULL vengono scartate.
    """
    cols_needed = ["match_api_id"] + HOME_ID_COLS + AWAY_ID_COLS \
        + HOME_X_COLS + AWAY_X_COLS + HOME_Y_COLS + AWAY_Y_COLS
    select_cols = ", ".join(f'"{c}"' for c in cols_needed)
    df = pd.read_sql(f"SELECT {select_cols} FROM Match", conn)

    rows = []
    for side, id_cols, x_cols, y_cols in [
        ("home", HOME_ID_COLS, HOME_X_COLS, HOME_Y_COLS),
        ("away", AWAY_ID_COLS, AWAY_X_COLS, AWAY_Y_COLS),
    ]:
        for i in range(11):
            sub = df[["match_api_id", id_cols[i], x_cols[i], y_cols[i]]].rename(
                columns={
                    id_cols[i]: "player_api_id",
                    x_cols[i]:  "pos_x",
                    y_cols[i]:  "pos_y",
                }
            )
            sub["side"] = side
            sub["position_idx"] = i + 1
            rows.append(sub)
    lineup = pd.concat(rows, ignore_index=True)
    lineup = lineup.dropna(subset=["player_api_id"])
    lineup["player_api_id"] = lineup["player_api_id"].astype("Int64")
    lineup["pos_x"] = lineup["pos_x"].astype("Int64")
    lineup["pos_y"] = lineup["pos_y"].astype("Int64")
    return lineup[["match_api_id", "player_api_id", "side", "position_idx", "pos_x", "pos_y"]]


def build_match_events(conn, valid_player_ids: set[int]) -> pd.DataFrame:
    """
    Per ogni match e per ogni colonna XML, parsa l'XML e produce le righe di
    match_event. Ritorna un DataFrame con tutte le righe concatenate.

    I riferimenti player1_id / player2_id che non esistono nella tabella Player
    vengono nullificati per evitare violazioni di FK durante il COPY in Postgres.
    """
    select_cols = ", ".join(['match_api_id'] + [f'"{c}"' for c in XML_COLUMNS])
    df = pd.read_sql(f"SELECT {select_cols} FROM Match", conn)

    all_rows: list[dict] = []
    for _, r in df.iterrows():
        match_id = int(r["match_api_id"])
        for col in XML_COLUMNS:
            for ev in parse_event_xml(r[col], col):
                ev["match_api_id"] = match_id
                all_rows.append(ev)

    out = pd.DataFrame(all_rows, columns=[
        "match_api_id", "event_type", "subtype", "elapsed_minute",
        "team_api_id", "player1_id", "player2_id",
        "card_type", "goal_type", "sort_order", "source_event_id",
    ])
    # tipi coerenti con lo schema postgres
    for c in ["match_api_id", "elapsed_minute", "team_api_id",
              "player1_id", "player2_id", "sort_order", "source_event_id"]:
        out[c] = out[c].astype("Int64")

    # Nullifico le FK player orfane (sono ~0.5% degli eventi: trasferimenti
    # piu' vecchi del dataset Player non tracciati nel sorgente).
    for col in ("player1_id", "player2_id"):
        mask_orphan = out[col].notna() & ~out[col].isin(valid_player_ids)
        n_orphans = int(mask_orphan.sum())
        if n_orphans:
            print(f"    [nullify] {col}: {n_orphans:,} riferimenti orfani -> NULL")
            out.loc[mask_orphan, col] = pd.NA
    return out


def extract_player_stats(conn) -> pd.DataFrame:
    df = pd.read_sql(
        """
        SELECT player_api_id,
               substr(date, 1, 10) AS snapshot_date,
               player_fifa_api_id,
               overall_rating, potential, preferred_foot,
               attacking_work_rate, defensive_work_rate,
               crossing, finishing, heading_accuracy, short_passing, volleys,
               dribbling, curve, free_kick_accuracy, long_passing, ball_control,
               acceleration, sprint_speed, agility, reactions, balance,
               shot_power, jumping, stamina, strength, long_shots, aggression,
               interceptions, positioning, vision, penalties, marking,
               standing_tackle, sliding_tackle,
               gk_diving, gk_handling, gk_kicking, gk_positioning, gk_reflexes
        FROM Player_Attributes
        """,
        conn,
    )
    return df


def extract_team_stats(conn) -> pd.DataFrame:
    df = pd.read_sql(
        """
        SELECT team_api_id,
               substr(date, 1, 10) AS snapshot_date,
               team_fifa_api_id,
               buildUpPlaySpeed, buildUpPlaySpeedClass,
               buildUpPlayDribbling, buildUpPlayDribblingClass,
               buildUpPlayPassing, buildUpPlayPassingClass,
               buildUpPlayPositioningClass,
               chanceCreationPassing, chanceCreationPassingClass,
               chanceCreationCrossing, chanceCreationCrossingClass,
               chanceCreationShooting, chanceCreationShootingClass,
               chanceCreationPositioningClass,
               defencePressure, defencePressureClass,
               defenceAggression, defenceAggressionClass,
               defenceTeamWidth, defenceTeamWidthClass,
               defenceDefenderLineClass
        FROM Team_Attributes
        """,
        conn,
    )
    return df


# ----------------------------------------------------------------------------
#  Main
# ----------------------------------------------------------------------------

def _coerce_int_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converte in Int64 (nullable integer) le colonne float che contengono solo
    valori interi + NaN. Evita che pandas serializzi 673 come "673.0", cosa
    che fa fallire il COPY di Postgres su colonne INTEGER.
    """
    for c in df.columns:
        if df[c].dtype == "float64":
            non_null = df[c].dropna()
            if len(non_null) > 0 and (non_null == non_null.astype("int64")).all():
                df[c] = df[c].astype("Int64")
    return df


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df = _coerce_int_columns(df)
    df.to_csv(path, index=False, quoting=csv.QUOTE_MINIMAL, encoding="utf-8")
    size_mb = path.stat().st_size / (1024 * 1024)
    print(f"  -> {path.name:<22} {len(df):>9,} righe ({size_mb:.2f} MB)")


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database non trovato: {DB_PATH}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[1/9] Connessione a {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    try:
        print("[2/9] Estrazione anagrafiche")
        write_csv(extract_country(conn), OUT_DIR / "country.csv")
        write_csv(extract_league(conn),  OUT_DIR / "league.csv")
        write_csv(extract_team(conn),    OUT_DIR / "team.csv")
        player_df = extract_player(conn)
        write_csv(player_df, OUT_DIR / "player.csv")
        valid_player_ids: set[int] = set(player_df["player_api_id"].astype(int).tolist())

        print("[3/9] Estrazione match (colonne base)")
        write_csv(extract_match_basic(conn), OUT_DIR / "match.csv")

        print("[4/9] Costruzione match_lineup (esplosione delle 44 colonne)")
        write_csv(build_match_lineup(conn), OUT_DIR / "match_lineup.csv")

        print("[5/9] Parsing XML e costruzione match_event")
        write_csv(build_match_events(conn, valid_player_ids), OUT_DIR / "match_event.csv")

        print("[6/9] Estrazione player_stats")
        write_csv(extract_player_stats(conn), OUT_DIR / "player_stats.csv")

        print("[7/9] Estrazione team_stats")
        write_csv(extract_team_stats(conn), OUT_DIR / "team_stats.csv")
    finally:
        conn.close()

    print("\n[8/9] Output completo in:", OUT_DIR)
    print("[9/9] Fatto.")


if __name__ == "__main__":
    main()
