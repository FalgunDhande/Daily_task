# Daily Task & Routine Tracker

A production-style personal productivity web app: manage tasks, recurring
routines and habits, track your money, and visualise your progress with
analytics. Built with Flask, SQLAlchemy, and a Chart.js / FullCalendar-powered
frontend.

**Database:** SQLite locally · PostgreSQL on Render (persistent across restarts)

---

## Features

- **Dashboard** — today's progress, streaks, monthly completion, overdue and
  upcoming tasks, a weekly activity chart.
- **Today** — a time-blocked daily planner (Morning / Afternoon / Evening / Night).
- **Tasks** — full CRUD, priorities, categories, due date/time, notes,
  recurring rules (daily/weekly/monthly/custom weekdays), search & filtering.
- **Calendar** — month/week/day views (FullCalendar), click a date to see or
  add tasks for that day.
- **Habits** — a monthly habit grid with automatic streak calculation.
- **Analytics** — monthly stats plus 4 charts: daily completion %, completed
  vs pending, category distribution, weekly productivity trend.
- **History** — a day-by-day log of completed and missed tasks.
- **Money Dashboard** — monthly income/expense summary, budget tracking,
  today's spending, weekly totals, savings rate.
- **Transactions** — full CRUD with categories, payment methods, date/time,
  notes, recurring expenses, CSV/Excel export.
- **Budgets** — monthly budget with per-category allocations and live
  spend-vs-budget tracking.
- **Savings Goals** — goal tracking with contribution history and progress %.
- **Notifications** — browser/OS push notifications via VAPID, overdue
  alerts, daily summaries.
- **Settings** — name, theme (light/dark), notification preferences,
  daily goal, default task duration.

---

## Project Structure

```
daily_tracker/
├── app.py                  # App factory, blueprints, Flask-Migrate, /health
├── config.py               # Environment-based configuration (SQLite / PostgreSQL)
├── seed.py                 # Idempotent default-data seeder
├── utils.py                # Recurring-task materialization, streak calculations
├── requirements.txt
├── Procfile                # Render start command: flask db upgrade && gunicorn app:app
├── runtime.txt
├── .env.example            # Template — copy to .env for local dev
├── migrations/             # Flask-Migrate / Alembic schema migrations
│   └── versions/
│       └── 0001_initial_schema.py
├── models/
│   ├── user.py             # User / settings
│   ├── task.py             # Category, Task, TaskCompletion, Reminder
│   ├── habit.py            # Habit, HabitCompletion
│   └── money.py            # Transaction, Budget, SavingsGoal, RecurringTransaction, …
├── routes/
│   ├── views.py            # Page routes (server-rendered templates)
│   ├── tasks.py            # /api/tasks, /api/dashboard, /api/reminders
│   ├── habits.py           # /api/habits
│   ├── calendar.py         # /api/calendar
│   ├── analytics.py        # /api/analytics, /api/history
│   ├── settings.py         # /api/settings
│   ├── notifications.py    # /api/notifications (VAPID push)
│   └── money.py            # /api/money/*
├── templates/              # Jinja2 templates (one per page) + base.html
└── static/
    ├── css/style.css
    └── js/                 # app.js (shared) + one file per page
```

---

## Local Development (SQLite — no setup required)

Requires Python 3.11+.

```bash
# 1. Clone / unzip the project
cd daily_tracker

# 2. Create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (optional) copy env template
cp .env.example .env   # or copy .env.example .env on Windows

# 5. Run the app
python app.py
```

The app starts at **http://localhost:5000**.

- SQLite database is created automatically at `instance/tracker.db`.
- Default categories, payment methods, and a user record are seeded on first run.
- `db.create_all()` handles schema creation locally so you do **not** need to
  run `flask db upgrade` for local SQLite development.

---

## Local Development with PostgreSQL (optional)

If you want to test against a local PostgreSQL database before deploying:

```bash
# Set DATABASE_URL in your .env file
DATABASE_URL=postgresql://user:password@localhost:5432/daily_tracker
```

Then run the migration to create the schema:

```bash
flask db upgrade
```

Then start the app:

```bash
python app.py
```

When `DATABASE_URL` is set, `db.create_all()` is skipped and Alembic manages
the schema.

---

## Deploying to Render (PostgreSQL — persistent data)

### Step 1 — Push to GitHub

Make sure your repository is up to date:

```bash
git add -A
git commit -m "Add Flask-Migrate and PostgreSQL support"
git push
```

### Step 2 — Create a Render PostgreSQL database

