-- Q10: Distanza minima fra due giocatori sul "grafo dei compagni di squadra" (max 6 hop).
-- played_with(a, b) := esistono partita e stagione in cui a e b sono dello stesso team.
-- In Postgres serve una CTE ricorsiva (BFS), che limito a profondita' 6 per
-- evitare esplosioni combinatorie. Questa e' esattamente la query in cui
-- una graph DB con shortestPath() vince per leggibilita' e performance.
-- Parametri: %(player_a)s, %(player_b)s

WITH RECURSIVE
played_for AS (
    SELECT DISTINCT
           l.player_api_id,
           CASE WHEN l.side = 'home' THEN m.home_team_api_id
                                     ELSE m.away_team_api_id END AS team_api_id,
           m.season
    FROM   soccer.match_lineup l
    JOIN   soccer.match m ON m.match_api_id = l.match_api_id
),
endpoints AS (
    SELECT
        (SELECT player_api_id FROM soccer.player WHERE player_name = %(player_a)s LIMIT 1) AS src,
        (SELECT player_api_id FROM soccer.player WHERE player_name = %(player_b)s LIMIT 1) AS dst
),
bfs (player_api_id, distance) AS (
    SELECT src AS player_api_id, 0 AS distance
    FROM   endpoints

    UNION

    SELECT pf2.player_api_id, b.distance + 1
    FROM   bfs b
    JOIN   played_for pf1 ON pf1.player_api_id = b.player_api_id
    JOIN   played_for pf2 ON pf2.team_api_id  = pf1.team_api_id
                          AND pf2.season       = pf1.season
                          AND pf2.player_api_id <> b.player_api_id
    WHERE  b.distance < 6
)
SELECT MIN(distance) AS shortest_path_hops
FROM   bfs
WHERE  player_api_id = (SELECT dst FROM endpoints);
