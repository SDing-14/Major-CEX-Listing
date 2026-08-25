"""
Sync new rows from listings.db into a Google Sheet.

Runs after each scrape cycle (see .github/workflows/scheduled_scrape.yml).
Uses a Google Cloud service account rather than a user OAuth flow, since this
has to run unattended in CI.

Required environment variables (set as GitHub Actions secrets):
  GOOGLE_SERVICE_ACCOUNT_JSON  - full contents of the service account key JSON
  GOOGLE_SHEET_ID              - the sheet's ID (from its URL:
                                  https://docs.google.com/spreadsheets/d/<ID>/edit)

Setup (one-time, done by a human, not this script):
  1. Create a service account in Google Cloud Console, generate a JSON key.
  2. Share the target Google Sheet with the service account's email
     (...@...iam.gserviceaccount.com) as an Editor.
  3. Put the JSON key contents and the sheet ID into the two secrets above.

The sheet's first row is expected to be a header: Ticker | Exchange |
Listing Date | Synced At. Data lives in the first worksheet/tab.
"""
import json
import os
import sqlite3
import sys

import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
HEADER = ["Ticker", "Exchange", "Listing Date", "Synced At"]


def get_worksheet():
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    sheet_id = os.environ.get("GOOGLE_SHEET_ID")

    if not creds_json or not sheet_id:
        return None

    creds_info = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    client = gspread.authorize(creds)

    sheet = client.open_by_key(sheet_id)
    ws = sheet.sheet1

    # Ensure header row exists (harmless if already present).
    first_row = ws.row_values(1)
    if first_row != HEADER:
        ws.update("A1", [HEADER])

    return ws


def fetch_existing_keys(ws):
    """Return the set of (exchange, ticker, listing_date) already in the
    sheet, so repeated runs only append genuinely new rows."""
    records = ws.get_all_values()[1:]  # skip header
    existing = set()
    for row in records:
        if len(row) < 3:
            continue
        ticker, exchange, listing_date = row[0], row[1], row[2]
        existing.add((exchange, ticker, listing_date))
    return existing


def main():
    ws = get_worksheet()
    if ws is None:
        print("GOOGLE_SERVICE_ACCOUNT_JSON / GOOGLE_SHEET_ID not set - skipping Sheets sync.")
        return

    conn = sqlite3.connect("listings.db")
    cur = conn.cursor()
    cur.execute("SELECT exchange, ticker, listing_date FROM listings")
    rows = cur.fetchall()
    conn.close()

    print(f"Checking {len(rows)} local listings against the Google Sheet...")
    existing = fetch_existing_keys(ws)
    print(f"{len(existing)} rows already in the sheet.")

    synced_at = __import__("time").strftime("%Y-%m-%d")
    new_rows = []
    for exchange, ticker, listing_date in rows:
        key = (exchange, ticker, listing_date)
        if key in existing:
            continue
        new_rows.append([ticker, exchange, listing_date, synced_at])
        existing.add(key)

    if new_rows:
        ws.append_rows(new_rows, value_input_option="USER_ENTERED")

    print(f"✓ Synced {len(new_rows)} new listing(s) to the Google Sheet.")


if __name__ == "__main__":
    main()
