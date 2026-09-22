# Daily Task & Routine Tracker

A production-style personal productivity web app: manage tasks, recurring
routines and habits, and track your progress day-wise, week-wise and
month-wise. Built with Flask, SQLAlchemy (SQLite), and a Chart.js /
FullCalendar-powered frontend.

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
- **Settings** — name, default task duration, week start day, theme
  (light/dark), notification preference, daily goal.
- Light/dark theme, responsive layout with a mobile hamburger menu, toast
  notifications, confirm-before-delete, loading & empty states.

## Project Structure

```
daily_tracker/
├── app.py                 # App factory, blueprint registration, DB init
├── config.py               # Environment-based configuration
├── seed.py                 # Seeds default categories + sample data on first run
├── utils.py                 # Recurring-task materialization, streak calculations
├── requirements.txt
├── Procfile
├── runtime.txt
├── models/
│   ├── user.py              # User / settings
│   ├── task.py               # Category, Task, TaskCompletion, Reminder
│   └── habit.py               # Habit, HabitCompletion
├── routes/
│   ├── views.py               # Page routes (server-rendered templates)
│   ├── tasks.py                 # /api/tasks, /api/dashboard, /api/reminders
│   ├── habits.py                 # /api/habits
│   ├── calendar.py                # /api/calendar
│   ├── analytics.py                # /api/analytics, /api/history
│   └── settings.py                  # /api/settings
├── templates/                # Jinja2 templates (one per page) + base.html
├── static/
│   ├── css/style.css            # Full responsive dashboard stylesheet
│   └── js/                        # app.js (shared) + one file per page
└── instance/
    └── tracker.db               # SQLite database (created automatically)
```

## How recurring tasks work

A recurring task is stored as a **template** row (`is_template=True`). When
the dashboard, calendar, or task list is loaded, `utils.ensure_occurrences()`
materializes real `Task` rows for each date the template should occur on
(daily / weekly / monthly / specific weekdays), within a rolling window
around "today". Completing an occurrence only affects that date — the
template itself is never marked complete.

## Local Setup

Requires Python 3.11+.

```bash
# 1. Clone / unzip the project, then cd into it
cd daily_tracker

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (optional) copy .env.example to .env and adjust values
cp .env.example .env

# 5. Run it
python app.py
```

The app will be available at **http://localhost:5000**. The SQLite database
(`instance/tracker.db`) and sample seed data (categories, a few sample tasks,
a recurring "Study Python" task, and sample habits) are created automatically
on first run — nothing else to set up.

## Deploying to Render (free tier)

1. Push this project to a GitHub repository.
2. On [Render](https://render.com), click **New +** → **Web Service** and
   connect your GitHub repo.
3. Configure the service:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
4. Add an environment variable:
   - `SECRET_KEY` → any random string
5. Click **Create Web Service**. Render will build and deploy automatically;
   subsequent pushes to your default branch redeploy the app.

> **Note on free-tier storage:** Render's free web services use an ephemeral
> filesystem, so the SQLite file resets on every redeploy/restart. For
> persistent data across deploys, either add a Render **Persistent Disk**
> (small paid add-on) mounted at `/opt/render/project/src/instance`, or point
> `DATABASE_URL` at a managed Postgres database (Render offers a free
> Postgres instance) — the app already normalizes `postgres://` URLs for
> SQLAlchemy, so no code changes are needed, just set the `DATABASE_URL`
> environment variable.

## API Overview

```
GET    /api/tasks                 List tasks (search/filter/sort via query params)
POST   /api/tasks                 Create a task
GET    /api/tasks/<id>            Get one task
PUT    /api/tasks/<id>            Update a task
DELETE /api/tasks/<id>            Delete a task
POST   /api/tasks/<id>/complete   Mark complete
POST   /api/tasks/<id>/uncomplete Mark pending

GET    /api/dashboard             Dashboard summary stats
GET    /api/categories            List categories
GET    /api/reminders/upcoming    Upcoming reminders (next ~12h)

GET    /api/calendar?start=&end=  Calendar events for a date range
GET    /api/calendar/day/<date>   Tasks for one specific day

GET    /api/habits?year=&month=   Habits + monthly completion grid
POST   /api/habits                Create habit
PUT    /api/habits/<id>           Update habit
DELETE /api/habits/<id>           Delete habit
POST   /api/habits/<id>/toggle    Toggle completion for a date

GET    /api/analytics?year=&month=  Monthly analytics + chart data
GET    /api/history?days=           Day-by-day completed/missed log

GET    /api/settings              Get user settings
PUT    /api/settings              Update user settings
```

All endpoints return and accept JSON.

## Tech Stack

- Backend: Python, Flask, Flask-SQLAlchemy
- Database: SQLite (swap to Postgres via `DATABASE_URL` with zero code changes)
- Frontend: HTML5, CSS3 (custom, responsive), vanilla JavaScript
- Charts: Chart.js
- Calendar: FullCalendar.js
- Icons: Font Awesome
