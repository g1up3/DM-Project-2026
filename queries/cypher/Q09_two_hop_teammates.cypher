// Q09: "Compagni dei compagni" del giocatore X (network a 2 hop).
// Versione season-aware: rispecchia la semantica SQL dove played_for(p, t, season)
// richiede che due giocatori condividano la STESSA stagione nello stesso team.
// Parametri: $player_name, $top_n

// Passo 1: compagni diretti (stesso team, stessa stagione di X)
MATCH (x:Player {name: $player_name})-[r1:PLAYED_FOR]->(t:Team)<-[r2:PLAYED_FOR]-(direct:Player)
WHERE r1.season = r2.season
WITH x, collect(DISTINCT direct) AS direct_set

// Passo 2: tutte le (team, season) coperte dai compagni diretti
MATCH (d:Player)-[r3:PLAYED_FOR]->(t2:Team)
WHERE d IN direct_set
WITH x, direct_set, collect(DISTINCT [t2.teamApiId, r3.season]) AS covered_pairs

// Passo 3: giocatori a 2 hop che si sovrappongono a covered_pairs
MATCH (p2:Player)-[r4:PLAYED_FOR]->(t3:Team)
WHERE p2 <> x AND NOT p2 IN direct_set
  AND [t3.teamApiId, r4.season] IN covered_pairs
// Raggruppa per nodo (= playerApiId), non per nome: due omonimi restano distinti.
RETURN p2.playerApiId AS player_2hop_api_id, p2.name AS player_2hop, count(*) AS connection_strength
ORDER BY connection_strength DESC, player_2hop, player_2hop_api_id
LIMIT $top_n;