1. Log in to [Render](https://render.com).
2. Click **New +** → **PostgreSQL**.
3. Fill in a name (e.g. `daily-tracker-db`), choose a region, and click **Create Database**.
4. After it is created, copy the **Internal Database URL** (starts with `postgresql://...`).

### Step 3 — Create the Render Web Service

1. Click **New +** → **Web Service**.
2. Connect your GitHub repository.
3. Configure the service:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `flask db upgrade && gunicorn app:app`
   - **Python Version**: 3.11.9 (matches `runtime.txt`)

### Step 4 — Set Environment Variables

In the Render web service **Environment** tab, add:

| Key | Value |
|-----|-------|
| `DATABASE_URL` | Paste the Internal Database URL from Step 2 |
| `SECRET_KEY` | Any long random string (e.g. `openssl rand -hex 32`) |
| `VAPID_PUBLIC_KEY` | Your VAPID public key (optional — only for push notifications) |
| `VAPID_PRIVATE_KEY` | Your VAPID private key (optional) |
| `VAPID_EMAIL` | `mailto:you@example.com` (optional) |

> **Important:** Do NOT set `FLASK_DEBUG=1` in production.

### Step 5 — Deploy

Click **Create Web Service**. Render will:

1. Install dependencies via `pip install -r requirements.txt`.
2. Run `flask db upgrade` — creates all tables in the empty PostgreSQL database.
3. Start `gunicorn app:app` — seeds default categories and user on first request.

Watch the deploy logs to confirm `flask db upgrade` completes successfully.

### Step 6 — Verify the Health Check

```
GET https://your-app.onrender.com/health
```

Expected response:

```json
{
  "status": "ok",
  "db": "ok"
}
```

### Step 7 — Test Data Persistence

1. Open the app and create:
   - A Task (e.g. "Python Practice")
   - An Expense (e.g. Food ₹250)
   - A Budget (e.g. ₹20,000)
   - A Habit (e.g. "Exercise")
2. Go to Render → your web service → **Manual Deploy** (or wait for a redeploy).
3. After restart, confirm all four items still exist.

The data will survive because it is stored in the Render-managed PostgreSQL
database, not in the ephemeral filesystem.

---

## Database Migration Workflow

For future schema changes:

```bash
# 1. Modify your SQLAlchemy model
# 2. Generate a new migration
flask db migrate -m "describe your change"

# 3. Review the generated file in migrations/versions/
# 4. Apply locally
flask db upgrade

# 5. Commit the migration file
git add migrations/versions/
git commit -m "Add migration: describe your change"
git push
```

Render will run `flask db upgrade` automatically on the next deploy.

---

## API Overview

```
GET  /health                        Database health check

GET    /api/tasks                   List tasks (search/filter/sort)
POST   /api/tasks                   Create a task
GET    /api/tasks/<id>              Get one task
PUT    /api/tasks/<id>              Update a task
DELETE /api/tasks/<id>              Delete a task
POST   /api/tasks/<id>/complete     Mark complete
POST   /api/tasks/<id>/uncomplete   Mark pending

GET    /api/dashboard               Dashboard summary stats
GET    /api/categories              List categories
GET    /api/reminders/upcoming      Upcoming reminders (next ~12 h)

GET    /api/calendar?start=&end=    Calendar events for a date range
GET    /api/calendar/day/<date>     Tasks for one specific day

GET    /api/habits?year=&month=     Habits + monthly completion grid
POST   /api/habits                  Create habit
PUT    /api/habits/<id>             Update habit
DELETE /api/habits/<id>             Delete habit
POST   /api/habits/<id>/toggle      Toggle completion for a date

GET    /api/analytics?year=&month=  Monthly analytics + chart data
GET    /api/history?days=           Day-by-day completed/missed log

GET    /api/settings                Get user settings
PUT    /api/settings                Update user settings

GET    /api/money/summary           Monthly income/expense/budget summary
GET    /api/money/transactions      List transactions (filter/sort/paginate)
POST   /api/money/transactions      Create transaction
PUT    /api/money/transactions/<id> Update transaction
DELETE /api/money/transactions/<id> Delete transaction
GET    /api/money/budgets           Get current-month budget
POST   /api/money/budgets           Create or update budget
GET    /api/money/goals             List savings goals
POST   /api/money/goals             Create savings goal
GET    /api/money/analytics         Money analytics (charts)
GET    /api/money/insights          AI-style spending insights
```

All endpoints return and accept JSON.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, Flask 3, Flask-SQLAlchemy, Flask-Migrate (Alembic) |
| Database (local) | SQLite (zero config) |
| Database (production) | PostgreSQL on Render |
| PostgreSQL driver | psycopg2-binary |
| Task scheduling | APScheduler |
| Push notifications | pywebpush (VAPID) |
| Frontend | HTML5, CSS3 (custom responsive), vanilla JavaScript |
| Charts | Chart.js |
| Calendar | FullCalendar.js |
| Icons | Font Awesome |
| Production server | Gunicorn |
| Hosting | Render |
