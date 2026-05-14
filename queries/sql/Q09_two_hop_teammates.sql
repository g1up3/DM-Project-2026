-- Q09: "Compagni dei compagni" del giocatore X (network a 2 hop).
-- played_for(player, team, season) := EXISTS (lineup di player in match in cui team gioca, in season)
-- Categoria C (graph-native): in SQL serve un doppio join attraverso "team x season".
-- Restituisce i giocatori a distanza 2 (escludendo X e i diretti compagni).
-- Parametri: %(player_name)s, %(top_n)s

WITH played_for AS (
    SELECT DISTINCT
           l.player_api_id,
           CASE WHEN l.side = 'home' THEN m.home_team_api_id
                                     ELSE m.away_team_api_id END AS team_api_id,
           m.season
    FROM   soccer.match_lineup l
    JOIN   soccer.match m ON m.match_api_id = l.match_api_id
), x_history AS (        -- (team, season) di X
    SELECT pf.team_api_id, pf.season
    FROM   played_for pf
    JOIN   soccer.player p ON p.player_api_id = pf.player_api_id
    WHERE  p.player_name = %(player_name)s
), direct_teammates AS ( -- player a distanza 1 da X (stesso team, stessa stagione)
    SELECT DISTINCT pf.player_api_id
    FROM   played_for pf
    JOIN   x_history h ON h.team_api_id = pf.team_api_id
                       AND h.season     = pf.season
), teams_of_direct AS (  -- (team, season) dei compagni diretti
    SELECT DISTINCT pf.team_api_id, pf.season
    FROM   played_for pf
    JOIN   direct_teammates d ON d.player_api_id = pf.player_api_id
)
SELECT p.player_name AS player_2hop,
       COUNT(*) AS connection_strength
FROM   played_for pf
JOIN   teams_of_direct td ON td.team_api_id = pf.team_api_id
                          AND td.season     = pf.season
JOIN   soccer.player p ON p.player_api_id = pf.player_api_id
WHERE  pf.player_api_id NOT IN (SELECT player_api_id FROM direct_teammates)
  AND  p.player_name <> %(player_name)s
GROUP  BY p.player_name
ORDER  BY connection_strength DESC, player_2hop
LIMIT  %(top_n)s;
