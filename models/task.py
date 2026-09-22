from datetime import datetime, date as date_cls
from models import db

PRIORITIES = ["Low", "Medium", "High", "Urgent"]
DEFAULT_CATEGORIES = [
    ("Study", "#6366f1", "fa-book"),
    ("Work", "#0ea5e9", "fa-briefcase"),
    ("Health", "#22c55e", "fa-heart-pulse"),
    ("Personal", "#f97316", "fa-user"),
    ("Job Search", "#ec4899", "fa-magnifying-glass"),
    ("Exercise", "#eab308", "fa-dumbbell"),
    ("Other", "#64748b", "fa-ellipsis"),
]
RECURRENCE_TYPES = ["none", "daily", "weekly", "monthly", "custom"]


class Category(db.Model):
    __tablename__ = "category"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=True, nullable=False)
    color = db.Column(db.String(20), default="#6366f1")
    icon = db.Column(db.String(40), default="fa-circle")

    def __init__(self, name: str, color: str = "#6366f1", icon: str = "fa-circle"):
        self.name = name
        self.color = color
        self.icon = icon

    tasks = db.relationship("Task", backref="category", lazy=True)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "color": self.color, "icon": self.icon}


class Task(db.Model):
    __tablename__ = "task"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    notes = db.Column(db.Text, default="")

    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), index=True)
    priority = db.Column(db.String(20), default="Medium", index=True)
    status = db.Column(db.String(20), default="pending", index=True)  # pending | completed

    due_date = db.Column(db.Date, index=True)
    due_time = db.Column(db.Time, nullable=True)
    time_block = db.Column(db.String(20), default="Morning")  # Morning/Afternoon/Evening/Night

    recurrence = db.Column(db.String(20), default="none")  # none/daily/weekly/monthly/custom
    recurrence_days = db.Column(db.String(30), default="")  # csv of weekday ints for custom
    is_template = db.Column(db.Boolean, default=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("task.id"), nullable=True, index=True)

    reminder_time = db.Column(db.Time, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    sort_order = db.Column(db.Integer, default=0)

    occurrences = db.relationship(
        "Task", backref=db.backref("parent", remote_side=[id]), lazy=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description or "",
            "notes": self.notes or "",
            "category_id": self.category_id,
            "category": self.category.name if self.category else None,
            "category_color": self.category.color if self.category else "#64748b",
            "priority": self.priority,
            "status": self.status,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "due_time": self.due_time.strftime("%H:%M") if self.due_time else None,
            "time_block": self.time_block,
            "recurrence": self.recurrence,
            "recurrence_days": self.recurrence_days,
            "is_template": self.is_template,
            "parent_id": self.parent_id,
            "reminder_time": self.reminder_time.strftime("%H:%M") if self.reminder_time else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "is_overdue": self.is_overdue(),
        }

    def is_overdue(self):
        if self.status == "completed" or not self.due_date or self.is_template:
            return False
        return self.due_date < date_cls.today()


class TaskCompletion(db.Model):
    """A log entry created every time a task occurrence is marked complete.
    Powers history / streak / analytics queries without recomputation."""

    __tablename__ = "task_completion"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("task.id"), nullable=False, index=True)
    completed_on = db.Column(db.Date, nullable=False, index=True)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

    task = db.relationship("Task", backref="completions")

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_title": self.task.title if self.task else None,
            "completed_on": self.completed_on.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class Reminder(db.Model):
    """A scheduled reminder tied to a task. status tracks delivery to avoid duplicates."""

    __tablename__ = "reminder"

    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_OVERDUE_SENT = "overdue_sent"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("task.id"), nullable=False, index=True)
    remind_at = db.Column(db.DateTime, nullable=False, index=True)
    seen = db.Column(db.Boolean, default=False)
    # Delivery tracking — prevents duplicate notifications after server restart
    status = db.Column(db.String(20), default="pending", index=True)
    sent_at = db.Column(db.DateTime, nullable=True)
    # Type: "reminder" | "overdue" | "summary"
    kind = db.Column(db.String(20), default="reminder")

    def __init__(self, task_id, remind_at, kind="reminder", status="pending", seen=False, sent_at=None):
        self.task_id = task_id
        self.remind_at = remind_at
        self.kind = kind
        self.status = status
        self.seen = seen
        self.sent_at = sent_at

    task = db.relationship("Task", backref="reminders")

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_title": self.task.title if self.task else None,
            "task_due_time": (
                self.task.due_time.strftime("%H:%M") if self.task and self.task.due_time else None
            ),
            "task_status": self.task.status if self.task else None,
            "remind_at": self.remind_at.isoformat(),
            "seen": self.seen,
            "status": self.status,
            "kind": self.kind,
        }
