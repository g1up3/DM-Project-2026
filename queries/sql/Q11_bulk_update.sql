-- Q11: Bulk UPDATE — normalise the 'subtype' field to lowercase on every
--      goal event with a known scorer (~21k rows touched).
-- Category D (write workload): tests bulk write performance.
-- (no parameters)
--
-- player1_id IS NOT NULL: the graph only materialises a goal as a
-- (:Player)-[:SCORED_IN]->(:Match) relationship when the scorer is known
-- (109 goal rows have a NULL scorer after the orphan-reference cleanup in the
-- ETL and have no counterpart in Neo4j). Restricting the UPDATE to the same
-- population makes the two write workloads touch exactly the same 21,442
-- logical rows; the harness verifies it via rowcount vs properties_set.
-- LOWER() is idempotent on this data (subtypes are already lowercase), so
-- the statement can be committed without changing the dataset.

UPDATE soccer.match_event
SET    subtype = LOWER(subtype)
WHERE  event_type = 'goal'
  AND  subtype IS NOT NULL
  AND  player1_id IS NOT NULL;
