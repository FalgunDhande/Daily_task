from datetime import datetime, date, timedelta
import calendar as cal
from flask import Blueprint, request, jsonify
from models.task import Task
from utils import ensure_occurrences

calendar_bp = Blueprint("calendar_api", __name__, url_prefix="/api")


@calendar_bp.route("/calendar", methods=["GET"])
def calendar_data():
    """Returns tasks between `start` and `end` (YYYY-MM-DD) as FullCalendar-style events."""
    start = request.args.get("start")
    end = request.args.get("end")
    if start and end:
        start_d = datetime.strptime(start[:10], "%Y-%m-%d").date()
        end_d = datetime.strptime(end[:10], "%Y-%m-%d").date()
    else:
        today = date.today()
        first = today.replace(day=1)
        last_day = cal.monthrange(today.year, today.month)[1]
        start_d = first
        end_d = today.replace(day=last_day)

    ensure_occurrences(start_d, end_d)

    tasks = Task.query.filter(
        Task.is_template == False,  # noqa: E712
        Task.due_date >= start_d,
        Task.due_date <= end_d,
    ).all()

    events = []
    for t in tasks:
        color = t.category.color if t.category else "#64748b"
        if t.status == "completed":
            color = "#22c55e"
        elif t.is_overdue():
            color = "#ef4444"
        events.append({
            "id": t.id,
            "title": t.title,
            "start": t.due_date.isoformat(),
            "allDay": True,
            "color": color,
            "extendedProps": {
                "priority": t.priority,
                "status": t.status,
                "category": t.category.name if t.category else None,
                "due_time": t.due_time.strftime("%H:%M") if t.due_time else None,
                "is_overdue": t.is_overdue(),
            },
        })
    return jsonify(events)


@calendar_bp.route("/calendar/day/<the_date>", methods=["GET"])
def calendar_day(the_date):
    d = datetime.strptime(the_date, "%Y-%m-%d").date()
    ensure_occurrences(d, d)
    tasks = Task.query.filter_by(is_template=False, due_date=d).all()
    return jsonify([t.to_dict() for t in tasks])
