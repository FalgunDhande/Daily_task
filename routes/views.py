from datetime import date
from flask import Blueprint, render_template

views_bp = Blueprint("views", __name__)


@views_bp.route("/")
def dashboard():
    return render_template("dashboard.html", active="dashboard")


@views_bp.route("/today")
def today():
    return render_template("today.html", active="today", today=date.today().isoformat())


@views_bp.route("/tasks")
def tasks():
    return render_template("tasks.html", active="tasks")


@views_bp.route("/calendar")
def calendar():
    return render_template("calendar.html", active="calendar")


@views_bp.route("/habits")
def habits():
    return render_template("habits.html", active="habits")


@views_bp.route("/analytics")
def analytics():
    return render_template("analytics.html", active="analytics")


@views_bp.route("/money")
@views_bp.route("/money/<path:subpage>")
def money(subpage=None):
    return render_template("money.html", active="money")


@views_bp.route("/history")
def history():
    return render_template("history.html", active="history")


@views_bp.route("/settings")
def settings():
    return render_template("settings.html", active="settings")
