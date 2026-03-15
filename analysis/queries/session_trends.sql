-- session_trends.sql
-- Session-level performance for correlation analysis.
-- Joins games table to aggregate per session, including mental state.

SELECT
    s.session_id,
    s.session_date,
    s.start_time,
    s.end_time,
    EXTRACT(EPOCH FROM (s.end_time - s.start_time)) / 3600   AS session_hours,
    s.mental_pregame,
    s.pause_taken,
    s.lp_end - s.lp_start                                    AS lp_delta,

    -- Aggregated from games
    COUNT(g.match_id)                                         AS games_played,
    SUM(CASE WHEN g.win THEN 1 ELSE 0 END)                    AS wins,
    ROUND(AVG(CASE WHEN g.win THEN 1.0 ELSE 0.0 END), 3)      AS winrate,
    ROUND(AVG(g.kda_ratio), 2)                                AS avg_kda,
    ROUND(AVG(g.cs_per_min), 1)                               AS avg_cs_per_min,
    ROUND(AVG(g.kill_participation), 3)                       AS avg_kp,
    ROUND(AVG(g.vision_score), 1)                             AS avg_vision,

    -- Tilt detection
    SUM(CASE WHEN g.tilt_check = 'Oui' THEN 1 ELSE 0 END)    AS tilt_games,
    STRING_AGG(DISTINCT g.tilt_check, ', ')
        FILTER (WHERE g.tilt_check IS NOT NULL)               AS tilt_summary,

    -- Game position performance (1st vs 2nd vs 3rd game)
    ROUND(AVG(CASE WHEN g.session_position = 1
        THEN CASE WHEN g.win THEN 1.0 ELSE 0.0 END END), 3)  AS wr_game_1,
    ROUND(AVG(CASE WHEN g.session_position = 2
        THEN CASE WHEN g.win THEN 1.0 ELSE 0.0 END END), 3)  AS wr_game_2,
    ROUND(AVG(CASE WHEN g.session_position >= 3
        THEN CASE WHEN g.win THEN 1.0 ELSE 0.0 END END), 3)  AS wr_game_3plus

FROM sessions s
LEFT JOIN games g ON g.session_id = s.session_id
GROUP BY s.session_id, s.session_date, s.start_time, s.end_time,
         s.mental_pregame, s.pause_taken, s.lp_start, s.lp_end
ORDER BY s.session_date DESC;
