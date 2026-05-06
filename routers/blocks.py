"""
routers/blocks.py — Time block status, notes, and checklist completion endpoints.

Checklist toggle: returns empty 200 (hx-swap="none" ignores response body).
Status update: returns just the one re-rendered block card (not the full timeline).
JS in app.js tracks open blocks and re-opens after status card swap.
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


# ── GET full timeline partial ────────────────────────────────────────────────
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
        checked_map: dict[str, list[str]] = {}
        for r in checked_rows:
            if r["is_checked"]:
                checked_map.setdefault(r["block_id"], [])
                checked_map[r["block_id"]].append(r["item_id"])

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


# ── POST toggle checklist item — hx-swap="none", JS handles visuals ─────────
@router.post("/checklist", response_class=HTMLResponse)
async def toggle_checklist(
    request: Request,
    date: str = Form(...),
    block_id: str = Form(...),
    item_id: str = Form(...),
    checked: str = Form("off"),
):
    """
    Persist the checkbox state.  The template uses hx-swap="none" so HTMX
    ignores this response entirely — all visual feedback is handled client-side
    by handleChecklistChange() in app.js.
    """
    is_checked = 1 if checked == "on" else 0
    checked_at = "datetime('now','localtime')" if is_checked else "NULL"

    async with get_db() as db:
        await db.execute(
            f"""
            INSERT INTO checklist_items (date, block_id, item_id, is_checked, checked_at)
            VALUES (?, ?, ?, ?, {checked_at})
            ON CONFLICT(date, block_id, item_id) DO UPDATE SET
                is_checked = excluded.is_checked,
                checked_at = {checked_at}
            """,
            (date, block_id, item_id, is_checked),
        )
        await db.commit()

    # Empty body — HTMX ignores it (hx-swap="none")
    return HTMLResponse("", status_code=200)


# ── POST update block status — re-renders ONLY this one card ────────────────
@router.post("/status", response_class=HTMLResponse)
async def update_block_status(
    request: Request,
    date: str = Form(...),
    block_id: str = Form(...),
    status: str = Form(...),
    notes: str = Form(""),
):
    """
    Saves the new status and returns just the block card partial.
    The template targets #block-{id} with hx-swap="outerHTML" so only that
    card is replaced.  app.js re-opens it if it was open before the swap.
    """
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO block_status (date, block_id, status, notes, updated_at)
            VALUES (?, ?, ?, ?, datetime('now','localtime'))
            ON CONFLICT(date, block_id) DO UPDATE SET
                status     = excluded.status,
                updated_at = excluded.updated_at
            """,
            (date, block_id, status, notes),
        )
        await db.commit()

    return await _block_partial(request, date, block_id)


# ── POST save notes (auto-save on blur) ─────────────────────────────────────
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
                notes      = excluded.notes,
                updated_at = excluded.updated_at
            """,
            (date, block_id, notes),
        )
        await db.commit()

    return HTMLResponse('<span class="text-green-600 text-xs font-medium">✓ Saved</span>')


# ── Internal helper — render a single block card ─────────────────────────────
async def _block_partial(request: Request, date: str, block_id: str) -> HTMLResponse:
    """Re-render a single block card for targeted HTMX outerHTML swap."""
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
