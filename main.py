"""
main.py — RPC Dashboard FastAPI application entry point.
Includes the nudge/reminder engine based on time of day and task status.
"""

from contextlib import asynccontextmanager
from datetime import date as dt_date, datetime
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import init_db, get_db
from routine_data import (
    get_blocks_for_day,
    PRIORITY_RULES,
    TRACKING_RULES,
    WEEKLY_CADENCE,
    PROJECT_CATEGORIES,
)
from routers import blocks, tasks, projects, picklist, future_walk, closeout


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="RPC Operating Dashboard", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Register all routers
app.include_router(blocks.router)
app.include_router(tasks.router)
app.include_router(projects.router)
app.include_router(picklist.router)
app.include_router(future_walk.router)
app.include_router(closeout.router)


# ── Nudge engine ─────────────────────────────────────────────────────────────
def get_nudges(weekday: int, hour: float, blocks_status: dict[str, str]) -> list[dict]:
    """Return time-aware priority nudges for the current moment."""
    nudges: list[dict[str, Any]] = []
    day_blocks = get_blocks_for_day(weekday)

    # Find the current or next block
    current = next(
        (b for b in day_blocks if b["start_hour"] <= hour < b["end_hour"]), None
    )
    upcoming = next(
        (b for b in day_blocks if b["start_hour"] > hour), None
    )

    if current and not current["is_lunch"]:
        status = blocks_status.get(current["id"], "pending")
        if status == "pending":
            nudges.append({
                "level": "info",
                "icon": "🕐",
                "text": f"You should be on: <strong>{current['label']}</strong> ({current['time_range']})",
            })
        elif status == "in-progress":
            nudges.append({
                "level": "success",
                "icon": "✅",
                "text": f"In progress: <strong>{current['label']}</strong> — keep going!",
            })

    # Warn if a block was skipped/missed
    missed = [
        b for b in day_blocks
        if b["end_hour"] <= hour
        and not b["is_lunch"]
        and blocks_status.get(b["id"], "pending") not in ("done", "skipped")
    ]
    for b in missed[-2:]:  # show last 2 max
        nudges.append({
            "level": "warning",
            "icon": "⚠️",
            "text": f"Not marked done: <strong>{b['label']}</strong> ({b['time_range']}) — update status or notes.",
        })

    # Thursday JSR hard deadline
    if weekday == 3 and hour >= 8.5 and hour < 9.0:
        nudges.append({
            "level": "critical",
            "icon": "🚨",
            "text": "JSR due at 9:00 AM — submit NOW if not done!",
        })

    # Friday weekly summary
    if weekday == 4 and hour >= 8.5 and hour < 9.0:
        nudges.append({
            "level": "critical",
            "icon": "🚨",
            "text": "Weekly Summary due at 9:00 AM — send NOW if not done!",
        })

    # Afternoon: remind about closeout prep
    if 13.0 <= hour < 14.0 and blocks_status.get("closeout", "pending") == "pending":
        nudges.append({
            "level": "warning",
            "icon": "📋",
            "text": "Close-out window — finish notes, picklist, and confirm overnight is set.",
        })

    return nudges


# ── Main dashboard page ───────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, date: str = "", tab: str = "timeline"):
    target = date or dt_date.today().isoformat()
    try:
        d = dt_date.fromisoformat(target)
    except ValueError:
        d = dt_date.today()
        target = d.isoformat()

    now = datetime.now()
    hour = now.hour + now.minute / 60

    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT block_id, status FROM block_status WHERE date=?", (target,)
        )
        blocks_status = {r["block_id"]: r["status"] for r in rows}

        task_counts = await db.execute_fetchall(
            """SELECT list_type, COUNT(*) as cnt FROM tasks
               WHERE is_done=0 GROUP BY list_type"""
        )
        task_summary = {r["list_type"]: r["cnt"] for r in task_counts}

        # Critical / blocked tasks
        critical_tasks = await db.execute_fetchall(
            "SELECT id, text, owner FROM tasks WHERE is_done=0 AND (is_critical=1 OR is_blocked=1) ORDER BY is_critical DESC LIMIT 5"
        )
        critical_tasks = [dict(r) for r in critical_tasks]

        # Unowned tasks
        unowned = await db.execute_fetchall(
            "SELECT COUNT(*) as cnt FROM tasks WHERE is_done=0 AND (owner IS NULL OR owner='')"
        )
        unowned_count = unowned[0]["cnt"] if unowned else 0

        # Projects overdue/blocked
        flagged_projects = await db.execute_fetchall(
            "SELECT COUNT(*) as cnt FROM projects WHERE status IN ('Overdue','Blocked') OR owner=''"
        )
        flagged_proj_count = flagged_projects[0]["cnt"] if flagged_projects else 0

        # Picklist zero on-hands
        zero_oh = await db.execute_fetchall(
            "SELECT COUNT(*) as cnt FROM picklist WHERE date=? AND qty_onhand=0 AND is_ordered=0",
            (target,),
        )
        zero_onhand_count = zero_oh[0]["cnt"] if zero_oh else 0

    nudges = get_nudges(d.weekday(), hour, blocks_status)
    day_name = d.strftime("%A")
    weekly_note = WEEKLY_CADENCE.get(day_name, "")

    return templates.TemplateResponse(
            request,
            "index.html",
            {
            "target_date": target,
            "day_name": day_name,
            "tab": tab,
            "nudges": nudges,
            "task_summary": task_summary,
            "critical_tasks": critical_tasks,
            "unowned_count": unowned_count,
            "flagged_proj_count": flagged_proj_count,
            "zero_onhand_count": zero_onhand_count,
            "priority_rules": PRIORITY_RULES,
            "weekly_note": weekly_note,
            "categories": PROJECT_CATEGORIES,
            "now_str": now.strftime("%I:%M %p"),
        },
    )


# ── Weekly view page ──────────────────────────────────────────────────────────
@app.get("/weekly", response_class=HTMLResponse)
async def weekly_view(request: Request):
    today = dt_date.today()
    # Show Mon–Fri of current week
    weekday = today.weekday()
    monday = today.toordinal() - weekday
    week_days = [
        dt_date.fromordinal(monday + i) for i in range(5)
    ]

    async with get_db() as db:
        day_summaries = []
        for d in week_days:
            ds = d.isoformat()
            block_rows = await db.execute_fetchall(
                "SELECT block_id, status FROM block_status WHERE date=?", (ds,)
            )
            status_map = {r["block_id"]: r["status"] for r in block_rows}
            day_blocks = get_blocks_for_day(d.weekday())
            done = sum(1 for b in day_blocks if status_map.get(b["id"]) == "done")
            total = sum(1 for b in day_blocks if not b["is_lunch"])
            day_summaries.append({
                "date": ds,
                "name": d.strftime("%A"),
                "done": done,
                "total": total,
                "cadence_note": WEEKLY_CADENCE.get(d.strftime("%A"), ""),
            })

    return templates.TemplateResponse(
            request,
            "partials/weekly.html",
            {
            "week_days": day_summaries,
            "cadence": WEEKLY_CADENCE,
            "tracking_rules": TRACKING_RULES,
            "priority_rules": PRIORITY_RULES,
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
