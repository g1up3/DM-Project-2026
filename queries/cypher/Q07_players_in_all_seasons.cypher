// Q07: Giocatori che hanno disputato almeno un match in TUTTE le 8 stagioni.
// (no parametri)
//
// Si raggruppa per nodo Player (cioe' per playerApiId), NON per nome: il
// dataset contiene 163 nomi omonimi e raggruppare per nome fonderebbe
// giocatori diversi (14 risultati fittizi su 550). Stessa semantica del
// GROUP BY p.player_api_id in SQL; l'id e' nel result-set per un confronto
// esatto fra i due sistemi.

MATCH (p:Player)-[:LINEUP_OF]->(m:Match)
WITH p, count(DISTINCT m.season) AS seasons_played
WHERE seasons_played = 8
RETURN p.playerApiId AS player_api_id, p.name AS player, seasons_played
ORDER BY player, player_api_id;
