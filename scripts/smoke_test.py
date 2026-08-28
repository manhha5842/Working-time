#!/usr/bin/env python3
"""Cheap CI smoke checks for the static dashboard."""
import json,re
from pathlib import Path
html=Path('site/index.html').read_text(encoding='utf-8')
js=Path('site/app.js').read_text(encoding='utf-8')
data=json.loads(Path('site/dashboard.json').read_text(encoding='utf-8'))
required=['summary','comparison','dailyChart','timeline','projects','projectDetail','categoriesChart','aiHero','aiHumanChart','diffChart','modelsChart','editorsChart','languagesChart','osChart','machinesChart','weekdaysChart','health']
missing=[x for x in required if f'id="{x}"' not in html]
if missing:raise SystemExit(f'Missing required DOM ids: {missing}')
if 'undefined -' in js or 'undefined ·' in js:raise SystemExit('Suspicious hard-coded undefined label found')
if not isinstance(data.get('daily'),list):raise SystemExit('dashboard.json missing daily[]')
if data.get('schema_version',0)<3:raise SystemExit(f"dashboard schema too old: {data.get('schema_version')}")
if data['daily']:
    d=data['daily'][-1]
    for key in ['projects','languages','editors','operating_systems','machines','categories','dependencies','ai','timelines']:
        if key not in d:raise SystemExit(f'Latest day missing {key}')
print(f"Smoke test OK: {len(data['daily'])} archived daily records, schema {data['schema_version']}")
