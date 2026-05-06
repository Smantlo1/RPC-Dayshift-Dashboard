"""
routine_data.py — Single source of truth for all routine time blocks.
Each block has: id, label, time_range, description, checklist items, output.
Day-specific overrides are handled via DAILY_OVERRIDES.
"""

from typing import TypedDict


class ChecklistItem(TypedDict):
    id: str
    text: str


class TimeBlock(TypedDict):
    id: str
    label: str
    time_range: str
    start_hour: float   # decimal hour for sorting/nudges
    end_hour: float
    description: str
    checklist: list[ChecklistItem]
    output: str
    module: str | None  # links to a special module tab if applicable
    is_lunch: bool


# ---------------------------------------------------------------------------
# BASELINE ROUTINE (Monday — all days inherit this unless overridden)
# ---------------------------------------------------------------------------
BASELINE_BLOCKS: list[TimeBlock] = [
    {
        "id": "turnover",
        "label": "Turnover + Reality Check",
        "time_range": "6:00 – 7:30 AM",
        "start_hour": 6.0,
        "end_hour": 7.5,
        "description": (
            "Arrive and walk with overnight RPC. Review OneNote for completion and accuracy. "
            "Identify missing fixtures, incomplete work, or anything that could impact tonight. "
            "Focus ONLY on understanding the current state of the store."
        ),
        "checklist": [
            {"id": "to_walk", "text": "Walk with overnight RPC"},
            {"id": "to_onenote", "text": "Review OneNote for completion & accuracy"},
            {"id": "to_fixtures", "text": "Identify missing fixtures"},
            {"id": "to_incomplete", "text": "Note any incomplete work"},
            {"id": "to_tonight", "text": "Flag anything that could impact tonight"},
        ],
        "output": "Short prioritized Today's Problems list ready for the morning.",
        "module": None,
        "is_lunch": False,
    },
    {
        "id": "morning_meeting",
        "label": "Morning Meeting",
        "time_range": "7:30 – 8:00 AM",
        "start_hour": 7.5,
        "end_hour": 8.0,
        "description": (
            "Attend morning meeting — goal is capturing actions, not just listening. "
            "Write down (or use AI) what needs to be done today, what is behind, and who owns each item. "
            "If no owner is clear, assign one before leaving the meeting."
        ),
        "checklist": [
            {"id": "mm_attend", "text": "Attend morning meeting"},
            {"id": "mm_capture", "text": "Capture all action items"},
            {"id": "mm_behind", "text": "Note what is behind schedule"},
            {"id": "mm_owners", "text": "Confirm owner for every action item"},
            {"id": "mm_assign", "text": "Assign owner for any unowned items"},
        ],
        "output": "Clear action list with ownership assigned for every item.",
        "module": "tasks",
        "is_lunch": False,
    },
    {
        "id": "followups",
        "label": "Follow-Ups + Tracking Updates",
        "time_range": "8:00 – 9:00 AM",
        "start_hour": 8.0,
        "end_hour": 9.0,
        "description": (
            "Send follow-ups from the meeting immediately. Address anything not completed overnight. "
            "Connect with dayshift OPL and ISG on daily priorities. Escalate missing fixtures, "
            "unanswered tickets, or missed deadlines. Update ALL Project Tracking Sheets (fixtures, "
            "signage, displays, RPS, SET). Rule: past due → escalate same day; 24h → follow up; "
            "48h → escalate. Place needed Add-On orders and add to tracking."
        ),
        "checklist": [
            {"id": "fu_followups", "text": "Send follow-ups from morning meeting"},
            {"id": "fu_overnight", "text": "Address anything not completed overnight"},
            {"id": "fu_opl", "text": "Connect with dayshift OPL and ISG"},
            {"id": "fu_escalate", "text": "Escalate missing fixtures / unanswered tickets"},
            {"id": "fu_fixtures", "text": "Update Fixtures tracking sheet"},
            {"id": "fu_signage", "text": "Update Signage tracking sheet"},
            {"id": "fu_displays", "text": "Update Displays tracking sheet"},
            {"id": "fu_rps", "text": "Update RPS tickets"},
            {"id": "fu_set", "text": "Update SET tickets"},
            {"id": "fu_addon", "text": "Place Add-On orders and add to tracking"},
        ],
        "output": "No unclear or unowned issues. Tracking fully updated.",
        "module": "projects",
        "is_lunch": False,
    },
    {
        "id": "quick_plan",
        "label": "Quick Planning",
        "time_range": "9:00 – 9:30 AM",
        "start_hour": 9.0,
        "end_hour": 9.5,
        "description": (
            "Review whether today's work is set up for success. Confirm what area is next in phasing. "
            "Simple questions: Are we on track today? Is the next area ready? "
            "If not — adjust now or escalate immediately."
        ),
        "checklist": [
            {"id": "qp_today", "text": "Confirm today's work is set up for success"},
            {"id": "qp_next", "text": "Confirm next phasing area is ready"},
            {"id": "qp_track", "text": "Are we on track? If not — adjust or escalate"},
        ],
        "output": "Clear plan for today + awareness of the next phase.",
        "module": None,
        "is_lunch": False,
    },
    {
        "id": "validation",
        "label": "Validation + Cleanup",
        "time_range": "9:30 – 10:45 AM",
        "start_hour": 9.5,
        "end_hour": 10.75,
        "description": (
            "Prevent future problems. Verify we have what we need for nightly notes. "
            "Clean up email — only items requiring follow-up remain, file everything else. "
            "Send follow-ups on outstanding issues, continue escalation if needed. "
            "Start or update notes for third shift and known issues."
        ),
        "checklist": [
            {"id": "val_nightly", "text": "Verify materials/info for nightly notes"},
            {"id": "val_email", "text": "Clean email inbox — only follow-ups remain"},
            {"id": "val_followups", "text": "Send outstanding follow-ups"},
            {"id": "val_escalate", "text": "Continue escalation on needed items"},
            {"id": "val_notes", "text": "Start/update third-shift notes and known issues"},
        ],
        "output": "Clean inbox, documented risks, all problem items actively escalated.",
        "module": None,
        "is_lunch": False,
    },
    {
        "id": "picklist",
        "label": "Picklist Start",
        "time_range": "10:45 – 11:00 AM",
        "start_hour": 10.75,
        "end_hour": 11.0,
        "description": (
            "Begin the picklist — focus on what fixtures are needed and when they must arrive. "
            "Identify missing major items or zero on-hands immediately. "
            "CRITICAL: If major items are missing, do NOT continue blindly — flag it, escalate, "
            "and prepare a basic backup plan before proceeding."
        ),
        "checklist": [
            {"id": "pl_open", "text": "Open picklist and review needed fixtures"},
            {"id": "pl_dates", "text": "Confirm needed-by dates for each item"},
            {"id": "pl_zeros", "text": "Identify zero on-hands immediately"},
            {"id": "pl_critical", "text": "Flag and escalate any critical missing items"},
            {"id": "pl_backup", "text": "Prepare backup plan for critical shortages"},
        ],
        "output": "Picklist started, critical gaps flagged, escalation in motion.",
        "module": None,
        "is_lunch": False,
    },
    {
        "id": "lunch",
        "label": "Lunch",
        "time_range": "11:00 AM – 12:00 PM",
        "start_hour": 11.0,
        "end_hour": 12.0,
        "description": "Lunch break. Step away. You've earned it.",
        "checklist": [],
        "output": "Rested and ready for the afternoon.",
        "module": None,
        "is_lunch": True,
    },
    {
        "id": "future_walk",
        "label": "Future Walk (up to 2 weeks out)",
        "time_range": "12:00 – 1:00 PM",
        "start_hour": 12.0,
        "end_hour": 13.0,
        "description": (
            "Walk upcoming areas (up to 2 weeks out). Verify fixtures are present or ordered "
            "and that the plan makes sense in reality. If anything is missing or off — "
            "place orders or escalate immediately. Build confidence that the next two weeks "
            "will NOT fail due to preventable issues."
        ),
        "checklist": [
            {"id": "fw_areas", "text": "Walk all upcoming areas (2-week window)"},
            {"id": "fw_fixtures", "text": "Verify fixtures present or ordered for each area"},
            {"id": "fw_plan", "text": "Confirm plan makes sense on the floor"},
            {"id": "fw_orders", "text": "Place missing orders immediately"},
            {"id": "fw_escalate", "text": "Escalate anything that cannot be self-resolved"},
        ],
        "output": "Confidence that next two weeks will not fail due to preventable issues.",
        "module": None,
        "is_lunch": False,
    },
    {
        "id": "closeout",
        "label": "Close Out + Prep",
        "time_range": "1:00 – 2:00 PM",
        "start_hour": 13.0,
        "end_hour": 14.0,
        "description": (
            "Finish and send overnight notes. Send any final follow-ups still outstanding. "
            "Prepare anything that gets you ahead for tomorrow. "
            "Ask two questions before you leave: Is overnight set up to succeed? Is tomorrow clear? "
            "A clean handoff means no confusion going into the night."
        ),
        "checklist": [
            {"id": "co_notes",    "text": "Finish and send overnight notes to third shift"},
            {"id": "co_followups","text": "Send all final follow-ups — nothing left waiting"},
            {"id": "co_trailer",  "text": "Confirm trailer staging is correct"},
            {"id": "co_tomorrow", "text": "Prep anything that gets you ahead for tomorrow"},
            {"id": "co_tracking", "text": "Confirm Tracking Sheet is fully updated"},
            {"id": "co_overnight","text": "Is overnight set up to succeed? (Y/N)"},
            {"id": "co_clear",    "text": "Is tomorrow clear of blockers? (Y/N)"},
        ],
        "output": "Clean handoff — notes sent, follow-ups done, tomorrow is ready.",
        "module": None,
        "is_lunch": False,
    },
]

