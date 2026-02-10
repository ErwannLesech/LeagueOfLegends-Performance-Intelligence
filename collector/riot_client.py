"""
Riot Games API client.
Covers: ACCOUNT-V1, SUMMONER-V4, MATCH-V5, LEAGUE-V4, SPECTATOR-V5.
All requests go through the rate limiter.
"""
from __future__ import annotations

import logging
from typing import Optional
from datetime import datetime

import requests

from config.settings import (
    RIOT_API_KEY, RIOT_BASE_URL, RIOT_ROUTING_URL,
    REGION, ROUTING,
)
from collector.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


class RiotAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"Riot API {status_code}: {message}")


class RiotClient:
    """
    Thin wrapper around the Riot REST API.
    Each method corresponds to one API endpoint.
    Rate limiting is applied automatically via the decorator.
    """

    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({
            "X-Riot-Token": RIOT_API_KEY,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
        })

    def _get(self, url: str, params: Optional[dict] = None) -> dict:
        rate_limiter.wait()
        try:
            resp = self._session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as e:
            status = e.response.status_code if e.response else 0
            if status == 429:
                retry_after = int(e.response.headers.get("Retry-After", 10))
                logger.warning(f"429 Rate limited by Riot. Sleeping {retry_after}s...")
                import time; time.sleep(retry_after + 1)
                return self._get(url, params)  # single retry
            raise RiotAPIError(status, str(e)) from e
        except requests.RequestException as e:
            raise RiotAPIError(0, str(e)) from e

    # ─── ACCOUNT-V1 ──────────────────────────────────────────────────────────

    def get_account_by_riot_id(self, game_name: str, tag_line: str) -> dict:
        """Returns puuid, gameName, tagLine."""
        url = f"{RIOT_ROUTING_URL}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        return self._get(url)

    # ─── SUMMONER-V4 ─────────────────────────────────────────────────────────

    def get_summoner_by_puuid(self, puuid: str) -> dict:
        url = f"{RIOT_BASE_URL}/lol/summoner/v4/summoners/by-puuid/{puuid}"
        return self._get(url)

    # ─── LEAGUE-V4 ───────────────────────────────────────────────────────────

    def get_ranked_info(self, summoner_id: str) -> list[dict]:
        """Returns list of ranked entries (solo + flex)."""
        url = f"{RIOT_BASE_URL}/lol/league/v4/entries/by-summoner/{summoner_id}"
        return self._get(url)

    # ─── MATCH-V5 ────────────────────────────────────────────────────────────

    def get_match_ids(
        self,
        puuid: str,
        queue: Optional[int] = None,
        count: int = 5,
        start: int = 0,
        start_time: Optional[int] = None,
    ) -> list[str]:
        """
        Returns list of match IDs (most recent first).
        queue: queue ID (420=ranked solo, None=all queues)
        start_time: unix timestamp — only matches after this time
        """
        url = f"{RIOT_ROUTING_URL}/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params: dict = {"count": count, "start": start}
        if queue is not None:
            params["queue"] = queue
        if start_time is not None:
            params["startTime"] = start_time
        result = self._get(url, params)
        return result if isinstance(result, list) else []

    def get_match(self, match_id: str) -> dict:
        """Full match data including all participants."""
        url = f"{RIOT_ROUTING_URL}/lol/match/v5/matches/{match_id}"
        return self._get(url)

    def get_match_timeline(self, match_id: str) -> dict:
        """Frame-by-frame timeline (heavy — use sparingly)."""
        url = f"{RIOT_ROUTING_URL}/lol/match/v5/matches/{match_id}/timeline"
        return self._get(url)

    # ─── SPECTATOR-V5 ────────────────────────────────────────────────────────

    def get_active_game(self, puuid: str) -> Optional[dict]:
        """
        Returns current game data if summoner is in game, None otherwise.
        Useful for the watcher to detect game start.
        """
        url = f"{RIOT_BASE_URL}/lol/spectator/v5/active-games/by-summoner/{puuid}"
        try:
            return self._get(url)
        except RiotAPIError as e:
            if e.status_code == 404:
                return None  # Not in game
            raise

    # ─── DATA DRAGON ─────────────────────────────────────────────────────────

    def get_latest_patch(self) -> str:
        """Returns the latest patch version string, e.g. '14.8.1'"""
        from config.settings import DATA_DRAGON_VERSIONS_URL
        rate_limiter.wait()
        resp = self._session.get(DATA_DRAGON_VERSIONS_URL, timeout=10)
        resp.raise_for_status()
        versions = resp.json()
        return versions[0]

    def get_champion_data(self, patch: str) -> dict:
        """Returns full champion data for a given patch."""
        from config.settings import DATA_DRAGON_BASE
        url = f"{DATA_DRAGON_BASE}/{patch}/data/en_US/champion.json"
        rate_limiter.wait()
        resp = self._session.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json().get("data", {})

    def get_champion_detail(self, patch: str, champion_id: str) -> dict:
        """Detailed data for a single champion (full stats, spells, lore)."""
        from config.settings import DATA_DRAGON_BASE
        url = f"{DATA_DRAGON_BASE}/{patch}/data/en_US/champion/{champion_id}.json"
        rate_limiter.wait()
        resp = self._session.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json().get("data", {}).get(champion_id, {})
