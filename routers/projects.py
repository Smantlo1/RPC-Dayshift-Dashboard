"""
routers/projects.py — Tracking Sheets tab: local project log + live Excel viewer.
"""

import time
from datetime import date as dt_date, datetime
from fastapi import APIRouter, Form, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from database import get_db
from routine_data import PROJECT_CATEGORIES, PROJECT_STATUSES, TRACKING_SHEET_VIEW_URL
from sheet_fetcher import get_sheet_data, status_class

router = APIRouter(prefix="/projects", tags=["projects"])
templates = Jinja2Templates(directory="templates")


async def _render(request: Request) -> HTMLResponse:
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM projects ORDER BY category, id"
        )
        projects = [dict(r) for r in rows]

    # Group by category
    grouped: dict[str, list] = {cat: [] for cat in PROJECT_CATEGORIES}
    for p in projects:
        cat = p["category"] if p["category"] in PROJECT_CATEGORIES else PROJECT_CATEGORIES[0]
        grouped[cat].append(p)

    # Summary: overdue or unowned
    flagged = [
        p for p in projects
        if p["status"] in ("Overdue", "Blocked") or not p["owner"].strip()
    ]

    return templates.TemplateResponse(
            request,
            "partials/projects.html",
            {
            "grouped":   grouped,
            "flagged":   flagged,
            "categories": PROJECT_CATEGORIES,
            "statuses":  PROJECT_STATUSES,
            "view_url":  TRACKING_SHEET_VIEW_URL,
        },
    )


@router.get("/", response_class=HTMLResponse)
async def get_projects(request: Request):
    return await _render(request)


@router.post("/add", response_class=HTMLResponse)
async def add_project(
    request: Request,
    category: str = Form(...),
    name: str = Form(...),
    status: str = Form("On Track"),
    owner: str = Form(""),
    due_date: str = Form(""),
    notes: str = Form(""),
    add_on_order: str = Form(""),
):
    if not name.strip():
        return await _render(request)

    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO projects (category, name, status, owner, due_date, notes, add_on_order, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now','localtime'))
            """,
            (category, name.strip(), status, owner.strip(), due_date, notes, add_on_order),
        )
        await db.commit()

    return await _render(request)


@router.post("/{proj_id}/update", response_class=HTMLResponse)
async def update_project(
    request: Request,
    proj_id: int,
    status: str = Form(...),
    owner: str = Form(""),
    notes: str = Form(""),
    due_date: str = Form(""),
    add_on_order: str = Form(""),
):
    async with get_db() as db:
        await db.execute(
            """
            UPDATE projects SET status=?, owner=?, notes=?, due_date=?, add_on_order=?,
            last_updated=datetime('now','localtime') WHERE id=?
            """,
            (status, owner.strip(), notes, due_date, add_on_order, proj_id),
        )
        await db.commit()

    return await _render(request)


@router.post("/{proj_id}/delete", response_class=HTMLResponse)
async def delete_project(request: Request, proj_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM projects WHERE id=?", (proj_id,))
        await db.commit()

    return await _render(request)


# ── Live sheet viewer ─────────────────────────────────────────────────────────

@router.get("/sheet", response_class=HTMLResponse)
async def sheet_viewer(
    request: Request,
    sheet: int = Query(default=0, ge=0),
    force: int = Query(default=0),
):
    """Return the parsed Excel table as an HTML partial (loaded via HTMX)."""
    data = await get_sheet_data(force=bool(force))

    fetched_dt = (
        datetime.fromtimestamp(
        # monotonic → wall time approximation
            time.time() - (time.monotonic() - data["fetched_at"])
        ).strftime("%I:%M %p")
        if data["fetched_at"]
        else "never"
    )

    # Clamp sheet index
    sheets = data["sheets"] or []
    active = min(sheet, max(len(sheets) - 1, 0))

    return templates.TemplateResponse(
        request,
        "partials/sheet_view.html",
        {
            "sheets":       sheets,
            "active_sheet": active,
            "error":        data["error"],
            "refreshed_at": fetched_dt,
            "view_url":     TRACKING_SHEET_VIEW_URL,
            "status_class": status_class,
        },
    )
