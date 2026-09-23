import logging
import os
from datetime import datetime, timedelta, date
from flask import Flask, jsonify
from flask_migrate import Migrate
from config import Config
from models import db

logger = logging.getLogger(__name__)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure the instance folder exists (needed for local SQLite)
    os.makedirs(os.path.join(app.root_path, "instance"), exist_ok=True)

    # ── Database ──────────────────────────────────────────────────────────────
    db.init_app(app)

    # Flask-Migrate / Alembic — manages schema via migrations/
    Migrate(app, db)

    # ── Blueprints ────────────────────────────────────────────────────────────
    from routes.views import views_bp
    from routes.tasks import tasks_bp
    from routes.habits import habits_bp
    from routes.calendar import calendar_bp
    from routes.analytics import analytics_bp
    from routes.settings import settings_bp
    from routes.notifications import notifications_bp
    from routes.money import money_bp

    app.register_blueprint(views_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(habits_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(money_bp)

    # ── Schema & seed ─────────────────────────────────────────────────────────
    with app.app_context():
        if not app.config.get("IS_PRODUCTION"):
            # Local development: create tables automatically so `python app.py`
            # works out of the box without needing to run flask db commands.
            # In production (DATABASE_URL is set), the Procfile runs
            # `flask db upgrade` before gunicorn, so create_all() is skipped.
            db.create_all()

        # Seed idempotent default data (only inserts if tables are empty)
        try:
            from seed import run_seed
            run_seed()
        except Exception as exc:
            logger.error("Seed error: %s", exc)

    # ── Scheduler ─────────────────────────────────────────────────────────────
    # Start outside the app_context block so it holds its own contexts
    _start_scheduler(app)

    # ── Health check ──────────────────────────────────────────────────────────
    @app.route("/health")
    def health():
        """
        GET /health → {"status": "ok", "db": "ok"}

        Used by Render's health-check and for manual verification after deploy.
        Never exposes credentials or internal stack traces.
        """
        db_status = "ok"
        try:
            # A lightweight query that works on both SQLite and PostgreSQL
            db.session.execute(db.text("SELECT 1"))
        except Exception as exc:
            logger.error("Health check DB error: %s", exc)
            db_status = "error"

        status_code = 200 if db_status == "ok" else 503
        return jsonify({"status": "ok" if db_status == "ok" else "degraded",
                        "db": db_status}), status_code

    # ── Error handlers ────────────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return {"error": "Not found"}, 404

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return {"error": "Internal server error"}, 500

    return app


def _start_scheduler(app):
    """
    Start the APScheduler background tick.
    - Every 60 s: create Reminder rows for tasks that don't have one yet.
    - Every 5 min: create overdue Reminder rows for past-due pending tasks.
    - Every 1 h: process recurring financial transactions.
    Skipped gracefully in Werkzeug reloader child processes to avoid double scheduler.
    """
    # In Werkzeug debug mode the reloader forks a child process.
    # Only run the scheduler in the child (WERKZEUG_RUN_MAIN=true) or in non-debug mode.
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true" and app.debug:
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler(daemon=True)
        scheduler.add_job(
            func=_tick_reminders,
            trigger="interval",
            seconds=60,
            id="reminder_tick",
            replace_existing=True,
            args=[app],
        )
        scheduler.add_job(
            func=_tick_overdue,
            trigger="interval",
            seconds=300,
            id="overdue_tick",
            replace_existing=True,
            args=[app],
        )
        scheduler.add_job(
            func=_tick_recurring_money,
            trigger="interval",
            seconds=3600,
            id="recurring_money_tick",
            replace_existing=True,
            args=[app],
        )
        scheduler.start()
        app._scheduler = scheduler  # keep reference so GC doesn't kill it
    except Exception as exc:
        logger.warning("[Scheduler] Could not start: %s", exc)


def _tick_reminders(app):
    """
    For every pending task that has a due_date + due_time but no Reminder row yet,
    create one at (due_datetime - offset_minutes). Idempotent — skips tasks that
    already have a reminder row.
    """
    from models.task import Task, Reminder
    from models.user import User

    with app.app_context():
        try:
            user = User.query.first()
            offset = (user.notif_reminder_offset if user else 10) or 10
            today = datetime.utcnow().date()

            tasks_with_time = Task.query.filter(
                Task.is_template == False,  # noqa: E712
                Task.status == "pending",
                Task.due_time != None,      # noqa: E711
                Task.due_date >= today,
            ).all()

            for task in tasks_with_time:
                task_dt = datetime.combine(task.due_date, task.due_time)
                remind_dt = task_dt - timedelta(minutes=offset)

                # Only create if no reminder row exists for this task yet
                existing = Reminder.query.filter_by(
                    task_id=task.id, kind="reminder"
                ).first()
                if not existing:
                    db.session.add(Reminder(
                        task_id=task.id,
                        remind_at=remind_dt,
                        kind="reminder",
                        status=Reminder.STATUS_PENDING,
                    ))

            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            logger.error("[Scheduler] tick_reminders error: %s", exc)


def _tick_overdue(app):
    """
    For every pending task whose due_date is in the past, create a single overdue
    Reminder row (if one doesn't already exist).
    """
    from models.task import Task, Reminder

    with app.app_context():
        try:
            today = date.today()
            now = datetime.utcnow()

            overdue_tasks = Task.query.filter(
                Task.is_template == False,  # noqa: E712
                Task.status == "pending",
                Task.due_date < today,
            ).all()

            for task in overdue_tasks:
                existing = Reminder.query.filter_by(
                    task_id=task.id, kind="overdue"
                ).first()
                if not existing:
                    db.session.add(Reminder(
                        task_id=task.id,
                        remind_at=now,
                        kind="overdue",
                        status=Reminder.STATUS_PENDING,
                    ))

            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            logger.error("[Scheduler] tick_overdue error: %s", exc)


def _tick_recurring_money(app):
    """Process recurring financial transactions once per hour."""
    from routes.money import process_recurring_transactions

    with app.app_context():
        try:
            count = process_recurring_transactions()
            if count:
                logger.info("[Scheduler] Processed %d recurring transactions", count)
        except Exception as exc:
            db.session.rollback()
            logger.error("[Scheduler] recurring_money error: %s", exc)


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
