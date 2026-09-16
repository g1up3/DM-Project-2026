// Q10: Distanza minima fra due giocatori sul "grafo dei compagni di squadra".
//
// Semantica (identica alla BFS SQL su mv_played_for): un hop player-player
// esiste solo se i due giocatori hanno vestito la stessa maglia NELLA STESSA
// STAGIONE (pf2.season = pf1.season nel join SQL). PLAYED_FOR e' direzionale
// Player->Team con una relazione per stagione, quindi un hop e' il gruppo
// (x)-[r1]->(Team)<-[r2]-(y) con r1.season = r2.season.
//
// Il quantified path pattern (GQL) permette di scrivere il vincolo di stagione
// DENTRO il gruppo ripetuto; SHORTEST 1 lo risolve con l'operatore
// StatefulShortestPath (BFS limitata, nessun fallback esaustivo).
// {1,6} = fino a 6 hop player-player, come WHERE distance < 6 in SQL.
//
// NB: la formulazione legacy shortestPath((a)-[:PLAYED_FOR*..12]-(b)) NON
// vincola la stagione fra archi consecutivi e da' risposte diverse dal SQL
// (es. Ibrahimovic -> Neuer: 2 hop invece di 3). Vedere il report, sez. 10.
// Parametri: $player_a, $player_b

MATCH (a:Player {name: $player_a}), (b:Player {name: $player_b})
MATCH path = SHORTEST 1 (a)
  ((x:Player)-[r1:PLAYED_FOR]->(:Team)<-[r2:PLAYED_FOR]-(y:Player) WHERE r1.season = r2.season){1,6}
  (b)
RETURN length(path) / 2 AS shortest_path_hops;
