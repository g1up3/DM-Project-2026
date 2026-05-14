# Esplorazione dataset — European Soccer Database

Report generato automaticamente da `etl/explore_dataset.py`.


## 1. Tabelle e dimensioni


| tabella           |   righe |   colonne |
|:------------------|--------:|----------:|
| Country           |      11 |         2 |
| League            |      11 |         3 |
| Match             |   25979 |       115 |
| Player            |   11060 |         7 |
| Player_Attributes |  183978 |        42 |
| Team              |     299 |         5 |
| Team_Attributes   |    1458 |        25 |


## 2. Schema di ogni tabella



### Country


| colonna   | tipo    |   NOT NULL |   PK |
|:----------|:--------|-----------:|-----:|
| id        | INTEGER |          0 |    1 |
| name      | TEXT    |          0 |    0 |


### League


| colonna    | tipo    |   NOT NULL |   PK |
|:-----------|:--------|-----------:|-----:|
| id         | INTEGER |          0 |    1 |
| country_id | INTEGER |          0 |    0 |
| name       | TEXT    |          0 |    0 |


### Match


| colonna          | tipo    |   NOT NULL |   PK |
|:-----------------|:--------|-----------:|-----:|
| id               | INTEGER |          0 |    1 |
| country_id       | INTEGER |          0 |    0 |
| league_id        | INTEGER |          0 |    0 |
| season           | TEXT    |          0 |    0 |
| stage            | INTEGER |          0 |    0 |
| date             | TEXT    |          0 |    0 |
| match_api_id     | INTEGER |          0 |    0 |
| home_team_api_id | INTEGER |          0 |    0 |
| away_team_api_id | INTEGER |          0 |    0 |
| home_team_goal   | INTEGER |          0 |    0 |
| away_team_goal   | INTEGER |          0 |    0 |
| home_player_X1   | INTEGER |          0 |    0 |
| home_player_X2   | INTEGER |          0 |    0 |
| home_player_X3   | INTEGER |          0 |    0 |
| home_player_X4   | INTEGER |          0 |    0 |
| home_player_X5   | INTEGER |          0 |    0 |
| home_player_X6   | INTEGER |          0 |    0 |
| home_player_X7   | INTEGER |          0 |    0 |
| home_player_X8   | INTEGER |          0 |    0 |
| home_player_X9   | INTEGER |          0 |    0 |
| home_player_X10  | INTEGER |          0 |    0 |
| home_player_X11  | INTEGER |          0 |    0 |
| away_player_X1   | INTEGER |          0 |    0 |
| away_player_X2   | INTEGER |          0 |    0 |
| away_player_X3   | INTEGER |          0 |    0 |
| away_player_X4   | INTEGER |          0 |    0 |
| away_player_X5   | INTEGER |          0 |    0 |
| away_player_X6   | INTEGER |          0 |    0 |
| away_player_X7   | INTEGER |          0 |    0 |
| away_player_X8   | INTEGER |          0 |    0 |
| away_player_X9   | INTEGER |          0 |    0 |
| away_player_X10  | INTEGER |          0 |    0 |
| away_player_X11  | INTEGER |          0 |    0 |
| home_player_Y1   | INTEGER |          0 |    0 |
| home_player_Y2   | INTEGER |          0 |    0 |
| home_player_Y3   | INTEGER |          0 |    0 |
| home_player_Y4   | INTEGER |          0 |    0 |
| home_player_Y5   | INTEGER |          0 |    0 |
| home_player_Y6   | INTEGER |          0 |    0 |
| home_player_Y7   | INTEGER |          0 |    0 |
| home_player_Y8   | INTEGER |          0 |    0 |
| home_player_Y9   | INTEGER |          0 |    0 |
| home_player_Y10  | INTEGER |          0 |    0 |
| home_player_Y11  | INTEGER |          0 |    0 |
| away_player_Y1   | INTEGER |          0 |    0 |
| away_player_Y2   | INTEGER |          0 |    0 |
| away_player_Y3   | INTEGER |          0 |    0 |
| away_player_Y4   | INTEGER |          0 |    0 |
| away_player_Y5   | INTEGER |          0 |    0 |
| away_player_Y6   | INTEGER |          0 |    0 |
| away_player_Y7   | INTEGER |          0 |    0 |
| away_player_Y8   | INTEGER |          0 |    0 |
| away_player_Y9   | INTEGER |          0 |    0 |
| away_player_Y10  | INTEGER |          0 |    0 |
| away_player_Y11  | INTEGER |          0 |    0 |
| home_player_1    | INTEGER |          0 |    0 |
| home_player_2    | INTEGER |          0 |    0 |
| home_player_3    | INTEGER |          0 |    0 |
| home_player_4    | INTEGER |          0 |    0 |
| home_player_5    | INTEGER |          0 |    0 |
| home_player_6    | INTEGER |          0 |    0 |
| home_player_7    | INTEGER |          0 |    0 |
| home_player_8    | INTEGER |          0 |    0 |
| home_player_9    | INTEGER |          0 |    0 |
| home_player_10   | INTEGER |          0 |    0 |
| home_player_11   | INTEGER |          0 |    0 |
| away_player_1    | INTEGER |          0 |    0 |
| away_player_2    | INTEGER |          0 |    0 |
| away_player_3    | INTEGER |          0 |    0 |
| away_player_4    | INTEGER |          0 |    0 |
| away_player_5    | INTEGER |          0 |    0 |
| away_player_6    | INTEGER |          0 |    0 |
| away_player_7    | INTEGER |          0 |    0 |
| away_player_8    | INTEGER |          0 |    0 |
| away_player_9    | INTEGER |          0 |    0 |
| away_player_10   | INTEGER |          0 |    0 |
| away_player_11   | INTEGER |          0 |    0 |
| goal             | TEXT    |          0 |    0 |
| shoton           | TEXT    |          0 |    0 |
| shotoff          | TEXT    |          0 |    0 |
| foulcommit       | TEXT    |          0 |    0 |
| card             | TEXT    |          0 |    0 |
| cross            | TEXT    |          0 |    0 |
| corner           | TEXT    |          0 |    0 |
| possession       | TEXT    |          0 |    0 |
| B365H            | NUMERIC |          0 |    0 |
| B365D            | NUMERIC |          0 |    0 |
| B365A            | NUMERIC |          0 |    0 |
| BWH              | NUMERIC |          0 |    0 |
| BWD              | NUMERIC |          0 |    0 |
| BWA              | NUMERIC |          0 |    0 |
| IWH              | NUMERIC |          0 |    0 |
| IWD              | NUMERIC |          0 |    0 |
| IWA              | NUMERIC |          0 |    0 |
| LBH              | NUMERIC |          0 |    0 |
| LBD              | NUMERIC |          0 |    0 |
| LBA              | NUMERIC |          0 |    0 |
| PSH              | NUMERIC |          0 |    0 |
| PSD              | NUMERIC |          0 |    0 |
| PSA              | NUMERIC |          0 |    0 |
| WHH              | NUMERIC |          0 |    0 |
| WHD              | NUMERIC |          0 |    0 |
| WHA              | NUMERIC |          0 |    0 |
| SJH              | NUMERIC |          0 |    0 |
| SJD              | NUMERIC |          0 |    0 |
| SJA              | NUMERIC |          0 |    0 |
| VCH              | NUMERIC |          0 |    0 |
| VCD              | NUMERIC |          0 |    0 |
| VCA              | NUMERIC |          0 |    0 |
| GBH              | NUMERIC |          0 |    0 |
| GBD              | NUMERIC |          0 |    0 |
| GBA              | NUMERIC |          0 |    0 |
| BSH              | NUMERIC |          0 |    0 |
| BSD              | NUMERIC |          0 |    0 |
| BSA              | NUMERIC |          0 |    0 |


