from flask import Blueprint, request, jsonify
from models import db
from models.user import User

settings_bp = Blueprint("settings_api", __name__, url_prefix="/api")


def get_or_create_user():
    user = User.query.first()
    if not user:
        user = User()
        db.session.add(user)
        db.session.commit()
    return user


@settings_bp.route("/settings", methods=["GET"])
def get_settings():
    return jsonify(get_or_create_user().to_dict())


@settings_bp.route("/settings", methods=["PUT"])
def update_settings():
    user = get_or_create_user()
    data = request.get_json(force=True) or {}
    for field in [
        "name", "email", "default_task_duration", "week_starts_monday",
        "theme", "notification_pref", "daily_goal",
    ]:
        if field in data:
            setattr(user, field, data[field])
    db.session.commit()
    return jsonify(user.to_dict())
