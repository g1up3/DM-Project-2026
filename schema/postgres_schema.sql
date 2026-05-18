-- ============================================================================
--  Schema relazionale PostgreSQL — European Soccer Database
--  Progetto Data Management 2025/26 — D'Angelica & Leone
--
--  Derivato dallo schema concettuale (schema/conceptual_er.md).
--  Lo schema originale del file SQLite e' stato ristrutturato:
--   - Match e' stato denormalizzato dalle 115 colonne originali in piu' tabelle
--     coerenti (match, match_lineup, match_event).
--   - Le colonne XML grezze sono sostituite da match_event (una riga per evento).
--   - Le 20 colonne di quote scommesse non vengono importate.
--   - Le date sono tipizzate come DATE / TIMESTAMP, non TEXT.
-- ============================================================================

-- Pulizia (utile in dev). Commentare in produzione.
DROP SCHEMA IF EXISTS soccer CASCADE;
CREATE SCHEMA soccer;
SET search_path TO soccer;

-- ----------------------------------------------------------------------------
--  Anagrafiche
-- ----------------------------------------------------------------------------

CREATE TABLE country (
    country_id   INTEGER     PRIMARY KEY,
    name         VARCHAR(80) NOT NULL UNIQUE
);

CREATE TABLE league (
    league_id    INTEGER     PRIMARY KEY,
    country_id   INTEGER     NOT NULL REFERENCES country(country_id),
    name         VARCHAR(80) NOT NULL UNIQUE
);

CREATE INDEX ix_league_country ON league(country_id);

CREATE TABLE team (
    team_api_id        INTEGER     PRIMARY KEY,
    team_fifa_api_id   INTEGER,                       -- nullable: 11 squadre lo hanno NULL
    team_long_name     VARCHAR(120) NOT NULL,
    team_short_name    CHAR(3)
);

CREATE INDEX ix_team_long_name ON team(team_long_name);

CREATE TABLE player (
    player_api_id      INTEGER     PRIMARY KEY,
    player_fifa_api_id INTEGER,
    player_name        VARCHAR(120) NOT NULL,
    birthday           DATE,
    height             NUMERIC(5,2),                  -- centimetri
    weight             INTEGER                        -- libbre (come da sorgente)
);

CREATE INDEX ix_player_name ON player(player_name);

-- ----------------------------------------------------------------------------
--  Partite e formazioni
-- ----------------------------------------------------------------------------

CREATE TABLE match (
    match_api_id       INTEGER     PRIMARY KEY,
    league_id          INTEGER     NOT NULL REFERENCES league(league_id),
    season             VARCHAR(9)  NOT NULL,          -- es. '2015/2016'
    stage              SMALLINT,
    match_date         DATE        NOT NULL,
    home_team_api_id   INTEGER     NOT NULL REFERENCES team(team_api_id),
    away_team_api_id   INTEGER     NOT NULL REFERENCES team(team_api_id),
    home_team_goal     SMALLINT    NOT NULL,
    away_team_goal     SMALLINT    NOT NULL,
    CHECK (home_team_api_id <> away_team_api_id)
);

CREATE INDEX ix_match_season       ON match(season);
CREATE INDEX ix_match_league       ON match(league_id);
CREATE INDEX ix_match_date         ON match(match_date);
CREATE INDEX ix_match_home_team    ON match(home_team_api_id);
CREATE INDEX ix_match_away_team    ON match(away_team_api_id);

-- 22 righe per partita (11 home + 11 away). Sostituisce le 44 colonne
-- home_player_1..11 / away_player_1..11 / X / Y del file SQLite originale.
CREATE TABLE match_lineup (
    match_api_id       INTEGER     NOT NULL REFERENCES match(match_api_id) ON DELETE CASCADE,
    player_api_id      INTEGER     NOT NULL REFERENCES player(player_api_id),
    side               CHAR(4)     NOT NULL CHECK (side IN ('home', 'away')),
    position_idx       SMALLINT    NOT NULL CHECK (position_idx BETWEEN 1 AND 11),
    pos_x              SMALLINT,                      -- coordinata X (formazione)
    pos_y              SMALLINT,                      -- coordinata Y (formazione)
    PRIMARY KEY (match_api_id, side, position_idx)
);