### Player


| colonna            | tipo    |   NOT NULL |   PK |
|:-------------------|:--------|-----------:|-----:|
| id                 | INTEGER |          0 |    1 |
| player_api_id      | INTEGER |          0 |    0 |
| player_name        | TEXT    |          0 |    0 |
| player_fifa_api_id | INTEGER |          0 |    0 |
| birthday           | TEXT    |          0 |    0 |
| height             | INTEGER |          0 |    0 |
| weight             | INTEGER |          0 |    0 |


### Player_Attributes


| colonna             | tipo    |   NOT NULL |   PK |
|:--------------------|:--------|-----------:|-----:|
| id                  | INTEGER |          0 |    1 |
| player_fifa_api_id  | INTEGER |          0 |    0 |
| player_api_id       | INTEGER |          0 |    0 |
| date                | TEXT    |          0 |    0 |
| overall_rating      | INTEGER |          0 |    0 |
| potential           | INTEGER |          0 |    0 |
| preferred_foot      | TEXT    |          0 |    0 |
| attacking_work_rate | TEXT    |          0 |    0 |
| defensive_work_rate | TEXT    |          0 |    0 |
| crossing            | INTEGER |          0 |    0 |
| finishing           | INTEGER |          0 |    0 |
| heading_accuracy    | INTEGER |          0 |    0 |
| short_passing       | INTEGER |          0 |    0 |
| volleys             | INTEGER |          0 |    0 |
| dribbling           | INTEGER |          0 |    0 |
| curve               | INTEGER |          0 |    0 |
| free_kick_accuracy  | INTEGER |          0 |    0 |
| long_passing        | INTEGER |          0 |    0 |
| ball_control        | INTEGER |          0 |    0 |
| acceleration        | INTEGER |          0 |    0 |
| sprint_speed        | INTEGER |          0 |    0 |
| agility             | INTEGER |          0 |    0 |
| reactions           | INTEGER |          0 |    0 |
| balance             | INTEGER |          0 |    0 |
| shot_power          | INTEGER |          0 |    0 |
| jumping             | INTEGER |          0 |    0 |
| stamina             | INTEGER |          0 |    0 |
| strength            | INTEGER |          0 |    0 |
| long_shots          | INTEGER |          0 |    0 |
| aggression          | INTEGER |          0 |    0 |
| interceptions       | INTEGER |          0 |    0 |
| positioning         | INTEGER |          0 |    0 |
| vision              | INTEGER |          0 |    0 |
| penalties           | INTEGER |          0 |    0 |
| marking             | INTEGER |          0 |    0 |
| standing_tackle     | INTEGER |          0 |    0 |
| sliding_tackle      | INTEGER |          0 |    0 |
| gk_diving           | INTEGER |          0 |    0 |
| gk_handling         | INTEGER |          0 |    0 |
| gk_kicking          | INTEGER |          0 |    0 |
| gk_positioning      | INTEGER |          0 |    0 |
| gk_reflexes         | INTEGER |          0 |    0 |


