"""Shared helper functions: recurring task materialization, streaks, stats."""
from datetime import date, timedelta
from models import db
from models.task import Task, TaskCompletion
from models.habit import Habit, HabitCompletion


def daterange(start, end):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def ensure_occurrences(start_date, end_date):
    """Make sure concrete Task rows exist for every recurring template
    in [start_date, end_date]. Idempotent."""
    templates = Task.query.filter_by(is_template=True).all()
    for tpl in templates:
        anchor = tpl.due_date or start_date
        for d in daterange(max(start_date, anchor), end_date):
            if not _recurs_on(tpl, d):
                continue
            exists = Task.query.filter_by(parent_id=tpl.id, due_date=d).first()
            if not exists:
                occ = Task(
                    title=tpl.title,
                    description=tpl.description,
                    notes=tpl.notes,
                    category_id=tpl.category_id,
                    priority=tpl.priority,
                    status="pending",
                    due_date=d,
                    due_time=tpl.due_time,
                    time_block=tpl.time_block,
                    recurrence="none",
                    is_template=False,
                    parent_id=tpl.id,
                    reminder_time=tpl.reminder_time,
                )
                db.session.add(occ)
    db.session.commit()


def _recurs_on(tpl, d):
    if tpl.recurrence == "daily":
        return True
    if tpl.recurrence == "weekly":
        return d.weekday() == tpl.due_date.weekday() if tpl.due_date else False
    if tpl.recurrence == "monthly":
        return tpl.due_date and d.day == tpl.due_date.day
    if tpl.recurrence == "custom":
        days = [int(x) for x in (tpl.recurrence_days or "").split(",") if x != ""]
        return d.weekday() in days
    return False


def is_productive_day(d):
    task_done = TaskCompletion.query.filter_by(completed_on=d).first() is not None
    habit_done = HabitCompletion.query.filter_by(completed_on=d).first() is not None
    return task_done or habit_done


def calculate_streaks():
    """Returns (current_streak, longest_streak) counted in productive days."""
    completions = set(
        r[0] for r in db.session.query(TaskCompletion.completed_on).distinct()
    ) | set(r[0] for r in db.session.query(HabitCompletion.completed_on).distinct())

    if not completions:
        return 0, 0

    all_days = sorted(completions)
    longest = cur_run = 1
    for i in range(1, len(all_days)):
        if (all_days[i] - all_days[i - 1]).days == 1:
            cur_run += 1
        else:
            cur_run = 1
        longest = max(longest, cur_run)

    # current streak: walk back from today (or yesterday if today not done yet)
    today = date.today()
    current = 0
    cursor = today
    if today not in completions:
        cursor = today - timedelta(days=1)
    while cursor in completions:
        current += 1
        cursor -= timedelta(days=1)

    return current, longest


def habit_streak(habit_id):
    days = sorted(
        r[0]
        for r in db.session.query(HabitCompletion.completed_on)
        .filter_by(habit_id=habit_id)
        .distinct()
    )
    if not days:
        return 0, 0
    longest = cur_run = 1
    for i in range(1, len(days)):
        if (days[i] - days[i - 1]).days == 1:
            cur_run += 1
        else:
            cur_run = 1
        longest = max(longest, cur_run)

    today = date.today()
    current = 0
    cursor = today
    days_set = set(days)
    if today not in days_set:
        cursor = today - timedelta(days=1)
    while cursor in days_set:
        current += 1
        cursor -= timedelta(days=1)
    return current, longest
