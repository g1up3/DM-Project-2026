"""
Esplorazione del dataset European Soccer Database.

Produce un report in Markdown (reports/dataset_exploration.md) con:
  1. Schema di ogni tabella (colonne, tipi, esempi)
  2. Conteggi righe / NULL per colonna
  3. Range temporale e distribuzioni rilevanti (stagioni, leghe, paesi)
  4. Anteprima e struttura dei campi XML in Match (goal, shoton, possession...)
  5. Verifiche di integrita' referenziale fra le tabelle

Uso:
    python3 explore_dataset.py
"""

import sqlite3
from pathlib import Path
from xml.etree import ElementTree as ET

import pandas as pd

HERE = Path(__file__).resolve().parent
# Cerca il file sqlite in due posizioni possibili: a fianco dello script o in ../database/
_CANDIDATES = [
    HERE.parent / "database.sqlite",
    HERE.parent / "database" / "database.sqlite",
    HERE / "database.sqlite",
]
DB_PATH = next((p for p in _CANDIDATES if p.exists()), _CANDIDATES[0])
REPORT_DIR = HERE.parent / "reports"
REPORT_PATH = REPORT_DIR / "dataset_exploration.md"

# Colonne XML di Match (dati grezzi degli eventi della partita)
XML_COLUMNS = [
    "goal", "shoton", "shotoff", "foulcommit", "card",
    "cross", "corner", "possession",
]

# Colonne giocatori in campo (formazione 11 vs 11)
HOME_PLAYER_COLS = [f"home_player_{i}" for i in range(1, 12)]
AWAY_PLAYER_COLS = [f"away_player_{i}" for i in range(1, 12)]


def md_table(df: pd.DataFrame) -> str:
    """Renderizza un DataFrame come tabella Markdown semplice."""
    if df.empty:
        return "_(vuoto)_\n"
    return df.to_markdown(index=False) + "\n"


def section(title: str, level: int = 2) -> str:
    return f"\n{'#' * level} {title}\n\n"