### Team


| colonna          | tipo    |   NOT NULL |   PK |
|:-----------------|:--------|-----------:|-----:|
| id               | INTEGER |          0 |    1 |
| team_api_id      | INTEGER |          0 |    0 |
| team_fifa_api_id | INTEGER |          0 |    0 |
| team_long_name   | TEXT    |          0 |    0 |
| team_short_name  | TEXT    |          0 |    0 |


### Team_Attributes


| colonna                        | tipo    |   NOT NULL |   PK |
|:-------------------------------|:--------|-----------:|-----:|
| id                             | INTEGER |          0 |    1 |
| team_fifa_api_id               | INTEGER |          0 |    0 |
| team_api_id                    | INTEGER |          0 |    0 |
| date                           | TEXT    |          0 |    0 |
| buildUpPlaySpeed               | INTEGER |          0 |    0 |
| buildUpPlaySpeedClass          | TEXT    |          0 |    0 |
| buildUpPlayDribbling           | INTEGER |          0 |    0 |
| buildUpPlayDribblingClass      | TEXT    |          0 |    0 |
| buildUpPlayPassing             | INTEGER |          0 |    0 |
| buildUpPlayPassingClass        | TEXT    |          0 |    0 |
| buildUpPlayPositioningClass    | TEXT    |          0 |    0 |
| chanceCreationPassing          | INTEGER |          0 |    0 |
| chanceCreationPassingClass     | TEXT    |          0 |    0 |
| chanceCreationCrossing         | INTEGER |          0 |    0 |
| chanceCreationCrossingClass    | TEXT    |          0 |    0 |
| chanceCreationShooting         | INTEGER |          0 |    0 |
| chanceCreationShootingClass    | TEXT    |          0 |    0 |
| chanceCreationPositioningClass | TEXT    |          0 |    0 |
| defencePressure                | INTEGER |          0 |    0 |
| defencePressureClass           | TEXT    |          0 |    0 |
| defenceAggression              | INTEGER |          0 |    0 |
| defenceAggressionClass         | TEXT    |          0 |    0 |
| defenceTeamWidth               | INTEGER |          0 |    0 |
| defenceTeamWidthClass          | TEXT    |          0 |    0 |
| defenceDefenderLineClass       | TEXT    |          0 |    0 |


