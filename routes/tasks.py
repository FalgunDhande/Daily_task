from datetime import datetime, date, timedelta
from flask import Blueprint, request, jsonify
from models import db
from models.task import Task, Category, TaskCompletion, Reminder, PRIORITIES
from utils import ensure_occurrences, calculate_streaks

tasks_bp = Blueprint("tasks_api", __name__, url_prefix="/api")


def _parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date() if s else None


def _parse_time(s):
    return datetime.strptime(s, "%H:%M").time() if s else None


# ---------- Categories ----------
@tasks_bp.route("/categories", methods=["GET"])
def get_categories():
    cats = Category.query.order_by(Category.id).all()
    return jsonify([c.to_dict() for c in cats])


# ---------- Tasks CRUD ----------
@tasks_bp.route("/tasks", methods=["GET"])
def get_tasks():
    # make sure recurring occurrences exist for a reasonable window around "today"
    ensure_occurrences(date.today() - timedelta(days=7), date.today() + timedelta(days=60))

    q = Task.query.filter_by(is_template=False)

    search = request.args.get("search")
    if search:
        q = q.filter(Task.title.ilike(f"%{search}%"))

    date_filter = request.args.get("date")
    if date_filter:
        q = q.filter(Task.due_date == _parse_date(date_filter))

    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    if date_from:
        q = q.filter(Task.due_date >= _parse_date(date_from))
    if date_to:
        q = q.filter(Task.due_date <= _parse_date(date_to))

    category_id = request.args.get("category_id")
    if category_id:
        q = q.filter(Task.category_id == int(category_id))

    priority = request.args.get("priority")
    if priority:
        q = q.filter(Task.priority == priority)

    status = request.args.get("status")
    if status:
        q = q.filter(Task.status == status)

    if request.args.get("overdue") == "true":
        q = q.filter(Task.status == "pending", Task.due_date < date.today())

    sort = request.args.get("sort", "due_date")
    if sort == "priority":
        order = {"Urgent": 0, "High": 1, "Medium": 2, "Low": 3}
        results = q.all()
        results.sort(key=lambda t: (order.get(t.priority, 4), t.due_date or date.max))
    else:
        results = q.all()
        results.sort(key=lambda t: (t.due_date or date.max, t.due_time or datetime.max.time()))

    return jsonify([t.to_dict() for t in results])


@tasks_bp.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    t = Task.query.get_or_404(task_id)
    return jsonify(t.to_dict())


@tasks_bp.route("/tasks", methods=["POST"])
def create_task():
    data = request.get_json(force=True) or {}
    if not data.get("title", "").strip():
        return jsonify({"error": "Task name is required"}), 400
    if data.get("priority") and data["priority"] not in PRIORITIES:
        return jsonify({"error": "Invalid priority"}), 400

    recurrence = data.get("recurrence", "none")
    is_template = recurrence != "none"

    task = Task(
        title=data["title"].strip(),
        description=data.get("description", ""),
        notes=data.get("notes", ""),
        category_id=data.get("category_id"),
        priority=data.get("priority", "Medium"),
        due_date=_parse_date(data.get("due_date")),
        due_time=_parse_time(data.get("due_time")),
        time_block=data.get("time_block", "Morning"),
        recurrence=recurrence,
        recurrence_days=",".join(str(x) for x in data.get("recurrence_days", [])),
        is_template=is_template,
        reminder_time=_parse_time(data.get("reminder_time")),
    )
    db.session.add(task)
    db.session.commit()

    if task.reminder_time and task.due_date:
        remind_dt = datetime.combine(task.due_date, task.reminder_time)
        db.session.add(Reminder(task_id=task.id, remind_at=remind_dt))
        db.session.commit()

    if is_template:
        ensure_occurrences(date.today(), date.today() + timedelta(days=60))

    return jsonify(task.to_dict()), 201


