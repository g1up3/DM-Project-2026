// Q07: Giocatori che hanno disputato almeno un match in TUTTE le 8 stagioni.
// (no parametri)

// Raggruppa per nome (come il GROUP BY player_name in SQL), così i giocatori
// omonimi (stesso nome, playerApiId diverso) hanno le stagioni aggregate,
// replicando la semantica della query SQL equivalente.
MATCH (p:Player)-[:LINEUP_OF]->(m:Match)
WITH p.name AS player_name, m.season AS season
WITH player_name, count(DISTINCT season) AS seasons_played
WHERE seasons_played = 8
RETURN player_name AS player, seasons_played
ORDER BY player;