## 3. Valori NULL per colonna



### Country (11 righe)


Nessun NULL.


### League (11 righe)


Nessun NULL.


### Match (25,979 righe)


| colonna    |   null |   pct_null |
|:-----------|-------:|-----------:|
| PSD        |  14811 |      57.01 |
| PSA        |  14811 |      57.01 |
| PSH        |  14811 |      57.01 |
| BSA        |  11818 |      45.49 |
| BSH        |  11818 |      45.49 |
| BSD        |  11818 |      45.49 |
| GBA        |  11817 |      45.49 |
| GBD        |  11817 |      45.49 |
| GBH        |  11817 |      45.49 |
| shotoff    |  11762 |      45.28 |
| goal       |  11762 |      45.28 |
| shoton     |  11762 |      45.28 |
| possession |  11762 |      45.28 |
| corner     |  11762 |      45.28 |
| cross      |  11762 |      45.28 |


### Player (11,060 righe)


Nessun NULL.


### Player_Attributes (183,978 righe)


| colonna             |   null |   pct_null |
|:--------------------|-------:|-----------:|
| attacking_work_rate |   3230 |       1.76 |
| agility             |   2713 |       1.47 |
| jumping             |   2713 |       1.47 |
| curve               |   2713 |       1.47 |
| volleys             |   2713 |       1.47 |
| balance             |   2713 |       1.47 |
| vision              |   2713 |       1.47 |
| sliding_tackle      |   2713 |       1.47 |
| standing_tackle     |    836 |       0.45 |
| marking             |    836 |       0.45 |
| penalties           |    836 |       0.45 |
| gk_diving           |    836 |       0.45 |
| positioning         |    836 |       0.45 |
| gk_handling         |    836 |       0.45 |
| interceptions       |    836 |       0.45 |


### Team (299 righe)


| colonna          |   null |   pct_null |
|:-----------------|-------:|-----------:|
| team_fifa_api_id |     11 |       3.68 |


### Team_Attributes (1,458 righe)


| colonna              |   null |   pct_null |
|:---------------------|-------:|-----------:|
| buildUpPlayDribbling |    969 |      66.46 |


## 4. Distribuzioni rilevanti



### Match per stagione


| season    |    n |
|:----------|-----:|
| 2008/2009 | 3326 |
| 2009/2010 | 3230 |
| 2010/2011 | 3260 |
| 2011/2012 | 3220 |
| 2012/2013 | 3260 |
| 2013/2014 | 3032 |
| 2014/2015 | 3325 |
| 2015/2016 | 3326 |


