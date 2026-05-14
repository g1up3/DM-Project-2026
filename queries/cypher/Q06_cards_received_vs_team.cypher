// Q06: Top giocatori per cartellini ricevuti contro la squadra X.
// "Contro X" = il cartellino appartiene a un giocatore NON della squadra X.
// Usa c.teamApiId (aggiunto su RECEIVED_CARD_IN tramite LOAD CSV) per
// identificare il team del cartellinato, replicando la logica SQL (e.team_api_id).
// Parametri: $team_name, $top_n

MATCH (target:Team {name: $team_name})
MATCH (m:Match)-[:HOME|AWAY]->(target)
MATCH (p:Player)-[c:RECEIVED_CARD_IN]->(m)
WHERE c.teamApiId IS NOT NULL
  AND c.teamApiId <> target.teamApiId
RETURN p.name AS player,
       sum(CASE WHEN c.cardType STARTS WITH 'y' THEN 1 ELSE 0 END) AS yellow,
       sum(CASE WHEN c.cardType = 'r'           THEN 1 ELSE 0 END) AS red,
       count(*) AS total_cards
ORDER BY total_cards DESC, player        // tiebreaker deterministico
LIMIT $top_n;
