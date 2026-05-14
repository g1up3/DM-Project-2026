# ETL — guida operativa

Pipeline completa per estrarre il dataset European Soccer dal file SQLite e
caricarlo sia in PostgreSQL sia in Neo4j seguendo gli schemi definiti in
`schema/`.

## Struttura

```
etl/
  sqlite_to_csv.py     # 1. dump tabelle SQLite -> CSV "grezzi" (opzionale)
  explore_dataset.py   # 2. esplorazione e report Markdown
  transform.py         # 3. pulizia, parsing XML, esplosione di Match
  load_postgres.py     # 4a. carico Postgres
  load_neo4j.py        # 4b. carico Neo4j
  requirements.txt
  README.md            # (questo file)
```

## Setup Python

```bash
cd etl
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Pipeline (ordine consigliato)

1. **Trasformazione**: produce i CSV puliti in `clean/`.
   ```bash
   python3 transform.py
   ```
2. **Carico Postgres** (vedi sezione sotto per l'installazione):
   ```bash
   python3 load_postgres.py
   ```
3. **Carico Neo4j** (vedi sezione sotto):
   ```bash
   python3 load_neo4j.py
   ```

## PostgreSQL — installazione e setup

### Installazione su macOS

Modo più semplice (Homebrew):
```bash
brew install postgresql@16
brew services start postgresql@16
```

### Creazione del DB e dell'utente

```bash
createdb soccer_db
# se serve un utente dedicato:
psql -d soccer_db -c "CREATE USER soccer_user WITH PASSWORD 'soccer';"
psql -d soccer_db -c "GRANT ALL ON DATABASE soccer_db TO soccer_user;"
```

### Configurazione delle variabili d'ambiente

Crea `etl/.env` (non committare in git):
```
PGHOST=localhost
PGPORT=5432
PGUSER=postgres
PGPASSWORD=postgres
PGDATABASE=soccer_db
```

Lo script applica `schema/postgres_schema.sql` (che include `DROP SCHEMA IF EXISTS`)
e poi carica i CSV via `COPY`.

## Neo4j — installazione e setup

### Opzione A: Neo4j Desktop (più facile)

1. Scaricare Neo4j Desktop da neo4j.com.
2. Creare un nuovo DBMS locale (versione 5.x).
3. Avviarlo e annotare URI / utente / password.
4. Aprire il pulsante **Open folder → Import** del DBMS: copiare lì i file di
   `clean/` (oppure usare la variabile `NEO4J_IMPORT_DIR` come sotto).

### Opzione B: Docker

```bash
docker run --name neo4j-soccer \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  -v $(pwd)/clean:/var/lib/neo4j/import:ro \
  -d neo4j:5
```

### Configurazione delle variabili d'ambiente

Aggiungi a `etl/.env`:
```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j
NEO4J_IMPORT_DIR=/percorso/alla/cartella/import
```

Per Neo4j Desktop, `NEO4J_IMPORT_DIR` è la cartella `import/` che si apre dal
pulsante "Open folder". Per Docker, lo script può essere eseguito senza
copiare i file (sono già montati nel volume).

## Verifica post-load

PostgreSQL:
```sql
SELECT COUNT(*) FROM soccer.match;          -- atteso ~25979
SELECT COUNT(*) FROM soccer.match_lineup;   -- atteso ~542281
SELECT COUNT(*) FROM soccer.match_event;    -- atteso ~917815
```

Neo4j:
```cypher
MATCH (n) RETURN labels(n)[0] AS l, count(*) ORDER BY count(*) DESC;
MATCH ()-[r]->() RETURN type(r) AS r, count(*) ORDER BY count(*) DESC;
```

## Troubleshooting

- **psycopg2 errore di connessione**: verifica che Postgres sia in esecuzione
  con `pg_isready`. Su Mac con Homebrew: `brew services list`.
- **Neo4j: file:/// non leggibile**: in `neo4j.conf` impostare
  `dbms.security.allow_csv_import_from_file_urls=true` e mettere i CSV nella
  cartella `import/` del DBMS.
- **Out of memory durante LINEUP_OF**: usare la versione APOC (`USE_APOC=true`)
  che fa il commit a batch di 5000 righe.