### Match per lega


| country     | league                   |   n_match |
|:------------|:-------------------------|----------:|
| England     | England Premier League   |      3040 |
| France      | France Ligue 1           |      3040 |
| Spain       | Spain LIGA BBVA          |      3040 |
| Italy       | Italy Serie A            |      3017 |
| Germany     | Germany 1. Bundesliga    |      2448 |
| Netherlands | Netherlands Eredivisie   |      2448 |
| Portugal    | Portugal Liga ZON Sagres |      2052 |
| Poland      | Poland Ekstraklasa       |      1920 |
| Scotland    | Scotland Premier League  |      1824 |
| Belgium     | Belgium Jupiler League   |      1728 |
| Switzerland | Switzerland Super League |      1422 |


### Range temporale dei match


| min_date            | max_date            |
|:--------------------|:--------------------|
| 2008-07-18 00:00:00 | 2016-05-25 00:00:00 |


### Player_Attributes: distribuzione snapshot per giocatore


|   n_snapshots |   n_players |
|--------------:|------------:|
|             2 |         158 |
|             3 |         331 |
|             4 |         393 |
|             5 |         433 |
|             6 |         484 |
|             7 |         491 |
|             8 |         498 |
|             9 |         442 |
|            10 |         391 |
|            11 |         346 |
|            12 |         340 |
|            13 |         343 |
|            14 |         339 |
|            15 |         358 |
|            16 |         357 |
|            17 |         354 |
|            18 |         404 |
|            19 |         392 |
|            20 |         397 |
|            21 |         389 |
|            22 |         385 |
|            23 |         359 |
|            24 |         317 |
|            25 |         327 |
|            26 |         287 |
|            27 |         247 |
|            28 |         213 |
|            29 |         214 |
|            30 |         182 |
|            31 |         140 |
|            32 |         117 |
|            33 |         124 |
|            34 |          96 |
|            35 |          72 |
|            36 |          74 |
|            37 |          54 |
|            38 |          52 |
|            39 |          33 |
|            40 |          24 |
|            41 |          25 |
|            42 |          15 |
|            43 |          12 |
|            44 |           9 |
|            45 |          10 |
|            46 |          10 |
|            47 |           4 |
|            48 |           6 |
|            50 |           4 |
|            51 |           1 |
|            52 |           1 |
|            53 |           2 |
|            54 |           1 |
|            55 |           1 |
|            56 |           2 |


## 5. Struttura dei campi XML di Match


I campi `goal`, `shoton`, `shotoff`, `foulcommit`, `card`, `cross`, `corner`, `possession` contengono XML grezzi con gli eventi della partita. Sotto, per ognuno: percentuale di NULL e un esempio di payload (troncato).


### goal


- NULL/vuoti: **11,762 / 25,979** (45.28%)


```xml
<goal><value><comment>n</comment><stats><goals>1</goals><shoton>1</shoton></stats><event_incident_typefk>406</event_incident_typefk><elapsed>22</elapsed><player2>38807</player2><subtype>header</subtype><player1>37799</player1><sortorder>5</sortorder><team>10261</team><id>378998</id><n>295</n><type>goal</type><goal_type>n</goal_type></value><value><comment>n</comment><stats><goals>1</goals><shoton>1</shoton></stats><event_incident_typefk>393</event_incident_typefk><elapsed>24</elapsed><player2>24154</player2><subtype>shot</subtype><player1>24148</player1><sortorder>4</sortorder><team>10260</tea...
```

Numero di elementi `<value>` in questo esempio: **2**

Tag presenti nel primo `<value>`: `comment`, `stats`, `event_incident_typefk`, `elapsed`, `player2`, `subtype`, `player1`, `sortorder`, `team`, `id`, `n`, `type`, `goal_type`