# ---------------------------------------------------------------------------
# DAY-SPECIFIC OVERRIDES — replaces or augments certain blocks per weekday
# Key = weekday number (0=Monday … 6=Sunday)
# ---------------------------------------------------------------------------

TUESDAY_EXTRA_BLOCK: TimeBlock = {
    "id": "tue_planning",
    "label": "Planning Lock-In (Tuesday)",
    "time_range": "9:00 – 10:45 AM",
    "start_hour": 9.0,
    "end_hour": 10.75,
    "description": (
        "Finalize the weekly plan. Confirm phasing. Complete the weekly planner. "
        "Review GC needs and flooring schedule. Finalize department PDFs in Adobe. "
        "This is the lock-in — decisions made here drive the whole week."
    ),
    "checklist": [
        {"id": "tue_plan", "text": "Finalize weekly plan"},
        {"id": "tue_phase", "text": "Confirm phasing sequence"},
        {"id": "tue_planner", "text": "Complete weekly planner document"},
        {"id": "tue_gc", "text": "Review GC needs"},
        {"id": "tue_floor", "text": "Review flooring schedule"},
        {"id": "tue_pdfs", "text": "Finalize department PDFs in Adobe"},
    ],
    "output": "Weekly plan locked in, phasing confirmed, PDFs finalized.",
    "module": "weekly",
    "is_lunch": False,
}

