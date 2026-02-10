"""
Watcher — background polling script.

Designed to run on Windows (where you play) or Linux.
Polls every WATCHER_POLL_INTERVAL seconds and detects:
  - Game in progress (via Spectator API)
  - New completed game (new match ID not yet in DB)

On detection of a completed game:
  1. Fetches full match data
  2. Transforms to ParticipantStats
  3. Persists to PostgreSQL
  4. Pushes row to Google Sheets

Run:
    python -m collector.watcher

Or on Windows at startup via Task Scheduler:
    pythonw -m collector.watcher   (no console window)
"""
from __future__ import annotations

import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import schedule

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    SUMMONER_NAME, SUMMONER_TAG,
    WATCHER_POLL_INTERVAL, WATCHER_MATCH_COUNT,
    TRACKED_QUEUES, LOG_LEVEL,
)
from collector.riot_client import RiotClient, RiotAPIError
from collector.models import ParticipantStats
from pipeline.transform import extract_participant_stats
from pipeline.load_db import upsert_game, get_known_match_ids, init_db
from pipeline.load_sheets import append_game_to_sheets

# ─── Logging setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/watcher.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("watcher")

Path("logs").mkdir(exist_ok=True)


class GameWatcher:
    def __init__(self) -> None:
        self.client = RiotClient()
        self.puuid: str | None = None
        self.summoner_id: str | None = None
        self._in_game: bool = False
        self._known_match_ids: set[str] = set()

    def _bootstrap(self) -> None:
        """Resolve PUUID + summoner ID once at startup."""
        logger.info(f"Bootstrapping summoner: {SUMMONER_NAME}#{SUMMONER_TAG}")
        account = self.client.get_account_by_riot_id(SUMMONER_NAME, SUMMONER_TAG)
        self.puuid = account["puuid"]
        summoner = self.client.get_summoner_by_puuid(self.puuid)
        self.summoner_id = summoner["id"]

        # Load already-known match IDs from DB to avoid reprocessing
        self._known_match_ids = get_known_match_ids()
        logger.info(
            f"Summoner resolved. PUUID: {self.puuid[:12]}... "
            f"Known matches in DB: {len(self._known_match_ids)}"
        )

    def _check_active_game(self) -> bool:
        """Returns True if summoner is currently in a game."""
        try:
            active = self.client.get_active_game(self.puuid)
            return active is not None
        except RiotAPIError:
            return False

    def _fetch_new_matches(self) -> list[str]:
        """Returns match IDs completed since last poll, not yet in DB."""
        new_ids = []
        for queue_id in TRACKED_QUEUES:
            ids = self.client.get_match_ids(
                puuid=self.puuid,
                queue=queue_id,
                count=WATCHER_MATCH_COUNT,
            )
            for mid in ids:
                if mid not in self._known_match_ids:
                    new_ids.append(mid)
        return list(set(new_ids))

    def _process_match(self, match_id: str) -> None:
        """Full pipeline for a single completed match."""
        logger.info(f"Processing match: {match_id}")
        try:
            raw = self.client.get_match(match_id)
            stats: ParticipantStats = extract_participant_stats(raw, self.puuid)

            # Persist to DB
            upsert_game(stats)
            self._known_match_ids.add(match_id)

            # Push to Google Sheets
            try:
                append_game_to_sheets(stats)
            except Exception as e:
                logger.warning(f"Sheets push failed (non-fatal): {e}")

            logger.info(
                f"Match {match_id} saved — "
                f"{stats.champion_name} vs {stats.opponent_champion_name} — "
                f"{stats.result} — {stats.kda_str} — {stats.cs_per_min:.1f} cs/min"
            )
        except RiotAPIError as e:
            logger.error(f"Riot API error on {match_id}: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error processing {match_id}: {e}")

    def poll(self) -> None:
        """Single poll cycle — called by scheduler."""
        if not self.puuid:
            try:
                self._bootstrap()
            except Exception as e:
                logger.error(f"Bootstrap failed: {e}")
                return

        logger.debug("Polling...")

        # Check if currently in game
        currently_in_game = self._check_active_game()
        if currently_in_game and not self._in_game:
            logger.info("Game detected — in progress")
            self._in_game = True
        elif not currently_in_game and self._in_game:
            logger.info("Game ended — checking for new match...")
            self._in_game = False
            time.sleep(30)  # Give Riot API time to register the match

        # Always check for new completed matches
        new_matches = self._fetch_new_matches()
        if new_matches:
            logger.info(f"Found {len(new_matches)} new match(es): {new_matches}")
            for match_id in new_matches:
                self._process_match(match_id)
        else:
            logger.debug("No new matches.")


def main() -> None:
    logger.info("=" * 60)
    logger.info("LoL Tracker Watcher starting")
    logger.info(f"Summoner: {SUMMONER_NAME}#{SUMMONER_TAG}")
    logger.info(f"Poll interval: {WATCHER_POLL_INTERVAL}s")
    logger.info("=" * 60)

    # Ensure DB tables exist
    init_db()

    watcher = GameWatcher()

    # Run once immediately, then on schedule
    watcher.poll()
    schedule.every(WATCHER_POLL_INTERVAL).seconds.do(watcher.poll)

    while True:
        schedule.run_pending()
        time.sleep(10)


if __name__ == "__main__":
    main()