### shoton


- NULL/vuoti: **11,762 / 25,979** (45.28%)


```xml
<shoton><value><stats><blocked>1</blocked></stats><event_incident_typefk>61</event_incident_typefk><elapsed>3</elapsed><subtype>blocked_shot</subtype><player1>24154</player1><sortorder>0</sortorder><team>10260</team><n>253</n><type>shoton</type><id>378828</id></value><value><stats><shoton>1</shoton></stats><event_incident_typefk>154</event_incident_typefk><elapsed>7</elapsed><subtype>header</subtype><player1>24157</player1><sortorder>2</sortorder><team>10260</team><n>258</n><type>shoton</type><id>378866</id></value><value><stats><shoton>1</shoton></stats><event_incident_typefk>153</event_incid...
```

Numero di elementi `<value>` in questo esempio: **12**

Tag presenti nel primo `<value>`: `stats`, `event_incident_typefk`, `elapsed`, `subtype`, `player1`, `sortorder`, `team`, `n`, `type`, `id`


### shotoff


- NULL/vuoti: **11,762 / 25,979** (45.28%)


```xml
<shotoff><value><stats><shotoff>1</shotoff></stats><event_incident_typefk>9</event_incident_typefk><elapsed>4</elapsed><subtype>distance</subtype><player1>30373</player1><sortorder>1</sortorder><team>10260</team><n>264</n><type>shotoff</type><id>378835</id></value><value><stats><shotoff>1</shotoff></stats><event_incident_typefk>9</event_incident_typefk><elapsed>5</elapsed><subtype>distance</subtype><player1>37799</player1><sortorder>2</sortorder><team>10261</team><n>257</n><type>shotoff</type><id>378845</id></value><value><stats><shotoff>1</shotoff></stats><event_incident_typefk>317</event_inc...
```

Numero di elementi `<value>` in questo esempio: **19**

Tag presenti nel primo `<value>`: `stats`, `event_incident_typefk`, `elapsed`, `subtype`, `player1`, `sortorder`, `team`, `n`, `type`, `id`


### foulcommit


- NULL/vuoti: **11,762 / 25,979** (45.28%)


```xml
<foulcommit><value><stats><foulscommitted>1</foulscommitted></stats><event_incident_typefk>37</event_incident_typefk><elapsed>1</elapsed><player2>32569</player2><player1>25518</player1><sortorder>1</sortorder><team>10261</team><n>267</n><type>foulcommit</type><id>378824</id></value><value><stats><foulscommitted>1</foulscommitted></stats><event_incident_typefk>37</event_incident_typefk><elapsed>2</elapsed><player2>24157</player2><player1>30929</player1><sortorder>0</sortorder><team>10261</team><n>277</n><type>foulcommit</type><id>378826</id></value><value><stats><foulscommitted>1</foulscommitte...
```

Numero di elementi `<value>` in questo esempio: **27**

Tag presenti nel primo `<value>`: `stats`, `event_incident_typefk`, `elapsed`, `player2`, `player1`, `sortorder`, `team`, `n`, `type`, `id`


### card


- NULL/vuoti: **11,762 / 25,979** (45.28%)


```xml
<card><value><comment>y</comment><stats><ycards>1</ycards></stats><event_incident_typefk>73</event_incident_typefk><elapsed>78</elapsed><card_type>y</card_type><subtype>serious_fouls</subtype><player1>24157</player1><sortorder>1</sortorder><team>10260</team><n>342</n><type>card</type><id>379481</id></value><value><comment>y</comment><stats><ycards>1</ycards></stats><event_incident_typefk>73</event_incident_typefk><elapsed>82</elapsed><card_type>y</card_type><subtype>serious_fouls</subtype><player1>30362</player1><sortorder>1</sortorder><team>10260</team><n>346</n><type>card</type><id>379503</i...
```

Numero di elementi `<value>` in questo esempio: **3**