TUESDAY_EXPENSES_BLOCK: TimeBlock = {
    "id": "tue_expenses",
    "label": "Expenses (Previous Weeks)",
    "time_range": "12:00 – 1:00 PM",
    "start_hour": 12.0,
    "end_hour": 13.0,
    "description": "Complete and submit expenses for previous weeks. Do not let these pile up.",
    "checklist": [
        {"id": "exp_review", "text": "Review all receipts / previous week expenses"},
        {"id": "exp_submit", "text": "Submit expense report"},
        {"id": "exp_confirm", "text": "Confirm submission confirmation received"},
    ],
    "output": "Expenses submitted for all previous weeks.",
    "module": None,
    "is_lunch": False,
}

WEDNESDAY_PREENTRY_BLOCK: TimeBlock = {
    "id": "wed_preentry",
    "label": "Pre-Entry for JSR + REXPRT Update",
    "time_range": "All Day Focus",
    "start_hour": 8.0,
    "end_hour": 16.0,
    "description": (
        "Begin pre-entry for JSR. Update REXPRT. "
        "Goal: make everything clear and accessible before Thursday's 9:00 AM deadline. "
        "No surprises tomorrow."
    ),
    "checklist": [
        {"id": "wed_jsr", "text": "Begin JSR pre-entry"},
        {"id": "wed_rexprt", "text": "Update REXPRT"},
        {"id": "wed_clear", "text": "Confirm everything is clear and accessible"},
        {"id": "wed_ready", "text": "Verify ready for Thursday 9:00 AM JSR deadline"},
    ],
    "output": "JSR pre-entry complete, REXPRT updated, ready for Thursday deadline.",
    "module": None,
    "is_lunch": False,
}

THURSDAY_JSR_BLOCK: TimeBlock = {
    "id": "thu_jsr",
    "label": "JSR Due — 9:00 AM HARD DEADLINE",
    "time_range": "By 9:00 AM",
    "start_hour": 8.0,
    "end_hour": 9.0,
    "description": (
        "JSR is due by 9:00 AM. No exceptions. Submit and confirm. "
        "Then follow up on any outstanding issues or risks. Accountability — no surprises."
    ),
    "checklist": [
        {"id": "thu_submit", "text": "Submit JSR by 9:00 AM"},
        {"id": "thu_confirm", "text": "Confirm JSR submission received"},
        {"id": "thu_risks", "text": "Follow up on outstanding issues and risks"},
    ],
    "output": "JSR submitted, confirmed, no open surprises.",
    "module": None,
    "is_lunch": False,
}

