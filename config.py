import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _build_db_url():
    url = os.environ.get("DATABASE_URL")
    if url:
        # Render / Heroku give postgres:// URLs; SQLAlchemy needs postgresql://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url
    # Local development fallback → SQLite
    return f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'tracker.db')}"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    SQLALCHEMY_DATABASE_URI = _build_db_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False

    # Connection-pool settings for PostgreSQL on Render.
    # pool_pre_ping: silently recycles stale connections after a Render restart.
    # pool_recycle: force-recycle connections every 5 minutes so they never
    #               hit Render's idle-connection timeout.
    # NOP for SQLite (SQLite uses a StaticPool and ignores these).
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # VAPID keys for Web Push notifications
    VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
    VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
    VAPID_EMAIL = os.environ.get("VAPID_EMAIL", "mailto:admin@dailytracker.app")

    # True when DATABASE_URL env var is set → production / PostgreSQL mode
    IS_PRODUCTION = bool(os.environ.get("DATABASE_URL"))
