"""
routers/tasks.py — Three-list system: Today, Obstacles, Upcoming.
"""

from datetime import date as dt_date
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from database import get_db

router = APIRouter(prefix="/tasks", tags=["tasks"])
templates = Jinja2Templates(directory="templates")

LIST_TYPES = ["today", "obstacles", "upcoming"]


def _today() -> str:
    return dt_date.today().isoformat()


async def _render_lists(request: Request) -> HTMLResponse:
    today = _today()
    async with get_db() as db:
        rows = await db.execute_fetchall(
            """
            SELECT id, text, list_type, is_done, is_blocked, is_critical, owner, notes,
                   created_date, updated_at
            FROM tasks
            WHERE is_done = 0 OR created_date = ?
            ORDER BY is_critical DESC, is_blocked DESC, id ASC
            """,
            (today,),
        )
        tasks = [dict(r) for r in rows]

    grouped: dict[str, list] = {lt: [] for lt in LIST_TYPES}
    for t in tasks:
        lt = t["list_type"] if t["list_type"] in LIST_TYPES else "today"
        grouped[lt].append(t)

    return templates.TemplateResponse(
            request,
            "partials/task_lists.html",
            {"grouped": grouped, "list_types": LIST_TYPES, "today": today},
    )


@router.get("/", response_class=HTMLResponse)
async def get_tasks(request: Request):
    return await _render_lists(request)


@router.post("/add", response_class=HTMLResponse)
async def add_task(
    request: Request,
    text: str = Form(...),
    list_type: str = Form("today"),
    owner: str = Form(""),
    is_critical: str = Form("off"),
):
    if not text.strip():
        return await _render_lists(request)

    critical = 1 if is_critical == "on" else 0
    today = _today()

    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO tasks (created_date, text, list_type, owner, is_critical, updated_at)
            VALUES (?, ?, ?, ?, ?, datetime('now','localtime'))
            """,
            (today, text.strip(), list_type, owner.strip(), critical),
        )
        await db.commit()

    return await _render_lists(request)


@router.post("/{task_id}/move", response_class=HTMLResponse)
async def move_task(request: Request, task_id: int, list_type: str = Form(...)):
    async with get_db() as db:
        await db.execute(
            "UPDATE tasks SET list_type=?, updated_at=datetime('now','localtime') WHERE id=?",
            (list_type, task_id),
        )
        await db.commit()

    return await _render_lists(request)


@router.post("/{task_id}/done", response_class=HTMLResponse)
async def complete_task(request: Request, task_id: int):
    async with get_db() as db:
        await db.execute(
            """UPDATE tasks SET is_done=1, done_at=datetime('now','localtime'),
               updated_at=datetime('now','localtime') WHERE id=?""",
            (task_id,),
        )
        await db.commit()

    return await _render_lists(request)


@router.post("/{task_id}/flag", response_class=HTMLResponse)
async def flag_task(
    request: Request,
    task_id: int,
    flag: str = Form(...),  # "blocked" | "critical" | "clear"
):
    async with get_db() as db:
        if flag == "blocked":
            await db.execute(
                "UPDATE tasks SET is_blocked=1, list_type='obstacles', updated_at=datetime('now','localtime') WHERE id=?",
                (task_id,),
            )
        elif flag == "critical":
            await db.execute(
                "UPDATE tasks SET is_critical=1, updated_at=datetime('now','localtime') WHERE id=?",
                (task_id,),
            )
        elif flag == "clear":
            await db.execute(
                "UPDATE tasks SET is_blocked=0, is_critical=0, updated_at=datetime('now','localtime') WHERE id=?",
                (task_id,),
            )
        await db.commit()

    return await _render_lists(request)


@router.post("/{task_id}/owner", response_class=HTMLResponse)
async def set_owner(request: Request, task_id: int, owner: str = Form(...)):
    async with get_db() as db:
        await db.execute(
            "UPDATE tasks SET owner=?, updated_at=datetime('now','localtime') WHERE id=?",
            (owner.strip(), task_id),
        )
        await db.commit()

    return await _render_lists(request)


@router.post("/{task_id}/delete", response_class=HTMLResponse)
async def delete_task(request: Request, task_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        await db.commit()

    return await _render_lists(request)
