"""
Google Sheets integration — pushes game data to the LoL Tracker spreadsheet.
Uses a service account for authentication (no OAuth flow needed).

Setup:
  1. Go to console.cloud.google.com → Create project → Enable Sheets API
  2. Create a service account → Download JSON key → save as service_account.json
  3. Share your Google Sheet with the service account email (editor access)
  4. Set GOOGLE_SPREADSHEET_ID in .env
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import gspread
from gspread.utils import ValueInputOption
from google.oauth2.service_account import Credentials

from config.settings import (
    GOOGLE_SERVICE_ACCOUNT_PATH,
    GOOGLE_SPREADSHEET_ID,
    SHEETS_GAME_LOG_TAB,
)
from config.sheets_schema import GAME_LOG_COLUMNS
from collector.models import ParticipantStats
from pipeline.load_db import get_games_ordered_for_sessions

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

_client: gspread.Client | None = None


def _raise_actionable_api_error(err: Exception) -> None:
    message = str(err)
    if "operation is not supported for this document" in message.lower():
        raise RuntimeError(
            "Google Sheets push failed: target document is not a native Google Sheet. "
            "Create/convert the file to Google Sheets format (not .xlsx in Drive), "
            "then use its ID in GOOGLE_SPREADSHEET_ID and share it with the service account."
        ) from err
    raise err


def _get_client() -> gspread.Client:
    global _client
    if _client is None:
        creds = Credentials.from_service_account_file(
            GOOGLE_SERVICE_ACCOUNT_PATH, scopes=SCOPES
        )
        _client = gspread.authorize(creds)
    return _client


def _format_value(val: Any, formatter) -> Any:
    if val is None:
        return ""
    if formatter:
        try:
            return formatter(val)
        except Exception:
            return str(val)
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, bool):
        return "Oui" if val else "Non"
    return val


def _build_session_map() -> dict[str, tuple[int, int]]:
    """
    Build session metadata from DB chronology.
    Rules:
      - New day -> session_id = 1, session_position = 1
      - Same day and gap > 1 hour -> session_id + 1, session_position = 1
      - Otherwise -> same session_id, session_position + 1
    """
    rows = get_games_ordered_for_sessions()
    if not rows:
        return {}

    sessions: dict[str, tuple[int, int]] = {}
    previous_game_date: datetime | None = None
    current_session_id = 1
    current_session_position = 1

    for match_id, game_date in rows:
        if previous_game_date is None:
            current_session_id = 1
            current_session_position = 1
        else:
            same_day = game_date.date() == previous_game_date.date()
            if not same_day:
                current_session_id = 1
                current_session_position = 1
            else:
                gap_seconds = (game_date - previous_game_date).total_seconds()
                if gap_seconds > 3600:
                    current_session_id += 1
                    current_session_position = 1
                else:
                    current_session_position += 1

        sessions[match_id] = (current_session_id, current_session_position)
        previous_game_date = game_date

    return sessions


def _stats_dict_with_session(stats: ParticipantStats, session_map: dict[str, tuple[int, int]]) -> dict[str, Any]:
    stats_dict = stats.model_dump()
    session_values = session_map.get(stats.match_id)
    if session_values:
        stats_dict["session_id"] = session_values[0]
        stats_dict["session_position"] = session_values[1]
    return stats_dict


def append_game_to_sheets(stats: ParticipantStats) -> None:
    """
    Appends a single game row to the Game Log sheet.
    Only writes API-collected fields — manual fields (review, mental, etc.)
    are left empty for you to fill in Sheets.
    """
    if not GOOGLE_SPREADSHEET_ID:
        logger.warning("GOOGLE_SPREADSHEET_ID not set — skipping Sheets push.")
        return

    try:
        client = _get_client()
        spreadsheet = client.open_by_key(GOOGLE_SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(SHEETS_GAME_LOG_TAB)

        session_map = _build_session_map()
        stats_dict = _stats_dict_with_session(stats, session_map)
        row = [
            _format_value(stats_dict.get(field), fmt)
            for field, _, fmt in GAME_LOG_COLUMNS
        ]

        worksheet.append_row(row, value_input_option=ValueInputOption.user_entered)
        logger.info(f"Appended game {stats.match_id} to Sheets.")

    except gspread.exceptions.SpreadsheetNotFound:
        logger.error(f"Spreadsheet not found: {GOOGLE_SPREADSHEET_ID}")
        raise
    except gspread.exceptions.WorksheetNotFound:
        logger.error(f"Worksheet '{SHEETS_GAME_LOG_TAB}' not found.")
        raise
    except gspread.exceptions.APIError as e:
        _raise_actionable_api_error(e)
    except Exception as e:
        logger.error(f"Sheets append failed: {e}")
        raise


def ensure_headers(tab_name: str = SHEETS_GAME_LOG_TAB) -> None:
    """
    Writes column headers to row 1 of the sheet if not already present.
    Safe to call multiple times.
    """
    if not GOOGLE_SPREADSHEET_ID:
        return

    try:
        client = _get_client()
        spreadsheet = client.open_by_key(GOOGLE_SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(tab_name)
    except gspread.exceptions.APIError as e:
        _raise_actionable_api_error(e)

    headers = [header for _, header, _ in GAME_LOG_COLUMNS]
    first_row = worksheet.row_values(1)

    if first_row != headers:
        worksheet.update(range_name="A1", values=[headers])
        logger.info(f"Headers written to '{tab_name}'.")


def bulk_push_games(stats_list: list[ParticipantStats]) -> None:
    """
    Push multiple games at once (used by backfill script).
    More efficient than appending one by one.
    """
    if not GOOGLE_SPREADSHEET_ID or not stats_list:
        return

    try:
        client = _get_client()
        spreadsheet = client.open_by_key(GOOGLE_SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(SHEETS_GAME_LOG_TAB)
    except gspread.exceptions.APIError as e:
        _raise_actionable_api_error(e)

    session_map = _build_session_map()
    rows = []
    for stats in sorted(stats_list, key=lambda s: s.game_date):
        stats_dict = _stats_dict_with_session(stats, session_map)
        row = [
            _format_value(stats_dict.get(field), fmt)
            for field, _, fmt in GAME_LOG_COLUMNS
        ]
        rows.append(row)

    try:
        worksheet.append_rows(rows, value_input_option=ValueInputOption.user_entered)
    except gspread.exceptions.APIError as e:
        _raise_actionable_api_error(e)
    logger.info(f"Bulk pushed {len(rows)} games to Sheets.")
