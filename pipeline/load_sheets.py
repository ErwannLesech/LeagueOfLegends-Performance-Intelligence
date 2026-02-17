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
from google.oauth2.service_account import Credentials

from config.settings import (
    GOOGLE_SERVICE_ACCOUNT_PATH,
    GOOGLE_SPREADSHEET_ID,
    SHEETS_GAME_LOG_TAB,
)
from config.sheets_schema import GAME_LOG_COLUMNS
from collector.models import ParticipantStats

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

_client: gspread.Client | None = None


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

        stats_dict = stats.model_dump()
        row = [
            _format_value(stats_dict.get(field), fmt)
            for field, _, fmt in GAME_LOG_COLUMNS
        ]

        worksheet.append_row(row, value_input_option="USER_ENTERED")
        logger.info(f"Appended game {stats.match_id} to Sheets.")

    except gspread.exceptions.SpreadsheetNotFound:
        logger.error(f"Spreadsheet not found: {GOOGLE_SPREADSHEET_ID}")
        raise
    except gspread.exceptions.WorksheetNotFound:
        logger.error(f"Worksheet '{SHEETS_GAME_LOG_TAB}' not found.")
        raise
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

    client = _get_client()
    spreadsheet = client.open_by_key(GOOGLE_SPREADSHEET_ID)
    worksheet = spreadsheet.worksheet(tab_name)

    headers = [header for _, header, _ in GAME_LOG_COLUMNS]
    first_row = worksheet.row_values(1)

    if first_row != headers:
        worksheet.update("A1", [headers])
        logger.info(f"Headers written to '{tab_name}'.")


def bulk_push_games(stats_list: list[ParticipantStats]) -> None:
    """
    Push multiple games at once (used by backfill script).
    More efficient than appending one by one.
    """
    if not GOOGLE_SPREADSHEET_ID or not stats_list:
        return

    client = _get_client()
    spreadsheet = client.open_by_key(GOOGLE_SPREADSHEET_ID)
    worksheet = spreadsheet.worksheet(SHEETS_GAME_LOG_TAB)

    rows = []
    for stats in stats_list:
        stats_dict = stats.model_dump()
        row = [
            _format_value(stats_dict.get(field), fmt)
            for field, _, fmt in GAME_LOG_COLUMNS
        ]
        rows.append(row)

    worksheet.append_rows(rows, value_input_option="USER_ENTERED")
    logger.info(f"Bulk pushed {len(rows)} games to Sheets.")
