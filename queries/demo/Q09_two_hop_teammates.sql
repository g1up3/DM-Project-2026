-- Q09: 2-hop teammates of Messi (demo version for psql, parameters inlined)
SET search_path TO soccer;

-- Q09: "Compagni dei compagni" del giocatore X (network a 2 hop).
-- played_for(player, team, season) e' precomputato come MATERIALIZED VIEW
-- soccer.mv_played_for (vedere schema/postgres_schema.sql). Questo replica la
-- relazione derivata :PLAYED_FOR di Neo4j, garantendo un confronto fair fra
-- i due sistemi: entrambi attraversano una struttura precomputata equivalente.
-- Categoria C (graph-native): doppio join attraverso "team x season".
-- Parametri: 'Lionel Messi', 20

WITH x_history AS (        -- (team, season) di X
    SELECT pf.team_api_id, pf.season
    FROM   soccer.mv_played_for pf
    JOIN   soccer.player p ON p.player_api_id = pf.player_api_id
    WHERE  p.player_name = 'Lionel Messi'
), direct_teammates AS ( -- player a distanza 1 da X (stesso team, stessa stagione)
    SELECT DISTINCT pf.player_api_id
    FROM   soccer.mv_played_for pf
    JOIN   x_history h ON h.team_api_id = pf.team_api_id
                       AND h.season     = pf.season
), teams_of_direct AS (  -- (team, season) dei compagni diretti
    SELECT DISTINCT pf.team_api_id, pf.season
    FROM   soccer.mv_played_for pf
    JOIN   direct_teammates d ON d.player_api_id = pf.player_api_id
)
SELECT p.player_name AS player_2hop,
       COUNT(*) AS connection_strength
FROM   soccer.mv_played_for pf
JOIN   teams_of_direct td ON td.team_api_id = pf.team_api_id
                          AND td.season     = pf.season
JOIN   soccer.player p ON p.player_api_id = pf.player_api_id
WHERE  pf.player_api_id NOT IN (SELECT player_api_id FROM direct_teammates)
  AND  p.player_name <> 'Lionel Messi'
GROUP  BY p.player_name
ORDER  BY connection_strength DESC, player_2hop
LIMIT  20;
