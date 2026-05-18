-- Q10: Distanza minima fra due giocatori sul "grafo dei compagni di squadra" (max 6 hop).
-- played_with(a, b) := esistono partita e stagione in cui a e b sono dello stesso team.
--
-- Usa la materialized view soccer.mv_played_for (precomputata e indicizzata),
-- analogo alla relazione :PLAYED_FOR di Neo4j. La CTE ricorsiva implementa
-- una BFS limitata a profondita' 6 (stesso limite usato dalla controparte
-- Cypher in queries/cypher/Q10_*.cypher, che ha *..12 dato che PLAYED_FOR
-- e' direzionale e ogni hop player-player attraversa 2 archi).
-- Parametri: %(player_a)s, %(player_b)s

WITH RECURSIVE
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
    JOIN   soccer.mv_played_for pf1 ON pf1.player_api_id = b.player_api_id
    JOIN   soccer.mv_played_for pf2 ON pf2.team_api_id    = pf1.team_api_id
                                    AND pf2.season         = pf1.season
                                    AND pf2.player_api_id <> b.player_api_id
    WHERE  b.distance < 6
)
SELECT MIN(distance) AS shortest_path_hops
FROM   bfs
WHERE  player_api_id = (SELECT dst FROM endpoints);
