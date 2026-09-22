from datetime import datetime
from models import db


class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), default="Falgun")
    email = db.Column(db.String(255), default="")  # Gmail / contact email
    default_task_duration = db.Column(db.Integer, default=30)  # minutes
    week_starts_monday = db.Column(db.Boolean, default=True)
    theme = db.Column(db.String(20), default="light")  # light | dark
    notification_pref = db.Column(db.Boolean, default=True)
    daily_goal = db.Column(db.Integer, default=5)  # tasks/habits per day
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ── Notification preferences ──────────────────────────────────────
    notif_browser = db.Column(db.Boolean, default=True)   # browser/OS notifications
    notif_sound = db.Column(db.Boolean, default=True)     # play audio
    notif_in_app = db.Column(db.Boolean, default=True)    # in-page alert modal
    notif_overdue = db.Column(db.Boolean, default=True)   # overdue task alert
    notif_daily_summary = db.Column(db.Boolean, default=True)  # daily summary push
    notif_reminder_offset = db.Column(db.Integer, default=10)  # minutes before task
    notif_summary_time = db.Column(db.String(5), default="08:00")  # HH:MM
    # Browser push subscription JSON blob (VAPID / Web Push)
    push_subscription = db.Column(db.Text, default="")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email or "",
            "default_task_duration": self.default_task_duration,
            "week_starts_monday": self.week_starts_monday,
            "theme": self.theme,
            "notification_pref": self.notification_pref,
            "daily_goal": self.daily_goal,
            "notif_browser": self.notif_browser,
            "notif_sound": self.notif_sound,
            "notif_in_app": self.notif_in_app,
            "notif_overdue": self.notif_overdue,
            "notif_daily_summary": self.notif_daily_summary,
            "notif_reminder_offset": self.notif_reminder_offset,
            "notif_summary_time": self.notif_summary_time or "08:00",
        }
