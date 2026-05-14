-- Q12: Schema evolution demo (demo version for psql)
SET search_path TO soccer;

\timing on
ALTER TABLE soccer.match ADD COLUMN total_goals SMALLINT;
UPDATE soccer.match SET total_goals = home_team_goal + away_team_goal;

-- Verify
SELECT match_api_id, home_team_goal, away_team_goal, total_goals
FROM   soccer.match LIMIT 5;

-- Cleanup
ALTER TABLE soccer.match DROP COLUMN total_goals;
