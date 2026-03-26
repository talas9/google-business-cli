"""Fetch daily Google Ads performance and update SQLite database.

Usage:
    python fetch_daily.py                    # Last 3 days (covers attribution backfill)
    python fetch_daily.py --days 7           # Last 7 days
    python fetch_daily.py --from 2026-03-01 --to 2026-03-24
    python fetch_daily.py --push             # Also git commit + push
    python fetch_daily.py --config           # Also snapshot campaign configs

All configuration via .env or environment variables. See .env.example.
"""
import argparse
import os
import subprocess
import sys
from datetime import datetime, timedelta

from gads_lib import (
    CUSTOMER_ID,
    DB_PATH,
    PROJECT_ROOT,
    get_credentials,
    get_db,
    run_gaql,
    today_local,
)


def fetch_performance(creds, date_from, date_to):
    query = f"""
    SELECT segments.date, campaign.name, campaign.id, campaign.status,
           campaign.advertising_channel_type, metrics.cost_micros,
           metrics.conversions, metrics.clicks, metrics.impressions,
           metrics.conversions_value, metrics.all_conversions, metrics.interactions
    FROM campaign
    WHERE segments.date BETWEEN '{date_from}' AND '{date_to}'
    ORDER BY segments.date, campaign.name
    """
    rows = run_gaql(creds, query)
    parsed = []
    for r in rows:
        seg, camp, m = r.get("segments", {}), r.get("campaign", {}), r.get("metrics", {})
        parsed.append((
            seg.get("date", ""), camp.get("name", ""), camp.get("id", ""),
            camp.get("advertisingChannelType", ""), camp.get("status", ""),
            int(m.get("impressions", 0)), int(m.get("clicks", 0)),
            float(m.get("conversions", 0)), int(m.get("costMicros", 0)) / 1_000_000,
            float(m.get("conversionsValue", 0)), float(m.get("allConversions", 0)),
            int(m.get("interactions", 0)),
        ))
    return parsed


def main():
    if not CUSTOMER_ID:
        print("ERROR: GOOGLE_ADS_CUSTOMER_ID not set. See .env.example.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Fetch Google Ads daily performance")
    parser.add_argument("--days", type=int, default=3, help="Days to fetch (default: 3)")
    parser.add_argument("--from", dest="date_from", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--to", dest="date_to", help="End date (YYYY-MM-DD)")
    parser.add_argument("--push", action="store_true", help="Git commit + push after update")
    parser.add_argument("--config", action="store_true", help="Also snapshot campaign configs")
    args = parser.parse_args()

    if args.date_from and args.date_to:
        date_from, date_to = args.date_from, args.date_to
    else:
        date_to = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        date_from = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")

    print(f"Fetching: {date_from} to {date_to}")
    creds = get_credentials()
    rows = fetch_performance(creds, date_from, date_to)
    print(f"  Got {len(rows)} rows")

    conn = get_db()
    for row in rows:
        conn.execute(
            """INSERT OR REPLACE INTO daily_performance
            (date, campaign_name, campaign_id, channel_type, status,
             impressions, clicks, conversions, cost, conv_value,
             all_conversions, interactions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", row)
    conn.commit()
    conn.close()
    print(f"  ✓ Updated {len(rows)} rows")

    if args.push:
        os.chdir(str(PROJECT_ROOT))
        subprocess.run(["git", "add", str(DB_PATH)], check=True)
        subprocess.run(["git", "commit", "-m", f"data: fetch {date_from} to {date_to}"], check=False)
        subprocess.run(["git", "pull", "--rebase"], check=False)
        subprocess.run(["git", "push"], check=False)
        print("  ✓ Git sync done")

    print("Done.")


if __name__ == "__main__":
    main()
