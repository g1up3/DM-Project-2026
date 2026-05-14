-- Q01: Top N marcatori della stagione X.
-- Categoria A (relazionale classica): aggregazione + JOIN su 3 tabelle.
-- Parametri: %(season)s, %(top_n)s

WITH scorers AS (
    SELECT m.season,
           p.player_api_id,
           p.player_name,
           COUNT(*) AS goals
    FROM   soccer.match_event e
    JOIN   soccer.match  m ON m.match_api_id = e.match_api_id
    JOIN   soccer.player p ON p.player_api_id = e.player1_id
    WHERE  e.event_type = 'goal'
      AND  m.season = %(season)s
    GROUP  BY m.season, p.player_api_id, p.player_name
)
SELECT season, player_name, goals
FROM   scorers
ORDER  BY goals DESC, player_name
LIMIT  %(top_n)s;
