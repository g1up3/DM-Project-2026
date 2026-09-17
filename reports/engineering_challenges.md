# Engineering challenges encountered and solved

This document collects the three non-obvious problems we ran into while
building the benchmark, and how we solved them. Each one is a story worth
telling: it shows the difference between "running queries on a clean dataset"
and actually building a robust pipeline on real, messy data.

---

## Challenge 1 — 5,632 orphan player references in match events

### Symptom

When we first tried to load `match_event.csv` into PostgreSQL, the `COPY`
command failed with a foreign-key violation. Some `player1_id` and
`player2_id` values in the parsed events did not match any `player_api_id`
in our `player` table.

### Investigation

We profiled the orphans across every reference in the dataset:

```
Match.home_team_api_id -> Team       :     0 / 25,979
Match.away_team_api_id -> Team       :     0 / 25,979
match_lineup -> Player               :     0 / 542,281
match_event.player1_id -> Player     : 4,632 / 857,315  (0.54%)
match_event.player2_id -> Player     : 1,021 / 207,966  (0.49%)
match_event.team_api_id -> Team      :     0 / 881,841
```

So the only orphans were in `match_event`, on the `player1_id` and
`player2_id` columns. The XML events parsed from the original Match table
reference player IDs that no longer exist in the Player roster — most likely
older transfers or short-term loanees that the source dataset chose not to
track.

### Solution

In `transform.py`, after parsing the XML events but before writing the CSV,
we built the set of valid `player_api_id` values from the Player table and
**nullified any orphan reference** in `match_event`:

```python
for col in ("player1_id", "player2_id"):
    mask_orphan = out[col].notna() & ~out[col].isin(valid_player_ids)
    if mask_orphan.any():
        print(f"[nullify] {col}: {mask_orphan.sum():,} orphan refs -> NULL")
        out.loc[mask_orphan, col] = pd.NA
```

This preserves **every event** (we lose no data about *what happened* in the
match) while making the schema referentially clean. The cost is the loss of
*who* did it for those 5k events, which is an acceptable trade given the
total volume (917k events).

### Result

After the fix (the denominators are the events that *have* a player1 / player2
reference — 852,683 and 206,945 respectively — not the 917,815 total events;
the 4,632 + 1,021 nullified references are no longer counted):
```
match_event -> Player (player1)  : 0 orphans / 852,683
match_event -> Player (player2)  : 0 orphans /  206,945
```

100% referential integrity. The COPY command now succeeds and the foreign
keys we declared in the DDL are real, enforced constraints.

---

## Challenge 2 — Postgres rejects pandas integer-with-NaN columns

### Symptom

Even after fixing the orphans, the `COPY` of `team` failed with:

```
psycopg2.errors.InvalidTextRepresentation: invalid input syntax for type
integer: "673.0"
CONTEXT: COPY team, line 2, column team_fifa_api_id: "673.0"
```

### Cause

`team_fifa_api_id` is `INTEGER NULL` in the schema. Eleven of the 299 teams
have NULL for this field. When pandas reads a column with mixed integer +
NaN values, it silently casts the entire column to `float64`. The CSV then
contains values like `673.0` instead of `673`, and Postgres refuses to
coerce a float string to INTEGER.

### Solution

We added a defensive cast in `transform.py` that detects integer-like float
columns and converts them to pandas' nullable `Int64` type before writing
the CSV. The check is automatic so it covers every table, every column:

```python
def _coerce_int_columns(df):
    for c in df.columns:
        if df[c].dtype == "float64":
            non_null = df[c].dropna()
            if (non_null == non_null.astype("int64")).all():
                df[c] = df[c].astype("Int64")
    return df
```

The size of `player_stats.csv` dropped from 37.7 MB to 25.5 MB after this
fix, just from removing all the fake ".0" suffixes.

---

## Challenge 3 — Wrong card type in the schema

### Symptom

After the integer fix, the `COPY` of `match_event` failed again:

```
psycopg2.errors.StringDataRightTruncation:
value too long for type character(1)
CONTEXT: COPY match_event, line 2726, column card_type: "y2"
```

### Cause

We had declared `card_type CHAR(1)` thinking yellow/red cards are encoded
as `'y'` or `'r'`. The actual encoding turned out to include `'y2'` for
*second yellow card* (which counts as a red, but is logged separately).

### Solution

Widened the column to `VARCHAR(2)` in the DDL.

This is the kind of bug that only surfaces when you actually load all the
data, not when you sample it: the second-yellow code is rare relative to
plain yellow/red.

---

## Lesson

Three real-world problems, three local fixes. Each one is small in isolation
but together they are the difference between a "demo on clean data" and a
**reproducible pipeline that ingests 1M+ rows and survives the load**.

The friction is itself part of the project. Knowing what to expect from this
kind of dataset is part of being a Data Management practitioner.
