from datetime import datetime
from models import db

FREQUENCIES = ["daily", "weekly", "custom"]


class Habit(db.Model):
    __tablename__ = "habit"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    target_frequency = db.Column(db.String(20), default="daily")  # daily/weekly/custom
    target_count = db.Column(db.Integer, default=7)  # times per week, for weekly/custom
    goal = db.Column(db.String(200), default="")
    start_date = db.Column(db.Date, default=datetime.utcnow().date)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "target_frequency": self.target_frequency,
            "target_count": self.target_count,
            "goal": self.goal or "",
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "active": self.active,
        }


class HabitCompletion(db.Model):
    __tablename__ = "habit_completion"

    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey("habit.id"), nullable=False, index=True)
    completed_on = db.Column(db.Date, nullable=False, index=True)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

    habit = db.relationship("Habit", backref="completions")

    __table_args__ = (
        db.UniqueConstraint("habit_id", "completed_on", name="uq_habit_date"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "habit_id": self.habit_id,
            "completed_on": self.completed_on.isoformat(),
        }
