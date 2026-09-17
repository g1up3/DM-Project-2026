// Q04: Top N squadre per percentuale di vittorie casalinghe.
// Parametri: $top_n, $min_home_matches
// Raggruppa per nodo Team (= team_api_id in SQL); tie-breaker sul nome in
// ORDER BY per un LIMIT deterministico in entrambi i sistemi.

MATCH (m:Match)-[:HOME]->(t:Team)
WITH t,
     count(m) AS home_matches,
     sum(CASE WHEN m.homeGoals > m.awayGoals THEN 1 ELSE 0 END) AS home_wins
WHERE home_matches >= $min_home_matches
RETURN t.name AS team,
       home_matches,
       home_wins,
       round(100.0 * home_wins / home_matches * 100) / 100 AS home_win_pct
ORDER BY home_win_pct DESC, home_matches DESC, team
LIMIT $top_n;
