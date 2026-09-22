from datetime import datetime, date, timedelta
import calendar as cal
from flask import Blueprint, request, jsonify
from models import db
from models.habit import Habit, HabitCompletion
from utils import habit_streak

habits_bp = Blueprint("habits_api", __name__, url_prefix="/api")


def _parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date() if s else None


@habits_bp.route("/habits", methods=["GET"])
def get_habits():
    year = request.args.get("year", type=int, default=date.today().year)
    month = request.args.get("month", type=int, default=date.today().month)
    days_in_month = cal.monthrange(year, month)[1]

    habits = Habit.query.filter_by(active=True).order_by(Habit.id).all()
    result = []
    for h in habits:
        completions = {
            c.completed_on.day
            for c in HabitCompletion.query.filter(
                HabitCompletion.habit_id == h.id,
                db.extract("year", HabitCompletion.completed_on) == year,
                db.extract("month", HabitCompletion.completed_on) == month,
            ).all()
        }
        current, longest = habit_streak(h.id)
        d = h.to_dict()
        d["days"] = {day: (day in completions) for day in range(1, days_in_month + 1)}
        d["current_streak"] = current
        d["longest_streak"] = longest
        d["completions_this_month"] = len(completions)
        result.append(d)
    return jsonify(result)


@habits_bp.route("/habits", methods=["POST"])
def create_habit():
    data = request.get_json(force=True) or {}
    if not data.get("name", "").strip():
        return jsonify({"error": "Habit name is required"}), 400
    habit = Habit(
        name=data["name"].strip(),
        target_frequency=data.get("target_frequency", "daily"),
        target_count=data.get("target_count", 7),
        goal=data.get("goal", ""),
        start_date=_parse_date(data.get("start_date")) or date.today(),
    )
    db.session.add(habit)
    db.session.commit()
    return jsonify(habit.to_dict()), 201


@habits_bp.route("/habits/<int:habit_id>", methods=["PUT"])
def update_habit(habit_id):
    habit = Habit.query.get_or_404(habit_id)
    data = request.get_json(force=True) or {}
    if "name" in data:
        if not data["name"].strip():
            return jsonify({"error": "Habit name is required"}), 400
        habit.name = data["name"].strip()
    if "target_frequency" in data:
        habit.target_frequency = data["target_frequency"]
    if "target_count" in data:
        habit.target_count = data["target_count"]
    if "goal" in data:
        habit.goal = data["goal"]
    if "active" in data:
        habit.active = data["active"]
    db.session.commit()
    return jsonify(habit.to_dict())


@habits_bp.route("/habits/<int:habit_id>", methods=["DELETE"])
def delete_habit(habit_id):
    habit = Habit.query.get_or_404(habit_id)
    HabitCompletion.query.filter_by(habit_id=habit.id).delete()
    db.session.delete(habit)
    db.session.commit()
    return jsonify({"deleted": True})


@habits_bp.route("/habits/<int:habit_id>/toggle", methods=["POST"])
def toggle_habit(habit_id):
    Habit.query.get_or_404(habit_id)
    data = request.get_json(force=True) or {}
    on = _parse_date(data.get("date")) or date.today()

    existing = HabitCompletion.query.filter_by(habit_id=habit_id, completed_on=on).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({"completed": False, "date": on.isoformat()})
    else:
        db.session.add(HabitCompletion(habit_id=habit_id, completed_on=on))
        db.session.commit()
        return jsonify({"completed": True, "date": on.isoformat()})
