"""
Patch meta pipeline — fetches champion data from Data Dragon.
Stores tier-relevant stats in the patch_meta table.
Run manually after each major patch, or schedule weekly.

Usage:
    python -m pipeline.patch_meta
    python -m pipeline.patch_meta --patch 14.8
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from collector.riot_client import RiotClient
from pipeline.load_db import init_db, _get_engine
from sqlalchemy import text

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Mid lane relevant tags
MID_TAGS = {"Mage", "Assassin", "Fighter", "Support", "Marksman"}

def fetch_and_store_patch_meta(patch: str | None = None) -> None:
    client = RiotClient()
    init_db()

    if patch is None:
        patch = client.get_latest_patch()
        logger.info(f"Latest patch: {patch}")

    logger.info(f"Fetching Data Dragon for patch {patch}...")
    champion_data = client.get_champion_data(patch)

    engine = _get_engine()
    inserted = 0
    skipped = 0

    with engine.connect() as conn:
        for champ_id, data in champion_data.items():
            name = data.get("name", champ_id)
            tags = data.get("tags", [])
            info = data.get("info", {})

            # Only store mid-relevant champions
            if not MID_TAGS.intersection(set(tags)):
                continue

            try:
                conn.execute(text("""
                    INSERT INTO patch_meta (
                        patch_version, champion_id, champion_name,
                        tags, info_attack, info_defense, info_magic, info_difficulty
                    ) VALUES (
                        :patch_version, :champion_id, :champion_name,
                        :tags, :info_attack, :info_defense, :info_magic, :info_difficulty
                    )
                    ON CONFLICT (patch_version, champion_id) DO UPDATE SET
                        tags = EXCLUDED.tags,
                        info_attack = EXCLUDED.info_attack,
                        info_defense = EXCLUDED.info_defense,
                        info_magic = EXCLUDED.info_magic,
                        info_difficulty = EXCLUDED.info_difficulty,
                        fetched_at = NOW();
                """), {
                    "patch_version": patch,
                    "champion_id": champ_id,
                    "champion_name": name,
                    "tags": tags,
                    "info_attack": info.get("attack", 0),
                    "info_defense": info.get("defense", 0),
                    "info_magic": info.get("magic", 0),
                    "info_difficulty": info.get("difficulty", 0),
                })
                inserted += 1
            except Exception as e:
                logger.warning(f"Skipped {name}: {e}")
                skipped += 1

        conn.commit()

    logger.info(f"Patch {patch} meta stored: {inserted} champions, {skipped} skipped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch LoL patch meta from Data Dragon")
    parser.add_argument("--patch", type=str, default=None,
                        help="Patch version (e.g. 14.8). Defaults to latest.")
    args = parser.parse_args()
    fetch_and_store_patch_meta(args.patch)