FRIDAY_SUMMARY_BLOCK: TimeBlock = {
    "id": "fri_summary",
    "label": "Weekly Summary — 9:00 AM HARD DEADLINE",
    "time_range": "By 9:00 AM",
    "start_hour": 8.0,
    "end_hour": 9.0,
    "description": (
        "Send Weekly Summary by 9:00 AM covering: progress, risks, and key updates. "
        "Then use the rest of the day for admin and stabilization: clean up overnight issues, "
        "resolve outstanding follow-ups, prepare notes for Sunday. "
        "Leave the site controlled going into the weekend."
    ),
    "checklist": [
        {"id": "fri_summary", "text": "Send Weekly Summary by 9:00 AM"},
        {"id": "fri_overnight", "text": "Clean up overnight issues"},
        {"id": "fri_followups", "text": "Resolve outstanding follow-ups"},
        {"id": "fri_sunday", "text": "Prepare notes for Sunday"},
        {"id": "fri_controlled", "text": "Confirm site is controlled going into weekend"},
    ],
    "output": "Weekly summary sent, site controlled, weekend handoff complete.",
    "module": None,
    "is_lunch": False,
}

# Weekday integer → list of block IDs to replace/inject + the replacement block
# This is processed in get_blocks_for_day()
DAILY_OVERRIDES: dict[int, dict] = {
    1: {  # Tuesday
        "replace": {"quick_plan": TUESDAY_EXTRA_BLOCK},
        "replace_block": {"future_walk": TUESDAY_EXPENSES_BLOCK},
    },
    2: {  # Wednesday
        "inject_after": {"followups": WEDNESDAY_PREENTRY_BLOCK},
    },
    3: {  # Thursday
        "replace": {"turnover": THURSDAY_JSR_BLOCK},
    },
    4: {  # Friday
        "replace": {"turnover": FRIDAY_SUMMARY_BLOCK},
    },
}


def get_blocks_for_day(weekday: int) -> list[TimeBlock]:
    """Return the ordered list of time blocks for the given weekday (0=Mon)."""
    import copy
    blocks = copy.deepcopy(BASELINE_BLOCKS)
    overrides = DAILY_OVERRIDES.get(weekday, {})

    # Replace blocks by id
    replacements = overrides.get("replace", {})
    replace_block = overrides.get("replace_block", {})
    inject_after = overrides.get("inject_after", {})

    result = []
    for block in blocks:
        bid = block["id"]
        if bid in replacements:
            result.append(replacements[bid])
        elif bid in replace_block:
            result.append(replace_block[bid])
        else:
            result.append(block)
        if bid in inject_after:
            result.append(inject_after[bid])

    return result


# ---------------------------------------------------------------------------
# PRIORITY RULES (used by nudge engine)
# ---------------------------------------------------------------------------
PRIORITY_RULES = [
    "1st: Make sure TODAY's work gets done.",
    "2nd: Make sure TOMORROW is set up.",
    "3rd: Escalate anything that could impact phasing — IMMEDIATELY.",
]

TRACKING_RULES = [
    "Keep only 3 lists: Today (must-do), Obstacles (needs escalation), Upcoming (future).",
    "If something doesn't fit one of those 3 lists — it waits.",
    "Past due → escalate SAME DAY.",
    "24 hours → follow up.",
    "48 hours → escalate.",
]

WEEKLY_CADENCE = {
    "Tuesday": "Planning Lock-In — finalize the weekly plan and phasing.",
    "Wednesday": "Pre-entry for JSR + REXPRT update.",
    "Thursday": "JSR due by 9:00 AM — no exceptions.",
    "Friday": "Weekly Summary due by 9:00 AM — leave site controlled.",
}

# Tracking sheet — live Excel file hosted in SharePoint/Teams
TRACKING_SHEET_VIEW_URL = (
    "https://teams.wal-mart.com/sites/5845NicevilleFL/Shared%20Documents/"
    "5845%20Niceville,%20FL/5845_Tracker_LIVE_v6%20(1).xlsx?web=1"
)
TRACKING_SHEET_EMBED_URL = (
    "https://teams.wal-mart.com/sites/5845NicevilleFL/Shared%20Documents/"
    "5845%20Niceville,%20FL/5845_Tracker_LIVE_v6%20(1).xlsx"
    "?action=embedview&wdAllowInteractivity=True&wdHideHeaders=False"
    "&wdDownloadButton=True&wdInConfigurator=True"
)

# Block status options
BLOCK_STATUSES = ["pending", "in-progress", "done", "skipped"]

# Project categories
PROJECT_CATEGORIES = ["Fixtures", "Signage", "Displays", "RPS Tickets", "SET Tickets"]

# Project status options
PROJECT_STATUSES = ["On Track", "At Risk", "Overdue", "Complete", "Blocked"]