CREATE INDEX ix_lineup_player ON match_lineup(player_api_id);
CREATE INDEX ix_lineup_match  ON match_lineup(match_api_id);

-- ----------------------------------------------------------------------------
--  Eventi della partita (parsing degli XML del sorgente)
-- ----------------------------------------------------------------------------

CREATE TABLE match_event (
    event_id           BIGSERIAL   PRIMARY KEY,       -- chiave sintetica
    match_api_id       INTEGER     NOT NULL REFERENCES match(match_api_id) ON DELETE CASCADE,
    event_type         VARCHAR(20) NOT NULL,          -- goal, shoton, shotoff, foulcommit, card, cross, corner, possession
    subtype            VARCHAR(40),                   -- header, distance, blocked_shot, ...
    elapsed_minute     SMALLINT,                      -- minuto della partita
    team_api_id        INTEGER     REFERENCES team(team_api_id),
    player1_id         INTEGER     REFERENCES player(player_api_id),
    player2_id         INTEGER     REFERENCES player(player_api_id),
    card_type          VARCHAR(2),                    -- 'y', 'r', 'y2' (doppio giallo) per type='card'; NULL altrimenti
    goal_type          VARCHAR(20),                   -- 'n', 'p' (rigore), 'o' (autogol), ...
    sort_order         SMALLINT,                      -- ordine all'interno della partita
    source_event_id    INTEGER,                       -- id originale presente nell'XML
    CHECK (event_type IN
        ('goal','shoton','shotoff','foulcommit','card','cross','corner','possession'))
);

CREATE INDEX ix_event_match      ON match_event(match_api_id);
CREATE INDEX ix_event_type       ON match_event(event_type);
CREATE INDEX ix_event_player1    ON match_event(player1_id);
CREATE INDEX ix_event_player2    ON match_event(player2_id);
CREATE INDEX ix_event_team       ON match_event(team_api_id);

-- ----------------------------------------------------------------------------
--  Statistiche storiche (snapshot temporali)
-- ----------------------------------------------------------------------------

CREATE TABLE player_stats (
    player_api_id           INTEGER     NOT NULL REFERENCES player(player_api_id) ON DELETE CASCADE,
    snapshot_date           DATE        NOT NULL,
    player_fifa_api_id      INTEGER,
    overall_rating          SMALLINT,
    potential               SMALLINT,
    preferred_foot          VARCHAR(8),
    attacking_work_rate     VARCHAR(16),
    defensive_work_rate     VARCHAR(16),
    crossing                SMALLINT,
    finishing               SMALLINT,
    heading_accuracy        SMALLINT,
    short_passing           SMALLINT,
    volleys                 SMALLINT,
    dribbling               SMALLINT,
    curve                   SMALLINT,
    free_kick_accuracy      SMALLINT,
    long_passing            SMALLINT,
    ball_control            SMALLINT,
    acceleration            SMALLINT,
    sprint_speed            SMALLINT,
    agility                 SMALLINT,
    reactions               SMALLINT,
    balance                 SMALLINT,
    shot_power              SMALLINT,
    jumping                 SMALLINT,
    stamina                 SMALLINT,
    strength                SMALLINT,
    long_shots              SMALLINT,
    aggression              SMALLINT,
    interceptions           SMALLINT,
    positioning             SMALLINT,
    vision                  SMALLINT,
    penalties               SMALLINT,
    marking                 SMALLINT,
    standing_tackle         SMALLINT,
    sliding_tackle          SMALLINT,
    gk_diving               SMALLINT,
    gk_handling             SMALLINT,
    gk_kicking              SMALLINT,
    gk_positioning          SMALLINT,
    gk_reflexes             SMALLINT,
    PRIMARY KEY (player_api_id, snapshot_date)
);

CREATE INDEX ix_player_stats_date ON player_stats(snapshot_date);

