// Q05: Coppie marcatore-assistman che hanno collaborato almeno N volte.
//
// Replica la semantica SQL: la JOIN SQL avviene sulla STESSA riga di
// match_event (player1=scorer, player2=assister, stesso evento). In Cypher
// l'evento e' stato spezzato in due relazioni (SCORED_IN, ASSISTED_IN) e le
// riaccoppiamo tramite sourceEventId. L'equivalenza con il SQL poggia su un
// invariante dei dati, verificato: ogni gol ha un sourceEventId non nullo e
// univoco (0 NULL, 0 duplicati su 40k gol; il MERGE del loader fallirebbe
// su una proprieta' NULL). Il guard IS NOT NULL rende l'assunzione esplicita
// (NULL = NULL in Cypher vale null, non true): se l'invariante cadesse, le
// coppie senza id verrebbero escluse qui mentre SQL le conterebbe — un
// limite della modellazione a due archi rispetto a un nodo :MatchEvent.
// Parametri: $min_partnerships

MATCH (scorer:Player)-[g:SCORED_IN]->(m:Match)<-[a:ASSISTED_IN]-(assister:Player)
WHERE g.sourceEventId IS NOT NULL
  AND a.sourceEventId IS NOT NULL
  AND g.sourceEventId = a.sourceEventId
WITH scorer.name AS scorer, assister.name AS assister, count(*) AS partnerships
WHERE partnerships >= $min_partnerships
RETURN scorer, assister, partnerships
ORDER BY partnerships DESC, scorer, assister;
