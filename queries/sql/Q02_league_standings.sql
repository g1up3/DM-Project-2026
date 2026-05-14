-- Q02: Classifica del campionato per stagione X e lega Y (3 punti vittoria, 1 pareggio).
-- Categoria A (relazionale classica): UNION ALL + aggregazione.
-- Parametri: %(season)s, %(league_name)s

WITH home AS (
    SELECT m.season, m.league_id,
           m.home_team_api_id AS team_id,
           CASE WHEN m.home_team_goal > m.away_team_goal THEN 3
                WHEN m.home_team_goal = m.away_team_goal THEN 1
                ELSE 0 END AS pts,
           m.home_team_goal AS gf,
           m.away_team_goal AS ga
    FROM   soccer.match m
), away AS (
    SELECT m.season, m.league_id,
           m.away_team_api_id AS team_id,
           CASE WHEN m.away_team_goal > m.home_team_goal THEN 3
                WHEN m.home_team_goal = m.away_team_goal THEN 1
                ELSE 0 END AS pts,
           m.away_team_goal AS gf,
           m.home_team_goal AS ga
    FROM   soccer.match m
), all_results AS (
    SELECT * FROM home
    UNION ALL
    SELECT * FROM away
)
SELECT t.team_long_name AS team,
       SUM(r.pts) AS points,
       SUM(r.gf)  AS goals_for,
       SUM(r.ga)  AS goals_against,
       SUM(r.gf) - SUM(r.ga) AS goal_diff
FROM   all_results r
JOIN   soccer.team   t ON t.team_api_id = r.team_id
JOIN   soccer.league l ON l.league_id   = r.league_id
WHERE  r.season = %(season)s
  AND  l.name   = %(league_name)s
GROUP  BY t.team_long_name
ORDER  BY points DESC, goal_diff DESC, team;
