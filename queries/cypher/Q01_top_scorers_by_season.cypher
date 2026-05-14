// Q01: Top N marcatori della stagione X.
// Parametri: $season, $top_n

MATCH (p:Player)-[:SCORED_IN]->(m:Match {season: $season})
WITH p, count(*) AS goals
RETURN $season AS season, p.name AS player_name, goals
ORDER BY goals DESC, player_name
LIMIT $top_n;
