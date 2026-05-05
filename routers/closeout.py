"""
routers/closeout.py — Daily closeout: notes, trailer staging, final follow-ups, tomorrow check.
"""

from datetime import date as dt_date
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from database import get_db

router = APIRouter(prefix="/closeout", tags=["closeout"])
templates = Jinja2Templates(directory="templates")


def _today() -> str:
    return dt_date.today().isoformat()


async def _render(request: Request, date: str) -> HTMLResponse:
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM closeout WHERE date=?", (date,)
        )
        record = dict(rows[0]) if rows else {
            "date": date,
            "notes": "",
            "trailer_staged": 0,
            "followups_sent": 0,
            "tomorrow_ready": 0,
            "picklist_done": 0,
            "submitted_at": None,
        }

    all_done = all([
        record["trailer_staged"],
        record["followups_sent"],
        record["tomorrow_ready"],
        record["picklist_done"],
    ])

    return templates.TemplateResponse(
            request,
            "partials/closeout.html",
            {
            "record": record,
            "all_done": all_done,
            "date": date,
        },
    )


@router.get("/", response_class=HTMLResponse)
async def get_closeout(request: Request, date: str = ""):
    return await _render(request, date or _today())


@router.post("/save", response_class=HTMLResponse)
async def save_closeout(
    request: Request,
    date: str = Form(...),
    notes: str = Form(""),
    trailer_staged: str = Form("off"),
    followups_sent: str = Form("off"),
    tomorrow_ready: str = Form("off"),
    picklist_done: str = Form("off"),
):
    trailer = 1 if trailer_staged == "on" else 0
    followups = 1 if followups_sent == "on" else 0
    tomorrow = 1 if tomorrow_ready == "on" else 0
    picklist = 1 if picklist_done == "on" else 0

    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO closeout (date, notes, trailer_staged, followups_sent,
                tomorrow_ready, picklist_done, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now','localtime'))
            ON CONFLICT(date) DO UPDATE SET
                notes=excluded.notes,
                trailer_staged=excluded.trailer_staged,
                followups_sent=excluded.followups_sent,
                tomorrow_ready=excluded.tomorrow_ready,
                picklist_done=excluded.picklist_done,
                updated_at=excluded.updated_at
            """,
            (date, notes, trailer, followups, tomorrow, picklist),
        )
        await db.commit()

    return await _render(request, date)


@router.post("/submit", response_class=HTMLResponse)
async def submit_closeout(request: Request, date: str = Form(...)):
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO closeout (date, submitted_at, updated_at)
            VALUES (?, datetime('now','localtime'), datetime('now','localtime'))
            ON CONFLICT(date) DO UPDATE SET
                submitted_at=datetime('now','localtime'),
                updated_at=datetime('now','localtime')
            """,
            (date,),
        )
        await db.commit()

    return await _render(request, date)
