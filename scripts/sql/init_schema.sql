-- init_schema.sql
-- Executed automatically by PostgreSQL Docker container on first run.
-- Idempotent — safe to re-run.

CREATE TABLE IF NOT EXISTS games (
    match_id                    VARCHAR(20) PRIMARY KEY,
    game_date                   TIMESTAMPTZ NOT NULL,
    patch                       VARCHAR(10),
    queue_id                    INTEGER,
    match_type                  VARCHAR(30),
    duration_seconds            INTEGER,
    duration_min                FLOAT,

    champion_name               VARCHAR(50),
    champion_id                 INTEGER,
    champion_level              INTEGER,
    role                        VARCHAR(20),
    lane                        VARCHAR(20),
    opponent_champion_name      VARCHAR(50),
    opponent_champion_id        INTEGER,

    win                         BOOLEAN NOT NULL,
    result                      VARCHAR(20),
    kills                       INTEGER,
    deaths                      INTEGER,
    assists                     INTEGER,
    kda_str                     VARCHAR(15),
    kda_ratio                   FLOAT,
    kill_participation          FLOAT,

    cs_total                    INTEGER,
    cs_per_min                  FLOAT,
    gold_earned                 INTEGER,
    gold_per_min                FLOAT,

    vision_score                INTEGER,
    wards_placed                INTEGER,
    wards_killed                INTEGER,
    control_wards_purchased     INTEGER,

    damage_dealt_to_champions   INTEGER,
    damage_taken                INTEGER,
    healing_done                INTEGER,
    solo_kills                  INTEGER,
    first_blood_kill            BOOLEAN,
    first_blood_assist          BOOLEAN,
    turrets_destroyed           INTEGER,
    inhibitors_destroyed        INTEGER,
    dragon_kills                INTEGER,
    baron_kills                 INTEGER,

    session_id                  INTEGER,
    session_position            INTEGER,
    win_cause                   VARCHAR(100),
    loss_cause                  VARCHAR(100),
    mental_pregame              INTEGER,
    tilt_check                  VARCHAR(20),
    pregame_note                TEXT,
    key_takeaway                TEXT,
    game_review                 TEXT,
    opgg_score                  FLOAT,
    snowball_who                VARCHAR(50),

    created_at                  TIMESTAMPTZ DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id      SERIAL PRIMARY KEY,
    session_date    DATE NOT NULL,
    start_time      TIME,
    end_time        TIME,
    mental_pregame  INTEGER,
    game_count      INTEGER DEFAULT 0,
    wins            INTEGER DEFAULT 0,
    losses          INTEGER DEFAULT 0,
    lp_start        INTEGER,
    lp_end          INTEGER,
    pause_taken     BOOLEAN DEFAULT FALSE,
    session_notes   TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS patch_meta (
    id              SERIAL PRIMARY KEY,
    patch_version   VARCHAR(10) NOT NULL,
    champion_id     VARCHAR(50) NOT NULL,
    champion_name   VARCHAR(50) NOT NULL,
    tags            TEXT[],
    info_attack     INTEGER,
    info_defense    INTEGER,
    info_magic      INTEGER,
    info_difficulty INTEGER,
    fetched_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (patch_version, champion_id)
);

-- Useful index for frequent queries
CREATE INDEX IF NOT EXISTS idx_games_date       ON games(game_date DESC);
CREATE INDEX IF NOT EXISTS idx_games_champion   ON games(champion_name);
CREATE INDEX IF NOT EXISTS idx_games_opponent   ON games(opponent_champion_name);
CREATE INDEX IF NOT EXISTS idx_games_patch      ON games(patch);
CREATE INDEX IF NOT EXISTS idx_games_win        ON games(win);
