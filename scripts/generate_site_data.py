#!/usr/bin/env python3
"""Generate sanitized aggregate JSON for the static GitHub Pages dashboard."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TIMEZONE = "Asia/Ho_Chi_Minh"
DATA_DIR = Path("data")
SITE_DIR = Path("site")
OUTPUT = SITE_DIR / "dashboard.json"


def load_records() -> list[dict]:
    records: list[dict] = []
    for path in sorted(DATA_DIR.glob("*/*/*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        data = payload.get("data") or []
        if not data:
            continue

        summary = data[0]
        day_text = summary.get("range", {}).get("date") or path.stem
        try:
            day = date.fromisoformat(day_text)
        except ValueError:
            continue

        records.append({
            "date": day,
            "grand_total": summary.get("grand_total") or {},
            "projects": summary.get("projects") or [],
            "languages": summary.get("languages") or [],
            "editors": summary.get("editors") or [],
            "operating_systems": summary.get("operating_systems") or [],
            "categories": summary.get("categories") or [],
        })
    return records


def seconds(record: dict) -> float:
    return float(record["grand_total"].get("total_seconds") or 0)


def sum_named(records: list[dict], key: str) -> list[dict]:
    totals: dict[str, float] = defaultdict(float)
    for record in records:
        for item in record[key]:
            totals[item.get("name") or "Unknown"] += float(item.get("total_seconds") or 0)
    return [
        {"name": name, "seconds": round(value, 3)}
        for name, value in sorted(totals.items(), key=lambda x: x[1], reverse=True)
    ]


def ai_totals(records: list[dict]) -> dict:
    totals = {
        "ai_additions": 0,
        "ai_deletions": 0,
        "human_additions": 0,
        "human_deletions": 0,
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "output_tokens": 0,
        "prompt_length_sum": 0,
        "prompt_events": 0,
        "sessions": 0,
        "cost": 0.0,
    }
    models: dict[str, dict[str, float]] = defaultdict(lambda: {"lines": 0.0, "cost": 0.0})

    for record in records:
        grand = record["grand_total"]
        totals["ai_additions"] += int(grand.get("ai_additions") or 0)
        totals["ai_deletions"] += int(grand.get("ai_deletions") or 0)
        totals["human_additions"] += int(grand.get("human_additions") or 0)
        totals["human_deletions"] += int(grand.get("human_deletions") or 0)
        totals["input_tokens"] += int(grand.get("ai_input_tokens") or 0)
        totals["cached_input_tokens"] += int(grand.get("ai_cached_input_tokens") or 0)
        totals["output_tokens"] += int(grand.get("ai_output_tokens") or 0)
        totals["prompt_length_sum"] += int(grand.get("ai_prompt_length_sum") or 0)
        totals["prompt_events"] += int(grand.get("ai_prompt_events_total") or 0)
        totals["sessions"] += int(grand.get("ai_sessions") or 0)
        totals["cost"] += float(grand.get("ai_model_total_cost") or 0)

        breakdown = grand.get("ai_model_breakdown") or []
        if breakdown:
            for item in breakdown:
                name = item.get("name") or "Unknown"
                models[name]["lines"] += float(item.get("lines") or 0)
                models[name]["cost"] += float(item.get("cost") or 0)
        else:
            for name, line_count in (grand.get("ai_model_line_changes") or {}).items():
                models[name]["lines"] += float(line_count or 0)
            for name, model_cost in (grand.get("ai_model_costs") or {}).items():
                models[name]["cost"] += float(model_cost or 0)

    totals["cost"] = round(totals["cost"], 6)
    totals["models"] = [
        {"name": name, "lines": round(stats["lines"], 3), "cost": round(stats["cost"], 6)}
        for name, stats in sorted(
            models.items(), key=lambda x: (x[1]["lines"], x[1]["cost"]), reverse=True
        )
    ]
    return totals


def period_seconds(records: list[dict], start: date, end: date) -> float:
    return sum(seconds(record) for record in records if start <= record["date"] <= end)


def main() -> None:
    records = load_records()
    now = datetime.now(ZoneInfo(TIMEZONE))
    today = now.date()
    total = sum(seconds(record) for record in records)
    active = [record for record in records if seconds(record) > 0]

    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    best = max(records, key=seconds, default=None)

    payload = {
        "generated_at": now.isoformat(),
        "timezone": TIMEZONE,
        "overview": {
            "today_seconds": round(period_seconds(records, today, today), 3),
            "week_seconds": round(period_seconds(records, week_start, today), 3),
            "month_seconds": round(period_seconds(records, month_start, today), 3),
            "year_seconds": round(period_seconds(records, year_start, today), 3),
            "all_time_seconds": round(total, 3),
            "daily_average_seconds": round(total / len(active), 3) if active else 0,
            "active_days": len(active),
            "best_day": {
                "date": best["date"].isoformat(),
                "seconds": round(seconds(best), 3),
            } if best else None,
        },
        "daily": [
            {"date": record["date"].isoformat(), "seconds": round(seconds(record), 3)}
            for record in records
        ],
        "projects": sum_named(records, "projects"),
        "languages": sum_named(records, "languages"),
        "editors": sum_named(records, "editors"),
        "operating_systems": sum_named(records, "operating_systems"),
        "categories": sum_named(records, "categories"),
        "ai": ai_totals(records),
    }

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {OUTPUT}")


if __name__ == "__main__":
    main()
