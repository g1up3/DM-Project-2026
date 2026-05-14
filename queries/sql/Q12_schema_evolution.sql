-- Q12: Schema evolution — add a new attribute "total_goals" to every Match,
--      computed as home_team_goal + away_team_goal.
-- In SQL this is a TWO-step operation: ALTER the schema, then UPDATE the data.
-- The migration cost grows with the table size, and the table is locked during
-- ALTER (depends on Postgres version).
-- (no parameters)

ALTER TABLE soccer.match
ADD  COLUMN IF NOT EXISTS total_goals SMALLINT;

UPDATE soccer.match
SET    total_goals = home_team_goal + away_team_goal
WHERE  total_goals IS NULL;
