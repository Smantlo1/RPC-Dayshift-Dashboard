"""
exporter.py — Build a self-contained HTML snapshot of the current dashboard.

No f-string backslashes (Python 3.11 restriction). All dynamic HTML is built
via pre-computed variables or regular string concatenation.
"""

from datetime import date, datetime
from typing import Optional

from database import get_db
from routine_data import PRIORITY_RULES, WEEKLY_CADENCE, get_blocks_for_day

_WM_BLUE  = "#0053e2"
_WM_SPARK = "#ffc220"
_PERSIST  = "https://puppy.walmart.com/sharing/s0m0660/rpc-dashboard"


# ── Low-level helpers (no f-string backslashes) ───────────────────────────────

def _badge(text: str, color: str, bg: str) -> str:
    style = (
        "display:inline-block;padding:2px 8px;border-radius:9999px;"
        "font-size:11px;font-weight:600;"
        "color:" + color + ";background:" + bg
    )
    return '<span style="' + style + '">' + text + "</span>"


def _status_badge(status: str) -> str:
    s = str(status).lower()
    if s in ("done", "complete", "on track", "ordered", "yes"):
        return _badge(status, "#166534", "#dcfce7")
    if s in ("overdue", "blocked", "critical", "no", "past due"):
        return _badge(status, "#991b1b", "#fee2e2")
    if s in ("at risk", "in progress", "pending", "tbd", "unknown"):
        return _badge(status, "#92400e", "#fef3c7")
    return _badge(status, "#374151", "#f3f4f6")


def _section(title: str, icon: str, body: str, accent: str = _WM_BLUE) -> str:
    hdr_style = (
        "background:" + accent + ";color:white;padding:12px 18px;"
        "font-weight:700;font-size:14px;"
    )
    return (
        '<div style="background:white;border-radius:12px;'
        "box-shadow:0 1px 3px rgba(0,0,0,.08);margin-bottom:20px;overflow:hidden;"
        '">'
        '<div style="' + hdr_style + '">' + icon + " " + title + "</div>"
        '<div style="padding:16px 18px;">' + body + "</div>"
        "</div>"
    )


def _pill_row(items: list) -> str:
    if not items:
        return (
            '<p style="color:#9ca3af;font-style:italic;font-size:13px;">'
            "Nothing here.</p>"
        )
    rows = []
    for item in items:
        is_done     = item.get("is_done", 0)
        is_blocked  = item.get("is_blocked", 0)
        is_critical = item.get("is_critical", 0)
        owner       = item.get("owner", "") or ""
        text        = item.get("text", item.get("fixture_name", ""))

        if is_done:
            icon = "\u2705"
        elif is_critical:
            icon = "\U0001f6a8"
        elif is_blocked:
            icon = "\u26d4"
        else:
            icon = "\u25fb\ufe0f"

        strike = "text-decoration:line-through;color:#9ca3af;" if is_done else ""

        row = (
            '<div style="display:flex;align-items:center;gap:8px;'
            "padding:6px 0;border-bottom:1px solid #f3f4f6;"
            '">'
            '<span style="font-size:14px;">' + icon + "</span>"
            '<span style="flex:1;font-size:13px;' + strike + '">' + text + "</span>"
        )
        if owner:
            row += (
                '<span style="font-size:11px;color:#6b7280;white-space:nowrap">'
                "\U0001f464 " + owner + "</span>"
            )
        row += "</div>"
        rows.append(row)
    return "".join(rows)


# ── Project table (avoids all f-string quoting issues) ───────────────────────

