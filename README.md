# ⚡ RPC Operating Dashboard

A lightweight, production-ready daily ops tool for the RPC-to-acting-RPM routine.
Built with **FastAPI + HTMX + Tailwind CSS + SQLite**.

## What it does

| Module | Purpose |
|---|---|
| **Timeline** | Full daily schedule, expandable time blocks, checklists, status, notes |
| **Tasks** | Three-list system: Today / Obstacles / Upcoming |
| **Projects** | Fixtures, Signage, Displays, RPS & SET ticket tracking |
| **Picklist** | Fixture picklist with zero on-hand alerts & backup plans |
| **Future Walk** | 2-week area walk log with auto obstacle creation |
| **Closeout** | 4-gate daily closeout with progress bar |
| **Weekly** | Week-at-a-glance with fixed cadence enforcement |

## Nudge Engine

The dashboard provides **time-aware priority nudges** based on:
- Which time block you should currently be in
- Blocks that are past-due and not marked done
- Thursday 9 AM JSR hard deadline alert
- Friday 9 AM Weekly Summary hard deadline alert
- Afternoon closeout reminders

## Priority Rules (always visible)

1. Make sure TODAY's work gets done.
2. Make sure TOMORROW is set up.
3. Escalate anything that could impact phasing — IMMEDIATELY.

## Tracking Rules

- Keep only 3 lists: **Today**, **Obstacles**, **Upcoming**
- Past due → escalate SAME DAY
- 24h → follow up | 48h → escalate

## Start the dashboard

```bat
start.bat
```

Or manually:
```bat
.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8001
```

Then open: **http://127.0.0.1:8001/**

## Tech stack

- **Backend**: FastAPI + aiosqlite (raw SQLite, no ORM bloat)
- **Frontend**: HTMX + Tailwind CDN (no build step, minimal memory)
- **Persistence**: SQLite (`dashboard.db`) — a single file, easy to back up
- **Styling**: Walmart color system (WCAG 2.2 AA)

## File structure

```
rpc_dashboard/
  main.py              # FastAPI app + nudge engine
  routine_data.py      # Single source of truth for all time blocks
  database.py          # SQLite schema + async context manager
  routers/
    blocks.py          # Time block status + checklist
    tasks.py           # Three-list task system
    projects.py        # Project tracking
    picklist.py        # Fixture picklist
    future_walk.py     # Future walk log
    closeout.py        # Daily closeout
  templates/
    base.html          # Nav + Tailwind config
    index.html         # Main tabbed layout + nudge bar
    partials/          # HTMX-swapped content partials
  static/
    app.js             # Live clock, auto-expand, keyboard shortcut (?)
  dashboard.db         # Persistent SQLite data (auto-created)
```
