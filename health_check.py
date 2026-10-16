"""
Post-run health check for listings.db.

Looks at the newest `created_at` per exchange (when the scraper last ADDED a
row) and flags exchanges that have gone quiet for longer than they ever do in
practice. Exit code 1 makes the GitHub Actions job fail, which triggers
GitHub's failure e-mail to the repo owner; everything else is a warning
printed to the log and the job summary.

Thresholds are days without a single new row. They are loose on purpose:
Coinbase and Bybit genuinely go two or three weeks without a listing, and
Binance Futures has had month-long stretches with only TradFi contracts
(whose "Multiple TradFi ... Perpetual Contracts" announcements carry no
ticker and are therefore, correctly, not recorded).

Usage: python health_check.py [listings.db]
"""
import os
import sqlite3
import sys
from datetime import datetime, timezone

# exchange -> (fail_after_days, warn_after_days)
THRESHOLDS = {
    "Upbit":        (7, 4),
    "Bithumb":      (7, 4),
    "Okx":          (14, 7),
    "Binance Spot": (10, 5),
    "Coinbase":     (28, 14),
    "Bybit":        (28, 14),
    "Binance Perp": (None, 21),   # warn only, see module docstring
}


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else "listings.db"
    if not os.path.exists(db_path):
        print(f"✗ {db_path} not found")
        return 1

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    rows = conn.execute(
        "SELECT exchange, COUNT(*), MAX(created_at), MAX(listing_date) FROM listings GROUP BY exchange"
    ).fetchall()
    conn.close()
    by_ex = {r[0]: r for r in rows}

    now = datetime.now(timezone.utc)
    lines, failures, warnings = [], [], []
    for ex, (fail_d, warn_d) in THRESHOLDS.items():
        r = by_ex.get(ex)
        if not r or not r[2]:
            failures.append(f"{ex}: no rows at all")
            lines.append(f"| {ex} | 0 | — | — | ✗ no data |")
            continue
        last = datetime.strptime(r[2][:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        age = (now - last).days
        status = "ok"
        if fail_d is not None and age >= fail_d:
            status = "✗ FAIL"
            failures.append(f"{ex}: nothing new for {age} days (limit {fail_d})")
        elif age >= warn_d:
            status = "⚠ warn"
            warnings.append(f"{ex}: nothing new for {age} days")
        lines.append(f"| {ex} | {r[1]} | {r[2][:16]} ({age}d ago) | {r[3]} | {status} |")

    table = "| Exchange | Rows | Last new row | Newest listing | Status |\n|---|---|---|---|---|\n" + "\n".join(lines)
    print("\nHEALTH CHECK\n" + table)
    for w in warnings:
        print(f"⚠ {w}")
    for f in failures:
        print(f"✗ {f}")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write("## Listing scrape health\n\n" + table + "\n\n")
            for w in warnings:
                fh.write(f"- ⚠ {w}\n")
            for f in failures:
                fh.write(f"- ✗ **{f}**\n")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
