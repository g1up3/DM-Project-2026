// Q10: Distanza minima fra due giocatori sul "grafo dei compagni di squadra".
// Cypher offre shortestPath() come primitiva.
//
// Profondita': PLAYED_FOR e' direzionale Player->Team, quindi per andare da
// Player a Player tramite il pattern non-direzionale (a)-[:PLAYED_FOR]-(b)
// servono 2 archi per ogni "hop" player-player. La controparte SQL permette
// fino a 6 hop player-player (BFS con WHERE distance < 6), quindi qui usiamo
// *..12 per equivalenza semantica: 12 archi = 6 hop player-player.
// Parametri: $player_a, $player_b

MATCH (a:Player {name: $player_a}), (b:Player {name: $player_b})
MATCH path = shortestPath((a)-[:PLAYED_FOR*..12]-(b))
RETURN length(path) / 2 AS shortest_path_hops;