Tag presenti nel primo `<value>`: `comment`, `stats`, `event_incident_typefk`, `elapsed`, `card_type`, `subtype`, `player1`, `sortorder`, `team`, `n`, `type`, `id`


### cross


- NULL/vuoti: **11,762 / 25,979** (45.28%)


```xml
<cross><value><stats><crosses>1</crosses></stats><event_incident_typefk>7</event_incident_typefk><elapsed>7</elapsed><subtype>cross</subtype><player1>30829</player1><sortorder>1</sortorder><team>10260</team><n>265</n><type>cross</type><id>378863</id></value><value><stats><crosses>1</crosses></stats><event_incident_typefk>7</event_incident_typefk><elapsed>14</elapsed><subtype>cross</subtype><player1>24148</player1><sortorder>0</sortorder><team>10260</team><n>255</n><type>cross</type><id>378921</id></value><value><stats><corners>1</corners></stats><event_incident_typefk>329</event_incident_typef...
```

Numero di elementi `<value>` in questo esempio: **33**

Tag presenti nel primo `<value>`: `stats`, `event_incident_typefk`, `elapsed`, `subtype`, `player1`, `sortorder`, `team`, `n`, `type`, `id`


### corner


- NULL/vuoti: **11,762 / 25,979** (45.28%)


```xml
<corner><value><stats><corners>1</corners></stats><event_incident_typefk>329</event_incident_typefk><elapsed>19</elapsed><subtype>cross</subtype><player1>38807</player1><sortorder>0</sortorder><team>10261</team><n>280</n><type>corner</type><id>378960</id></value><value><stats><corners>1</corners></stats><event_incident_typefk>330</event_incident_typefk><elapsed>22</elapsed><subtype>short</subtype><player1>40565</player1><sortorder>0</sortorder><team>10261</team><n>263</n><type>corner</type><id>378992</id></value><value><stats><corners>1</corners></stats><event_incident_typefk>329</event_incide...
```

Numero di elementi `<value>` in questo esempio: **12**

Tag presenti nel primo `<value>`: `stats`, `event_incident_typefk`, `elapsed`, `subtype`, `player1`, `sortorder`, `team`, `n`, `type`, `id`


### possession


- NULL/vuoti: **11,762 / 25,979** (45.28%)


```xml
<possession><value><comment>56</comment><event_incident_typefk>352</event_incident_typefk><elapsed>25</elapsed><subtype>possession</subtype><sortorder>1</sortorder><awaypos>44</awaypos><homepos>56</homepos><n>68</n><type>special</type><id>379029</id></value><value><comment>54</comment><elapsed_plus>1</elapsed_plus><event_incident_typefk>352</event_incident_typefk><elapsed>45</elapsed><subtype>possession</subtype><sortorder>4</sortorder><awaypos>46</awaypos><homepos>54</homepos><n>117</n><type>special</type><id>379251</id></value><value><comment>54</comment><event_incident_typefk>352</event_inc...
```

Numero di elementi `<value>` in questo esempio: **4**

Tag presenti nel primo `<value>`: `comment`, `event_incident_typefk`, `elapsed`, `subtype`, `sortorder`, `awaypos`, `homepos`, `n`, `type`, `id`


## 6. Verifica integrita' referenziale


| check                                                    | n                               |
|:---------------------------------------------------------|:--------------------------------|
| Match.home_team_api_id -> Team.team_api_id (orfani)      | 0                               |
| Match.away_team_api_id -> Team.team_api_id (orfani)      | 0                               |
| Match.league_id -> League.id (orfani)                    | 0                               |
| Match.country_id -> Country.id (orfani)                  | 0                               |
| Match.player_X (home/away 1..11) -> Player.player_api_id | 0 orfani su 542,281 riferimenti |
| Player_Attributes.player_api_id -> Player (orfani)       | 0                               |
| Team_Attributes.team_api_id -> Team (orfani)             | 0                               |
