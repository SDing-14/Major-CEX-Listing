"""
Sync new rows from listings.db into a Notion database.

Runs after each scrape cycle (see .github/workflows/scheduled_scrape.yml).
Uses the plain Notion REST API with an internal integration token - this is
intentionally independent of any Claude/MCP session, since it has to run
unattended in CI.

Required environment variables (set as GitHub Actions secrets):
  NOTION_TOKEN        - internal integration secret from notion.so/my-integrations
  NOTION_DATABASE_ID  - the target database's ID (32-char id in its URL)

Notion database is expected to have these properties (create once, manually
or via the Claude/Notion MCP setup step):
  Ticker        (title)
  Exchange      (select)
  Listing Date  (date)
  Synced At     (date)
"""
import os
import sqlite3
import sys
import time
import requests

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def get_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def fetch_existing_keys(token, database_id):
    """Return the set of (exchange, ticker, listing_date) already in Notion,
    so we only create pages for genuinely new rows instead of duplicating on
    every run."""
    existing = set()
    url = f"{NOTION_API}/databases/{database_id}/query"
    payload = {"page_size": 100}

    while True:
        resp = requests.post(url, headers=get_headers(token), json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        for page in data.get("results", []):
            props = page.get("properties", {})
            ticker = "".join(
                t.get("plain_text", "") for t in props.get("Ticker", {}).get("title", [])
            )
            exchange = (props.get("Exchange", {}).get("select") or {}).get("name", "")
            date_prop = (props.get("Listing Date", {}).get("date") or {}).get("start", "")
            existing.add((exchange, ticker, date_prop))

        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]

    return existing


def create_page(token, database_id, exchange, ticker, listing_date):
    url = f"{NOTION_API}/pages"
    payload = {
        "parent": {"database_id": database_id},
        "properties": {
            "Ticker": {"title": [{"text": {"content": ticker}}]},
            "Exchange": {"select": {"name": exchange}},
            "Listing Date": {"date": {"start": listing_date}},
            "Synced At": {"date": {"start": time.strftime("%Y-%m-%d")}},
        },
    }
    resp = requests.post(url, headers=get_headers(token), json=payload, timeout=30)
    resp.raise_for_status()


def main():
    token = os.environ.get("NOTION_TOKEN")
    database_id = os.environ.get("NOTION_DATABASE_ID")

    if not token or not database_id:
        print("NOTION_TOKEN / NOTION_DATABASE_ID not set - skipping Notion sync.")
        return

    conn = sqlite3.connect("listings.db")
    cur = conn.cursor()
    cur.execute("SELECT exchange, ticker, listing_date FROM listings")
    rows = cur.fetchall()
    conn.close()

    # Notion's date property wants YYYY-MM-DD; the sqlite db stores YYYY/MM/DD
    rows = [(ex, tk, dt.replace('/', '-')) for ex, tk, dt in rows]

    print(f"Checking {len(rows)} local listings against Notion...")
    existing = fetch_existing_keys(token, database_id)
    print(f"{len(existing)} rows already in Notion.")

    created = 0
    for exchange, ticker, listing_date in rows:
        key = (exchange, ticker, listing_date)
        if key in existing:
            continue
        try:
            create_page(token, database_id, exchange, ticker, listing_date)
            created += 1
            existing.add(key)  # avoid re-creating within this same run
        except requests.HTTPError as e:
            print(f"  ! Failed to sync {key}: {e}", file=sys.stderr)

    print(f"✓ Synced {created} new listing(s) to Notion.")


if __name__ == "__main__":
    main()
