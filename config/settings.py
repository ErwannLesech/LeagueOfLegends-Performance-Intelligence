"""
Central configuration — loaded once at startup.
All values come from .env
"""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─── Paths ────────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent.parent
OUTPUTS_DIR = ROOT_DIR / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)

# ─── Riot API ─────────────────────────────────────────────────────────────────
RIOT_API_KEY: str = os.environ["RIOT_API_KEY"]
SUMMONER_NAME: str = os.environ["SUMMONER_NAME"]
SUMMONER_TAG: str = os.environ.get("SUMMONER_TAG", "EUW")
REGION: str = os.environ.get("REGION", "euw1")
ROUTING: str = os.environ.get("ROUTING", "europe")

# Base URLs
RIOT_BASE_URL = f"https://{REGION}.api.riotgames.com"
RIOT_ROUTING_URL = f"https://{ROUTING}.api.riotgames.com"

# Rate limit — dev key: 20 req/s, 100 req/2min
# We stay conservative: 1 req/s, max 90/2min
RATE_LIMIT_CALLS = 90
RATE_LIMIT_PERIOD = 120  # seconds

# ─── Database ─────────────────────────────────────────────────────────────────
DB_HOST: str = os.environ.get("POSTGRES_HOST", "localhost")
DB_PORT: int = int(os.environ.get("POSTGRES_PORT", 5432))
DB_NAME: str = os.environ.get("POSTGRES_DB", "lol_tracker")
DB_USER: str = os.environ.get("POSTGRES_USER", "lol_user")
DB_PASSWORD: str = os.environ.get("POSTGRES_PASSWORD", "admin")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ─── Google Sheets ────────────────────────────────────────────────────────────
GOOGLE_SPREADSHEET_ID: str = os.environ.get("GOOGLE_SPREADSHEET_ID", "")
GOOGLE_SERVICE_ACCOUNT_PATH: str = os.environ.get(
    "GOOGLE_SERVICE_ACCOUNT_PATH", "./service_account.json"
)
SHEETS_GAME_LOG_TAB: str = os.environ.get("SHEETS_GAME_LOG_TAB", "Game Log")
SHEETS_SESSION_TAB: str = os.environ.get("SHEETS_SESSION_TAB", "Session Stats")

# ─── Watcher ──────────────────────────────────────────────────────────────────
WATCHER_POLL_INTERVAL: int = int(os.environ.get("WATCHER_POLL_INTERVAL", 300))
WATCHER_MATCH_COUNT: int = int(os.environ.get("WATCHER_MATCH_COUNT", 5))

# ─── Excel ────────────────────────────────────────────────────────────────────
EXCEL_OUTPUT_PATH: Path = Path(
    os.environ.get("EXCEL_OUTPUT_PATH", str(OUTPUTS_DIR / "LoL_Tracker.xlsx"))
)

# ─── Logging ──────────────────────────────────────────────────────────────────
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")

# ─── Game constants ───────────────────────────────────────────────────────────
# Queue IDs — https://static.developer.riotgames.com/docs/lol/queues.json
QUEUE_RANKED_SOLO = 420
QUEUE_RANKED_FLEX = 440
QUEUE_NORMAL_DRAFT = 400
QUEUE_NORMAL_BLIND = 430
QUEUE_ARAM = 450

TRACKED_QUEUES = [QUEUE_RANKED_SOLO, QUEUE_RANKED_FLEX, QUEUE_NORMAL_DRAFT]

# Match categories tracked by watcher/backfill after fetching raw games.
# Possible values currently produced by pipeline.transform.classify_match_type:
# - ranked_solo_duo
# - ranked_flex
# - other
TRACKED_MATCH_TYPES = ["ranked_solo_duo", "ranked_flex"]

# Champions mid pool (used for filtering/alerts)
MID_POOL = ["Orianna", "Ahri", "Galio", "Mel", "Anivia"]

# Data Dragon version endpoint
DATA_DRAGON_VERSIONS_URL = "https://ddragon.leagueoflegends.com/api/versions.json"
DATA_DRAGON_BASE = "https://ddragon.leagueoflegends.com/cdn"
