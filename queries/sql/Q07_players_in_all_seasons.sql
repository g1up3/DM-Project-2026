-- Q07: Giocatori che hanno disputato almeno un match in TUTTE le 8 stagioni del dataset.
-- Categoria B (multi-hop): aggregazione + filtro su numero distinto di stagioni.
-- (no parametri)
--
-- Si raggruppa per player_api_id, NON per nome: il dataset contiene 163 nomi
-- omonimi (giocatori diversi con lo stesso player_name). Raggruppando per nome,
-- due omonimi con 4 stagioni ciascuno risulterebbero un unico giocatore con 8
-- stagioni: 14 "giocatori" fittizi su 550 (verificato). L'id compare nel
-- result-set cosi' che il confronto fra i due sistemi sia esatto anche in
-- presenza di omonimi.

SELECT p.player_api_id           AS player_api_id,
       p.player_name             AS player,
       COUNT(DISTINCT m.season)  AS seasons_played
FROM   soccer.match_lineup l
JOIN   soccer.match  m ON m.match_api_id = l.match_api_id
JOIN   soccer.player p ON p.player_api_id = l.player_api_id
GROUP  BY p.player_api_id, p.player_name
HAVING COUNT(DISTINCT m.season) = 8
ORDER  BY player, player_api_id;
