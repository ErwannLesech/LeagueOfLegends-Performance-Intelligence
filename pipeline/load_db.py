"""
Database layer — PostgreSQL persistence via SQLAlchemy.
All writes use upsert (INSERT ... ON CONFLICT DO NOTHING) to be idempotent.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from config.settings import DATABASE_URL
from collector.models import ParticipantStats

logger = logging.getLogger(__name__)

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    return _engine


def init_db() -> None:
    """
    Create tables if they don't exist.
    Safe to call multiple times (idempotent).
    Also called from docker-entrypoint via init_schema.sql
    """
    engine = _get_engine()
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS games (
                    match_id                    VARCHAR(20) PRIMARY KEY,
                    game_date                   TIMESTAMPTZ NOT NULL,
                    patch                       VARCHAR(10),
                    queue_id                    INTEGER,
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

                    -- Manual fields (filled by user in Sheets/Excel, synced back)
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
            """))

            conn.execute(text("""
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
            """))

            conn.execute(text("""
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
            """))

            conn.commit()
            logger.info("DB tables initialized.")
    except SQLAlchemyError as e:
        logger.error(f"DB init failed: {e}")
        raise


def upsert_game(stats: ParticipantStats) -> None:
    """
    Insert a game row. If match_id already exists, skip (idempotent).
    """
    engine = _get_engine()
    sql = text("""
        INSERT INTO games (
            match_id, game_date, patch, queue_id, duration_seconds, duration_min,
            champion_name, champion_id, champion_level, role, lane,
            opponent_champion_name, opponent_champion_id,
            win, result, kills, deaths, assists, kda_str, kda_ratio, kill_participation,
            cs_total, cs_per_min, gold_earned, gold_per_min,
            vision_score, wards_placed, wards_killed, control_wards_purchased,
            damage_dealt_to_champions, damage_taken, healing_done, solo_kills,
            first_blood_kill, first_blood_assist,
            turrets_destroyed, inhibitors_destroyed, dragon_kills, baron_kills
        ) VALUES (
            :match_id, :game_date, :patch, :queue_id, :duration_seconds, :duration_min,
            :champion_name, :champion_id, :champion_level, :role, :lane,
            :opponent_champion_name, :opponent_champion_id,
            :win, :result, :kills, :deaths, :assists, :kda_str, :kda_ratio, :kill_participation,
            :cs_total, :cs_per_min, :gold_earned, :gold_per_min,
            :vision_score, :wards_placed, :wards_killed, :control_wards_purchased,
            :damage_dealt_to_champions, :damage_taken, :healing_done, :solo_kills,
            :first_blood_kill, :first_blood_assist,
            :turrets_destroyed, :inhibitors_destroyed, :dragon_kills, :baron_kills
        )
        ON CONFLICT (match_id) DO NOTHING;
    """)

    try:
        with engine.connect() as conn:
            conn.execute(sql, stats.model_dump())
            conn.commit()
            logger.debug(f"Upserted game {stats.match_id}")
    except SQLAlchemyError as e:
        logger.error(f"DB upsert failed for {stats.match_id}: {e}")
        raise


def get_known_match_ids() -> set[str]:
    """Returns all match IDs already in DB."""
    engine = _get_engine()
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT match_id FROM games;"))
            return {row[0] for row in result}
    except SQLAlchemyError as e:
        logger.warning(f"Could not load known match IDs: {e}")
        return set()


def get_games_as_df(limit: Optional[int] = None):
    """Returns games table as a pandas DataFrame. Used by analysis scripts."""
    import pandas as pd
    engine = _get_engine()
    query = "SELECT * FROM games ORDER BY game_date DESC"
    if limit:
        query += f" LIMIT {limit}"
    return pd.read_sql(query, engine)