def _proj_table(proj_list: list) -> str:
    if not proj_list:
        return (
            '<p style="color:#9ca3af;font-size:13px;font-style:italic;">'
            "No projects.</p>"
        )
    rows = []
    unowned_em = '<em style="color:#dc2626">Unowned</em>'
    for p in proj_list:
        owner_cell = p.get("owner") or unowned_em
        due        = p.get("due_date", "") or ""
        notes_txt  = (p.get("notes") or "")[:60]
        row = (
            '<tr style="border-bottom:1px solid #f3f4f6;">'
            '<td style="padding:6px 8px;font-size:12px;">' + p["name"] + "</td>"
            '<td style="padding:6px 8px;">' + _status_badge(p["status"]) + "</td>"
            '<td style="padding:6px 8px;font-size:12px;color:#374151;">' + owner_cell + "</td>"
            '<td style="padding:6px 8px;font-size:11px;color:#6b7280;">' + due + "</td>"
            '<td style="padding:6px 8px;font-size:11px;color:#6b7280;">' + notes_txt + "</td>"
            "</tr>"
        )
        rows.append(row)

    header = (
        '<table style="width:100%;border-collapse:collapse;">'
        '<thead><tr style="background:#f9fafb;font-size:11px;color:#6b7280;'
        'text-transform:uppercase;">'
        '<th style="padding:6px 8px;text-align:left;">Name</th>'
        '<th style="padding:6px 8px;text-align:left;">Status</th>'
        '<th style="padding:6px 8px;text-align:left;">Owner</th>'
        '<th style="padding:6px 8px;text-align:left;">Due</th>'
        '<th style="padding:6px 8px;text-align:left;">Notes</th>'
        "</tr></thead><tbody>"
    )
    return header + "".join(rows) + "</tbody></table>"


# ── Main export builder ───────────────────────────────────────────────────────

