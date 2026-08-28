#!/usr/bin/env python3
"""Archive WakaTime daily summaries with a 30-day backfill window.

Missing days in the last 30 days are backfilled automatically. Existing data from
recent days is refreshed because WakaTime can update summaries after the fact.
Older archived days are left untouched to keep daily API usage small.
"""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

API_URL = "https://wakatime.com/api/v1/users/current/summaries"
TIMEZONE = "Asia/Ho_Chi_Minh"
BACKFILL_DAYS = 30
REFRESH_DAYS = 7
DATA_DIR = Path("data")


def fetch_day(api_key: str, day: str) -> dict:
    query = urlencode({"start": day, "end": day, "timezone": TIMEZONE})
    credentials = base64.b64encode(f"{api_key}:".encode()).decode()
    request = Request(
        f"{API_URL}?{query}",
        headers={
            "Authorization": f"Basic {credentials}",
            "User-Agent": "working-time-github-action/1.1",
            "Accept": "application/json",
        },
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def output_path(day: str) -> Path:
    year, month, _ = day.split("-")
    return DATA_DIR / year / month / f"{day}.json"


def save_day(day: str, payload: dict) -> Path:
    path = output_path(day)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def should_fetch(day, today) -> bool:
    path = output_path(day.isoformat())
    age_days = (today - day).days
    return not path.exists() or age_days < REFRESH_DAYS


def main() -> None:
    api_key = os.environ.get("WAKATIME_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("WAKATIME_API_KEY is not configured")

    today = datetime.now(ZoneInfo(TIMEZONE)).date()
    fetched = 0
    skipped = 0
    failed = 0

    # Walk oldest -> newest so a first run immediately builds a useful 30-day
    # archive. After that, only missing days plus the recent refresh window are
    # requested from WakaTime.
    for offset in range(BACKFILL_DAYS - 1, -1, -1):
        day = today - timedelta(days=offset)
        day_text = day.isoformat()

        if not should_fetch(day, today):
            skipped += 1
            continue

        try:
            payload = fetch_day(api_key, day_text)
            output = save_day(day_text, payload)
            fetched += 1
            print(f"Saved {day_text} -> {output}")
        except HTTPError as exc:
            failed += 1
            print(f"WARN {day_text}: WakaTime returned HTTP {exc.code}; keeping any existing archive")
        except (URLError, TimeoutError) as exc:
            failed += 1
            print(f"WARN {day_text}: WakaTime request failed: {exc}; keeping any existing archive")

    print(
        f"Archive sync complete: fetched={fetched}, skipped={skipped}, failed={failed}, "
        f"backfill_window={BACKFILL_DAYS}d, refresh_window={REFRESH_DAYS}d"
    )


if __name__ == "__main__":
    main()
