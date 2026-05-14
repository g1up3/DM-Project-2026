// Q03: Media gol per partita per ogni lega in una stagione.
// Parametri: $season

MATCH (m:Match {season: $season})-[:IN_LEAGUE]->(l:League)
WITH l.name AS league, count(m) AS matches,
     sum(m.homeGoals + m.awayGoals) AS total_goals
RETURN league,
       matches,
       round(toFloat(total_goals) / matches * 1000) / 1000 AS avg_goals_per_match,
       total_goals
ORDER BY avg_goals_per_match DESC;
