"""
Data models for League of Legends game data.
Using Pydantic v2 for validation and serialization.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


class SummonerInfo(BaseModel):
    puuid: str
    summoner_id: str
    account_id: str
    name: str
    tag: str
    profile_icon_id: int
    summoner_level: int
    region: str


class RankedInfo(BaseModel):
    queue_type: str  # RANKED_SOLO_5x5 | RANKED_FLEX_SR
    tier: str        # IRON / BRONZE / ... / CHALLENGER
    rank: str        # I / II / III / IV
    lp: int
    wins: int
    losses: int

    @property
    def winrate(self) -> float:
        total = self.wins + self.losses
        return self.wins / total if total > 0 else 0.0

    @property
    def full_rank(self) -> str:
        return f"{self.tier} {self.rank} {self.lp} LP"


class ParticipantStats(BaseModel):
    """Stats extracted from match participant data for our summoner."""
    match_id: str
    game_date: datetime
    patch: str
    queue_id: int
    match_type: str
    duration_seconds: int

    # Champion
    champion_id: int
    champion_name: str
    champion_level: int
    role: str        # SOLO / CARRY / SUPPORT / JUNGLE / NONE
    lane: str        # TOP / JUNGLE / MIDDLE / BOTTOM / NONE

    # Result
    win: bool
    result: str      # "Victoire" | "Défaite"

    # KDA
    kills: int
    deaths: int
    assists: int
    kda_ratio: float
    kill_participation: float  # 0.0 → 1.0

    # Farming
    cs_total: int
    cs_per_min: float
    gold_earned: int
    gold_per_min: float

    # Vision
    vision_score: int
    wards_placed: int
    wards_killed: int
    control_wards_purchased: int

    # Combat
    damage_dealt_to_champions: int
    damage_taken: int
    healing_done: int
    solo_kills: int
    first_blood_kill: bool
    first_blood_assist: bool

    # Objectives
    turrets_destroyed: int
    inhibitors_destroyed: int
    dragon_kills: int
    baron_kills: int

    # Opponent mid
    opponent_champion_name: Optional[str] = None
    opponent_champion_id: Optional[int] = None

    # Computed fields (enriched post-extract)
    kda_str: Optional[str] = None         # "6/2/10"
    duration_min: Optional[float] = None

    # Manual fields (filled by user, stored in DB)
    win_cause: Optional[str] = None
    loss_cause: Optional[str] = None
    mental_pregame: Optional[int] = None
    tilt_check: Optional[str] = None
    session_id: Optional[int] = None
    session_position: Optional[int] = None
    pregame_note: Optional[str] = None
    key_takeaway: Optional[str] = None
    game_review: Optional[str] = None
    opgg_score: Optional[float] = None
    snowball_who: Optional[str] = None

    @field_validator("kda_str", mode="before")
    @classmethod
    def build_kda_str(cls, v: Optional[str], info: any) -> Optional[str]:
        if v:
            return v
        data = info.data
        k = data.get("kills")
        d = data.get("deaths")
        a = data.get("assists")
        if k is not None and d is not None and a is not None:
            return f"{k}/{d}/{a}"
        return None

    @field_validator("duration_min", mode="before")
    @classmethod
    def compute_duration_min(cls, v: Optional[float], info: any) -> Optional[float]:
        if v:
            return v
        secs = info.data.get("duration_seconds")
        if secs:
            return round(secs / 60, 1)
        return None


class MatchSummary(BaseModel):
    """Full match context — our player + relevant team info."""
    match_id: str
    game_date: datetime
    patch: str
    queue_id: int
    queue_name: str
    duration_seconds: int
    game_version: str

    our_stats: ParticipantStats
    team_won: bool

    # All participants (for team composition context)
    blue_team: list[dict]
    red_team: list[dict]


class PatchMeta(BaseModel):
    """Champion meta data from Data Dragon for a given patch."""
    patch_version: str
    champion_id: str
    champion_name: str
    base_stats: dict
    tags: list[str]    # e.g. ["Mage", "Support"]
    partype: str       # resource type
    info: dict         # attack, defense, magic, difficulty (0-10)
