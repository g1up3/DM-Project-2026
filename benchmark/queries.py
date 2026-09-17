"""
Definizione delle 10 query del benchmark con relativi parametri.
Ogni query e' identificata da un id Q01..Q10 e ha:
  - file SQL    in queries/sql/<id>_*.sql
  - file Cypher in queries/cypher/<id>_*.cypher
  - dizionario di parametri da passare a entrambi i driver

I parametri sono nominali: SQL usa %(name)s, Cypher usa $name.
"""

from dataclasses import dataclass


@dataclass
class QueryDef:
    id: str
    name: str
    category: str            # 'A_relational' | 'B_multihop' | 'C_graph_native' | 'D_write'
    sql_file: str
    cypher_file: str
    params: dict
    notes: str = ""
    # Solo per le query write (categoria D), in modalita' --write-mode commit:
    # statement eseguiti (fuori dal timer) dopo ogni run per riportare il DB
    # allo stato iniziale. None = la query e' idempotente, nessun cleanup.
    cleanup_sql: str | None = None
    cleanup_cypher: str | None = None


QUERIES: list[QueryDef] = [
    QueryDef(
        id="Q01",
        name="Top scorers by season",
        category="A_relational",
        sql_file="Q01_top_scorers_by_season.sql",
        cypher_file="Q01_top_scorers_by_season.cypher",
        params={"season": "2015/2016", "top_n": 10},
    ),
    QueryDef(
        id="Q02",
        name="League standings by season",
        category="A_relational",
        sql_file="Q02_league_standings.sql",
        cypher_file="Q02_league_standings.cypher",
        params={"season": "2015/2016", "league_name": "Italy Serie A"},
    ),
    QueryDef(
        id="Q03",
        name="Goals per match by league",
        category="A_relational",
        sql_file="Q03_goals_per_match_by_league.sql",
        cypher_file="Q03_goals_per_match_by_league.cypher",
        params={"season": "2015/2016"},
    ),
    QueryDef(
        id="Q04",
        name="Home win percentage by team",
        category="A_relational",
        sql_file="Q04_home_win_pct.sql",
        cypher_file="Q04_home_win_pct.cypher",
        params={"top_n": 10, "min_home_matches": 50},
    ),
    QueryDef(
        id="Q05",
        name="Goal-assist partnerships",
        category="B_multihop",
        sql_file="Q05_goal_assist_partnerships.sql",
        cypher_file="Q05_goal_assist_partnerships.cypher",
        params={"min_partnerships": 10},
    ),
    QueryDef(
        id="Q06",
        name="Cards received vs Real Madrid",
        category="B_multihop",
        sql_file="Q06_cards_received_vs_team.sql",
        cypher_file="Q06_cards_received_vs_team.cypher",
        params={"team_name": "Real Madrid CF", "top_n": 15},
    ),
    QueryDef(
        id="Q07",
        name="Players in all 8 seasons",
        category="B_multihop",
        sql_file="Q07_players_in_all_seasons.sql",
        cypher_file="Q07_players_in_all_seasons.cypher",
        params={},
    ),
    QueryDef(
        id="Q08",
        name="Teammates of Messi 2015/16",
        category="C_graph_native",
        sql_file="Q08_teammates_of_player_in_season.sql",
        cypher_file="Q08_teammates_of_player_in_season.cypher",
        params={"player_name": "Lionel Messi", "season": "2015/2016", "top_n": 20},
    ),
    QueryDef(
        id="Q09",
        name="2-hop teammates of Messi",
        category="C_graph_native",
        sql_file="Q09_two_hop_teammates.sql",
        cypher_file="Q09_two_hop_teammates.cypher",
        params={"player_name": "Lionel Messi", "top_n": 20},
    ),
    QueryDef(
        id="Q10",
        name="Shortest path Messi -> Pirlo",
        category="C_graph_native",
        sql_file="Q10_shortest_path_between_players.sql",
        cypher_file="Q10_shortest_path_between_players.cypher",
        params={"player_a": "Lionel Messi", "player_b": "Andrea Pirlo"},
    ),
    QueryDef(
        id="Q11",
        name="Bulk UPDATE on event subtype",
        category="D_write",
        sql_file="Q11_bulk_update.sql",
        cypher_file="Q11_bulk_update.cypher",
        params={},
        notes="Mass write workload (no SELECT). LOWER() e' idempotente sui dati: "
              "nessun cleanup necessario dopo il commit.",
    ),
    QueryDef(
        id="Q12",
        name="Schema evolution: add totalGoals",
        category="D_write",
        sql_file="Q12_schema_evolution.sql",
        cypher_file="Q12_schema_evolution.cypher",
        params={},
        notes="DDL+UPDATE in SQL vs single SET in Cypher",
        cleanup_sql="ALTER TABLE soccer.match DROP COLUMN IF EXISTS total_goals",
        cleanup_cypher="MATCH (m:Match) REMOVE m.totalGoals",
    ),
]
