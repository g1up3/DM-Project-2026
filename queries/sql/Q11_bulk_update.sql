-- Q11: Bulk UPDATE — normalise the 'subtype' field to lowercase on every
--      goal event in the database (~40k rows touched).
-- Category D (write workload): tests bulk write performance.
-- (no parameters)

UPDATE soccer.match_event
SET    subtype = LOWER(subtype)
WHERE  event_type = 'goal'
  AND  subtype IS NOT NULL;
