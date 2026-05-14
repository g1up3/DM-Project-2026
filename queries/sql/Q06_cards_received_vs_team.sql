-- Q06: Top giocatori per cartellini ricevuti contro la squadra X.
-- "Contro X" = quando si gioca una partita in cui X e' una delle due squadre,
-- e il cartellinato NON e' un giocatore di X (filtro tramite team della partita).
-- Categoria B (multi-hop): join 4 tabelle con disuguaglianza fra team.
-- Parametri: %(team_name)s, %(top_n)s

SELECT p.player_name AS player,
       SUM(CASE WHEN e.card_type LIKE 'y%%' THEN 1 ELSE 0 END) AS yellow,
       SUM(CASE WHEN e.card_type =  'r'    THEN 1 ELSE 0 END) AS red,
       COUNT(*) AS total_cards
FROM   soccer.match_event e
JOIN   soccer.match  m ON m.match_api_id  = e.match_api_id
JOIN   soccer.team   t ON t.team_api_id   = CASE
            WHEN m.home_team_api_id = e.team_api_id THEN m.away_team_api_id
            ELSE m.home_team_api_id END                           -- la squadra avversaria
JOIN   soccer.player p ON p.player_api_id = e.player1_id
WHERE  e.event_type = 'card'
  AND  t.team_long_name = %(team_name)s
  AND  e.team_api_id IS NOT NULL
  AND  e.team_api_id <> t.team_api_id                            -- doppia sicurezza
GROUP  BY p.player_name
ORDER  BY total_cards DESC, player        -- tiebreaker deterministico
LIMIT  %(top_n)s;
