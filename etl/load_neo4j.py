"""
Carica i CSV puliti (cartella clean/) in Neo4j seguendo lo schema definito
in schema/neo4j_schema.md.

Pre-requisiti:
    1. Neo4j in esecuzione localmente (Desktop o Docker, vedi etl/README.md).
    2. I CSV in clean/ devono essere accessibili al server Neo4j.
       Lo script li copia in 'import/' di Neo4j se viene fornito NEO4J_IMPORT_DIR,
       altrimenti carica via stream HTTP/file:/// dipendentemente dalla configurazione.
       La via piu' semplice e' impostare NEO4J_IMPORT_DIR.
    3. Variabili d'ambiente:
            NEO4J_URI       (default: bolt://localhost:7687)
            NEO4J_USER      (default: neo4j)
            NEO4J_PASSWORD  (default: password)
            NEO4J_DATABASE  (default: neo4j)
            NEO4J_IMPORT_DIR (consigliato: cartella 'import' della tua DB Neo4j)
    4. Pacchetti Python: neo4j

Pipeline:
    1. (opzionale) Copia i CSV nella cartella 'import' di Neo4j.
    2. Pulizia DB: MATCH (n) DETACH DELETE n  (commentabile in produzione).
    3. Crea vincoli + indici.
    4. Carica nodi: Country, League, Team, Player, Match.
    5. Carica relazioni base: IN_COUNTRY, IN_LEAGUE, HOME, AWAY.
    6. Carica LINEUP_OF da match_lineup.csv.
    7. Parsa match_event.csv e carica SCORED_IN, ASSISTED_IN, RECEIVED_CARD_IN,
       COMMITTED_FOUL_IN.
    8. Calcola la relazione derivata PLAYED_FOR.

Uso:
    python3 load_neo4j.py
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from neo4j import GraphDatabase

try:
    from dotenv import load_dotenv  # opzionale
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

HERE = Path(__file__).resolve().parent
CLEAN_DIR = HERE.parent / "clean"

URI      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
USER     = os.getenv("NEO4J_USER",     "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
IMPORT_DIR = os.getenv("NEO4J_IMPORT_DIR")  # se settato, copio i CSV qui

CSV_FILES = [
    "country.csv", "league.csv", "team.csv", "player.csv",
    "match.csv", "match_lineup.csv", "match_event.csv",
]


def copy_csvs_to_import_dir() -> None:
    if not IMPORT_DIR:
        print("[!] NEO4J_IMPORT_DIR non impostata. Assicurati che i CSV siano "
              "raggiungibili dal server Neo4j (file:/// o URL).")
        return
    target = Path(IMPORT_DIR)
    target.mkdir(parents=True, exist_ok=True)
    for f in CSV_FILES:
        src = CLEAN_DIR / f
        if src.exists():
            shutil.copy(src, target / f)
            print(f"  copiato {f} -> {target}")


def run(session, query: str, **params):
    return session.run(query, **params).consume().counters


# ----------------------------------------------------------------------------
#  Cypher
# ----------------------------------------------------------------------------

CONSTRAINTS = [
    "CREATE CONSTRAINT country_id_unique IF NOT EXISTS FOR (c:Country) REQUIRE c.countryId IS UNIQUE",
    "CREATE CONSTRAINT league_id_unique  IF NOT EXISTS FOR (l:League)  REQUIRE l.leagueId IS UNIQUE",
    "CREATE CONSTRAINT team_id_unique    IF NOT EXISTS FOR (t:Team)    REQUIRE t.teamApiId IS UNIQUE",
    "CREATE CONSTRAINT player_id_unique  IF NOT EXISTS FOR (p:Player)  REQUIRE p.playerApiId IS UNIQUE",
    "CREATE CONSTRAINT match_id_unique   IF NOT EXISTS FOR (m:Match)   REQUIRE m.matchApiId IS UNIQUE",
    "CREATE INDEX player_name_idx  IF NOT EXISTS FOR (p:Player) ON (p.name)",
    "CREATE INDEX team_name_idx    IF NOT EXISTS FOR (t:Team)   ON (t.name)",
    "CREATE INDEX match_season_idx IF NOT EXISTS FOR (m:Match)  ON (m.season)",
    "CREATE INDEX match_date_idx   IF NOT EXISTS FOR (m:Match)  ON (m.date)",
]

LOAD_NODES = [
    # Country
    """
    LOAD CSV WITH HEADERS FROM 'file:///country.csv' AS row
    MERGE (c:Country {countryId: toInteger(row.country_id)})
    SET c.name = row.name
    """,
    # League
    """
    LOAD CSV WITH HEADERS FROM 'file:///league.csv' AS row
    MERGE (l:League {leagueId: toInteger(row.league_id)})
    SET l.name = row.name
    WITH l, row
    MATCH (c:Country {countryId: toInteger(row.country_id)})
    MERGE (l)-[:IN_COUNTRY]->(c)
    """,
    # Team
    """
    LOAD CSV WITH HEADERS FROM 'file:///team.csv' AS row
    MERGE (t:Team {teamApiId: toInteger(row.team_api_id)})
    SET t.teamFifaApiId = CASE WHEN row.team_fifa_api_id = '' THEN null ELSE toInteger(row.team_fifa_api_id) END,
        t.name          = row.team_long_name,
        t.shortName     = row.team_short_name
    """,
    # Player
    """
    LOAD CSV WITH HEADERS FROM 'file:///player.csv' AS row
    MERGE (p:Player {playerApiId: toInteger(row.player_api_id)})
    SET p.playerFifaApiId = CASE WHEN row.player_fifa_api_id = '' THEN null ELSE toInteger(row.player_fifa_api_id) END,
        p.name     = row.player_name,
        p.birthday = CASE WHEN row.birthday = '' THEN null ELSE date(row.birthday) END,
        p.height   = CASE WHEN row.height = ''  THEN null ELSE toFloat(row.height) END,
        p.weight   = CASE WHEN row.weight = ''  THEN null ELSE toInteger(row.weight) END
    """,
    # Match
    """
    LOAD CSV WITH HEADERS FROM 'file:///match.csv' AS row
    MERGE (m:Match {matchApiId: toInteger(row.match_api_id)})
    SET m.season    = row.season,
        m.stage     = toInteger(row.stage),
        m.date      = date(row.match_date),
        m.homeGoals = toInteger(row.home_team_goal),
        m.awayGoals = toInteger(row.away_team_goal)
    WITH m, row
    MATCH (l:League {leagueId: toInteger(row.league_id)})
    MERGE (m)-[:IN_LEAGUE]->(l)
    WITH m, row
    MATCH (h:Team {teamApiId: toInteger(row.home_team_api_id)})
    MERGE (m)-[:HOME]->(h)
    WITH m, row
    MATCH (a:Team {teamApiId: toInteger(row.away_team_api_id)})
    MERGE (m)-[:AWAY]->(a)
    """,
]

LOAD_LINEUP = """
CALL apoc.periodic.iterate(
  "LOAD CSV WITH HEADERS FROM 'file:///match_lineup.csv' AS row RETURN row",
  "MATCH (p:Player {playerApiId: toInteger(row.player_api_id)})
   MATCH (m:Match  {matchApiId:  toInteger(row.match_api_id)})
   MERGE (p)-[r:LINEUP_OF {side: row.side, positionIdx: toInteger(row.position_idx)}]->(m)
   SET r.posX = CASE WHEN row.pos_x = '' THEN null ELSE toInteger(row.pos_x) END,
       r.posY = CASE WHEN row.pos_y = '' THEN null ELSE toInteger(row.pos_y) END",
  {batchSize: 5000, parallel: false}
)
"""

# Versione senza APOC (piu' lenta, ma funziona su istanze "vanilla")
LOAD_LINEUP_NO_APOC = """
LOAD CSV WITH HEADERS FROM 'file:///match_lineup.csv' AS row
MATCH (p:Player {playerApiId: toInteger(row.player_api_id)})
MATCH (m:Match  {matchApiId:  toInteger(row.match_api_id)})
MERGE (p)-[r:LINEUP_OF {side: row.side, positionIdx: toInteger(row.position_idx)}]->(m)
SET r.posX = CASE WHEN row.pos_x = '' THEN null ELSE toInteger(row.pos_x) END,
    r.posY = CASE WHEN row.pos_y = '' THEN null ELSE toInteger(row.pos_y) END