async def build_export_html(date_str: Optional[str] = None) -> str:
    today    = date_str or date.today().isoformat()
    now_str  = (
        datetime.now().strftime("%A, %B %d, %Y \u00b7 %I:%M %p")
        .replace(" 0", " ")
    )
    weekday  = date.fromisoformat(today).weekday()
    day_name = date.fromisoformat(today).strftime("%A")
    cadence_note = WEEKLY_CADENCE.get(day_name, "")

    async with get_db() as db:
        b_rows = await db.execute_fetchall(
            "SELECT block_id, status, notes FROM block_status WHERE date=?", (today,)
        )
        blk_map = {r["block_id"]: dict(r) for r in b_rows}

        tasks_raw = await db.execute_fetchall(
            "SELECT * FROM tasks WHERE is_done=0 "
            "ORDER BY is_critical DESC, is_blocked DESC, id"
        )
        today_tasks = [dict(r) for r in tasks_raw if r["list_type"] == "today"]
        obs_tasks   = [dict(r) for r in tasks_raw if r["list_type"] == "obstacles"]
        up_tasks    = [dict(r) for r in tasks_raw if r["list_type"] == "upcoming"]

        done_raw = await db.execute_fetchall(
            "SELECT text, owner FROM tasks WHERE is_done=1 "
            "ORDER BY done_at DESC LIMIT 5"
        )
        done_tasks = [dict(r) for r in done_raw]

        proj_raw = await db.execute_fetchall(
            "SELECT * FROM projects ORDER BY status DESC, last_updated DESC"
        )
        projects = [dict(r) for r in proj_raw]

        pick_raw = await db.execute_fetchall(
            "SELECT * FROM picklist WHERE date=? ORDER BY is_critical DESC, needed_by",
            (today,)
        )
        picks = [dict(r) for r in pick_raw]

        walk_raw = await db.execute_fetchall(
            "SELECT * FROM future_walk ORDER BY target_date, walk_date DESC LIMIT 20"
        )
        walks = [dict(r) for r in walk_raw]

        co_raw = await db.execute_fetchall(
            "SELECT * FROM closeout WHERE date=?", (today,)
        )
        closeout = dict(co_raw[0]) if co_raw else {}

    # ── Priority Alerts ───────────────────────────────────────────────────────
    criticals = [
        t for t in today_tasks + obs_tasks
        if t.get("is_critical") or t.get("is_blocked")
    ]
    unowned = [t for t in today_tasks + obs_tasks if not t.get("owner")]

    alerts_html = ""
    if criticals:
        _uo_em = '<em style="color:#dc2626">UNOWNED</em>'
        crit_items = []
        for c in criticals[:6]:
            flag      = "\U0001f6a8" if c.get("is_critical") else "\u26d4"
            owner_part = (" \u2014 " + c["owner"]) if c.get("owner") else (" " + _uo_em)
            crit_items.append(
                '<li style="margin:4px 0">' + flag
                + " <strong>" + c["text"] + "</strong>" + owner_part + "</li>"
            )
        alerts_html += (
            '<ul style="margin:0;padding-left:18px;font-size:13px;">'
            + "".join(crit_items)
            + "</ul>"
        )
    if unowned:
        alerts_html += (
            '<p style="margin:8px 0 0;font-size:13px;color:#b45309;">'
            "\u26a0\ufe0f <strong>" + str(len(unowned))
            + " task(s)</strong> have no owner assigned.</p>"
        )
    if not alerts_html:
        alerts_html = (
            '<p style="color:#16a34a;font-size:13px;">'
            "\u2705 No critical or unowned items right now.</p>"
        )
    priority_alert_section = _section("Priority Alerts", "\U0001f6a8", alerts_html, "#dc2626")

    # ── Daily Rules ───────────────────────────────────────────────────────────
    rules_html = (
        '<ol style="margin:0;padding-left:20px;font-size:13px;line-height:1.7;">'
        + "".join("<li>" + r + "</li>" for r in PRIORITY_RULES)
        + "</ol>"
    )
    if cadence_note:
        rules_html += (
            '<div style="margin-top:10px;padding:8px 12px;background:#fffbeb;'
            "border-left:3px solid #f59e0b;border-radius:4px;font-size:13px;"
            '">'
            "\U0001f4c5 <strong>" + day_name + " note:</strong> " + cadence_note
            + "</div>"
        )
    rules_section = _section("Daily Priority Rules", "\U0001f4cb", rules_html, "#374151")

    # ── Three Lists ───────────────────────────────────────────────────────────
    def _list_section(title: str, icon: str, items: list, accent: str) -> str:
        count_str = " (" + str(len(items)) + ")"
        return _section(title + count_str, icon, _pill_row(items), accent)

    lists_html = (
        _list_section("Today \u2014 Must Do",          "\U0001f4cc", today_tasks, _WM_BLUE)
        + _list_section("Obstacles \u2014 Escalate",   "\u26d4",     obs_tasks,   "#dc2626")
        + _list_section("Upcoming",                    "\U0001f51c", up_tasks,    "#374151")
    )
    if done_tasks:
        done_items = "".join(
            '<div style="font-size:12px;color:#6b7280;padding:3px 0;'
            "border-bottom:1px solid #f3f4f6;"
            '">'
            "\u2705 " + d["text"] + ((" \u2014 " + d["owner"]) if d.get("owner") else "")
            + "</div>"
            for d in done_tasks
        )
        lists_html += _section("Recently Completed (last 5)", "\u2705", done_items, "#16a34a")

    # ── Timeline ──────────────────────────────────────────────────────────────
    blocks = get_blocks_for_day(weekday)
    tl_rows = []
    for b in blocks:
        if b.get("is_lunch"):
            tl_rows.append(
                '<div style="padding:8px 0;color:#9ca3af;font-size:12px;'
                "border-bottom:1px solid #f3f4f6;"
                '">'
                "\U0001f37d\ufe0f " + b["time_range"] + " \u2014 Lunch</div>"
            )
            continue
        st     = blk_map.get(b["id"], {})
        status = st.get("status", "pending")
        notes  = st.get("notes", "") or ""
        badge  = _status_badge(status)
        notes_p = (
            '<p style="font-size:11px;color:#6b7280;margin:4px 0 0;">' + notes + "</p>"
            if notes else ""
        )
        tl_rows.append(
            '<div style="padding:8px 0;border-bottom:1px solid #f3f4f6;">'
            '<div style="display:flex;justify-content:space-between;align-items:center;">'
            '<span style="font-size:13px;font-weight:600">'
            + b["time_range"] + " \u2014 " + b["label"]
            + "</span>" + badge + "</div>"
            + notes_p
            + "</div>"
        )
    timeline_section = _section("Today\u2019s Timeline", "\U0001f550", "".join(tl_rows))

    # ── Projects ──────────────────────────────────────────────────────────────
    cats: dict = {}
    for p in projects:
        cats.setdefault(p["category"], []).append(p)

    proj_body = ""
    for cat, items in cats.items():
        proj_body += (
            '<h4 style="font-size:12px;font-weight:700;color:#374151;'
            "margin:12px 0 6px;text-transform:uppercase;letter-spacing:.05em;"
            '">' + cat + "</h4>"
            + _proj_table(items)
        )
    if not proj_body:
        proj_body = (
            '<p style="color:#9ca3af;font-size:13px;font-style:italic;">'
            "No projects tracked yet.</p>"
        )
    projects_section = _section("Project Tracking", "\U0001f4ca", proj_body)

    # ── Picklist ──────────────────────────────────────────────────────────────
    if picks:
        pick_rows = []
        for pk in picks:
            zero_style = (
                'color:#dc2626;font-weight:600;'
                if pk["qty_onhand"] == 0 else ""
            )
            crit_bg = (
                'background:#fff7ed;'
                if pk["is_critical"] else ""
            )
            flag = "\U0001f6a8 " if pk["is_critical"] else ""
            status_label = "ordered" if pk["is_ordered"] else "pending"
            backup = (pk.get("backup_plan") or "")[:50]
            pick_rows.append(
                '<tr style="border-bottom:1px solid #f3f4f6;' + crit_bg + '">'
                '<td style="padding:6px 8px;font-size:12px;">' + flag + pk["fixture_name"] + "</td>"
                '<td style="padding:6px 8px;font-size:12px;">' + (pk.get("needed_by") or "") + "</td>"
                '<td style="padding:6px 8px;font-size:12px;' + zero_style + '">'
                + str(pk["qty_onhand"]) + "</td>"
                '<td style="padding:6px 8px;font-size:12px;">' + str(pk["qty_needed"]) + "</td>"
                '<td style="padding:6px 8px;">' + _status_badge(status_label) + "</td>"
                '<td style="padding:6px 8px;font-size:11px;color:#6b7280;">' + backup + "</td>"
                "</tr>"
            )
        pick_body = (
            '<table style="width:100%;border-collapse:collapse;">'
            '<thead><tr style="background:#f9fafb;font-size:11px;color:#6b7280;'
            'text-transform:uppercase;">'
            '<th style="padding:6px 8px;text-align:left;">Fixture</th>'
            '<th style="padding:6px 8px;text-align:left;">Needed By</th>'
            '<th style="padding:6px 8px;text-align:left;">On Hand</th>'
            '<th style="padding:6px 8px;text-align:left;">Needed</th>'
            '<th style="padding:6px 8px;text-align:left;">Status</th>'
            '<th style="padding:6px 8px;text-align:left;">Backup</th>'
            "</tr></thead><tbody>"
            + "".join(pick_rows)
            + "</tbody></table>"
        )
    else:
        pick_body = (
            '<p style="color:#9ca3af;font-size:13px;font-style:italic;">'
            "No picklist items for today.</p>"
        )
    picklist_section = _section("Picklist", "\U0001f4e6", pick_body, "#7c3aed")

    # ── Future Walk ───────────────────────────────────────────────────────────
    if walks:
        walk_rows = []
        for w in walks:
            issues = (w.get("issues") or "")[:60]
            ordered = "\u2705" if w["is_ordered"] else "\u25fb\ufe0f"
            walk_rows.append(
                '<tr style="border-bottom:1px solid #f3f4f6;">'
                '<td style="padding:6px 8px;font-size:12px;">' + w["area_name"] + "</td>"
                '<td style="padding:6px 8px;font-size:12px;">' + (w.get("target_date") or "") + "</td>"
                '<td style="padding:6px 8px;">' + _status_badge(w.get("fixture_status", "Unknown")) + "</td>"
                '<td style="padding:6px 8px;font-size:12px;">' + ordered + "</td>"
                '<td style="padding:6px 8px;font-size:11px;color:#6b7280;">' + issues + "</td>"
                "</tr>"
            )
        walk_body = (
            '<table style="width:100%;border-collapse:collapse;">'
            '<thead><tr style="background:#f9fafb;font-size:11px;color:#6b7280;'
            'text-transform:uppercase;">'
            '<th style="padding:6px 8px;text-align:left;">Area</th>'
            '<th style="padding:6px 8px;text-align:left;">Target Date</th>'
            '<th style="padding:6px 8px;text-align:left;">Fixture Status</th>'
            '<th style="padding:6px 8px;text-align:left;">Ordered</th>'
            '<th style="padding:6px 8px;text-align:left;">Issues</th>'
            "</tr></thead><tbody>"
            + "".join(walk_rows)
            + "</tbody></table>"
        )
    else:
        walk_body = (
            '<p style="color:#9ca3af;font-size:13px;font-style:italic;">'
            "No future walk entries.</p>"
        )
    walk_section = _section("Future Walk (Next 2 Weeks)", "\U0001f52e", walk_body, "#0891b2")

    # ── Closeout ──────────────────────────────────────────────────────────────
    co_checks = [
        ("\U0001f4dd Notes finalized",  closeout.get("notes_done")),
        ("\U0001f69a Trailer staged",   closeout.get("trailer_staged")),
        ("\U0001f4e7 Follow-ups sent",  closeout.get("followups_sent")),
        ("\u2705 Tomorrow ready",       closeout.get("tomorrow_ready")),
        ("\U0001f4cb Picklist done",    closeout.get("picklist_done")),
    ]
    co_body = "".join(
        '<div style="padding:5px 0;font-size:13px;">'
        + ("\u2705" if val else "\u25fb\ufe0f") + " " + label + "</div>"
        for label, val in co_checks
    )
    co_notes = closeout.get("notes", "") or ""
    if co_notes:
        co_body += (
            '<div style="margin-top:10px;padding:8px 12px;background:#f9fafb;'
            "border-radius:6px;font-size:12px;color:#374151;"
            '">'
            "<strong>Closeout notes:</strong><br>" + co_notes + "</div>"
        )
    if not closeout:
        co_body = (
            '<p style="color:#9ca3af;font-size:13px;font-style:italic;">'
            "Closeout not yet started.</p>"
        )
    closeout_section = _section("Closeout Status", "\U0001f512", co_body, "#374151")

    # ── Assemble ──────────────────────────────────────────────────────────────
    edit_link  = "http://127.0.0.1:8001"
    spark_hex  = _WM_SPARK
    blue_hex   = _WM_BLUE

    page = (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>RPC Daily Operating Dashboard \u2014 " + today + "</title>\n"
        "<style>\n"
        "*{box-sizing:border-box;margin:0;padding:0}\n"
        "body{font-family:system-ui,-apple-system,sans-serif;"
        "background:#f3f4f6;color:#111827;}\n"
        "a{color:" + blue_hex + ";text-decoration:none}\n"
        "a:hover{text-decoration:underline}\n"
        "@media(max-width:640px){.mg{grid-template-columns:1fr!important}}\n"
        "</style>\n"
        "</head>\n"
        "<body>\n"
        # Header
        '<div style="background:' + blue_hex + ';color:white;padding:16px 24px;'
        "display:flex;justify-content:space-between;align-items:center;"
        'flex-wrap:wrap;gap:8px;">\n'
        "  <div>\n"
        '    <div style="font-size:20px;font-weight:800;letter-spacing:-.02em;">'
        "\U0001f436 RPC Daily Operating Dashboard</div>\n"
        '    <div style="font-size:13px;opacity:.85;margin-top:2px;">' + now_str + "</div>\n"
        "  </div>\n"
        "  <div>\n"
        '    <div style="background:' + spark_hex + ';color:#111;padding:4px 12px;'
        "border-radius:20px;font-size:12px;font-weight:700;margin-bottom:4px;"
        '">READ-ONLY SNAPSHOT</div>\n'
        '    <div style="font-size:12px;opacity:.8;">Edit at '
        '<a href="' + edit_link + '" style="color:' + spark_hex + ';">'
        + edit_link + "</a>"
        ' \u00b7 <a href="' + _PERSIST + '" style="color:' + spark_hex + ';">'
        "Refresh this page</a></div>\n"
        "  </div>\n"
        "</div>\n\n"
        # Body
        '<div style="max-width:1100px;margin:24px auto;padding:0 16px;">\n'
        + priority_alert_section + "\n"
        '<div class="mg" style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">\n'
        "  <div>\n"
        + rules_section + timeline_section + closeout_section
        + "  </div>\n"
        "  <div>\n"
        + lists_html
        + "  </div>\n"
        "</div>\n"
        + projects_section + picklist_section + walk_section
        + "</div>\n"
        # Footer
        '<div style="text-align:center;padding:24px;color:#9ca3af;font-size:12px;'
        'border-top:1px solid #e5e7eb;">\n'
        "RPC Daily Operating Dashboard \u00b7 Published by Code Puppy \u00b7\n"
        '<a href="' + _PERSIST + '">Persistent link</a> (updates when republished) \u00b7\n'
        '<a href="' + edit_link + '">Open live dashboard</a>\n'
        "</div>\n"
        "</body>\n</html>"
    )
    return page
