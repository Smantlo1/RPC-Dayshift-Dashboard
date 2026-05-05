"""
routers/future_walk.py — Future Walk: upcoming areas, fixture checks, issue logging.
Auto-creates Obstacles tasks when problems are found.
"""

from datetime import date as dt_date
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from database import get_db

router = APIRouter(prefix="/future-walk", tags=["future_walk"])
templates = Jinja2Templates(directory="templates")

FIXTURE_STATUSES = ["Present", "Ordered", "Missing", "Unknown"]


def _today() -> str:
    return dt_date.today().isoformat()


async def _render(request: Request, walk_date: str) -> HTMLResponse:
    async with get_db() as db:
        rows = await db.execute_fetchall(
            """SELECT * FROM future_walk WHERE walk_date=?
               ORDER BY target_date ASC, id ASC""",
            (walk_date,),
        )
        items = [dict(r) for r in rows]

    problems = [i for i in items if i["fixture_status"] == "Missing" or i["issues"].strip()]
    unescalated_problems = [p for p in problems if not p["is_escalated"]]

    return templates.TemplateResponse(
            request,
            "partials/future_walk.html",
            {
            "items": items,
            "problems": problems,
            "unescalated_problems": unescalated_problems,
            "walk_date": walk_date,
            "fixture_statuses": FIXTURE_STATUSES,
        },
    )


@router.get("/", response_class=HTMLResponse)
async def get_future_walk(request: Request, walk_date: str = ""):
    return await _render(request, walk_date or _today())


@router.post("/add", response_class=HTMLResponse)
async def add_area(
    request: Request,
    walk_date: str = Form(...),
    area_name: str = Form(...),
    target_date: str = Form(""),
    fixture_status: str = Form("Unknown"),
    issues: str = Form(""),
    notes: str = Form(""),
):
    if not area_name.strip():
        return await _render(request, walk_date)

    async with get_db() as db:
        cursor = await db.execute(
            """
            INSERT INTO future_walk (walk_date, area_name, target_date, fixture_status,
                issues, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now','localtime'))
            """,
            (walk_date, area_name.strip(), target_date, fixture_status, issues, notes),
        )
        new_id = cursor.lastrowid

        # Auto-create obstacle task if missing fixtures or issues logged
        if fixture_status == "Missing" or issues.strip():
            obstacle_text = f"[Future Walk] {area_name}: "
            if fixture_status == "Missing":
                obstacle_text += "MISSING FIXTURES. "
            if issues.strip():
                obstacle_text += issues.strip()

            await db.execute(
                """
                INSERT INTO tasks (created_date, text, list_type, is_blocked, is_critical,
                    owner, notes, updated_at)
                VALUES (?, ?, 'obstacles', 1, 1, '', ?, datetime('now','localtime'))
                """,
                (walk_date, obstacle_text.strip(), f"Auto-created from Future Walk: {area_name}"),
            )
            await db.execute(
                "UPDATE future_walk SET obstacle_created=1 WHERE id=?", (new_id,)
            )

        await db.commit()

    return await _render(request, walk_date)


@router.post("/{item_id}/update", response_class=HTMLResponse)
async def update_area(
    request: Request,
    item_id: int,
    walk_date: str = Form(...),
    fixture_status: str = Form("Unknown"),
    is_ordered: str = Form("off"),
    is_escalated: str = Form("off"),
    issues: str = Form(""),
    notes: str = Form(""),
):
    ordered = 1 if is_ordered == "on" else 0
    escalated = 1 if is_escalated == "on" else 0

    async with get_db() as db:
        await db.execute(
            """
            UPDATE future_walk SET fixture_status=?, is_ordered=?, is_escalated=?,
                issues=?, notes=?, updated_at=datetime('now','localtime')
            WHERE id=?
            """,
            (fixture_status, ordered, escalated, issues, notes, item_id),
        )
        await db.commit()

    return await _render(request, walk_date)


@router.post("/{item_id}/delete", response_class=HTMLResponse)
async def delete_area(request: Request, item_id: int, walk_date: str = Form(...)):
    async with get_db() as db:
        await db.execute("DELETE FROM future_walk WHERE id=?", (item_id,))
        await db.commit()

    return await _render(request, walk_date)