"""

LOAD_GOALS = """
LOAD CSV WITH HEADERS FROM 'file:///match_event.csv' AS row
WITH row WHERE row.event_type = 'goal' AND row.player1_id <> ''
MATCH (p:Player {playerApiId: toInteger(row.player1_id)})
MATCH (m:Match  {matchApiId:  toInteger(row.match_api_id)})
MERGE (p)-[g:SCORED_IN {sourceEventId: toInteger(row.source_event_id)}]->(m)
SET g.minute   = toInteger(row.elapsed_minute),
    g.subtype  = row.subtype,
    g.goalType = row.goal_type,
    g.teamApiId = CASE WHEN row.team_api_id = '' THEN null ELSE toInteger(row.team_api_id) END
"""

LOAD_ASSISTS = """
LOAD CSV WITH HEADERS FROM 'file:///match_event.csv' AS row
WITH row WHERE row.event_type = 'goal' AND row.player2_id <> ''
MATCH (p:Player {playerApiId: toInteger(row.player2_id)})
MATCH (m:Match  {matchApiId:  toInteger(row.match_api_id)})
MERGE (p)-[a:ASSISTED_IN {sourceEventId: toInteger(row.source_event_id)}]->(m)
SET a.minute = toInteger(row.elapsed_minute)
"""

LOAD_CARDS = """
LOAD CSV WITH HEADERS FROM 'file:///match_event.csv' AS row
WITH row WHERE row.event_type = 'card' AND row.player1_id <> ''
MATCH (p:Player {playerApiId: toInteger(row.player1_id)})
MATCH (m:Match  {matchApiId:  toInteger(row.match_api_id)})
MERGE (p)-[c:RECEIVED_CARD_IN {sourceEventId: toInteger(row.source_event_id)}]->(m)
SET c.minute     = toInteger(row.elapsed_minute),
    c.cardType   = row.card_type,
    c.subtype    = row.subtype,
    c.teamApiId  = CASE WHEN row.team_api_id = '' THEN null ELSE toInteger(row.team_api_id) END
