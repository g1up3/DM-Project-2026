-- Q08: Compagni di squadra del giocatore X nella stagione Y, ordinati per partite condivise.
-- Categoria C (graph-native): self-join su match_lineup con stesso side.
-- Parametri: %(player_name)s, %(season)s, %(top_n)s

SELECT teammate.player_name AS teammate,
       COUNT(*) AS shared_matches
FROM   soccer.match_lineup l1
JOIN   soccer.match m  ON m.match_api_id = l1.match_api_id
JOIN   soccer.player p ON p.player_api_id = l1.player_api_id
JOIN   soccer.match_lineup l2
       ON l2.match_api_id = l1.match_api_id
      AND l2.side         = l1.side
      AND l2.player_api_id <> l1.player_api_id
JOIN   soccer.player teammate ON teammate.player_api_id = l2.player_api_id
WHERE  p.player_name = %(player_name)s
  AND  m.season      = %(season)s
GROUP  BY teammate.player_name
ORDER  BY shared_matches DESC, teammate
LIMIT  %(top_n)s;
