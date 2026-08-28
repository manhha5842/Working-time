#!/usr/bin/env python3
"""Generate sanitized dashboard data from the durable WakaTime archive."""
from __future__ import annotations
import json
from datetime import date,datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
TIMEZONE="Asia/Ho_Chi_Minh";TZ=ZoneInfo(TIMEZONE);DATA_DIR=Path("data");TIMELINE_DIR=Path("timeline");SITE_DIR=Path("site");OUTPUT=SITE_DIR/"dashboard.json"
SLICES=("project","language","category","editor","os","machine")

def load_json(path):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError):return {}

def timeline_path(day,slice_by):return TIMELINE_DIR/slice_by/f"{day.year:04d}"/f"{day.month:02d}"/f"{day.isoformat()}.json"
def legacy_timeline_path(day):return TIMELINE_DIR/f"{day.year:04d}"/f"{day.month:02d}"/f"{day.isoformat()}.json"
def duration_name(item,slice_by):
    keys={"project":("project",),"language":("language",),"category":("category",),"editor":("editor",),"os":("os","operating_system"),"machine":("machine",)}[slice_by]
    for k in keys:
        if item.get(k):return str(item[k])
    return "Unknown"
def timeline_items(day,slice_by):
    path=timeline_path(day,slice_by)
    if slice_by=="project" and not path.exists():path=legacy_timeline_path(day)
    payload=load_json(path);result=[]
    for item in payload.get("data") or []:
        start=float(item.get("time") or 0);duration=max(0.0,float(item.get("duration") or 0))
        if not start or not duration:continue
        local=datetime.fromtimestamp(start,tz=TZ)
        result.append({"name":duration_name(item,slice_by),"start_minute":round(local.hour*60+local.minute+local.second/60,3),"duration_seconds":round(duration,3),"ai_additions":int(item.get("ai_additions") or 0),"ai_deletions":int(item.get("ai_deletions") or 0),"human_additions":int(item.get("human_additions") or 0),"human_deletions":int(item.get("human_deletions") or 0)})
    return result

def load_records():
    records=[]
    for path in sorted(DATA_DIR.glob("*/*/*.json")):
        payload=load_json(path);data=payload.get("data") or []
        if not data:continue
        s=data[0];text=s.get("range",{}).get("date") or path.stem
        try:d=date.fromisoformat(text)
        except ValueError:continue
        records.append({"date":d,"grand_total":s.get("grand_total") or {},"projects":s.get("projects") or [],"languages":s.get("languages") or [],"editors":s.get("editors") or [],"operating_systems":s.get("operating_systems") or [],"machines":s.get("machines") or [],"categories":s.get("categories") or [],"dependencies":s.get("dependencies") or [],"timelines":{k:timeline_items(d,k) for k in SLICES}})
    return records

def seconds(r):return float(r["grand_total"].get("total_seconds") or 0)
def named_items(items):return [{"name":x.get("name") or "Unknown","seconds":round(float(x.get("total_seconds") or 0),3)} for x in items if float(x.get("total_seconds") or 0)>0]
def models(item):return [{"name":m.get("name") or "Unknown","lines":float(m.get("lines") or 0),"cost":round(float(m.get("cost") or 0),6)} for m in item.get("ai_model_breakdown") or []]
def ai_fields(item):
    return {"ai_additions":int(item.get("ai_additions") or 0),"ai_deletions":int(item.get("ai_deletions") or 0),"human_additions":int(item.get("human_additions") or 0),"human_deletions":int(item.get("human_deletions") or 0),"input_tokens":int(item.get("ai_input_tokens") or 0),"cached_input_tokens":int(item.get("ai_cached_input_tokens") or 0),"output_tokens":int(item.get("ai_output_tokens") or 0),"prompt_length_sum":int(item.get("ai_prompt_length_sum") or 0),"prompt_length_avg":int(item.get("ai_prompt_length_avg") or 0),"prompt_length_avg_per_session":int(item.get("ai_prompt_length_avg_per_session") or 0),"prompt_length_median_per_session":int(item.get("ai_prompt_length_median_per_session") or 0),"prompt_events":int(item.get("ai_prompt_events_total") or 0),"prompts_avg_per_session":int(item.get("ai_prompt_events_avg_per_session") or 0),"prompts_median_per_session":int(item.get("ai_prompt_events_median_per_session") or 0),"sessions":int(item.get("ai_sessions") or 0),"cost":round(float(item.get("ai_model_total_cost") or 0),6),"models":models(item)}
def project_item(item):
    out={"name":item.get("name") or "Unknown","seconds":round(float(item.get("total_seconds") or 0),3)};out.update(ai_fields(item));out["tokens"]=out["input_tokens"]+out["cached_input_tokens"]+out["output_tokens"];return out
def daily_item(r):return {"date":r["date"].isoformat(),"seconds":round(seconds(r),3),"projects":[project_item(x) for x in r["projects"]],"languages":named_items(r["languages"]),"editors":named_items(r["editors"]),"operating_systems":named_items(r["operating_systems"]),"machines":named_items(r["machines"]),"categories":named_items(r["categories"]),"dependencies":named_items(r["dependencies"]),"ai":ai_fields(r["grand_total"]),"timelines":r["timelines"]}
def period_seconds(records,start,end):return sum(seconds(r) for r in records if start<=r["date"]<=end)

def main():
    records=load_records();now=datetime.now(TZ);today=now.date();active=[r for r in records if seconds(r)>0];best=max(records,key=seconds,default=None);first=min((r["date"] for r in records),default=None);last=max((r["date"] for r in records),default=None)
    total=sum(seconds(r) for r in records);week_start=today-timedelta(days=today.weekday());month_start=today.replace(day=1);year_start=today.replace(month=1,day=1)
    payload={"schema_version":3,"generated_at":now.isoformat(),"timezone":TIMEZONE,"archive":{"first_date":first.isoformat() if first else None,"last_date":last.isoformat() if last else None,"archived_days":len(records),"active_days":len(active)},"overview":{"today_seconds":round(period_seconds(records,today,today),3),"week_seconds":round(period_seconds(records,week_start,today),3),"month_seconds":round(period_seconds(records,month_start,today),3),"year_seconds":round(period_seconds(records,year_start,today),3),"all_archived_seconds":round(total,3),"daily_average_seconds":round(total/len(active),3) if active else 0,"active_days":len(active),"best_day":{"date":best["date"].isoformat(),"seconds":round(seconds(best),3)} if best else None},"daily":[daily_item(r) for r in records]}
    SITE_DIR.mkdir(parents=True,exist_ok=True);OUTPUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8");print(f"Generated {OUTPUT} with {len(records)} archived days")
if __name__=="__main__":main()