CREATE TABLE team_stats (
    team_api_id                 INTEGER     NOT NULL REFERENCES team(team_api_id) ON DELETE CASCADE,
    snapshot_date               DATE        NOT NULL,
    team_fifa_api_id            INTEGER,
    buildUpPlaySpeed            SMALLINT,
    buildUpPlaySpeedClass       VARCHAR(20),
    buildUpPlayDribbling        SMALLINT,             -- 66% NULL nei dati: ammesso
    buildUpPlayDribblingClass   VARCHAR(20),
    buildUpPlayPassing          SMALLINT,
    buildUpPlayPassingClass     VARCHAR(20),
    buildUpPlayPositioningClass VARCHAR(20),
    chanceCreationPassing       SMALLINT,
    chanceCreationPassingClass  VARCHAR(20),
    chanceCreationCrossing      SMALLINT,
    chanceCreationCrossingClass VARCHAR(20),
    chanceCreationShooting      SMALLINT,
    chanceCreationShootingClass VARCHAR(20),
    chanceCreationPositioningClass VARCHAR(20),
    defencePressure             SMALLINT,
    defencePressureClass        VARCHAR(20),
    defenceAggression           SMALLINT,
    defenceAggressionClass      VARCHAR(20),
    defenceTeamWidth            SMALLINT,
    defenceTeamWidthClass       VARCHAR(20),
    defenceDefenderLineClass    VARCHAR(20),
    PRIMARY KEY (team_api_id, snapshot_date)
);

CREATE INDEX ix_team_stats_date ON team_stats(snapshot_date);

-- ----------------------------------------------------------------------------
--  Viste utili per la presentazione e le query OLAP
-- ----------------------------------------------------------------------------

-- Classifica marcatori per stagione
CREATE OR REPLACE VIEW v_top_scorers_by_season AS
SELECT
    m.season,
    p.player_api_id,
    p.player_name,
    COUNT(*) AS goals
FROM match_event e
JOIN match  m ON m.match_api_id = e.match_api_id
JOIN player p ON p.player_api_id = e.player1_id
WHERE e.event_type = 'goal'
GROUP BY m.season, p.player_api_id, p.player_name;

-- Statistiche di team aggregate per stagione (tre punti per vittoria)
CREATE OR REPLACE VIEW v_standings_by_season AS
WITH results AS (
    SELECT season, home_team_api_id AS team_id,
           CASE WHEN home_team_goal > away_team_goal THEN 3
                WHEN home_team_goal = away_team_goal THEN 1 ELSE 0 END AS pts,
           home_team_goal AS gf, away_team_goal AS ga
    FROM match
    UNION ALL
    SELECT season, away_team_api_id AS team_id,
           CASE WHEN away_team_goal > home_team_goal THEN 3
                WHEN home_team_goal = away_team_goal THEN 1 ELSE 0 END AS pts,
           away_team_goal AS gf, home_team_goal AS ga
    FROM match
)
SELECT r.season,
       t.team_api_id,
       t.team_long_name,
       SUM(r.pts) AS points,
       SUM(r.gf) AS goals_for,
       SUM(r.ga) AS goals_against
FROM results r
JOIN team t ON t.team_api_id = r.team_id
GROUP BY r.season, t.team_api_id, t.team_long_name;

-- ----------------------------------------------------------------------------
--  Materialized view: played_for (player, team, season)
--
--  Replica esatta della relazione derivata :PLAYED_FOR in Neo4j (calcolata
--  in fase di load via aggregazione di LINEUP_OF — vedere load_neo4j.py:218).
--
--  Senza questa MV il benchmark sarebbe asimmetrico: Q08/Q09/Q10 in Cypher
--  attraversano direttamente PLAYED_FOR (gia' materializzato), mentre in
--  SQL dovrebbero ricostruirlo on-the-fly via CTE in ogni esecuzione.
--  Materializzare in Postgres mette i due sistemi sullo stesso piano in
--  termini di "cosa serve precomputare per supportare queste query".
-- ----------------------------------------------------------------------------

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_played_for AS
SELECT DISTINCT
    l.player_api_id,
    CASE WHEN l.side = 'home' THEN m.home_team_api_id
                              ELSE m.away_team_api_id END AS team_api_id,
    m.season
FROM match_lineup l
JOIN match m ON m.match_api_id = l.match_api_id;

-- Indici per supportare i pattern di accesso piu' frequenti delle query Q08/Q09/Q10:
--   - lookup di team/season per un giocatore noto (Q09/Q10 BFS step iniziale)
--   - lookup di tutti i giocatori che hanno giocato in un (team, season)
CREATE INDEX IF NOT EXISTS ix_mv_played_for_player
    ON mv_played_for(player_api_id);
CREATE INDEX IF NOT EXISTS ix_mv_played_for_team_season
    ON mv_played_for(team_api_id, season);
