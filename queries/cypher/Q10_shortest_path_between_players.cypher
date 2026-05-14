// Q10: Distanza minima fra due giocatori sul "grafo dei compagni di squadra".
// Cypher offre shortestPath() come primitiva. Profondita' max 6.
// Parametri: $player_a, $player_b

MATCH (a:Player {name: $player_a}), (b:Player {name: $player_b})
MATCH path = shortestPath((a)-[:PLAYED_FOR*..6]-(b))
RETURN length(path) / 2 AS shortest_path_hops;
