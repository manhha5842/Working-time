#!/usr/bin/env python3
"""Generate README dashboard from archived WakaTime daily JSON files."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TIMEZONE = "Asia/Ho_Chi_Minh"
DATA_DIR = Path("data")
README = Path("README.md")


def human_duration(seconds: float) -> str:
    minutes = int(round(seconds / 60))
    hours, minutes = divmod(minutes, 60)
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"


def load_daily_records() -> list[dict]:
    records: list[dict] = []
    for path in sorted(DATA_DIR.glob("*/*/*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        data = payload.get("data") or []
        if not data:
            continue

        summary = data[0]
        day_str = summary.get("range", {}).get("date") or path.stem
        try:
            day = date.fromisoformat(day_str)
        except ValueError:
            continue

        grand_total = summary.get("grand_total") or {}
        total_seconds = float(grand_total.get("total_seconds") or 0)

        records.append(
            {
                "date": day,
                "seconds": total_seconds,
                "languages": summary.get("languages") or [],
                "projects": summary.get("projects") or [],
                "editors": summary.get("editors") or [],
                "operating_systems": summary.get("operating_systems") or [],
            }
        )
    return records


def sum_between(records: list[dict], start: date, end: date) -> float:
    return sum(r["seconds"] for r in records if start <= r["date"] <= end)


def aggregate_named(records: list[dict], key: str) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for record in records:
        for item in record[key]:
            name = item.get("name") or "Unknown"
            totals[name] += float(item.get("total_seconds") or 0)
    return dict(sorted(totals.items(), key=lambda item: item[1], reverse=True))


def top_rows(items: dict[str, float], total: float, limit: int = 8) -> str:
    if not items:
        return "| No data yet | — | — |"

    rows = []
    for name, seconds in list(items.items())[:limit]:
        pct = (seconds / total * 100) if total else 0
        rows.append(f"| {name} | {human_duration(seconds)} | {pct:.1f}% |")
    return "\n".join(rows)


def weekly_rows(records: list[dict], today: date) -> str:
    by_day = {r["date"]: r["seconds"] for r in records}
    start = today - timedelta(days=6)
    rows = []
    for offset in range(7):
        day = start + timedelta(days=offset)
        rows.append(
            f"| {day.strftime('%a')} | {day.isoformat()} | {human_duration(by_day.get(day, 0))} |"
        )
    return "\n".join(rows)


def main() -> None:
    records = load_daily_records()
    now = datetime.now(ZoneInfo(TIMEZONE))
    today = now.date()

    total_seconds = sum(r["seconds"] for r in records)
    active_days = sum(1 for r in records if r["seconds"] > 0)
    daily_average = total_seconds / active_days if active_days else 0

    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    today_seconds = sum_between(records, today, today)
    week_seconds = sum_between(records, week_start, today)
    month_seconds = sum_between(records, month_start, today)
    year_seconds = sum_between(records, year_start, today)

    best_day = max(records, key=lambda r: r["seconds"], default=None)
    best_day_text = (
        f"{best_day['date'].isoformat()} ({human_duration(best_day['seconds'])})"
        if best_day and best_day["seconds"] > 0
        else "—"
    )

    languages = aggregate_named(records, "languages")
    projects = aggregate_named(records, "projects")
    editors = aggregate_named(records, "editors")
    systems = aggregate_named(records, "operating_systems")

    readme = f"""# ⏱️ Working Time Dashboard

Personal coding-time archive powered by **WakaTime + GitHub Actions**.

> Last updated: **{now.strftime('%Y-%m-%d %H:%M')} ICT**

## Overview

| Metric | Coding time |
|---|---:|
| Today | **{human_duration(today_seconds)}** |
| This week | **{human_duration(week_seconds)}** |
| This month | **{human_duration(month_seconds)}** |
| This year | **{human_duration(year_seconds)}** |
| All archived time | **{human_duration(total_seconds)}** |
| Daily average (active days) | **{human_duration(daily_average)}** |
| Active days | **{active_days}** |
| Best day | **{best_day_text}** |

## Last 7 Days

| Day | Date | Coding time |
|---|---|---:|
{weekly_rows(records, today)}

## Top Languages

| Language | Time | Share |
|---|---:|---:|
{top_rows(languages, total_seconds)}

## Top Projects

| Project | Time | Share |
|---|---:|---:|
{top_rows(projects, total_seconds)}

## Editors

| Editor | Time | Share |
|---|---:|---:|
{top_rows(editors, total_seconds)}

## Operating Systems

| OS | Time | Share |
|---|---:|---:|
{top_rows(systems, total_seconds)}

## How it works

```text
WakaTime API
    ↓
GitHub Actions (daily)
    ↓
data/YYYY/MM/YYYY-MM-DD.json
    ↓
scripts/generate_readme.py
    ↓
README.md
```

The workflow refreshes the most recent **7 days** on every run, so a missed or delayed run can recover automatically.

### Required secret

Create this repository secret in **Settings → Secrets and variables → Actions**:

```text
WAKATIME_API_KEY
```

Never commit the API key into the repository.
"""

    README.write_text(readme, encoding="utf-8")
    print("README.md generated")


if __name__ == "__main__":
    main()
