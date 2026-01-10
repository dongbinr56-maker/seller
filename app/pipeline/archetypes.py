from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, List, Tuple


def _hash_int(s: str) -> int:
    return int(hashlib.md5(s.encode("utf-8")).hexdigest(), 16)


@dataclass(frozen=True)
class Archetype:
    key: str
    niche: str
    recipe: List[str]                    # render_pdf가 순회하는 page ids
    preview_pages: Tuple[int, int, int]  # preview에 쓸 page index (0-based)
    cover_subtitle: str
    included_lines: List[str]
    howto_lines: List[str]


THEMES: List[str] = [
    "blue_minimal",
    "charcoal_mono",
    "warm_neutral",
]


ARCHETYPES: Dict[str, Archetype] = {
    # ----------------
    # BUDGET (5)
    # ----------------
    "cash_flow": Archetype(
        key="cash_flow",
        niche="BUDGET",
        recipe=[
            "cover",
            "quick_start",
            "cashflow_monthly",
            "cashflow_weekly",
            "bills_due_table",
            "expense_log",
            "sinking_funds",
            "notes_summary",
        ],
        preview_pages=(0, 2, 3),
        cover_subtitle="Cash flow clarity in minutes a day",
        included_lines=[
            "Monthly and weekly cash flow pages",
            "Bills due table plus expense log",
            "Sinking funds tracker and notes",
        ],
        howto_lines=[
            "Print only the pages you need",
            "Fill one line per transaction",
            "Review weekly and adjust quickly",
        ],
    ),
    "bills_due": Archetype(
        key="bills_due",
        niche="BUDGET",
        recipe=[
            "cover",
            "quick_start",
            "bills_calendar",
            "bills_due_table",
            "payment_log",
            "category_budget",
            "expense_log",
            "notes_summary",
        ],
        preview_pages=(0, 2, 3),
        cover_subtitle="A clean system for due dates",
        included_lines=[
            "Bills calendar and due table",
            "Payment log and category budget",
            "Expense log and notes summary",
        ],
        howto_lines=[
            "Write recurring bills first",
            "Check off when paid",
            "Do a fast monthly reset",
        ],
    ),
    "debt_payoff": Archetype(
        key="debt_payoff",
        niche="BUDGET",
        recipe=[
            "cover",
            "quick_start",
            "debt_list",
            "avalanche_tracker",
            "snowball_tracker",
            "payment_log",
            "progress_meter",
            "notes_summary",
        ],
        preview_pages=(0, 2, 3),
        cover_subtitle="A payoff plan you can follow",
        included_lines=[
            "Debt list and payment log",
            "Avalanche and snowball trackers",
            "Progress meter and notes",
        ],
        howto_lines=[
            "List balances from statements",
            "Pick avalanche or snowball",
            "Track each payment you make",
        ],
    ),
    "annual_overview": Archetype(
        key="annual_overview",
        niche="BUDGET",
        recipe=[
            "cover",
            "quick_start",
            "annual_overview",
            "monthly_overview",
            "income_summary",
            "expense_summary",
            "savings_goal_tracker",
            "notes_summary",
        ],
        preview_pages=(0, 2, 3),
        cover_subtitle="Year-at-a-glance money dashboard",
        included_lines=[
            "Annual and monthly overview pages",
            "Income and expense summaries",
            "Savings goal tracker and notes",
        ],
        howto_lines=[
            "Update totals once a month",
            "Compare months using summaries",
            "Keep goals visible all year",
        ],
    ),
    "savings_goal": Archetype(
        key="savings_goal",
        niche="BUDGET",
        recipe=[
            "cover",
            "quick_start",
            "savings_goal_tracker",
            "sinking_funds",
            "no_spend_calendar",
            "challenge_tracker",
            "expense_log",
            "notes_summary",
        ],
        preview_pages=(0, 2, 4),
        cover_subtitle="Small wins that add up",
        included_lines=[
            "Savings goal and sinking funds",
            "No-spend calendar and challenges",
            "Expense log and notes summary",
        ],
        howto_lines=[
            "Pick one goal per sheet",
            "Track weekly deposits",
            "Use challenges for momentum",
        ],
    ),

    # ----------------
    # ADHD (5)  (내부 니치 유지)
    # ----------------
    "brain_dump": Archetype(
        key="brain_dump",
        niche="ADHD",
        recipe=[
            "cover",
            "quick_start",
            "inbox_capture",
            "clarify_next_action",
            "priority_matrix",
            "time_block",
            "habit_grid",
            "notes_summary",
        ],
        preview_pages=(0, 2, 4),
        cover_subtitle="Get thoughts out. Get moving.",
        included_lines=[
            "Inbox capture and next actions",
            "Priority matrix and time blocks",
            "Habit grid and notes summary",
        ],
        howto_lines=[
            "Dump everything into Inbox first",
            "Convert items to next actions",
            "Plan one focused block at a time",
        ],
    ),
    "focus_blocks": Archetype(
        key="focus_blocks",
        niche="ADHD",
        recipe=[
            "cover",
            "quick_start",
            "focus_blocks",
            "deep_work_log",
            "distraction_log",
            "break_plan",
            "mood_checkin",
            "notes_summary",
        ],
        preview_pages=(0, 2, 3),
        cover_subtitle="A lightweight focus system",
        included_lines=[
            "Focus blocks and deep work log",
            "Distraction log and break plan",
            "Mood check-in and notes summary",
        ],
        howto_lines=[
            "Set one block goal",
            "Log distractions fast",
            "Plan breaks before you start",
        ],
    ),
    "routine_builder": Archetype(
        key="routine_builder",
        niche="ADHD",
        recipe=[
            "cover",
            "quick_start",
            "morning_routine",
            "evening_routine",
            "weekly_routine",
            "habit_grid",
            "gratitude_log",
            "notes_summary",
        ],
        preview_pages=(0, 2, 4),
        cover_subtitle="Routines that feel doable",
        included_lines=[
            "Morning and evening routines",
            "Weekly routine and habit grid",
            "Gratitude and notes summary",
        ],
        howto_lines=[
            "Start with the smallest version",
            "Repeat for one week",
            "Adjust, do not restart",
        ],
    ),
    "weekly_review": Archetype(
        key="weekly_review",
        niche="ADHD",
        recipe=[
            "cover",
            "quick_start",
            "weekly_goals",
            "daily_priorities",
            "wins_lessons",
            "next_week_plan",
            "habit_grid",
            "notes_summary",
        ],
        preview_pages=(0, 2, 5),
        cover_subtitle="Close the week. Reset the next.",
        included_lines=[
            "Weekly goals and daily priorities",
            "Wins/lessons and next-week plan",
            "Habit grid and notes summary",
        ],
        howto_lines=[
            "Pick 3 outcomes for the week",
            "Choose one priority per day",
            "Review once, then move on",
        ],
    ),
    "project_planner": Archetype(
        key="project_planner",
        niche="ADHD",
        recipe=[
            "cover",
            "quick_start",
            "project_overview",
            "task_backlog",
            "kanban_board",
            "milestones",
            "meeting_notes",
            "notes_summary",
        ],
        preview_pages=(0, 2, 3),
        cover_subtitle="From ideas to finished",
        included_lines=[
            "Project overview and task backlog",
            "Kanban and milestones",
            "Meeting notes and summary",
        ],
        howto_lines=[
            "Define the next milestone",
            "Pull tasks into Doing",
            "Keep notes in one system",
        ],
    ),
}


