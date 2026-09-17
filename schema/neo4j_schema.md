# Schema Neo4j (graph model)

Modello a grafo equivalente allo schema concettuale (`schema/conceptual_er.md`),
da contrapporre allo schema relazionale di PostgreSQL nel confronto sperimentale
del progetto.

## Filosofia di modellazione

In Neo4j conviene **esplicitare come relazioni** ciò che in SQL sono colonne FK
"interne" a tabelle. Questo rende le query di tipo *graph traversal* (vicinato,
shortest path, comunità) molto più naturali ed efficienti.

Convenzioni:
- nodi in **PascalCase** (`Player`, `Match`),
- relazioni in **MAIUSCOLO_SNAKE_CASE** (`PLAYS_IN`, `LINEUP_OF`, `SCORED_IN`),
- proprietà in `camelCase`.

## Nodi

| Label | Proprietà | Note |
|---|---|---|
| `Country` | `countryId`, `name` | |
| `League`  | `leagueId`, `name` | |
| `Team`    | `teamApiId`, `teamFifaApiId`, `name`, `shortName` | |
| `Player`  | `playerApiId`, `playerFifaApiId`, `name`, `birthday`, `height`, `weight` | |
| `Match`   | `matchApiId`, `season`, `stage`, `date`, `homeGoals`, `awayGoals` | |
| `PlayerStats` | `playerApiId`, `date`, ...attributi FIFA | snapshot temporale |
| `TeamStats`   | `teamApiId`, `date`, ...attributi tattici | snapshot temporale |

## Relazioni

