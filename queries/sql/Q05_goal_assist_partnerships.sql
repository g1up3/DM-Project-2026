-- Q05: Coppie marcatore-assistman che hanno collaborato almeno N volte (gol + assist).
-- Categoria B (multi-hop): self-join sullo stesso evento attraverso player1/player2.
-- Parametri: %(min_partnerships)s

SELECT scorer.player_name  AS scorer,
       assister.player_name AS assister,
       COUNT(*) AS partnerships
FROM   soccer.match_event e
JOIN   soccer.player scorer   ON scorer.player_api_id   = e.player1_id
JOIN   soccer.player assister ON assister.player_api_id = e.player2_id
WHERE  e.event_type = 'goal'
  AND  e.player2_id IS NOT NULL
GROUP  BY scorer.player_name, assister.player_name
HAVING COUNT(*) >= %(min_partnerships)s
ORDER  BY partnerships DESC, scorer, assister;
