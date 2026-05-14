// Q12: Schema evolution — add a new attribute "totalGoals" to every Match.
// In Cypher there is no schema migration: SET adds the property directly,
// and only on the matched nodes. ONE statement, no DDL.
// (no parameters)

MATCH (m:Match)
SET   m.totalGoals = m.homeGoals + m.awayGoals;
