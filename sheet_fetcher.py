"""
sheet_fetcher.py — Fetch the live tracking-sheet xlsx from SharePoint,
parse it with openpyxl, and cache the result in-memory.

Auth strategy (layered — first that works wins):
  1. Plain request — works if Walmart VPN grants access without a challenge.
  2. Windows Negotiate/NTLM SSPI — uses the current domain user's token
     automatically via requests-negotiate-sspi (no password prompt).
  3. Failure — returns a clear error string; caller shows it in the UI.

Cache TTL: CACHE_TTL seconds (default 10 min). Force-refresh via force=True.
"""

import asyncio
import io
import logging
import time
from datetime import date, datetime
from typing import Optional

from routine_data import TRACKING_SHEET_RAW_URL, TRACKING_SHEET_VIEW_URL

log = logging.getLogger(__name__)

CACHE_TTL = 600  # seconds
MAX_ROWS = 500
MAX_COLS = 40

# ── Status keywords for cell colouring in the template ───────────────────────
_STATUS_CLASSES: list[tuple[frozenset, str]] = [
    (frozenset({"on track", "complete", "done", "ordered", "yes"}),   "cell-ok"),
    (frozenset({"overdue", "past due", "blocked", "critical", "no"}), "cell-bad"),
    (frozenset({"at risk", "in progress", "pending", "tbd"}),         "cell-warn"),
]


def status_class(val: str) -> str:
    """Return a CSS class name for known status values, else ''."""
    key = val.strip().lower()
    for keywords, cls in _STATUS_CLASSES:
        if key in keywords:
            return cls
    return ""


# ── In-memory cache ───────────────────────────────────────────────────────────
_cache: dict = {
    "sheets":     None,   # list[SheetData] or None
    "error":      None,   # str or None
    "fetched_at": 0.0,
}


def _is_fresh() -> bool:
    return (
        _cache["sheets"] is not None
        and (time.monotonic() - _cache["fetched_at"]) < CACHE_TTL
    )


# ── Cell formatter ────────────────────────────────────────────────────────────
def _fmt(val) -> str:
    if val is None:
        return ""
    if isinstance(val, bool):
        return "Yes" if val else "No"
    if isinstance(val, (datetime, date)):
        return val.strftime("%m/%d/%Y")
    if isinstance(val, float):
        return str(int(val)) if val == int(val) else f"{val:.2f}"
    return str(val).strip()


# ── Core fetch + parse (blocking — runs in a thread pool) ────────────────────────
def _fetch_bytes() -> tuple[Optional[bytes], Optional[str]]:
    """Return (xlsx_bytes, error_string). One of them will be None.

    Auth strategy:
      Walmart’s SharePoint returns 403 (not 401) when no auth headers
      are present, so the standard “retry on 401” pattern never fires.
      Instead we lead with Windows Negotiate/SSPI on the first attempt
      whenever the package is available (domain-joined machines always
      have a valid Kerberos/NTLM token).  Plain fallback covers edge
      cases where the library is missing.
    """
    try:
        import requests
    except ImportError:
        return None, "requests is not installed (run: uv pip install requests)"

    session = requests.Session()
    session.headers.update({
        "User-Agent": "RPC-Dashboard/1.0 (internal-tool)",
        "Accept": (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
            "application/octet-stream,*/*"
        ),
    })

    # ── Resolve auth: prefer SSPI (domain creds, no prompt) ─────────────
    sspi_auth = None
    try:
        from requests_negotiate_sspi import HttpNegotiateAuth
        sspi_auth = HttpNegotiateAuth()
        log.debug("SSPI available — leading with Windows Negotiate auth")
    except ImportError:
        log.debug("requests_negotiate_sspi not found — trying unauthenticated")

    def _get(auth=None):
        return session.get(
            TRACKING_SHEET_RAW_URL,
            auth=auth,
            timeout=25,
            allow_redirects=True,
            stream=False,
        )

    # ── Attempt 1: SSPI auth (if available) or plain ────────────────────
    try:
        resp = _get(auth=sspi_auth)
    except requests.exceptions.ConnectionError:
        return None, (
            "Cannot reach SharePoint — make sure you are on "
            "Walmart VPN or Eagle WiFi."
        )
    except requests.exceptions.Timeout:
        return None, "Request timed out (25s) — check VPN / Eagle WiFi."
    except Exception as exc:
        return None, f"Unexpected network error: {exc}"

    # ── Attempt 2: if we led with plain and got 401 OR 403, retry with SSPI ─
    # (Walmart SharePoint skips the 401 challenge and returns 403 directly
    #  when no Negotiate header is present.)
    if resp.status_code in (401, 403) and sspi_auth is None:
        try:
            from requests_negotiate_sspi import HttpNegotiateAuth
            log.debug("Got %d — retrying with Windows Negotiate auth", resp.status_code)
            resp = _get(auth=HttpNegotiateAuth())
        except ImportError:
            pass  # sspi not available; fall through to error below

    # ── Check final status ───────────────────────────────────────────────────
    if resp.status_code in (401, 403):
        return None, (
            f"SharePoint returned HTTP {resp.status_code} — authentication "
            "required. Make sure you are signed into SharePoint on VPN."
        )
    if resp.status_code != 200:
        return None, f"SharePoint returned HTTP {resp.status_code}."

    # ── Guard: we must have xlsx bytes, not an HTML login page ───────────────
    ct = resp.headers.get("content-type", "")
    if "html" in ct.lower():
        return None, (
            "SharePoint returned an HTML page instead of the xlsx file "
            "(you may need to open the sheet in your browser first to "
            "establish a session, then retry)."
        )
    if len(resp.content) < 4 or resp.content[:4] != b"PK\x03\x04":
        return None, (
            "Response does not look like a valid xlsx file "
            f"(Content-Type: {ct or 'unknown'})."
        )

    return resp.content, None


