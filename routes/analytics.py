from datetime import date, timedelta
import calendar as cal
from collections import defaultdict
from flask import Blueprint, request, jsonify
from models import db
from models.task import Task, TaskCompletion, Category
from utils import calculate_streaks

analytics_bp = Blueprint("analytics_api", __name__, url_prefix="/api")


@analytics_bp.route("/analytics", methods=["GET"])
def monthly_analytics():
    year = request.args.get("year", type=int, default=date.today().year)
    month = request.args.get("month", type=int, default=date.today().month)
    days_in_month = cal.monthrange(year, month)[1]
    month_start = date(year, month, 1)
    month_end = date(year, month, days_in_month)

    tasks = Task.query.filter(
        Task.is_template == False,  # noqa: E712
        Task.due_date >= month_start,
        Task.due_date <= month_end,
    ).all()

    total = len(tasks)
    completed = [t for t in tasks if t.status == "completed"]
    pending = [t for t in tasks if t.status == "pending" and not t.is_overdue()]
    overdue = [t for t in tasks if t.is_overdue()]
    completion_pct = round(len(completed) / total * 100) if total else 0

    # daily completion % across the month
    daily_pct = []
    day_completion_counts = defaultdict(int)
    day_totals = defaultdict(int)
    for t in tasks:
        day_totals[t.due_date.day] += 1
        if t.status == "completed":
            day_completion_counts[t.due_date.day] += 1
    for d in range(1, days_in_month + 1):
        tot = day_totals.get(d, 0)
        c = day_completion_counts.get(d, 0)
        daily_pct.append(round(c / tot * 100) if tot else 0)

    best_day_num = max(range(1, days_in_month + 1), key=lambda d: day_completion_counts.get(d, 0), default=1)
    best_day = f"{year}-{month:02d}-{best_day_num:02d}" if day_completion_counts else None

    # most productive category
    cat_counts = defaultdict(int)
    for t in completed:
        cat_counts[t.category.name if t.category else "Other"] += 1
    most_productive_category = max(cat_counts, key=cat_counts.get) if cat_counts else None

    # category distribution (all tasks, not just completed)
    cat_dist = defaultdict(int)
    for t in tasks:
        cat_dist[t.category.name if t.category else "Other"] += 1

    # weekly productivity trend (completion % by ISO week within month)
    week_totals = defaultdict(int)
    week_completed = defaultdict(int)
    for t in tasks:
        week_num = t.due_date.isocalendar()[1]
        week_totals[week_num] += 1
        if t.status == "completed":
            week_completed[week_num] += 1
    weekly_trend = [
        {"week": f"Week {i+1}", "pct": round(week_completed[w] / week_totals[w] * 100) if week_totals[w] else 0}
        for i, w in enumerate(sorted(week_totals.keys()))
    ]

    current_streak, longest_streak = calculate_streaks()

    return jsonify({
        "year": year,
        "month": month,
        "total_tasks": total,
        "completed_tasks": len(completed),
        "pending_tasks": len(pending),
        "overdue_tasks": len(overdue),
        "completion_pct": completion_pct,
        "best_day": best_day,
        "most_productive_category": most_productive_category,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "charts": {
            "daily_completion_pct": daily_pct,
            "completed_vs_pending": {"completed": len(completed), "pending": len(pending) + len(overdue)},
            "category_distribution": cat_dist,
            "weekly_trend": weekly_trend,
        },
    })


@analytics_bp.route("/history", methods=["GET"])
def history():
    days_back = request.args.get("days", type=int, default=30)
    start = date.today() - timedelta(days=days_back)

    completions = (
        TaskCompletion.query.filter(TaskCompletion.completed_on >= start)
        .order_by(TaskCompletion.completed_on.desc())
        .all()
    )
    missed = Task.query.filter(
        Task.is_template == False,  # noqa: E712
        Task.status == "pending",
        Task.due_date >= start,
        Task.due_date < date.today(),
    ).all()

    by_day = defaultdict(lambda: {"completed": [], "missed": []})
    for c in completions:
        by_day[c.completed_on.isoformat()]["completed"].append(c.task.title if c.task else "Task")
    for m in missed:
        by_day[m.due_date.isoformat()]["missed"].append(m.title)

    days = sorted(by_day.keys(), reverse=True)
    return jsonify([{"date": d, **by_day[d]} for d in days])
