#!/usr/bin/env python3
"""Archive WakaTime summaries and project durations.

Missing days in the last 30 days are backfilled automatically. Existing data from
recent days is refreshed because WakaTime can update summaries/durations after
the fact. Duration requests use slice_by=project so the public archive never
needs to expose source file paths or entities.
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

SUMMARY_API_URL = "https://wakatime.com/api/v1/users/current/summaries"
DURATIONS_API_URL = "https://wakatime.com/api/v1/users/current/durations"
TIMEZONE = "Asia/Ho_Chi_Minh"
BACKFILL_DAYS = 30
REFRESH_DAYS = 7
DATA_DIR = Path("data")
TIMELINE_DIR = Path("timeline")


def request_json(api_key: str, url: str, params: dict[str, str]) -> dict:
    query = urlencode(params)
    credentials = base64.b64encode(f"{api_key}:".encode()).decode()
    request = Request(
        f"{url}?{query}",
        headers={
            "Authorization": f"Basic {credentials}",
            "User-Agent": "working-time-github-action/1.2",
            "Accept": "application/json",
        },
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def summary_path(day: str) -> Path:
    year, month, _ = day.split("-")
    return DATA_DIR / year / month / f"{day}.json"


def timeline_path(day: str) -> Path:
    year, month, _ = day.split("-")
    return TIMELINE_DIR / year / month / f"{day}.json"


def save_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def should_fetch(path: Path, day, today) -> bool:
    age_days = (today - day).days
    return not path.exists() or age_days < REFRESH_DAYS


def sync_one(label: str, api_key: str, day, today, path: Path, url: str, params: dict[str, str]) -> str:
    if not should_fetch(path, day, today):
        return "skipped"
    try:
        payload = request_json(api_key, url, params)
        output = save_json(path, payload)
        print(f"Saved {label} {day.isoformat()} -> {output}")
        return "fetched"
    except HTTPError as exc:
        print(f"WARN {label} {day.isoformat()}: WakaTime returned HTTP {exc.code}; keeping any existing archive")
        return "failed"
    except (URLError, TimeoutError) as exc:
        print(f"WARN {label} {day.isoformat()}: request failed: {exc}; keeping any existing archive")
        return "failed"


def main() -> None:
    api_key = os.environ.get("WAKATIME_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("WAKATIME_API_KEY is not configured")

    today = datetime.now(ZoneInfo(TIMEZONE)).date()
    counts = {"summaries": {"fetched": 0, "skipped": 0, "failed": 0}, "durations": {"fetched": 0, "skipped": 0, "failed": 0}}

    for offset in range(BACKFILL_DAYS - 1, -1, -1):
        day = today - timedelta(days=offset)
        day_text = day.isoformat()

        summary_status = sync_one(
            "summary",
            api_key,
            day,
            today,
            summary_path(day_text),
            SUMMARY_API_URL,
            {"start": day_text, "end": day_text, "timezone": TIMEZONE},
        )
        counts["summaries"][summary_status] += 1

        duration_status = sync_one(
            "durations",
            api_key,
            day,
            today,
            timeline_path(day_text),
            DURATIONS_API_URL,
            {"date": day_text, "timezone": TIMEZONE, "slice_by": "project"},
        )
        counts["durations"][duration_status] += 1

    print(
        "Archive sync complete: "
        f"summaries={counts['summaries']}, durations={counts['durations']}, "
        f"backfill_window={BACKFILL_DAYS}d, refresh_window={REFRESH_DAYS}d"
    )


if __name__ == "__main__":
    main()