| Pattern | Proprietà | Significato |
|---|---|---|
| `(:League)-[:IN_COUNTRY]->(:Country)` | — | la lega è in quella nazione |
| `(:Match)-[:IN_LEAGUE]->(:League)` | — | la partita appartiene a quella lega |
| `(:Match)-[:HOME]->(:Team)` | — | squadra di casa |
| `(:Match)-[:AWAY]->(:Team)` | — | squadra in trasferta |
| `(:Player)-[:LINEUP_OF]->(:Match)` | `side` ('home'/'away'), `positionIdx` (1..11), `posX`, `posY` | giocatore in formazione |
| `(:Player)-[:SCORED_IN]->(:Match)` | `minute`, `subtype`, `goalType`, `teamApiId` | gol segnato (player1 dell'evento `goal`) |
| `(:Player)-[:ASSISTED_IN]->(:Match)` | `minute`, `relatedGoalId` | assist (player2 dell'evento `goal`) |
| `(:Player)-[:RECEIVED_CARD_IN]->(:Match)` | `minute`, `cardType` ('y'/'r'), `subtype` | cartellino |
| `(:Player)-[:COMMITTED_FOUL_IN]->(:Match)` | `minute`, `victimPlayerId` | fallo commesso |
| `(:Player)-[:PLAYED_FOR]->(:Team)` | `season`, `appearances` | derivata: aggrega LINEUP_OF per (player, team, season) |
| `(:PlayerStats)-[:STATS_OF]->(:Player)` | — | snapshot collegato al giocatore |
| `(:TeamStats)-[:STATS_OF]->(:Team)` | — | snapshot collegato alla squadra |

## Mappatura dal modello concettuale

Il modello concettuale (`conceptual_er.md`) ha un'entità `MatchEvent` con
relazioni *generiche* `OF_MATCH`, `BY_TEAM`, `BY_PLAYER` (player1) e
`WITH_PLAYER` (player2). Lo schema a grafo **non la implementa alla lettera**:
l'evento non è un nodo ma viene *specializzato per tipo* in relazioni
dirette giocatore→partita, perché è così che le query lo attraversano:

| Concettuale | Grafo | Note |
|---|---|---|
| `MatchEvent(type='goal') BY_PLAYER Player` | `(Player)-[:SCORED_IN]->(Match)` | `OF_MATCH` diventa il nodo di arrivo; `BY_TEAM` la proprietà `teamApiId` |
| `MatchEvent(type='goal') WITH_PLAYER Player` | `(Player)-[:ASSISTED_IN]->(Match)` | riaccoppiata a `SCORED_IN` via `sourceEventId` (Q05) |
| `MatchEvent(type='card') BY_PLAYER Player` | `(Player)-[:RECEIVED_CARD_IN]->(Match)` | `cardType`, `minute` come proprietà |
| `MatchEvent(type='foulcommit') BY_PLAYER / WITH_PLAYER` | `(Player)-[:COMMITTED_FOUL_IN {victimPlayerId}]->(Match)` | il "player2" (vittima) è una proprietà |
| `MatchEvent(type in shoton, shotoff, cross, corner, possession)` | **non caricati** | nessuna delle 12 query li usa (scelta di scope) |

Trade-off della specializzazione: i traversal per tipo di evento sono
immediati (Q01, Q06: nessun filtro su `event_type`), ma un evento *ternario*
come il gol con assist viene spezzato in due archi che vanno riaccoppiati per
valore (`sourceEventId`): la modellazione alternativa con un nodo
`(:MatchEvent)` collegato a marcatore, assistman e partita renderebbe Q05 una
pura navigazione di vicinato, al prezzo di un hop in più in ogni query sui
gol. Analogamente, `season` come proprietà di `PLAYED_FOR` (invece di un nodo
`TeamSeason`) rende il vincolo di stagione un predicato da ricordare in ogni
traversal (vedere il report, sez. 10.2).

## Vincoli e indici (Cypher)

```cypher
// Vincoli di unicità (servono come "PK")
CREATE CONSTRAINT country_id_unique IF NOT EXISTS
    FOR (c:Country) REQUIRE c.countryId IS UNIQUE;

CREATE CONSTRAINT league_id_unique IF NOT EXISTS
    FOR (l:League) REQUIRE l.leagueId IS UNIQUE;

CREATE CONSTRAINT team_id_unique IF NOT EXISTS
    FOR (t:Team) REQUIRE t.teamApiId IS UNIQUE;

CREATE CONSTRAINT player_id_unique IF NOT EXISTS
    FOR (p:Player) REQUIRE p.playerApiId IS UNIQUE;

CREATE CONSTRAINT match_id_unique IF NOT EXISTS
    FOR (m:Match) REQUIRE m.matchApiId IS UNIQUE;

CREATE CONSTRAINT player_stats_unique IF NOT EXISTS
    FOR (s:PlayerStats) REQUIRE (s.playerApiId, s.date) IS UNIQUE;

CREATE CONSTRAINT team_stats_unique IF NOT EXISTS
    FOR (s:TeamStats) REQUIRE (s.teamApiId, s.date) IS UNIQUE;

// Indici secondari su attributi cercati spesso
CREATE INDEX player_name_idx     IF NOT EXISTS FOR (p:Player) ON (p.name);
CREATE INDEX team_name_idx       IF NOT EXISTS FOR (t:Team)   ON (t.name);
CREATE INDEX match_season_idx    IF NOT EXISTS FOR (m:Match)  ON (m.season);
CREATE INDEX match_date_idx      IF NOT EXISTS FOR (m:Match)  ON (m.date);
```

## Esempi di query "graph-native"

Query interessanti pensate per mettere in evidenza i **vantaggi del modello a
grafo** rispetto al SQL equivalente. Saranno le query candidate per il
benchmark del progetto.

### 1. Compagni di squadra di un giocatore in una stagione

```cypher
MATCH (p:Player {name: 'Lionel Messi'})-[:LINEUP_OF]->(m:Match)
      <-[:LINEUP_OF]-(c:Player)
WHERE m.season = '2014/2015' AND c.playerApiId <> p.playerApiId
RETURN c.name, count(*) AS shared_matches
ORDER BY shared_matches DESC
LIMIT 20;
```

### 2. Giocatori connessi a 2-hop (compagni dei compagni)

```cypher
MATCH (p:Player {name: 'Cristiano Ronaldo'})-[:PLAYED_FOR]->(t1:Team)
      <-[:PLAYED_FOR]-(c1:Player)-[:PLAYED_FOR]->(t2:Team)
      <-[:PLAYED_FOR]-(c2:Player)
WHERE c2 <> p
RETURN DISTINCT c2.name LIMIT 50;
```

### 3. Shortest path tra due giocatori

```cypher
MATCH p = shortestPath(
  (a:Player {name: 'Lionel Messi'})-[:PLAYED_FOR*..6]-(b:Player {name: 'Andrea Pirlo'})
)
RETURN p;
```

### 4. Chi ha segnato di più contro una squadra specifica

```cypher
MATCH (p:Player)-[:SCORED_IN]->(m:Match)-[:HOME|AWAY]->(t:Team {name: 'Real Madrid CF'})
RETURN p.name, count(*) AS goals_vs_real
ORDER BY goals_vs_real DESC
LIMIT 10;
```

### 5. Top assistman di una stagione

```cypher
MATCH (p:Player)-[a:ASSISTED_IN]->(m:Match {season: '2015/2016'})
RETURN p.name, count(a) AS assists
ORDER BY assists DESC
LIMIT 10;
```

## Cosa NON viene caricato in Neo4j (scelta di scope)

Lo schema dichiara i nodi `PlayerStats` e `TeamStats` per completezza
concettuale, ma il loader `etl/load_neo4j.py` **non li importa**:

- nessuna delle 12 query del benchmark li interroga (le query si concentrano
  su matches, lineup, eventi e relazioni player-team),
- l'import aumenterebbe il tempo di caricamento di Neo4j di alcuni minuti
  (~184k nodi `PlayerStats` con ~40 attributi ciascuno + 1.5k `TeamStats`)
  senza alcun beneficio sperimentale,
- Postgres li carica per coerenza con lo schema SQL completo, ma il dato resta
  inutilizzato in entrambi i sistemi durante il benchmark.

In una versione production-ready dello schema, lo stesso loader li
caricherebbe come nodi `:PlayerStats {playerApiId, date, ...attributi}` con
relazione `:STATS_OF` verso il `:Player` corrispondente. Lo schema concettuale
in questo file riflette gia' quel design "completo".

## Note operative per il caricamento

- Caricare prima i nodi anagrafici (`Country`, `League`, `Team`, `Player`).
- Creare i vincoli **prima** di caricare le relazioni (i vincoli creano
  automaticamente indici di lookup, e senza di essi `MATCH ... MERGE` esplode
  in tempi di caricamento).
- Importare i `Match` (dimensione contenuta: ~26k nodi).
- Esplodere i `match_lineup` come `LINEUP_OF` (~570k relazioni).
- Parsare gli XML una volta sola (in Python, durante l'ETL) e generare CSV
  pronti per `LOAD CSV` (un CSV per ciascun tipo di evento).
- La relazione derivata `:PLAYED_FOR` si calcola con una query Cypher di
  aggregazione **dopo** aver caricato `LINEUP_OF`:

```cypher
MATCH (p:Player)-[:LINEUP_OF]->(m:Match)<-[:HOME|AWAY]-(t:Team)
WITH p, t, m.season AS season, count(*) AS apps
MERGE (p)-[r:PLAYED_FOR {season: season}]->(t)
SET r.appearances = apps;
```
