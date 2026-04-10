"""
Mapping between DB fields and Google Sheets columns.
Order matters — it defines column position in the sheet.
"""
from __future__ import annotations
from typing import Any, Callable
import datetime

# Each entry: (db_field, sheet_header, formatter_fn)
# formatter_fn is optional — applied before writing to Sheets

def _pct(v: Any) -> str:
    if v is None:
        return ""
    return f"{v:.0%}"

def _round1(v: Any) -> str:
    if v is None:
        return ""
    return f"{v:.1f}"

def _round2(v: Any) -> str:
    if v is None:
        return ""
    return f"{v:.2f}"

def _date(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, datetime.datetime):
        return v.strftime("%Y-%m-%d")
    return str(v)

GAME_LOG_COLUMNS: list[tuple[str, str, Callable | None]] = [
    ("game_date",           "Date",                  _date),
    ("session_id",          "Session #",              None),
    ("champion_name",       "Champion joué",          None),
    ("opponent_champion_name", "Adversaire mid",       None),
    ("result",              "Résultat",               None),
    ("duration_min",        "Durée (min)",            _round1),
    ("kda_str",             "K / D / A",              None),
    ("kill_participation",  "Kill Part. %",           _pct),
    ("win_cause",           "Cause victoire",         None),
    ("loss_cause",          "Cause défaite",          None),
    ("vision_score",        "Vision score",           None),
    ("cs_per_min",          "CS/min",                 _round1),
    ("mental_pregame",      "Mental pré (1-5)",       None),
    ("tilt_check",          "Tilt check",             None),
    ("session_position",    "Pos. session",           None),
    ("pregame_note",        "Pre-game note",          None),
    ("key_takeaway",        "Retenu (mot-clé)",       None),
    ("game_review",         "Game review",            None),
    # Auto-computed from Riot API
    ("kda_ratio",           "KDA ratio",              _round2),
    ("control_wards_purchased", "Control wards achetées", None),
    ("wards_placed",        "Wards posées",           None),
    ("wards_killed",        "Wards tuées",            None),
    ("solo_kills",          "Solo kills",             None),
    ("match_id",            "Match ID",               None),  # for deduplication
]

SESSION_COLUMNS: list[tuple[str, str, Callable | None]] = [
    ("session_id",          "Session #",              None),
    ("session_date",        "Date",                   _date),
    ("start_time",          "Heure début",            None),
    ("end_time",            "Heure fin",              None),
    ("mental_pregame",      "Mental pré (1-5)",       None),
    ("game_count",          "Nb games",               None),
    ("wins",                "Victoires",              None),
    ("losses",              "Défaites",               None),
    ("winrate",             "Winrate %",              _pct),
    ("lp_delta",            "LP delta",               None),
    ("end_streak",          "Streak fin",             None),
    ("pause_taken",         "Pause prise ?",          None),
    ("session_notes",       "Notes session",          None),
]
