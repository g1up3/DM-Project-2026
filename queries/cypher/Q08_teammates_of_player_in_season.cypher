// Q08: Compagni di squadra del giocatore X nella stagione Y, ordinati per partite condivise.
// In Cypher: 1 hop di traversal attraverso il Match comune con side uguale.
// Parametri: $player_name, $season, $top_n

MATCH (p:Player {name: $player_name})-[l1:LINEUP_OF]->(m:Match)<-[l2:LINEUP_OF]-(teammate:Player)
WHERE m.season  = $season
  AND l1.side   = l2.side
  AND teammate <> p
// Raggruppa per nodo (= playerApiId), non per nome: 163 omonimi nel dataset.
RETURN teammate.playerApiId AS teammate_api_id, teammate.name AS teammate, count(*) AS shared_matches
ORDER BY shared_matches DESC, teammate, teammate_api_id
LIMIT $top_n;
