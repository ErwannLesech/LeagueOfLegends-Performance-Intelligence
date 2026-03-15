-- matchup_matrix.sql
-- Winrate per champion × opponent matchup.
-- Filter on champion_name in Looker Studio to focus on your pool.

SELECT
    champion_name                                           AS my_champion,
    opponent_champion_name                                  AS opponent,
    COUNT(*)                                                AS games,
    SUM(CASE WHEN win THEN 1 ELSE 0 END)                    AS wins,
    ROUND(AVG(CASE WHEN win THEN 1.0 ELSE 0.0 END), 3)      AS winrate,
    ROUND(AVG(kda_ratio), 2)                                AS avg_kda,
    ROUND(AVG(cs_per_min), 1)                               AS avg_cs_per_min,
    ROUND(AVG(kill_participation), 3)                       AS avg_kp,
    ROUND(AVG(vision_score), 1)                             AS avg_vision,
    ROUND(AVG(duration_min), 1)                             AS avg_game_duration,
    ROUND(AVG(damage_dealt_to_champions), 0)                AS avg_damage,
    -- Loss analysis
    STRING_AGG(DISTINCT loss_cause, ', ')
        FILTER (WHERE NOT win AND loss_cause IS NOT NULL)   AS common_loss_causes,
    STRING_AGG(DISTINCT win_cause, ', ')
        FILTER (WHERE win AND win_cause IS NOT NULL)        AS common_win_causes
FROM games
WHERE
    opponent_champion_name IS NOT NULL
    AND champion_name IN ('Orianna', 'Ahri', 'Galio', 'Mel', 'Anivia')
GROUP BY champion_name, opponent_champion_name
ORDER BY champion_name, games DESC;
