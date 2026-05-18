// Q05: Coppie marcatore-assistman che hanno collaborato almeno N volte.
//
// Replica la semantica SQL: la JOIN SQL avviene sulla STESSA riga di
// match_event (player1=scorer, player2=assister, stesso evento). Per
// replicarla in Cypher accoppiamo SCORED_IN e ASSISTED_IN sullo stesso
// sourceEventId, e ci proteggiamo dal caso `sourceEventId IS NULL`
// (NULL = NULL in Cypher e' "null" non "true" → escluderebbe quelle coppie
// silenziosamente). Se nei dati esistono goal con source_event_id NULL,
// senza il guard escluderemmo coppie che SQL invece accoppia.
// Parametri: $min_partnerships

MATCH (scorer:Player)-[g:SCORED_IN]->(m:Match)<-[a:ASSISTED_IN]-(assister:Player)
WHERE g.sourceEventId IS NOT NULL
  AND a.sourceEventId IS NOT NULL
  AND g.sourceEventId = a.sourceEventId
WITH scorer.name AS scorer, assister.name AS assister, count(*) AS partnerships
WHERE partnerships >= $min_partnerships
RETURN scorer, assister, partnerships
ORDER BY partnerships DESC, scorer, assister;
