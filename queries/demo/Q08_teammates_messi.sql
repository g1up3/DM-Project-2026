-- Q08: Teammates of Messi in season 2015/16 (demo version for psql)
SET search_path TO soccer;

SELECT DISTINCT p2.player_name AS teammate
FROM   soccer.match_lineup l1
JOIN   soccer.match m  ON m.match_api_id = l1.match_api_id
JOIN   soccer.match_lineup l2 ON l2.match_api_id = l1.match_api_id
                              AND l2.side = l1.side
                              AND l2.player_api_id <> l1.player_api_id
JOIN   soccer.player p1 ON p1.player_api_id = l1.player_api_id
JOIN   soccer.player p2 ON p2.player_api_id = l2.player_api_id
WHERE  p1.player_name = 'Lionel Messi'
  AND  m.season = '2015/2016'
ORDER  BY teammate
LIMIT  20;
