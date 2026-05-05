"""
routers/picklist.py — Fixture picklist: needed-by dates, zero on-hands, risk flags.
"""

from datetime import date as dt_date
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from database import get_db

router = APIRouter(prefix="/picklist", tags=["picklist"])
templates = Jinja2Templates(directory="templates")


def _today() -> str:
    return dt_date.today().isoformat()


async def _render(request: Request, date: str) -> HTMLResponse:
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM picklist WHERE date=? ORDER BY is_critical DESC, needed_by ASC, id ASC",
            (date,),
        )
        items = [dict(r) for r in rows]

    # Identify zero on-hands and critical items
    zero_onhand = [i for i in items if i["qty_onhand"] == 0 and not i["is_ordered"]]
    critical_unresolved = [i for i in items if i["is_critical"] and not i["is_ordered"]]

    return templates.TemplateResponse(
            request,
            "partials/picklist.html",
            {
            "items": items,
            "zero_onhand": zero_onhand,
            "critical_unresolved": critical_unresolved,
            "date": date,
        },
    )


@router.get("/", response_class=HTMLResponse)
async def get_picklist(request: Request, date: str = ""):
    return await _render(request, date or _today())


@router.post("/add", response_class=HTMLResponse)
async def add_item(
    request: Request,
    date: str = Form(...),
    fixture_name: str = Form(...),
    needed_by: str = Form(""),
    qty_needed: int = Form(0),
    qty_onhand: int = Form(0),
    is_critical: str = Form("off"),
    backup_plan: str = Form(""),
    notes: str = Form(""),
):
    if not fixture_name.strip():
        return await _render(request, date)

    critical = 1 if is_critical == "on" else 0

    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO picklist (date, fixture_name, needed_by, qty_needed, qty_onhand,
                is_critical, backup_plan, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now','localtime'))
            """,
            (date, fixture_name.strip(), needed_by, qty_needed, qty_onhand,
             critical, backup_plan, notes),
        )
        await db.commit()

    return await _render(request, date)


@router.post("/{item_id}/update", response_class=HTMLResponse)
async def update_item(
    request: Request,
    item_id: int,
    date: str = Form(...),
    qty_onhand: int = Form(0),
    is_ordered: str = Form("off"),
    is_critical: str = Form("off"),
    backup_plan: str = Form(""),
    notes: str = Form(""),
):
    ordered = 1 if is_ordered == "on" else 0
    critical = 1 if is_critical == "on" else 0

    async with get_db() as db:
        await db.execute(
            """
            UPDATE picklist SET qty_onhand=?, is_ordered=?, is_critical=?,
                backup_plan=?, notes=?, updated_at=datetime('now','localtime')
            WHERE id=?
            """,
            (qty_onhand, ordered, critical, backup_plan, notes, item_id),
        )
        await db.commit()

    return await _render(request, date)


@router.post("/{item_id}/ordered", response_class=HTMLResponse)
async def mark_ordered(request: Request, item_id: int, date: str = Form(...)):
    async with get_db() as db:
        await db.execute(
            "UPDATE picklist SET is_ordered=1, updated_at=datetime('now','localtime') WHERE id=?",
            (item_id,),
        )
        await db.commit()

    return await _render(request, date)


@router.post("/{item_id}/delete", response_class=HTMLResponse)
async def delete_item(request: Request, item_id: int, date: str = Form(...)):
    async with get_db() as db:
        await db.execute("DELETE FROM picklist WHERE id=?", (item_id,))
        await db.commit()

    return await _render(request, date)