def explore() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database non trovato: {DB_PATH}")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    out: list[str] = []
    out.append("# Esplorazione dataset — European Soccer Database\n")
    out.append("Report generato automaticamente da `etl/explore_dataset.py`.\n")

    # --- 1. Lista tabelle ---
    tables = pd.read_sql(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;",
        conn,
    )["name"].tolist()

    out.append(section("1. Tabelle e dimensioni"))
    rows = []
    for t in tables:
        n = pd.read_sql(f'SELECT COUNT(*) AS n FROM "{t}"', conn).iloc[0]["n"]
        cols = pd.read_sql(f'PRAGMA table_info("{t}")', conn)
        rows.append({"tabella": t, "righe": n, "colonne": len(cols)})
    out.append(md_table(pd.DataFrame(rows)))

    # --- 2. Schema dettagliato per tabella ---
    out.append(section("2. Schema di ogni tabella"))
    for t in tables:
        out.append(section(t, level=3))
        cols = pd.read_sql(f'PRAGMA table_info("{t}")', conn)
        cols = cols[["name", "type", "notnull", "pk"]]
        cols.columns = ["colonna", "tipo", "NOT NULL", "PK"]
        out.append(md_table(cols))

    # --- 3. NULL per colonna (top 15 per tabella) ---
    out.append(section("3. Valori NULL per colonna"))
    for t in tables:
        cols = pd.read_sql(f'PRAGMA table_info("{t}")', conn)["name"].tolist()
        n_total = pd.read_sql(f'SELECT COUNT(*) AS n FROM "{t}"', conn).iloc[0]["n"]
        if n_total == 0 or not cols:
            continue
        # COUNT delle NULL per ogni colonna
        select_parts = [f'SUM(CASE WHEN "{c}" IS NULL THEN 1 ELSE 0 END) AS "{c}"' for c in cols]
        q = f'SELECT {", ".join(select_parts)} FROM "{t}"'
        nulls = pd.read_sql(q, conn).T.reset_index()
        nulls.columns = ["colonna", "null"]
        nulls["pct_null"] = (nulls["null"] / n_total * 100).round(2)
        nulls = nulls.sort_values("null", ascending=False)
        # mostriamo solo le colonne con almeno un NULL, top 15
        nulls = nulls[nulls["null"] > 0].head(15)
        out.append(section(f"{t} ({n_total:,} righe)", level=3))
        if nulls.empty:
            out.append("Nessun NULL.\n")
        else:
            out.append(md_table(nulls))

    # --- 4. Distribuzioni: stagioni, leghe, paesi ---
    out.append(section("4. Distribuzioni rilevanti"))

    # 4a. Match per stagione
    seasons = pd.read_sql(
        "SELECT season, COUNT(*) AS n FROM Match GROUP BY season ORDER BY season",
        conn,
    )
    out.append(section("Match per stagione", level=3))
    out.append(md_table(seasons))

    # 4b. Match per lega (con paese)
    leagues = pd.read_sql(
        """
        SELECT c.name AS country, l.name AS league, COUNT(*) AS n_match
        FROM Match m
        JOIN League l ON l.id = m.league_id
        JOIN Country c ON c.id = m.country_id
        GROUP BY c.name, l.name
        ORDER BY n_match DESC
        """,
        conn,
    )
    out.append(section("Match per lega", level=3))
    out.append(md_table(leagues))

    # 4c. Range date
    rng = pd.read_sql(
        "SELECT MIN(date) AS min_date, MAX(date) AS max_date FROM Match",
        conn,
    )
    out.append(section("Range temporale dei match", level=3))
    out.append(md_table(rng))

    # 4d. Player_Attributes: snapshot per giocatore
    snap = pd.read_sql(
        """
        SELECT n_snapshots, COUNT(*) AS n_players
        FROM (
            SELECT player_api_id, COUNT(*) AS n_snapshots
            FROM Player_Attributes
            GROUP BY player_api_id
        )
        GROUP BY n_snapshots
        ORDER BY n_snapshots
        """,
        conn,
    )
    out.append(section("Player_Attributes: distribuzione snapshot per giocatore", level=3))
    out.append(md_table(snap))

    # --- 5. Anteprima dei campi XML di Match ---
    out.append(section("5. Struttura dei campi XML di Match"))
    out.append(
        "I campi `goal`, `shoton`, `shotoff`, `foulcommit`, `card`, `cross`, "
        "`corner`, `possession` contengono XML grezzi con gli eventi della partita. "
        "Sotto, per ognuno: percentuale di NULL e un esempio di payload (troncato).\n"
    )
    n_match = pd.read_sql("SELECT COUNT(*) AS n FROM Match", conn).iloc[0]["n"]
    for col in XML_COLUMNS:
        out.append(section(col, level=3))
        n_null = pd.read_sql(
            f'SELECT COUNT(*) AS n FROM Match WHERE "{col}" IS NULL OR "{col}" = ""',
            conn,
        ).iloc[0]["n"]
        pct_null = round(n_null / n_match * 100, 2) if n_match else 0
        out.append(f"- NULL/vuoti: **{n_null:,} / {n_match:,}** ({pct_null}%)\n\n")

        sample = pd.read_sql(
            f'SELECT "{col}" AS payload FROM Match WHERE "{col}" IS NOT NULL AND LENGTH("{col}") > 50 LIMIT 1',
            conn,
        )
        if not sample.empty:
            payload = sample.iloc[0]["payload"]
            preview = payload[:600] + ("..." if len(payload) > 600 else "")
            out.append("```xml\n" + preview + "\n```\n")

            # Conta i tag <value> dentro questo XML di esempio
            try:
                root = ET.fromstring(payload)
                values = root.findall("value")
                out.append(f"Numero di elementi `<value>` in questo esempio: **{len(values)}**\n")
                if values:
                    first = values[0]
                    children_tags = [child.tag for child in first]
                    out.append(
                        "Tag presenti nel primo `<value>`: "
                        + ", ".join(f"`{c}`" for c in children_tags)
                        + "\n"
                    )
            except ET.ParseError as e:
                out.append(f"_Parse error: {e}_\n")
        else:
            out.append("_Nessun esempio non vuoto trovato._\n")

    # --- 6. Integrita' referenziale ---
    out.append(section("6. Verifica integrita' referenziale"))
    checks = []

    # 6a. Match.home_team_api_id / away_team_api_id presenti in Team
    for col in ("home_team_api_id", "away_team_api_id"):
        q = f"""
            SELECT COUNT(*) AS n FROM Match m
            WHERE m."{col}" IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM Team t WHERE t.team_api_id = m."{col}")
        """
        n = pd.read_sql(q, conn).iloc[0]["n"]
        checks.append({"check": f"Match.{col} -> Team.team_api_id (orfani)", "n": int(n)})

    # 6b. Match.league_id / country_id
    for col, target_t, target_c in [
        ("league_id", "League", "id"),
        ("country_id", "Country", "id"),
    ]:
        q = f"""
            SELECT COUNT(*) AS n FROM Match m
            WHERE m."{col}" IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM "{target_t}" x WHERE x."{target_c}" = m."{col}")
        """
        n = pd.read_sql(q, conn).iloc[0]["n"]
        checks.append({"check": f"Match.{col} -> {target_t}.{target_c} (orfani)", "n": int(n)})

    # 6c. home_player_X / away_player_X presenti in Player (aggregato)
    union_parts = " UNION ALL ".join(
        [f'SELECT "{c}" AS pid FROM Match WHERE "{c}" IS NOT NULL' for c in HOME_PLAYER_COLS + AWAY_PLAYER_COLS]
    )
    q_players = f"""
        WITH used_players AS ({union_parts})
        SELECT
            COUNT(*) AS tot_riferimenti,
            SUM(CASE WHEN p.player_api_id IS NULL THEN 1 ELSE 0 END) AS orfani
        FROM used_players u
        LEFT JOIN Player p ON p.player_api_id = u.pid
    """
    pl = pd.read_sql(q_players, conn).iloc[0]
    checks.append({"check": "Match.player_X (home/away 1..11) -> Player.player_api_id", "n": f"{int(pl['orfani']):,} orfani su {int(pl['tot_riferimenti']):,} riferimenti"})

    # 6d. Player_Attributes -> Player
    q = """
        SELECT COUNT(*) AS n FROM Player_Attributes pa
        WHERE NOT EXISTS (SELECT 1 FROM Player p WHERE p.player_api_id = pa.player_api_id)
    """
    n = pd.read_sql(q, conn).iloc[0]["n"]
    checks.append({"check": "Player_Attributes.player_api_id -> Player (orfani)", "n": int(n)})

    # 6e. Team_Attributes -> Team
    q = """
        SELECT COUNT(*) AS n FROM Team_Attributes ta
        WHERE NOT EXISTS (SELECT 1 FROM Team t WHERE t.team_api_id = ta.team_api_id)
    """
    n = pd.read_sql(q, conn).iloc[0]["n"]
    checks.append({"check": "Team_Attributes.team_api_id -> Team (orfani)", "n": int(n)})

    out.append(md_table(pd.DataFrame(checks)))

    conn.close()

    REPORT_PATH.write_text("\n".join(out), encoding="utf-8")
    print(f"Report scritto in: {REPORT_PATH}")


if __name__ == "__main__":
    explore()
