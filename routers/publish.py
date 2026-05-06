"""
routers/publish.py — Export + one-click publish to puppy.walmart.com.

Endpoints:
  GET  /publish/export        → download self-contained HTML snapshot
  POST /publish/now           → export + upload to puppy.walmart.com
  GET  /publish/status        → current publish meta (url, last published)

Uses urllib.request (not requests) so it inherits the Windows Certificate Store
and properly trusts Walmart's internal TLS inspection cert — exactly the same
mechanism the share-puppy agent itself uses.
"""

import asyncio
import configparser
import json
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from exporter import build_export_html
from sheet_fetcher import _load_settings, _save_settings

router = APIRouter(prefix="/publish", tags=["publish"])
templates = Jinja2Templates(directory="templates")

UPLOAD_URL   = "https://puppy.walmart.com/api/sharing/upload"
PAGE_NAME    = "rpc-dashboard"
BUSINESS     = "s0m0660"   # must match the sharing URL segment
PERSIST_URL  = f"https://puppy.walmart.com/sharing/{BUSINESS}/{PAGE_NAME}"
PUPPY_CFG    = Path.home() / ".code_puppy" / "puppy.cfg"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_token() -> Optional[str]:
    cfg = configparser.ConfigParser()
    cfg.read(PUPPY_CFG)
    return cfg.get("puppy", "puppy_token", fallback=None)


def _save_publish_meta(url: str, ts: str) -> None:
    s = _load_settings()
    s["publish_url"] = url
    s["published_at"] = ts
    _save_settings(s)


def get_publish_meta() -> dict:
    s = _load_settings()
    return {
        "url": s.get("publish_url", PERSIST_URL),
        "published_at": s.get("published_at"),
    }


def _do_upload(html: str) -> dict:
    """Blocking upload via urllib (inherits Windows cert store, no verify=False needed)."""
    token = _get_token()
    if not token:
        return {"success": False, "error": "No puppy_token in ~/.code_puppy/puppy.cfg"}

    payload = json.dumps({
        "name": PAGE_NAME,
        "business": BUSINESS,
        "html_content": html,
        "description": "RPC Daily Operating Dashboard — auto-published snapshot",
        "access_level": "business",
    }).encode("utf-8")

    req = urllib.request.Request(
        UPLOAD_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read())
            url = body.get("url") or PERSIST_URL
            return {"success": True, "url": url, "body": body}
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read()).get("detail", str(exc))
        except Exception:
            detail = str(exc)
        return {"success": False, "error": f"HTTP {exc.code}: {detail}"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/export", response_class=Response)
async def download_export():
    """Download today's snapshot as a self-contained HTML file."""
    html = await build_export_html()
    fname = f"rpc-dashboard-{datetime.now().strftime('%Y%m%d-%H%M')}.html"
    return Response(
        content=html.encode("utf-8"),
        media_type="text/html",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.post("/now", response_class=HTMLResponse)
async def publish_now(request: Request):
    """Export + upload to puppy.walmart.com. Returns HTMX partial."""
    # Run the blocking upload in a thread so we don't lock the event loop
    html = await build_export_html()
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _do_upload, html)

    now_str = datetime.now().strftime("%I:%M %p")
    if result["success"]:
        url = result.get("url", PERSIST_URL)
        _save_publish_meta(url, now_str)
        return HTMLResponse(_render_status(url=url, published_at=now_str, success=True))
    else:
        return HTMLResponse(_render_status(
            url=get_publish_meta()["url"],
            published_at=get_publish_meta().get("published_at"),
            success=False,
            error=result["error"],
        ))


@router.get("/status", response_class=HTMLResponse)
async def publish_status(request: Request):
    """Return the current publish status badge (HTMX polled)."""
    meta = get_publish_meta()
    return HTMLResponse(_render_status(
        url=meta["url"],
        published_at=meta.get("published_at"),
        success=bool(meta.get("published_at")),
    ))


# ── Partial renderer ──────────────────────────────────────────────────────────

def _render_status(
    url: str,
    published_at: Optional[str],
    success: bool,
    error: Optional[str] = None,
) -> str:
    # All variants use id="pub-area" so HTMX outerHTML swap keeps the anchor alive
    if error:
        return f"""
        <div id="pub-area"
             class="flex items-center gap-2 text-xs text-red-700
                    bg-red-50 border border-red-200 px-3 py-2 rounded-lg">
          <span>❌ {error[:80]}</span>
          <button hx-post="/publish/now" hx-target="#pub-area" hx-swap="outerHTML"
                  hx-indicator="#pub-spinner"
                  class="ml-1 underline hover:no-underline">Retry</button>
        </div>"""

    if published_at and success:
        return f"""
        <div id="pub-area"
             class="flex items-center gap-2 text-xs text-green-700
                    bg-green-50 border border-green-200 px-3 py-2 rounded-lg">
          <span>✅ {published_at}</span>
          <a href="{url}" target="_blank" rel="noopener noreferrer"
             class="text-wm-blue underline hover:no-underline font-medium">
            View ↗
          </a>
          <button hx-post="/publish/now" hx-target="#pub-area" hx-swap="outerHTML"
                  hx-indicator="#pub-spinner"
                  class="text-wm-gray100 underline hover:no-underline">
            Republish
          </button>
        </div>"""

    # Never published yet
    return f"""
    <div id="pub-area"
         class="flex items-center gap-2 text-xs text-wm-gray100
                bg-wm-gray10 border border-wm-gray50 px-2 py-1.5 rounded-lg">
      <span>Not published</span>
      <a href="{url}" target="_blank" rel="noopener noreferrer"
         class="text-wm-blue underline hover:no-underline">Link ↗</a>
    </div>"""