"""

LOAD_FOULS = """
LOAD CSV WITH HEADERS FROM 'file:///match_event.csv' AS row
WITH row WHERE row.event_type = 'foulcommit' AND row.player1_id <> ''
MATCH (p:Player {playerApiId: toInteger(row.player1_id)})
MATCH (m:Match  {matchApiId:  toInteger(row.match_api_id)})
MERGE (p)-[f:COMMITTED_FOUL_IN {sourceEventId: toInteger(row.source_event_id)}]->(m)
SET f.minute = toInteger(row.elapsed_minute),
    f.victimPlayerId = CASE WHEN row.player2_id = '' THEN null ELSE toInteger(row.player2_id) END
"""

DERIVE_PLAYED_FOR = """
MATCH (p:Player)-[:LINEUP_OF]->(m:Match)-[:HOME|AWAY]->(t:Team)
WITH p, t, m.season AS season, count(*) AS apps
MERGE (p)-[r:PLAYED_FOR {season: season}]->(t)
SET r.appearances = apps
"""


def main(use_apoc: bool = False) -> None:
    if not CLEAN_DIR.exists():
        sys.exit("Cartella clean/ non trovata. Eseguire prima transform.py.")

    if IMPORT_DIR:
        print(f"[0/8] Copio i CSV in {IMPORT_DIR}")
        copy_csvs_to_import_dir()
    else:
        print("[0/8] NEO4J_IMPORT_DIR non impostata: salto la copia.")
        print("      Assicurati che il server abbia accesso ai file file:///<nome>.csv.")

    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    try:
        with driver.session(database=DATABASE) as session:
            print("[1/8] Pulizia DB (MATCH (n) DETACH DELETE n)")
            session.run("MATCH (n) DETACH DELETE n").consume()

            print("[2/8] Vincoli e indici")
            for q in CONSTRAINTS:
                session.run(q).consume()

            print("[3/8] Carico nodi (Country, League, Team, Player, Match) e relazioni base")
            for q in LOAD_NODES:
                c = run(session, q)
                print(f"  nodi creati: {c.nodes_created}, prop set: {c.properties_set}, rel create: {c.relationships_created}")

            print("[4/8] LINEUP_OF (542k relazioni — puo' richiedere alcuni minuti)")
            q = LOAD_LINEUP if use_apoc else LOAD_LINEUP_NO_APOC
            session.run(q).consume()

            print("[5/8] SCORED_IN")
            session.run(LOAD_GOALS).consume()

            print("[6/8] ASSISTED_IN")
            session.run(LOAD_ASSISTS).consume()

            print("[7/8] RECEIVED_CARD_IN + COMMITTED_FOUL_IN")
            session.run(LOAD_CARDS).consume()
            session.run(LOAD_FOULS).consume()

            print("[8/8] Relazione derivata PLAYED_FOR")
            session.run(DERIVE_PLAYED_FOR).consume()

            print("\nSmoke test:")
            r = session.run("""
                MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n
                ORDER BY n DESC
            """).data()
            for row in r:
                print(f"  {row['label']:<10} {row['n']:>10,}")
            r = session.run("""
                MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS n
                ORDER BY n DESC
            """).data()
            for row in r:
                print(f"  -[:{row['rel']}]-> {row['n']:>10,}")

    finally:
        driver.close()
    print("\nFatto.")


if __name__ == "__main__":
    main(use_apoc=os.getenv("USE_APOC", "false").lower() == "true")
