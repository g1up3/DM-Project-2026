-- Q03: Media gol per partita per ogni lega nella stagione X.
-- Categoria A (relazionale classica): aggregazione + GROUP BY.
-- Parametri: %(season)s

SELECT l.name AS league,
       COUNT(*) AS matches,
       AVG(m.home_team_goal + m.away_team_goal)::NUMERIC(5,3) AS avg_goals_per_match,
       SUM(m.home_team_goal + m.away_team_goal) AS total_goals
FROM   soccer.match m
JOIN   soccer.league l ON l.league_id = m.league_id
WHERE  m.season = %(season)s
GROUP  BY l.name
ORDER  BY avg_goals_per_match DESC;
