// Q05: Coppie marcatore-assistman che hanno collaborato almeno N volte.
// Si appoggia al sourceEventId condiviso tra SCORED_IN e ASSISTED_IN.
// Parametri: $min_partnerships

MATCH (scorer:Player)-[g:SCORED_IN]->(m:Match)<-[a:ASSISTED_IN]-(assister:Player)
WHERE g.sourceEventId = a.sourceEventId
WITH scorer.name AS scorer, assister.name AS assister, count(*) AS partnerships
WHERE partnerships >= $min_partnerships
RETURN scorer, assister, partnerships
ORDER BY partnerships DESC, scorer, assister;