def pick_theme(seed_text: str) -> str:
    idx = _hash_int(seed_text) % len(THEMES)
    return THEMES[idx]


def pick_archetype(slug: str, niche: str, title: str) -> Archetype:
    s = (slug or "").lower()
    t = (title or "").lower()
    n = (niche or "").upper()

    # ---------- keyword 우선 매칭 (정확도 높을수록 “복붙” 느낌이 줄어듦) ----------
    # BUDGET
    if ("cash-flow" in s) or ("cash flow" in t) or ("forecast" in t):
        return ARCHETYPES["cash_flow"]
    if ("bill" in s) or ("due" in s) or ("bill" in t) or ("due date" in t):
        return ARCHETYPES["bills_due"]
    if ("debt" in s) or ("avalanche" in s) or ("snowball" in s) or ("payoff" in t):
        return ARCHETYPES["debt_payoff"]
    if ("annual" in s) or ("year" in s) or ("yearly" in t):
        return ARCHETYPES["annual_overview"]
    if ("savings" in s) or ("save" in s) or ("goal" in s) or ("no-spend" in s) or ("challenge" in t):
        return ARCHETYPES["savings_goal"]

    # ADHD / Productivity
    if ("brain-dump" in s) or ("brain dump" in t) or ("inbox" in t) or ("capture" in t):
        return ARCHETYPES["brain_dump"]
    if ("focus" in s) or ("deep work" in t) or ("distraction" in t):
        return ARCHETYPES["focus_blocks"]
    if ("routine" in s) or ("morning" in t) or ("evening" in t):
        return ARCHETYPES["routine_builder"]
    if ("weekly-review" in s) or ("weekly review" in t) or ("wins" in t):
        return ARCHETYPES["weekly_review"]
    if ("project" in s) or ("kanban" in t) or ("milestone" in t):
        return ARCHETYPES["project_planner"]

    # ---------- fallback: niche별로 해시 분산 ----------
    if n == "BUDGET":
        keys = ["cash_flow", "bills_due", "debt_payoff", "annual_overview", "savings_goal"]
    else:
        keys = ["brain_dump", "focus_blocks", "routine_builder", "weekly_review", "project_planner"]

    idx = _hash_int(slug) % len(keys)
    return ARCHETYPES[keys[idx]]