def _parse(xlsx_bytes: bytes) -> tuple[Optional[list], Optional[str]]:
    """Parse xlsx bytes → list of sheet dicts. Returns (sheets, error)."""
    try:
        import openpyxl
    except ImportError:
        return None, "openpyxl is not installed (run: uv pip install openpyxl)"

    try:
        wb = openpyxl.load_workbook(
            io.BytesIO(xlsx_bytes),
            read_only=True,
            data_only=True,
        )
    except Exception as exc:
        return None, f"Could not open workbook: {exc}"

    sheets = []
    for name in wb.sheetnames:
        ws = wb[name]
        all_rows: list[tuple] = []
        for row in ws.iter_rows(values_only=True):
            all_rows.append(row)
            if len(all_rows) > MAX_ROWS + 20:  # +20 to account for header scan
                break

        if not all_rows:
            continue

        # Find the first non-blank row → treat as header
        header_idx = 0
        for i, row in enumerate(all_rows):
            if any(c is not None for c in row):
                header_idx = i
                break

        raw_headers = list(all_rows[header_idx])[:MAX_COLS]

        # Trim trailing empty columns
        last_col = 0
        for i, h in enumerate(raw_headers):
            if h is not None and str(h).strip():
                last_col = i
        last_col += 1  # exclusive
        raw_headers = raw_headers[:last_col]

        headers = [_fmt(h) or f"Col {i+1}" for i, h in enumerate(raw_headers)]

        data_rows: list[list[str]] = []
        truncated = False
        for row in all_rows[header_idx + 1:]:
            cells = [_fmt(c) for c in list(row)[:last_col]]
            if any(cells):  # skip fully empty rows
                data_rows.append(cells)
            if len(data_rows) >= MAX_ROWS:
                truncated = True
                break

        sheets.append({
            "name":      name,
            "headers":   headers,
            "rows":      data_rows,
            "row_count": len(data_rows),
            "truncated": truncated,
        })

    wb.close()

    if not sheets:
        return None, "Workbook has no data in any sheet."

    return sheets, None


def _run_fetch() -> None:
    """Blocking: fetch + parse and write into _cache."""
    raw, err = _fetch_bytes()
    if err:
        _cache.update({"sheets": None, "error": err, "fetched_at": time.monotonic()})
        return
    sheets, err = _parse(raw)
    _cache.update({"sheets": sheets, "error": err, "fetched_at": time.monotonic()})


# ── Public async API ──────────────────────────────────────────────────────────
async def get_sheet_data(force: bool = False) -> dict:
    """
    Returns a dict with keys:
      sheets      list[dict] | None
      error       str | None
      fetched_at  float (monotonic timestamp)
      view_url    str
    """
    if not force and _is_fresh():
        return {**_cache, "view_url": TRACKING_SHEET_VIEW_URL}

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _run_fetch)
    return {**_cache, "view_url": TRACKING_SHEET_VIEW_URL}
