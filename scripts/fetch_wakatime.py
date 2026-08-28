#!/usr/bin/env python3
"""Archive WakaTime summaries and duration slices without exposing the API key."""
from __future__ import annotations
import base64,json,os,time
from datetime import datetime,timedelta
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from zoneinfo import ZoneInfo

SUMMARY_API_URL="https://wakatime.com/api/v1/users/current/summaries"
DURATIONS_API_URL="https://wakatime.com/api/v1/users/current/durations"
TIMEZONE="Asia/Ho_Chi_Minh"; BACKFILL_DAYS=30; REFRESH_DAYS=7
DATA_DIR=Path("data"); TIMELINE_DIR=Path("timeline")
TIMELINE_SLICES=("project","language","category","editor","os","machine")

def request_json(api_key,url,params):
    credentials=base64.b64encode(f"{api_key}:".encode()).decode()
    req=Request(f"{url}?{urlencode(params)}",headers={"Authorization":f"Basic {credentials}","User-Agent":"working-time-github-action/2.0","Accept":"application/json"})
    with urlopen(req,timeout=35) as response:return json.load(response)

def summary_path(day):
    y,m,_=day.split("-");return DATA_DIR/y/m/f"{day}.json"

def timeline_path(day,slice_by):
    y,m,_=day.split("-");return TIMELINE_DIR/slice_by/y/m/f"{day}.json"

def legacy_timeline_path(day):
    y,m,_=day.split("-");return TIMELINE_DIR/y/m/f"{day}.json"

def save_json(path,payload):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def should_fetch(path,day,today):return not path.exists() or (today-day).days<REFRESH_DAYS

def sync_one(label,api_key,day,today,path,url,params):
    if not should_fetch(path,day,today):return "skipped"
    try:
        save_json(path,request_json(api_key,url,params));print(f"Saved {label} {day.isoformat()} -> {path}");time.sleep(.12);return "fetched"
    except HTTPError as exc:
        print(f"WARN {label} {day.isoformat()}: HTTP {exc.code}; keeping archive");return "failed"
    except (URLError,TimeoutError) as exc:
        print(f"WARN {label} {day.isoformat()}: {exc}; keeping archive");return "failed"

def main():
    api_key=os.environ.get("WAKATIME_API_KEY","").strip()
    if not api_key:raise SystemExit("WAKATIME_API_KEY is not configured")
    today=datetime.now(ZoneInfo(TIMEZONE)).date();counts={"summary":{"fetched":0,"skipped":0,"failed":0}}
    for s in TIMELINE_SLICES:counts[s]={"fetched":0,"skipped":0,"failed":0}
    for offset in range(BACKFILL_DAYS-1,-1,-1):
        day=today-timedelta(days=offset);text=day.isoformat()
        st=sync_one("summary",api_key,day,today,summary_path(text),SUMMARY_API_URL,{"start":text,"end":text,"timezone":TIMEZONE});counts["summary"][st]+=1
        for slice_by in TIMELINE_SLICES:
            path=timeline_path(text,slice_by)
            # Existing project archives are valid fallbacks; avoid a needless historical refetch.
            if slice_by=="project" and not path.exists() and legacy_timeline_path(text).exists() and (today-day).days>=REFRESH_DAYS:
                counts[slice_by]["skipped"]+=1;continue
            st=sync_one(f"duration/{slice_by}",api_key,day,today,path,DURATIONS_API_URL,{"date":text,"timezone":TIMEZONE,"slice_by":slice_by});counts[slice_by][st]+=1
    print(f"Archive sync complete: {counts}; window={BACKFILL_DAYS}d refresh={REFRESH_DAYS}d")
if __name__=="__main__":main()
