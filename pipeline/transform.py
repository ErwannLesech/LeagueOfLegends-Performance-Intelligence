"""
Transform layer — converts raw Riot API match data into clean ParticipantStats.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from collector.models import ParticipantStats

logger = logging.getLogger(__name__)

# Riot queue ID → human-readable name
QUEUE_NAMES = {
    420: "Ranked Solo",
    440: "Ranked Flex",
    400: "Normal Draft",
    430: "Normal Blind",
    450: "ARAM",
    490: "Quickplay",
}


def extract_participant_stats(raw_match: dict, puuid: str) -> ParticipantStats:
    """
    Extract stats for our summoner from a raw MATCH-V5 response.
    Also identifies the opponent mid laner.
    """
    info = raw_match["info"]
    metadata = raw_match["metadata"]
    match_id = metadata["matchId"]

    # Find our participant
    our_p = _find_participant(info["participants"], puuid)
    if our_p is None:
        raise ValueError(f"PUUID {puuid} not found in match {match_id}")

    # Identify opponent (same lane, opposite team)
    opponent = _find_opponent(info["participants"], our_p)

    # Compute kill participation
    our_team_id = our_p["teamId"]
    team_kills = sum(
        p["kills"] for p in info["participants"] if p["teamId"] == our_team_id
    )
    kp = _kill_participation(our_p["kills"], our_p["assists"], team_kills)

    # Extract patch from game version (e.g. "14.8.440.6074" → "14.8")
    patch = _parse_patch(info.get("gameVersion", ""))

    # Game date
    game_date = datetime.fromtimestamp(
        info["gameStartTimestamp"] / 1000, tz=timezone.utc
    )

    # Team composition (for context)
    queue_id = info.get("queueId", 0)

    k = our_p["kills"]
    d = our_p["deaths"]
    a = our_p["assists"]

    stats = ParticipantStats(
        match_id=match_id,
        game_date=game_date,
        patch=patch,
        queue_id=queue_id,
        duration_seconds=info["gameDuration"],

        champion_id=our_p["championId"],
        champion_name=our_p["championName"],
        champion_level=our_p["champLevel"],
        role=our_p.get("role", "NONE"),
        lane=our_p.get("lane", "NONE"),

        win=our_p["win"],
        result="Victoire" if our_p["win"] else "Défaite",

        kills=k,
        deaths=d,
        assists=a,
        kda_ratio=_kda_ratio(k, d, a),
        kill_participation=kp,
        kda_str=f"{k}/{d}/{a}",
        duration_min=round(info["gameDuration"] / 60, 1),

        cs_total=our_p["totalMinionsKilled"] + our_p.get("neutralMinionsKilled", 0),
        cs_per_min=_cs_per_min(
            our_p["totalMinionsKilled"] + our_p.get("neutralMinionsKilled", 0),
            info["gameDuration"],
        ),
        gold_earned=our_p["goldEarned"],
        gold_per_min=round(our_p["goldEarned"] / (info["gameDuration"] / 60), 0),

        vision_score=our_p.get("visionScore", 0),
        wards_placed=our_p.get("wardsPlaced", 0),
        wards_killed=our_p.get("wardsKilled", 0),
        control_wards_purchased=our_p.get("visionWardsBoughtInGame", 0),

        damage_dealt_to_champions=our_p.get("totalDamageDealtToChampions", 0),
        damage_taken=our_p.get("totalDamageTaken", 0),
        healing_done=our_p.get("totalHeal", 0),
        solo_kills=our_p.get("soloKills", 0),
        first_blood_kill=our_p.get("firstBloodKill", False),
        first_blood_assist=our_p.get("firstBloodAssist", False),

        turrets_destroyed=our_p.get("turretKills", 0),
        inhibitors_destroyed=our_p.get("inhibitorKills", 0),
        dragon_kills=our_p.get("dragonKills", 0),
        baron_kills=our_p.get("baronKills", 0),

        opponent_champion_name=opponent.get("championName") if opponent else None,
        opponent_champion_id=opponent.get("championId") if opponent else None,
    )

    logger.debug(
        f"Extracted: {stats.champion_name} vs {stats.opponent_champion_name} "
        f"— {stats.result} — {stats.kda_str}"
    )
    return stats


def _find_participant(participants: list[dict], puuid: str) -> Optional[dict]:
    for p in participants:
        if p.get("puuid") == puuid:
            return p
    return None


def _find_opponent(participants: list[dict], our_p: dict) -> Optional[dict]:
    """
    Find the opposing mid laner.
    Strategy: same individual position (MIDDLE) or team role, opposite team.
    Falls back to same lane assignment.
    """
    our_team = our_p["teamId"]
    our_lane = our_p.get("lane", "NONE")
    our_role = our_p.get("role", "NONE")
    our_position = our_p.get("individualPosition", "")

    # Priority: match by individualPosition
    for p in participants:
        if p["teamId"] != our_team:
            if p.get("individualPosition", "") == our_position and our_position:
                return p

    # Fallback: match by lane
    for p in participants:
        if p["teamId"] != our_team and p.get("lane") == our_lane and our_lane != "NONE":
            return p

    return None


def _kda_ratio(k: int, d: int, a: int) -> float:
    if d == 0:
        return float(k + a)
    return round((k + a) / d, 2)


def _kill_participation(kills: int, assists: int, team_kills: int) -> float:
    if team_kills == 0:
        return 0.0
    return round((kills + assists) / team_kills, 3)


def _cs_per_min(cs: int, duration_seconds: int) -> float:
    if duration_seconds == 0:
        return 0.0
    return round(cs / (duration_seconds / 60), 1)


def _parse_patch(game_version: str) -> str:
    """'14.8.440.6074' → '14.8'"""
    parts = game_version.split(".")
    if len(parts) >= 2:
        return f"{parts[0]}.{parts[1]}"
    return game_version
