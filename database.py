"""
database.py — SQLite persistence layer (raw aiosqlite for low-memory footprint).
All schema creation is idempotent — safe to call on every startup.
"""

import aiosqlite
from contextlib import asynccontextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "dashboard.db"


@asynccontextmanager
async def get_db():
    """Async context manager — use as: async with get_db() as db:"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        yield db


async def init_db() -> None:
    """Create all tables if they don't exist. Safe to call repeatedly."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")

        # ── Time block status per day ────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS block_status (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT    NOT NULL,
                block_id    TEXT    NOT NULL,
                status      TEXT    NOT NULL DEFAULT 'pending',
                notes       TEXT    DEFAULT '',
                updated_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
                UNIQUE(date, block_id)
            )
        """)

        # ── Per-block checklist item completion ──────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS checklist_items (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT    NOT NULL,
                block_id    TEXT    NOT NULL,
                item_id     TEXT    NOT NULL,
                is_checked  INTEGER NOT NULL DEFAULT 0,
                checked_at  TEXT,
                UNIQUE(date, block_id, item_id)
            )
        """)

        # ── Three-list task system ───────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                created_date TEXT   NOT NULL,
                text        TEXT    NOT NULL,
                list_type   TEXT    NOT NULL DEFAULT 'today',
                is_done     INTEGER NOT NULL DEFAULT 0,
                is_blocked  INTEGER NOT NULL DEFAULT 0,
                is_critical INTEGER NOT NULL DEFAULT 0,
                owner       TEXT    DEFAULT '',
                notes       TEXT    DEFAULT '',
                done_at     TEXT,
                updated_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        # ── Project tracking ────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                category    TEXT    NOT NULL,
                name        TEXT    NOT NULL,
                status      TEXT    NOT NULL DEFAULT 'On Track',
                owner       TEXT    DEFAULT '',
                notes       TEXT    DEFAULT '',
                due_date    TEXT    DEFAULT '',
                add_on_order TEXT   DEFAULT '',
                last_updated TEXT   NOT NULL DEFAULT (datetime('now','localtime')),
                created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        # ── Picklist items ──────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS picklist (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT    NOT NULL,
                fixture_name TEXT   NOT NULL,
                needed_by   TEXT    DEFAULT '',
                qty_needed  INTEGER DEFAULT 0,
                qty_onhand  INTEGER DEFAULT 0,
                is_critical INTEGER NOT NULL DEFAULT 0,
                is_ordered  INTEGER NOT NULL DEFAULT 0,
                backup_plan TEXT    DEFAULT '',
                notes       TEXT    DEFAULT '',
                updated_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        # ── Future walk items ───────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS future_walk (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                walk_date       TEXT    NOT NULL,
                area_name       TEXT    NOT NULL,
                target_date     TEXT    DEFAULT '',
                fixture_status  TEXT    DEFAULT 'Unknown',
                issues          TEXT    DEFAULT '',
                is_ordered      INTEGER NOT NULL DEFAULT 0,
                is_escalated    INTEGER NOT NULL DEFAULT 0,
                obstacle_created INTEGER NOT NULL DEFAULT 0,
                notes           TEXT    DEFAULT '',
                updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        # ── Closeout records ────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS closeout (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                date            TEXT    NOT NULL UNIQUE,
                notes           TEXT    DEFAULT '',
                trailer_staged  INTEGER NOT NULL DEFAULT 0,
                followups_sent  INTEGER NOT NULL DEFAULT 0,
                tomorrow_ready  INTEGER NOT NULL DEFAULT 0,
                picklist_done   INTEGER NOT NULL DEFAULT 0,
                submitted_at    TEXT,
                updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        await db.commit()
