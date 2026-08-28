#!/usr/bin/env python3
"""Generate sanitized WakaTime-like dashboard data from archived data."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TIMEZONE = "Asia/Ho_Chi_Minh"
TZ = ZoneInfo(TIMEZONE)
DATA_DIR = Path("data")
TIMELINE_DIR = Path("timeline")
SITE_DIR = Path("site")
OUTPUT = SITE_DIR / "dashboard.json"


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def timeline_items(day: date) -> list[dict]:
    path = TIMELINE_DIR / f"{day.year:04d}" / f"{day.month:02d}" / f"{day.isoformat()}.json"
    payload = load_json(path)
    result: list[dict] = []
    for item in payload.get("data") or []:
        start = float(item.get("time") or 0)
        duration = max(0.0, float(item.get("duration") or 0))
        if not start or not duration:
            continue
        local = datetime.fromtimestamp(start, tz=TZ)
        start_minute = local.hour * 60 + local.minute + local.second / 60
        result.append({
            "project": item.get("project") or "Unknown",
            "start_minute": round(start_minute, 3),
            "duration_seconds": round(duration, 3),
            "ai_additions": int(item.get("ai_additions") or 0),
            "ai_deletions": int(item.get("ai_deletions") or 0),
            "human_additions": int(item.get("human_additions") or 0),
            "human_deletions": int(item.get("human_deletions") or 0),
        })
    return result


def load_records() -> list[dict]:
    records: list[dict] = []
    for path in sorted(DATA_DIR.glob("*/*/*.json")):
        payload = load_json(path)
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
            "machines": summary.get("machines") or [],
            "categories": summary.get("categories") or [],
            "timeline": timeline_items(day),
        })
    return records


def seconds(record: dict) -> float:
    return float(record["grand_total"].get("total_seconds") or 0)


def named_items(items: list[dict]) -> list[dict]:
    return [{"name": item.get("name") or "Unknown", "seconds": round(float(item.get("total_seconds") or 0), 3)} for item in items]


def project_item(item: dict) -> dict:
    input_tokens = int(item.get("ai_input_tokens") or 0)
    cached_tokens = int(item.get("ai_cached_input_tokens") or 0)
    output_tokens = int(item.get("ai_output_tokens") or 0)
    return {
        "name": item.get("name") or "Unknown",
        "seconds": round(float(item.get("total_seconds") or 0), 3),
        "ai_additions": int(item.get("ai_additions") or 0),
        "ai_deletions": int(item.get("ai_deletions") or 0),
        "human_additions": int(item.get("human_additions") or 0),
        "human_deletions": int(item.get("human_deletions") or 0),
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_tokens,
        "output_tokens": output_tokens,
        "tokens": input_tokens + cached_tokens + output_tokens,
        "prompt_events": int(item.get("ai_prompt_events_total") or 0),
        "sessions": int(item.get("ai_sessions") or 0),
        "cost": round(float(item.get("ai_model_total_cost") or 0), 6),
        "models": [{"name": model.get("name") or "Unknown", "lines": float(model.get("lines") or 0), "cost": round(float(model.get("cost") or 0), 6)} for model in (item.get("ai_model_breakdown") or [])],
    }


def ai_item(grand: dict) -> dict:
    return {
        "ai_additions": int(grand.get("ai_additions") or 0),
        "ai_deletions": int(grand.get("ai_deletions") or 0),
        "human_additions": int(grand.get("human_additions") or 0),
        "human_deletions": int(grand.get("human_deletions") or 0),
        "input_tokens": int(grand.get("ai_input_tokens") or 0),
        "cached_input_tokens": int(grand.get("ai_cached_input_tokens") or 0),
        "output_tokens": int(grand.get("ai_output_tokens") or 0),
        "prompt_length_sum": int(grand.get("ai_prompt_length_sum") or 0),
        "prompt_events": int(grand.get("ai_prompt_events_total") or 0),
        "sessions": int(grand.get("ai_sessions") or 0),
        "cost": round(float(grand.get("ai_model_total_cost") or 0), 6),
        "models": [{"name": model.get("name") or "Unknown", "lines": float(model.get("lines") or 0), "cost": round(float(model.get("cost") or 0), 6)} for model in (grand.get("ai_model_breakdown") or [])],
    }


def daily_item(record: dict) -> dict:
    return {
        "date": record["date"].isoformat(),
        "seconds": round(seconds(record), 3),
        "projects": [project_item(item) for item in record["projects"]],
        "languages": named_items(record["languages"]),
        "editors": named_items(record["editors"]),
        "operating_systems": named_items(record["operating_systems"]),
        "machines": named_items(record["machines"]),
        "categories": named_items(record["categories"]),
        "ai": ai_item(record["grand_total"]),
        "timeline": record["timeline"],
    }


def period_seconds(records: list[dict], start: date, end: date) -> float:
    return sum(seconds(record) for record in records if start <= record["date"] <= end)


def main() -> None:
    records = load_records()
    now = datetime.now(TZ)
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
            "best_day": {"date": best["date"].isoformat(), "seconds": round(seconds(best), 3)} if best else None,
        },
        "daily": [daily_item(record) for record in records],
    }
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {OUTPUT}")


if __name__ == "__main__":
    main()
