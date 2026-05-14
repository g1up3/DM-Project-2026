-- Q04: Top N squadre per percentuale di vittorie casalinghe (su tutto il dataset).
-- Categoria A (relazionale classica): aggregazione condizionale + filtri.
-- Parametri: %(top_n)s, %(min_home_matches)s

SELECT t.team_long_name AS team,
       COUNT(*) AS home_matches,
       SUM(CASE WHEN m.home_team_goal > m.away_team_goal THEN 1 ELSE 0 END) AS home_wins,
       ROUND(100.0 *
             SUM(CASE WHEN m.home_team_goal > m.away_team_goal THEN 1 ELSE 0 END)::numeric
             / COUNT(*), 2) AS home_win_pct
FROM   soccer.match m
JOIN   soccer.team  t ON t.team_api_id = m.home_team_api_id
GROUP  BY t.team_long_name
HAVING COUNT(*) >= %(min_home_matches)s
ORDER  BY home_win_pct DESC, home_matches DESC
LIMIT  %(top_n)s;
