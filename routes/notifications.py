"""Notification routes: due-reminder polling, push subscription, settings, daily summary."""
import json
from datetime import datetime, timedelta, date

from flask import Blueprint, request, jsonify, current_app
from models import db
from models.task import Task, Reminder
from models.user import User

notifications_bp = Blueprint("notifications_api", __name__, url_prefix="/api/notifications")


# ─── helpers ──────────────────────────────────────────────────────────────────

def _get_user():
    user = User.query.first()
    if not user:
        user = User()
        db.session.add(user)
        db.session.commit()
    return user


def _try_push(subscription_json: str, payload: dict, app_config):
    """Attempt a VAPID web push. Silently fails if not configured."""
    if not subscription_json:
        return
    try:
        from pywebpush import webpush  # WebPushException handled by bare except below
        sub = json.loads(subscription_json)
        webpush(
            subscription_info=sub,
            data=json.dumps(payload),
            vapid_private_key=app_config.get("VAPID_PRIVATE_KEY", ""),
            vapid_claims={"sub": app_config.get("VAPID_EMAIL", "mailto:admin@example.com")},
        )
    except Exception:
        pass  # Push is best-effort — browser polling is the primary path


# ─── VAPID public key ──────────────────────────────────────────────────────────

@notifications_bp.route("/vapid-public-key", methods=["GET"])
def vapid_public_key():
    key = current_app.config.get("VAPID_PUBLIC_KEY", "")
    return jsonify({"vapid_public_key": key})


# ─── Push subscription ────────────────────────────────────────────────────────

@notifications_bp.route("/subscribe", methods=["POST"])
def subscribe():
    data = request.get_json(force=True) or {}
    user = _get_user()
    sub = data.get("subscription")
    user.push_subscription = json.dumps(sub) if sub else ""
    db.session.commit()
    return jsonify({"ok": True})


# ─── Settings ─────────────────────────────────────────────────────────────────

NOTIF_FIELDS = [
    "notif_browser", "notif_sound", "notif_in_app",
    "notif_overdue", "notif_daily_summary",
    "notif_reminder_offset", "notif_summary_time",
]


@notifications_bp.route("/settings", methods=["GET"])
def get_notif_settings():
    return jsonify(_get_user().to_dict())


@notifications_bp.route("/settings", methods=["PUT"])
def update_notif_settings():
    user = _get_user()
    data = request.get_json(force=True) or {}
    for field in NOTIF_FIELDS:
        if field in data:
            setattr(user, field, data[field])
    db.session.commit()
    return jsonify(user.to_dict())


# ─── Due reminders (browser poll) ─────────────────────────────────────────────

@notifications_bp.route("/due", methods=["GET"])
def due_reminders():
    """
    Returns reminders that became due in the last 2 minutes and are still pending.
    The frontend polls this every 60s and fires browser notifications for each result.
    """
    now = datetime.utcnow()
    window_start = now - timedelta(minutes=2)
    reminders = (
        Reminder.query
        .filter(
            Reminder.remind_at >= window_start,
            Reminder.remind_at <= now,
            Reminder.status == Reminder.STATUS_PENDING,
        )
        .order_by(Reminder.remind_at.asc())
        .limit(20)
        .all()
    )
    return jsonify([r.to_dict() for r in reminders])


@notifications_bp.route("/<int:reminder_id>/mark-sent", methods=["POST"])
def mark_sent(reminder_id):
    r = Reminder.query.get_or_404(reminder_id)
    r.status = Reminder.STATUS_SENT
    r.seen = True
    r.sent_at = datetime.utcnow()
    db.session.commit()
    return jsonify(r.to_dict())


# ─── Upcoming reminders (for the bell badge) ──────────────────────────────────

@notifications_bp.route("/upcoming", methods=["GET"])
def upcoming_reminders():
    now = datetime.utcnow()
    window_end = now + timedelta(hours=12)
    reminders = (
        Reminder.query
        .filter(
            Reminder.remind_at >= now - timedelta(hours=1),
            Reminder.remind_at <= window_end,
            Reminder.seen == False,  # noqa: E712
        )
        .order_by(Reminder.remind_at.asc())
        .limit(10)
        .all()
    )
    return jsonify([r.to_dict() for r in reminders])


# ─── Daily summary payload ────────────────────────────────────────────────────

@notifications_bp.route("/daily-summary", methods=["GET"])
def daily_summary():
    today = date.today()
    todays = Task.query.filter_by(is_template=False, due_date=today).all()
    completed = [t for t in todays if t.status == "completed"]
    pending = [t for t in todays if t.status == "pending"]

    # Next 2 pending tasks sorted by time
    upcoming = sorted(pending, key=lambda t: t.due_time or datetime.max.time())[:2]

    pct = round(len(completed) / len(todays) * 100) if todays else 0

    return jsonify({
        "total": len(todays),
        "completed": len(completed),
        "pending": len(pending),
        "completion_pct": pct,
        "upcoming": [
            {
                "title": t.title,
                "due_time": t.due_time.strftime("%H:%M") if t.due_time else None,
            }
            for t in upcoming
        ],
        "date": today.isoformat(),
    })


# ─── Test notification payload (frontend fires actual notification) ───────────

@notifications_bp.route("/test", methods=["POST"])
def test_notification():
    """Returns a test notification payload — the frontend actually shows it."""
    return jsonify({
        "id": 0,
        "task_id": 0,
        "task_title": "Test Notification",
        "task_due_time": datetime.now().strftime("%H:%M"),
        "task_status": "pending",
        "remind_at": datetime.utcnow().isoformat(),
        "kind": "test",
        "status": "pending",
        "seen": False,
    })
