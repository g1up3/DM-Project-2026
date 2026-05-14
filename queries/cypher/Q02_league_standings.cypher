// Q02: Classifica del campionato per stagione e lega.
// Parametri: $season, $league_name

MATCH (m:Match {season: $season})-[:IN_LEAGUE]->(:League {name: $league_name})
MATCH (m)-[:HOME]->(home:Team), (m)-[:AWAY]->(away:Team)
WITH m, home, away,
     CASE WHEN m.homeGoals > m.awayGoals THEN 3
          WHEN m.homeGoals = m.awayGoals THEN 1
          ELSE 0 END AS hpts,
     CASE WHEN m.awayGoals > m.homeGoals THEN 3
          WHEN m.homeGoals = m.awayGoals THEN 1
          ELSE 0 END AS apts
WITH collect({team: home, pts: hpts, gf: m.homeGoals, ga: m.awayGoals})
     + collect({team: away, pts: apts, gf: m.awayGoals, ga: m.homeGoals}) AS rows
UNWIND rows AS r
WITH r.team AS team, sum(r.pts) AS points, sum(r.gf) AS gf, sum(r.ga) AS ga
RETURN team.name AS team, points, gf AS goals_for, ga AS goals_against, gf - ga AS goal_diff
ORDER BY points DESC, goal_diff DESC, team;
