#!/usr/bin/env python3
"""Fetch recent WakaTime daily summaries and persist them as raw JSON."""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

API_URL = "https://wakatime.com/api/v1/users/current/summaries"
TIMEZONE = "Asia/Ho_Chi_Minh"
LOOKBACK_DAYS = 7
DATA_DIR = Path("data")


def fetch_day(api_key: str, day: str) -> dict:
    query = urlencode({"start": day, "end": day, "timezone": TIMEZONE})
    credentials = base64.b64encode(f"{api_key}:".encode()).decode()
    request = Request(
        f"{API_URL}?{query}",
        headers={
            "Authorization": f"Basic {credentials}",
            "User-Agent": "working-time-github-action/1.0",
            "Accept": "application/json",
        },
    )

    with urlopen(request, timeout=30) as response:
        return json.load(response)


def save_day(day: str, payload: dict) -> Path:
    year, month, _ = day.split("-")
    output_dir = DATA_DIR / year / month
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{day}.json"
    output_file.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_file


def main() -> None:
    api_key = os.environ.get("WAKATIME_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("WAKATIME_API_KEY is not configured")

    today = datetime.now(ZoneInfo(TIMEZONE)).date()

    # Include today and the previous 6 days. Re-fetching makes the archive
    # self-healing if a scheduled workflow was skipped or WakaTime was delayed.
    for offset in range(LOOKBACK_DAYS - 1, -1, -1):
        day = (today - timedelta(days=offset)).isoformat()
        payload = fetch_day(api_key, day)
        output = save_day(day, payload)
        print(f"Saved {day} -> {output}")


if __name__ == "__main__":
    main()
