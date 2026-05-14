-- Q07: Giocatori che hanno disputato almeno un match in TUTTE le 8 stagioni del dataset.
-- Categoria B (multi-hop): aggregazione + filtro su numero distinto di stagioni.
-- (no parametri)

SELECT p.player_name AS player,
       COUNT(DISTINCT m.season) AS seasons_played
FROM   soccer.match_lineup l
JOIN   soccer.match  m ON m.match_api_id = l.match_api_id
JOIN   soccer.player p ON p.player_api_id = l.player_api_id
GROUP  BY p.player_name
HAVING COUNT(DISTINCT m.season) = 8
ORDER  BY player;