@tasks_bp.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.get_json(force=True) or {}

    if "title" in data:
        if not data["title"].strip():
            return jsonify({"error": "Task name is required"}), 400
        task.title = data["title"].strip()
    if "description" in data:
        task.description = data["description"]
    if "notes" in data:
        task.notes = data["notes"]
    if "category_id" in data:
        task.category_id = data["category_id"]
    if "priority" in data:
        if data["priority"] not in PRIORITIES:
            return jsonify({"error": "Invalid priority"}), 400
        task.priority = data["priority"]
    if "due_date" in data:
        task.due_date = _parse_date(data["due_date"])
    if "due_time" in data:
        task.due_time = _parse_time(data["due_time"])
    if "time_block" in data:
        task.time_block = data["time_block"]
    if "reminder_time" in data:
        task.reminder_time = _parse_time(data["reminder_time"])

    db.session.commit()
    return jsonify(task.to_dict())


@tasks_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    TaskCompletion.query.filter_by(task_id=task.id).delete()
    Reminder.query.filter_by(task_id=task.id).delete()
    if task.is_template:
        for occ in list(task.occurrences):
            TaskCompletion.query.filter_by(task_id=occ.id).delete()
            db.session.delete(occ)
    db.session.delete(task)
    db.session.commit()
    return jsonify({"deleted": True})


@tasks_bp.route("/tasks/<int:task_id>/complete", methods=["POST"])
def complete_task(task_id):
    task = Task.query.get_or_404(task_id)
    task.status = "completed"
    task.completed_at = datetime.utcnow()
    on = task.due_date or date.today()
    if not TaskCompletion.query.filter_by(task_id=task.id, completed_on=on).first():
        db.session.add(TaskCompletion(task_id=task.id, completed_on=on))
    db.session.commit()
    return jsonify(task.to_dict())


@tasks_bp.route("/tasks/<int:task_id>/uncomplete", methods=["POST"])
def uncomplete_task(task_id):
    task = Task.query.get_or_404(task_id)
    task.status = "pending"
    task.completed_at = None
    on = task.due_date or date.today()
    TaskCompletion.query.filter_by(task_id=task.id, completed_on=on).delete()
    db.session.commit()
    return jsonify(task.to_dict())


# ---------- Dashboard summary ----------
@tasks_bp.route("/dashboard", methods=["GET"])
def dashboard_summary():
    ensure_occurrences(date.today() - timedelta(days=1), date.today() + timedelta(days=1))
    today = date.today()

    todays = Task.query.filter_by(is_template=False, due_date=today).all()
    completed_today = [t for t in todays if t.status == "completed"]
    pending_today = [t for t in todays if t.status == "pending"]

    month_start = today.replace(day=1)
    month_tasks = Task.query.filter(
        Task.is_template == False,  # noqa: E712
        Task.due_date >= month_start,
        Task.due_date <= today,
    ).all()
    month_completed = [t for t in month_tasks if t.status == "completed"]

    total_completed = Task.query.filter_by(is_template=False, status="completed").count()
    overdue = Task.query.filter(
        Task.is_template == False,  # noqa: E712
        Task.status == "pending",
        Task.due_date < today,
    ).count()
    upcoming = Task.query.filter(
        Task.is_template == False,  # noqa: E712
        Task.status == "pending",
        Task.due_date > today,
        Task.due_date <= today + timedelta(days=7),
    ).count()

    current_streak, longest_streak = calculate_streaks()

    daily_pct = round(len(completed_today) / len(todays) * 100) if todays else 0
    monthly_pct = round(len(month_completed) / len(month_tasks) * 100) if month_tasks else 0

    return jsonify({
        "date": today.isoformat(),
        "day_name": today.strftime("%A"),
        "completed_today": len(completed_today),
        "pending_today": len(pending_today),
        "daily_completion_pct": daily_pct,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "monthly_completion_pct": monthly_pct,
        "total_completed": total_completed,
        "overdue_tasks": overdue,
        "upcoming_tasks": upcoming,
    })


@tasks_bp.route("/reminders/upcoming", methods=["GET"])
def upcoming_reminders():
    """Legacy redirect — now handled by notifications blueprint."""
    from flask import redirect, url_for
    return redirect(url_for("notifications_api.upcoming_reminders"))

