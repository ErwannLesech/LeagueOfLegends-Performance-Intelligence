"""
Backfill script — imports your last N ranked games into the DB and Sheets.
Run once after setup to populate historical data.

Usage:
    python scripts/backfill.py              # Last 20 ranked solo games
    python scripts/backfill.py --count 100  # Last 100
    python scripts/backfill.py --queue 420  # Ranked solo only (default)
    python scripts/backfill.py --queue 0    # All queues
    python scripts/backfill.py --db-only    # Skip Sheets push
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import SUMMONER_NAME, SUMMONER_TAG, QUEUE_RANKED_SOLO
from collector.riot_client import RiotClient, RiotAPIError
from collector.models import ParticipantStats
from pipeline.transform import extract_participant_stats
from pipeline.load_db import init_db, upsert_game, get_known_match_ids
from pipeline.load_sheets import bulk_push_games, ensure_headers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("backfill")


def run_backfill(count: int, queue_id: int | None, skip_sheets: bool) -> None:
    init_db()

    client = RiotClient()
    known_ids = get_known_match_ids()
    logger.info(f"Already in DB: {len(known_ids)} matches")

    # Resolve summoner
    logger.info(f"Resolving {SUMMONER_NAME}#{SUMMONER_TAG}...")
    account = client.get_account_by_riot_id(SUMMONER_NAME, SUMMONER_TAG)
    puuid = account["puuid"]
    logger.info(f"PUUID: {puuid[:16]}...")

    # Fetch match IDs in batches (API max 100 per call, but dev key recommends ≤20)
    all_ids: list[str] = []
    batch_size = 20
    start = 0

    while len(all_ids) < count:
        remaining = count - len(all_ids)
        batch = min(remaining, batch_size)
        logger.info(f"Fetching match IDs {start} → {start + batch}...")

        ids = client.get_match_ids(
            puuid=puuid,
            queue=queue_id if queue_id != 0 else None,
            count=batch,
            start=start,
        )
        if not ids:
            logger.info("No more matches.")
            break

        all_ids.extend(ids)
        start += batch

        if len(ids) < batch:
            break

        time.sleep(2)  # Be polite with dev key

    logger.info(f"Total match IDs fetched: {len(all_ids)}")

    # Filter already-known
    to_process = [mid for mid in all_ids if mid not in known_ids]
    logger.info(f"New matches to process: {len(to_process)}")

    if not to_process:
        logger.info("Nothing to backfill.")
        return

    # Process each match
    processed: list[ParticipantStats] = []
    errors = 0

    for i, match_id in enumerate(to_process, 1):
        logger.info(f"[{i}/{len(to_process)}] Processing {match_id}...")
        try:
            raw = client.get_match(match_id)
            stats = extract_participant_stats(raw, puuid)
            upsert_game(stats)
            processed.append(stats)
            logger.info(
                f"  {stats.champion_name} vs {stats.opponent_champion_name} "
                f"— {stats.result} — {stats.kda_str}"
            )
        except RiotAPIError as e:
            logger.error(f"  API error: {e}")
            errors += 1
        except Exception as e:
            logger.exception(f"  Unexpected error: {e}")
            errors += 1

        time.sleep(1.2)  # Dev key rate limit

    logger.info(f"\nBackfill complete: {len(processed)} games saved, {errors} errors.")

    # Push to Sheets
    if not skip_sheets and processed:
        logger.info("Pushing to Google Sheets...")
        try:
            ensure_headers()
            bulk_push_games(processed)
        except Exception as e:
            logger.error(f"Sheets push failed: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill historical LoL games")
    parser.add_argument("--count",   type=int, default=20, help="Number of games to fetch")
    parser.add_argument("--queue",   type=int, default=420, help="Queue ID (420=ranked solo, 0=all)")
    parser.add_argument("--db-only", action="store_true", help="Skip Google Sheets push")
    args = parser.parse_args()

    run_backfill(
        count=args.count,
        queue_id=args.queue if args.queue != 0 else None,
        skip_sheets=args.db_only,
    )
