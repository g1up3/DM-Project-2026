// Q11: Bulk UPDATE — normalise the 'subtype' field to lowercase on every
//      SCORED_IN relationship (~40k relationships touched).
// (no parameters)

MATCH ()-[g:SCORED_IN]->()
WHERE g.subtype IS NOT NULL
SET   g.subtype = toLower(g.subtype);
