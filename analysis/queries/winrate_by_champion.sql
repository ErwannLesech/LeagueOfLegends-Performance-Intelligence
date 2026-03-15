-- winrate_by_champion.sql
-- Use in Looker Studio as a custom query on the PostgreSQL connector.
-- Shows winrate, avg KDA, avg CS/min per champion over the last 90 days.

SELECT
    champion_name,
    COUNT(*)                                            AS games_played,
    SUM(CASE WHEN win THEN 1 ELSE 0 END)                AS wins,
    ROUND(AVG(CASE WHEN win THEN 1.0 ELSE 0.0 END), 3)  AS winrate,
    ROUND(AVG(kda_ratio), 2)                            AS avg_kda,
    ROUND(AVG(kills), 1)                                AS avg_kills,
    ROUND(AVG(deaths), 1)                               AS avg_deaths,
    ROUND(AVG(assists), 1)                              AS avg_assists,
    ROUND(AVG(cs_per_min), 1)                           AS avg_cs_per_min,
    ROUND(AVG(kill_participation), 3)                   AS avg_kill_participation,
    ROUND(AVG(vision_score), 1)                         AS avg_vision_score,
    ROUND(AVG(damage_dealt_to_champions), 0)            AS avg_damage,
    MIN(game_date)                                      AS first_game,
    MAX(game_date)                                      AS last_game,
    patch                                               AS last_patch
FROM games
WHERE game_date >= NOW() - INTERVAL '90 days'
GROUP BY champion_name, patch
HAVING COUNT(*) >= 2
ORDER BY games_played DESC, winrate DESC;
