"""
routers/blocks.py — Time block status, notes, and checklist completion endpoints.
"""

from datetime import date as dt_date
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from database import get_db
from routine_data import get_blocks_for_day, BLOCK_STATUSES

router = APIRouter(prefix="/blocks", tags=["blocks"])
templates = Jinja2Templates(directory="templates")


def _today() -> str:
    return dt_date.today().isoformat()


# ── GET timeline partial for a given date ───────────────────────────────────
@router.get("/timeline", response_class=HTMLResponse)
async def get_timeline(request: Request, date: str = ""):
    target = date or _today()
    try:
        d = dt_date.fromisoformat(target)
    except ValueError:
        d = dt_date.today()
        target = d.isoformat()

    blocks = get_blocks_for_day(d.weekday())

    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT block_id, status, notes FROM block_status WHERE date=?", (target,)
        )
        status_map = {r["block_id"]: dict(r) for r in rows}

        checked_rows = await db.execute_fetchall(
            "SELECT block_id, item_id, is_checked FROM checklist_items WHERE date=?",
            (target,),
        )
        checked_map: dict[str, set[str]] = {}
        for r in checked_rows:
            checked_map.setdefault(r["block_id"], set())
            if r["is_checked"]:
                checked_map[r["block_id"]].add(r["item_id"])

    return templates.TemplateResponse(
            request,
            "partials/timeline.html",
            {
            "blocks": blocks,
            "status_map": status_map,
            "checked_map": checked_map,
            "target_date": target,
            "statuses": BLOCK_STATUSES,
        },
    )


# ── PATCH block status ───────────────────────────────────────────────────────
@router.post("/status", response_class=HTMLResponse)
async def update_block_status(
    request: Request,
    date: str = Form(...),
    block_id: str = Form(...),
    status: str = Form(...),
    notes: str = Form(""),
):
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO block_status (date, block_id, status, notes, updated_at)
            VALUES (?, ?, ?, ?, datetime('now','localtime'))
            ON CONFLICT(date, block_id) DO UPDATE SET
                status=excluded.status,
                notes=excluded.notes,
                updated_at=excluded.updated_at
            """,
            (date, block_id, status, notes),
        )
        await db.commit()

    return await get_timeline(request, date=date)


# ── POST toggle checklist item ───────────────────────────────────────────────
@router.post("/checklist", response_class=HTMLResponse)
async def toggle_checklist(
    request: Request,
    date: str = Form(...),
    block_id: str = Form(...),
    item_id: str = Form(...),
    checked: str = Form("off"),
):
    is_checked = 1 if checked == "on" else 0
    dt_expr = "datetime('now','localtime')"
    val_expr = dt_expr if is_checked else "NULL"
    sql = f"""
        INSERT INTO checklist_items (date, block_id, item_id, is_checked, checked_at)
        VALUES (?, ?, ?, ?, {val_expr})
        ON CONFLICT(date, block_id, item_id) DO UPDATE SET
            is_checked=excluded.is_checked,
            checked_at={val_expr}
    """

    async with get_db() as db:
        await db.execute(sql, (date, block_id, item_id, is_checked))
        await db.commit()

    # Return just the updated block row
    return await _block_partial(request, date, block_id)


async def _block_partial(request: Request, date: str, block_id: str) -> HTMLResponse:
    """Re-render a single block card for HTMX swap."""
    d = dt_date.fromisoformat(date)
    blocks = get_blocks_for_day(d.weekday())
    block = next((b for b in blocks if b["id"] == block_id), None)
    if not block:
        return HTMLResponse("")

    async with get_db() as db:
        row = await db.execute_fetchall(
            "SELECT status, notes FROM block_status WHERE date=? AND block_id=?",
            (date, block_id),
        )
        status_data = dict(row[0]) if row else {"status": "pending", "notes": ""}

        checked_rows = await db.execute_fetchall(
            "SELECT item_id, is_checked FROM checklist_items WHERE date=? AND block_id=?",
            (date, block_id),
        )
        checked_set = {r["item_id"] for r in checked_rows if r["is_checked"]}

    return templates.TemplateResponse(
            request,
            "partials/block_card.html",
            {
            "block": block,
            "status_data": status_data,
            "checked_set": checked_set,
            "target_date": date,
            "statuses": BLOCK_STATUSES,
        },
    )


# ── GET block notes save (inline edit) ──────────────────────────────────────
@router.post("/notes", response_class=HTMLResponse)
async def save_block_notes(
    request: Request,
    date: str = Form(...),
    block_id: str = Form(...),
    notes: str = Form(""),
):
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO block_status (date, block_id, status, notes, updated_at)
            VALUES (?, ?, 'pending', ?, datetime('now','localtime'))
            ON CONFLICT(date, block_id) DO UPDATE SET
                notes=excluded.notes,
                updated_at=excluded.updated_at
            """,
            (date, block_id, notes),
        )
        await db.commit()

    return HTMLResponse(
        f'<span class="text-green-600 text-xs font-medium">✓ Saved</span>'
    )
