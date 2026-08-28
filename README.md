# ⏱️ Working Time Dashboard

Personal coding-time archive powered by **WakaTime + GitHub Actions**.

> Dashboard data will appear after the first successful workflow run.

## Overview

| Metric | Coding time |
|---|---:|
| Today | — |
| This week | — |
| This month | — |
| This year | — |
| All archived time | — |
| Daily average (active days) | — |
| Active days | — |
| Best day | — |

## Last 7 Days

The workflow will populate this section automatically.

## Top Languages

The workflow will populate this section automatically.

## Top Projects

The workflow will populate this section automatically.

## Editors

The workflow will populate this section automatically.

## Operating Systems

The workflow will populate this section automatically.

## How it works

```text
WakaTime API
    ↓
GitHub Actions (daily at 02:10 ICT)
    ↓
data/YYYY/MM/YYYY-MM-DD.json
    ↓
scripts/generate_readme.py
    ↓
README.md
```

Every run refreshes the most recent **7 days**, helping recover data if a scheduled workflow is skipped or WakaTime data arrives late.

## Setup

Create a repository secret at **Settings → Secrets and variables → Actions → New repository secret**:

```text
WAKATIME_API_KEY
```

Then open **Actions → Backup WakaTime and update dashboard → Run workflow** to trigger the first import manually.

> Never commit your WakaTime API key into this repository.
