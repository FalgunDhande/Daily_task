"""Money Management API: transactions, budgets, savings goals, recurring, analytics, export."""
import csv
import io
import calendar as cal
from datetime import datetime, date, timedelta
from collections import defaultdict
from flask import Blueprint, request, jsonify, Response

from models import db
from models.money import (
    ExpenseCategory, PaymentMethod, Transaction,
    Budget, BudgetCategory, SavingsGoal,
    SavingsContribution, RecurringTransaction,
)

money_bp = Blueprint("money_api", __name__, url_prefix="/api/money")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date() if s else None


def _parse_time(s):
    return datetime.strptime(s, "%H:%M").time() if s else None


def _amount_to_paise(val):
    """Convert a user-supplied amount (float/int/string) to integer paise."""
    return int(round(float(val) * 100))


def _paise_to_rupees(paise):
    return round(paise / 100, 2)


# ══════════════════════════════════════════════════════════════════════════════
#  CATEGORIES & PAYMENT METHODS
# ══════════════════════════════════════════════════════════════════════════════

@money_bp.route("/categories", methods=["GET"])
def get_categories():
    cats = ExpenseCategory.query.order_by(ExpenseCategory.type, ExpenseCategory.name).all()
    return jsonify([c.to_dict() for c in cats])


@money_bp.route("/categories", methods=["POST"])
def create_category():
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Category name is required"}), 400
    cat = ExpenseCategory(
        name=name,
        type=data.get("type", "personal"),
        icon=data.get("icon", "fa-circle"),
        monthly_budget=_amount_to_paise(data.get("monthly_budget", 0)),
    )
    db.session.add(cat)
    db.session.commit()
    return jsonify(cat.to_dict()), 201


@money_bp.route("/payment-methods", methods=["GET"])
def get_payment_methods():
    methods = PaymentMethod.query.order_by(PaymentMethod.id).all()
    return jsonify([m.to_dict() for m in methods])


@money_bp.route("/payment-methods", methods=["POST"])
def create_payment_method():
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Payment method name is required"}), 400
    pm = PaymentMethod(name=name, icon=data.get("icon", "fa-circle"))
    db.session.add(pm)
    db.session.commit()
    return jsonify(pm.to_dict()), 201


# ══════════════════════════════════════════════════════════════════════════════
#  TRANSACTIONS CRUD
# ══════════════════════════════════════════════════════════════════════════════

@money_bp.route("/transactions", methods=["GET"])
def get_transactions():
    q = Transaction.query

    # ── Filters ──
    txn_type = request.args.get("type")
    if txn_type:
        q = q.filter(Transaction.type == txn_type)

    category_id = request.args.get("category_id")
    if category_id:
        q = q.filter(Transaction.category_id == int(category_id))

    payment_id = request.args.get("payment_method_id")
    if payment_id:
        q = q.filter(Transaction.payment_method_id == int(payment_id))

    date_val = request.args.get("date")
    if date_val:
        q = q.filter(Transaction.transaction_date == _parse_date(date_val))

    date_from = request.args.get("date_from")
    if date_from:
        q = q.filter(Transaction.transaction_date >= _parse_date(date_from))

    date_to = request.args.get("date_to")
    if date_to:
        q = q.filter(Transaction.transaction_date <= _parse_date(date_to))

    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)
    if month and year:
        days_in_month = cal.monthrange(year, month)[1]
        q = q.filter(
            Transaction.transaction_date >= date(year, month, 1),
            Transaction.transaction_date <= date(year, month, days_in_month),
        )

    amount_min = request.args.get("amount_min")
    if amount_min:
        q = q.filter(Transaction.amount >= _amount_to_paise(amount_min))

    amount_max = request.args.get("amount_max")
    if amount_max:
        q = q.filter(Transaction.amount <= _amount_to_paise(amount_max))

    search = request.args.get("search")
    if search:
        term = f"%{search}%"
        q = q.filter(
            db.or_(
                Transaction.description.ilike(term),
                Transaction.notes.ilike(term),
            )
        )

    # ── Sorting ──
    sort = request.args.get("sort", "newest")
    if sort == "oldest":
        q = q.order_by(Transaction.transaction_date.asc(), Transaction.id.asc())
    elif sort == "highest":
        q = q.order_by(Transaction.amount.desc())
    elif sort == "lowest":
        q = q.order_by(Transaction.amount.asc())
    else:  # newest
        q = q.order_by(Transaction.transaction_date.desc(), Transaction.id.desc())

    # ── Pagination ──
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    per_page = min(per_page, 200)

    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        "transactions": [t.to_dict() for t in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    })


@money_bp.route("/transactions/<int:txn_id>", methods=["GET"])
def get_transaction(txn_id):
    t = Transaction.query.get_or_404(txn_id)
    return jsonify(t.to_dict())


@money_bp.route("/transactions", methods=["POST"])
def create_transaction():
    data = request.get_json(force=True) or {}

    # Validation
    amount = data.get("amount")
    if amount is None or float(amount) <= 0:
        return jsonify({"error": "Amount must be greater than zero"}), 400

    txn_type = data.get("type", "expense")
    if txn_type not in ("expense", "income"):
        return jsonify({"error": "Type must be 'expense' or 'income'"}), 400

    txn_date = data.get("transaction_date")
    if not txn_date:
        return jsonify({"error": "Transaction date is required"}), 400

    txn = Transaction(
        user_id=1,
        amount=_amount_to_paise(amount),
        type=txn_type,
        category_id=data.get("category_id"),
        description=(data.get("description") or "").strip(),
        transaction_date=_parse_date(txn_date),
        transaction_time=_parse_time(data.get("transaction_time")),
        payment_method_id=data.get("payment_method_id"),
        notes=(data.get("notes") or "").strip(),
    )
    db.session.add(txn)
    db.session.commit()
    return jsonify(txn.to_dict()), 201


@money_bp.route("/transactions/<int:txn_id>", methods=["PUT"])
def update_transaction(txn_id):
    txn = Transaction.query.get_or_404(txn_id)
    data = request.get_json(force=True) or {}

    if "amount" in data:
        if float(data["amount"]) <= 0:
            return jsonify({"error": "Amount must be greater than zero"}), 400
        txn.amount = _amount_to_paise(data["amount"])
    if "type" in data:
        if data["type"] not in ("expense", "income"):
            return jsonify({"error": "Invalid type"}), 400
        txn.type = data["type"]
    if "category_id" in data:
        txn.category_id = data["category_id"]
    if "description" in data:
        txn.description = (data["description"] or "").strip()
    if "transaction_date" in data:
        txn.transaction_date = _parse_date(data["transaction_date"])
    if "transaction_time" in data:
        txn.transaction_time = _parse_time(data["transaction_time"])
    if "payment_method_id" in data:
        txn.payment_method_id = data["payment_method_id"]
    if "notes" in data:
        txn.notes = (data["notes"] or "").strip()

    db.session.commit()
    return jsonify(txn.to_dict())


@money_bp.route("/transactions/<int:txn_id>", methods=["DELETE"])
def delete_transaction(txn_id):
    txn = Transaction.query.get_or_404(txn_id)
    db.session.delete(txn)
    db.session.commit()
    return jsonify({"deleted": True})


# ══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

@money_bp.route("/summary", methods=["GET"])
def money_summary():
    today = date.today()
    month_start = today.replace(day=1)
    days_in_month = cal.monthrange(today.year, today.month)[1]
    month_end = date(today.year, today.month, days_in_month)
    week_start = today - timedelta(days=today.weekday())  # Monday

    # Monthly transactions
    month_txns = Transaction.query.filter(
        Transaction.transaction_date >= month_start,
        Transaction.transaction_date <= month_end,
    ).all()

    month_income = sum(t.amount for t in month_txns if t.type == "income")
    month_expenses = sum(t.amount for t in month_txns if t.type == "expense")
    remaining = month_income - month_expenses

    # Today's spending
    today_txns = [t for t in month_txns if t.transaction_date == today and t.type == "expense"]
    today_spending = sum(t.amount for t in today_txns)

    # This week's spending
    week_txns = [t for t in month_txns if t.transaction_date >= week_start and t.type == "expense"]
    week_spending = sum(t.amount for t in week_txns)

    # Budget
    budget = Budget.query.filter_by(
        user_id=1, month=today.month, year=today.year
    ).first()
    budget_amount = budget.amount if budget else 0
    budget_used_pct = round(month_expenses / budget_amount * 100, 1) if budget_amount else 0

    # Savings rate
    savings = month_income - month_expenses
    savings_rate = round(savings / month_income * 100, 1) if month_income > 0 else 0

    return jsonify({
        "month": today.month,
        "year": today.year,
        "month_name": today.strftime("%B"),
        "today_spending": _paise_to_rupees(today_spending),
        "week_spending": _paise_to_rupees(week_spending),
        "month_income": _paise_to_rupees(month_income),
        "month_expenses": _paise_to_rupees(month_expenses),
        "remaining": _paise_to_rupees(remaining),
        "budget": _paise_to_rupees(budget_amount),
        "budget_used_pct": budget_used_pct,
        "budget_remaining": _paise_to_rupees(budget_amount - month_expenses) if budget_amount else 0,
        "savings": _paise_to_rupees(savings),
        "savings_rate": savings_rate,
    })


# ══════════════════════════════════════════════════════════════════════════════
#  DAILY & MONTHLY VIEWS
# ══════════════════════════════════════════════════════════════════════════════

@money_bp.route("/daily", methods=["GET"])
def daily_spending():
    target = request.args.get("date", date.today().isoformat())
    d = _parse_date(target)

    txns = Transaction.query.filter(
        Transaction.transaction_date == d,
        Transaction.type == "expense",
    ).order_by(Transaction.id.desc()).all()

    total = sum(t.amount for t in txns)

    # Category breakdown
    cat_totals = defaultdict(int)
    for t in txns:
        cat_name = t.category.name if t.category else "Other"
        cat_totals[cat_name] += t.amount

    category_breakdown = [
        {"name": name, "amount": _paise_to_rupees(amt)}
        for name, amt in sorted(cat_totals.items(), key=lambda x: -x[1])
    ]

    return jsonify({
        "date": d.isoformat(),
        "date_display": d.strftime("%d %B %Y"),
        "day_name": d.strftime("%A"),
        "total": _paise_to_rupees(total),
        "category_breakdown": category_breakdown,
        "transactions": [t.to_dict() for t in txns],
    })


@money_bp.route("/monthly", methods=["GET"])
def monthly_view():
    year = request.args.get("year", type=int, default=date.today().year)
    month = request.args.get("month", type=int, default=date.today().month)
    days_in_month = cal.monthrange(year, month)[1]
    month_start = date(year, month, 1)
    month_end = date(year, month, days_in_month)

    txns = Transaction.query.filter(
        Transaction.transaction_date >= month_start,
        Transaction.transaction_date <= month_end,
    ).all()

    income = sum(t.amount for t in txns if t.type == "income")
    expenses = sum(t.amount for t in txns if t.type == "expense")
    remaining = income - expenses

    budget = Budget.query.filter_by(user_id=1, month=month, year=year).first()
    budget_amount = budget.amount if budget else 0
    budget_remaining = budget_amount - expenses if budget_amount else 0

    savings_rate = round((income - expenses) / income * 100, 1) if income > 0 else 0

    # Category breakdown (expenses only)
    cat_totals = defaultdict(lambda: {"amount": 0, "icon": "fa-circle"})
    for t in txns:
        if t.type == "expense":
            name = t.category.name if t.category else "Other"
            cat_totals[name]["amount"] += t.amount
            if t.category:
                cat_totals[name]["icon"] = t.category.icon

    category_breakdown = [
        {"name": name, "amount": _paise_to_rupees(d["amount"]), "icon": d["icon"]}
        for name, d in sorted(cat_totals.items(), key=lambda x: -x[1]["amount"])
    ]

    return jsonify({
        "year": year,
        "month": month,
        "month_name": date(year, month, 1).strftime("%B %Y"),
        "income": _paise_to_rupees(income),
        "expenses": _paise_to_rupees(expenses),
        "remaining": _paise_to_rupees(remaining),
        "budget": _paise_to_rupees(budget_amount),
        "budget_remaining": _paise_to_rupees(budget_remaining),
        "savings_rate": savings_rate,
        "category_breakdown": category_breakdown,
    })


# ══════════════════════════════════════════════════════════════════════════════
#  CALENDAR
# ══════════════════════════════════════════════════════════════════════════════

@money_bp.route("/calendar", methods=["GET"])
def money_calendar():
    year = request.args.get("year", type=int, default=date.today().year)
    month = request.args.get("month", type=int, default=date.today().month)
    days_in_month = cal.monthrange(year, month)[1]
    month_start = date(year, month, 1)
    month_end = date(year, month, days_in_month)

    txns = Transaction.query.filter(
        Transaction.transaction_date >= month_start,
        Transaction.transaction_date <= month_end,
        Transaction.type == "expense",
    ).all()

    daily_totals = defaultdict(int)
    for t in txns:
        daily_totals[t.transaction_date.day] += t.amount

    days = []
    for d in range(1, days_in_month + 1):
        days.append({
            "day": d,
            "date": date(year, month, d).isoformat(),
            "amount": _paise_to_rupees(daily_totals.get(d, 0)),
        })

    max_amount = max((d["amount"] for d in days), default=0)

    return jsonify({
        "year": year,
        "month": month,
        "month_name": date(year, month, 1).strftime("%B %Y"),
        "first_weekday": date(year, month, 1).weekday(),  # 0=Mon
        "days": days,
        "max_amount": max_amount,
    })


# ══════════════════════════════════════════════════════════════════════════════
#  ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

@money_bp.route("/analytics", methods=["GET"])
def money_analytics():
    year = request.args.get("year", type=int, default=date.today().year)
    month = request.args.get("month", type=int, default=date.today().month)
    days_in_month = cal.monthrange(year, month)[1]
    month_start = date(year, month, 1)
    month_end = date(year, month, days_in_month)

    txns = Transaction.query.filter(
        Transaction.transaction_date >= month_start,
        Transaction.transaction_date <= month_end,
    ).all()

    # ── Category pie (expenses only) ──
    cat_totals = defaultdict(int)
    for t in txns:
        if t.type == "expense":
            cat_totals[t.category.name if t.category else "Other"] += t.amount
    total_expenses = sum(cat_totals.values())
    category_pie = [
        {
            "name": name,
            "amount": _paise_to_rupees(amt),
            "pct": round(amt / total_expenses * 100, 1) if total_expenses else 0,
        }
        for name, amt in sorted(cat_totals.items(), key=lambda x: -x[1])
    ]

    # ── Daily spending bar chart ──
    daily_spending = [0] * days_in_month
    for t in txns:
        if t.type == "expense":
            daily_spending[t.transaction_date.day - 1] += t.amount
    daily_spending_chart = [_paise_to_rupees(x) for x in daily_spending]

    # ── Monthly comparison (last 6 months) ──
    monthly_comparison = []
    for i in range(5, -1, -1):
        m = month - i
        y = year
        while m <= 0:
            m += 12
            y -= 1
        dim = cal.monthrange(y, m)[1]
        ms = date(y, m, 1)
        me = date(y, m, dim)
        m_txns = Transaction.query.filter(
            Transaction.transaction_date >= ms,
            Transaction.transaction_date <= me,
        ).all()
        m_income = sum(t.amount for t in m_txns if t.type == "income")
        m_expense = sum(t.amount for t in m_txns if t.type == "expense")
        monthly_comparison.append({
            "month": date(y, m, 1).strftime("%b %Y"),
            "income": _paise_to_rupees(m_income),
            "expenses": _paise_to_rupees(m_expense),
            "savings": _paise_to_rupees(m_income - m_expense),
        })

    # ── Payment method breakdown ──
    pm_totals = defaultdict(int)
    for t in txns:
        if t.type == "expense":
            pm_name = t.payment_method.name if t.payment_method else "Other"
            pm_totals[pm_name] += t.amount
    payment_method_chart = [
        {"name": name, "amount": _paise_to_rupees(amt)}
        for name, amt in sorted(pm_totals.items(), key=lambda x: -x[1])
    ]

    return jsonify({
        "year": year,
        "month": month,
        "category_pie": category_pie,
        "daily_spending": daily_spending_chart,
        "monthly_comparison": monthly_comparison,
        "payment_method": payment_method_chart,
    })


# ══════════════════════════════════════════════════════════════════════════════
#  INSIGHTS
# ══════════════════════════════════════════════════════════════════════════════

@money_bp.route("/insights", methods=["GET"])
def money_insights():
    today = date.today()
    month_start = today.replace(day=1)
    days_in_month = cal.monthrange(today.year, today.month)[1]
    month_end = date(today.year, today.month, days_in_month)

    txns = Transaction.query.filter(
        Transaction.transaction_date >= month_start,
        Transaction.transaction_date <= month_end,
    ).all()

    expenses = [t for t in txns if t.type == "expense"]
    income = [t for t in txns if t.type == "income"]
    total_exp = sum(t.amount for t in expenses)
    total_inc = sum(t.amount for t in income)

    insights = []

    # Highest spending category
    cat_totals = defaultdict(int)
    for t in expenses:
        cat_totals[t.category.name if t.category else "Other"] += t.amount
    if cat_totals:
        top_cat = max(cat_totals, key=cat_totals.get)
        insights.append({
            "icon": "fa-arrow-trend-up",
            "color": "#ef4444",
            "text": f"Your highest spending category is {top_cat} at ₹{_paise_to_rupees(cat_totals[top_cat]):,.2f}.",
        })

    # Average daily spending
    days_elapsed = (today - month_start).days + 1
    if days_elapsed > 0 and total_exp > 0:
        avg = total_exp / days_elapsed
        insights.append({
            "icon": "fa-calculator",
            "color": "#6366f1",
            "text": f"Your average daily spending is ₹{_paise_to_rupees(int(avg)):,.2f}.",
        })

    # Budget usage
    budget = Budget.query.filter_by(user_id=1, month=today.month, year=today.year).first()
    if budget and budget.amount > 0:
        pct = round(total_exp / budget.amount * 100, 1)
        insights.append({
            "icon": "fa-chart-pie",
            "color": "#f59e0b" if pct < 90 else "#ef4444",
            "text": f"You have spent {pct}% of your monthly budget.",
        })

    # Savings rate
    if total_inc > 0:
        rate = round((total_inc - total_exp) / total_inc * 100, 1)
        insights.append({
            "icon": "fa-piggy-bank",
            "color": "#22c55e",
            "text": f"Your current savings rate is {rate}%.",
        })

    # Month-over-month comparison
    prev_month = today.month - 1
    prev_year = today.year
    if prev_month == 0:
        prev_month = 12
        prev_year -= 1
    prev_dim = cal.monthrange(prev_year, prev_month)[1]
    prev_start = date(prev_year, prev_month, 1)
    prev_end = date(prev_year, prev_month, prev_dim)
    prev_txns = Transaction.query.filter(
        Transaction.transaction_date >= prev_start,
        Transaction.transaction_date <= prev_end,
        Transaction.type == "expense",
    ).all()
    prev_total = sum(t.amount for t in prev_txns)
    if prev_total > 0 and total_exp > 0:
        diff = total_exp - prev_total
        if diff > 0:
            insights.append({
                "icon": "fa-arrow-up",
                "color": "#ef4444",
                "text": f"You spent ₹{_paise_to_rupees(diff):,.2f} more this month than last month.",
            })
        elif diff < 0:
            insights.append({
                "icon": "fa-arrow-down",
                "color": "#22c55e",
                "text": f"You spent ₹{_paise_to_rupees(abs(diff)):,.2f} less this month than last month.",
            })

    return jsonify({"insights": insights})


# ══════════════════════════════════════════════════════════════════════════════
#  DAILY LIMIT
# ══════════════════════════════════════════════════════════════════════════════

@money_bp.route("/daily-limit", methods=["GET"])
def daily_limit():
    today = date.today()
    days_in_month = cal.monthrange(today.year, today.month)[1]
    days_remaining = days_in_month - today.day + 1
    month_start = today.replace(day=1)
    month_end = date(today.year, today.month, days_in_month)

    budget = Budget.query.filter_by(user_id=1, month=today.month, year=today.year).first()
    budget_amount = budget.amount if budget else 0

    month_spent = db.session.query(
        db.func.coalesce(db.func.sum(Transaction.amount), 0)
    ).filter(
        Transaction.transaction_date >= month_start,
        Transaction.transaction_date <= month_end,
        Transaction.type == "expense",
    ).scalar()

    today_spent = db.session.query(
        db.func.coalesce(db.func.sum(Transaction.amount), 0)
    ).filter(
        Transaction.transaction_date == today,
        Transaction.type == "expense",
    ).scalar()

    budget_remaining = budget_amount - month_spent if budget_amount else 0
    suggested_daily = int(budget_remaining / days_remaining) if days_remaining > 0 and budget_remaining > 0 else 0
    remaining_today = max(0, suggested_daily - today_spent)

    return jsonify({
        "budget_remaining": _paise_to_rupees(budget_remaining),
        "days_remaining": days_remaining,
        "suggested_daily": _paise_to_rupees(suggested_daily),
        "today_spent": _paise_to_rupees(today_spent),
        "remaining_today": _paise_to_rupees(remaining_today),
    })


# ══════════════════════════════════════════════════════════════════════════════
#  BUDGETS CRUD
# ══════════════════════════════════════════════════════════════════════════════

@money_bp.route("/budgets", methods=["GET"])
def get_budgets():
    year = request.args.get("year", type=int, default=date.today().year)
    month = request.args.get("month", type=int, default=date.today().month)

    budget = Budget.query.filter_by(user_id=1, month=month, year=year).first()
    if not budget:
        return jsonify(None)

    # Calculate spending per category for budget view
    days_in_month = cal.monthrange(year, month)[1]
    month_start = date(year, month, 1)
    month_end = date(year, month, days_in_month)

    expenses = Transaction.query.filter(
        Transaction.transaction_date >= month_start,
        Transaction.transaction_date <= month_end,
        Transaction.type == "expense",
    ).all()

    total_spent = sum(t.amount for t in expenses)
    cat_spent = defaultdict(int)
    for t in expenses:
        if t.category_id:
            cat_spent[t.category_id] += t.amount

    budget_data = budget.to_dict()
    budget_data["total_spent"] = _paise_to_rupees(total_spent)
    budget_data["total_remaining"] = _paise_to_rupees(budget.amount - total_spent)
    budget_data["total_pct"] = round(total_spent / budget.amount * 100, 1) if budget.amount else 0

    # Enrich category budgets with spending data
    for cb in budget_data["category_budgets"]:
        spent = _paise_to_rupees(cat_spent.get(cb["category_id"], 0))
        cb["spent"] = spent
        cb["remaining"] = cb["amount"] - spent
        cb["pct"] = round(spent / cb["amount"] * 100, 1) if cb["amount"] else 0

    return jsonify(budget_data)


@money_bp.route("/budgets", methods=["POST"])
def create_or_update_budget():
    data = request.get_json(force=True) or {}
    month = data.get("month", date.today().month)
    year = data.get("year", date.today().year)
    amount = data.get("amount")

    if amount is None or float(amount) <= 0:
        return jsonify({"error": "Budget amount must be greater than zero"}), 400

    budget = Budget.query.filter_by(user_id=1, month=month, year=year).first()
    if budget:
        budget.amount = _amount_to_paise(amount)
    else:
        budget = Budget(user_id=1, month=month, year=year, amount=_amount_to_paise(amount))
        db.session.add(budget)
    db.session.flush()

    # Handle category budgets
    cat_budgets = data.get("category_budgets", [])
    if cat_budgets:
        BudgetCategory.query.filter_by(budget_id=budget.id).delete()
        for cb in cat_budgets:
            if float(cb.get("amount", 0)) > 0:
                db.session.add(BudgetCategory(
                    budget_id=budget.id,
                    category_id=cb["category_id"],
                    amount=_amount_to_paise(cb["amount"]),
                ))

    db.session.commit()
    return jsonify(budget.to_dict()), 201


@money_bp.route("/budgets/<int:budget_id>", methods=["PUT"])
def update_budget(budget_id):
    budget = Budget.query.get_or_404(budget_id)
    data = request.get_json(force=True) or {}

    if "amount" in data:
        if float(data["amount"]) <= 0:
            return jsonify({"error": "Budget amount must be greater than zero"}), 400
        budget.amount = _amount_to_paise(data["amount"])

    if "category_budgets" in data:
        BudgetCategory.query.filter_by(budget_id=budget.id).delete()
        for cb in data["category_budgets"]:
            if float(cb.get("amount", 0)) > 0:
                db.session.add(BudgetCategory(
                    budget_id=budget.id,
                    category_id=cb["category_id"],
                    amount=_amount_to_paise(cb["amount"]),
                ))

    db.session.commit()
    return jsonify(budget.to_dict())


@money_bp.route("/budgets/<int:budget_id>", methods=["DELETE"])
def delete_budget(budget_id):
    budget = Budget.query.get_or_404(budget_id)
    db.session.delete(budget)
    db.session.commit()
    return jsonify({"deleted": True})


# ══════════════════════════════════════════════════════════════════════════════
#  SAVINGS GOALS
# ══════════════════════════════════════════════════════════════════════════════

@money_bp.route("/goals", methods=["GET"])
def get_goals():
    goals = SavingsGoal.query.filter_by(user_id=1).order_by(SavingsGoal.created_at.desc()).all()
    return jsonify([g.to_dict() for g in goals])


@money_bp.route("/goals", methods=["POST"])
def create_goal():
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    target = data.get("target_amount")

    if not name:
        return jsonify({"error": "Goal name is required"}), 400
    if target is None or float(target) <= 0:
        return jsonify({"error": "Target amount must be greater than zero"}), 400

    goal = SavingsGoal(
        user_id=1,
        name=name,
        target_amount=_amount_to_paise(target),
        target_date=_parse_date(data.get("target_date")),
    )
    db.session.add(goal)
    db.session.commit()
    return jsonify(goal.to_dict()), 201


@money_bp.route("/goals/<int:goal_id>", methods=["PUT"])
def update_goal(goal_id):
    goal = SavingsGoal.query.get_or_404(goal_id)
    data = request.get_json(force=True) or {}

    if "name" in data:
        goal.name = (data["name"] or "").strip()
    if "target_amount" in data:
        goal.target_amount = _amount_to_paise(data["target_amount"])
    if "target_date" in data:
        goal.target_date = _parse_date(data["target_date"])
    if "status" in data:
        goal.status = data["status"]

    db.session.commit()
    return jsonify(goal.to_dict())


@money_bp.route("/goals/<int:goal_id>", methods=["DELETE"])
def delete_goal(goal_id):
    goal = SavingsGoal.query.get_or_404(goal_id)
    db.session.delete(goal)
    db.session.commit()
    return jsonify({"deleted": True})


@money_bp.route("/goals/<int:goal_id>/contribute", methods=["POST"])
def contribute_to_goal(goal_id):
    goal = SavingsGoal.query.get_or_404(goal_id)
    data = request.get_json(force=True) or {}
    amount = data.get("amount")

    if amount is None or float(amount) <= 0:
        return jsonify({"error": "Contribution amount must be greater than zero"}), 400

    paise = _amount_to_paise(amount)
    contrib = SavingsContribution(
        goal_id=goal.id,
        amount=paise,
        date=_parse_date(data.get("date")) or date.today(),
        notes=(data.get("notes") or "").strip(),
    )
    db.session.add(contrib)
    goal.current_amount += paise

    # Auto-complete if target reached
    if goal.current_amount >= goal.target_amount:
        goal.status = "completed"

    db.session.commit()
    return jsonify(goal.to_dict()), 201


# ══════════════════════════════════════════════════════════════════════════════
#  RECURRING TRANSACTIONS
# ══════════════════════════════════════════════════════════════════════════════

@money_bp.route("/recurring", methods=["GET"])
def get_recurring():
    items = RecurringTransaction.query.filter_by(user_id=1).order_by(
        RecurringTransaction.active.desc(), RecurringTransaction.next_date.asc()
    ).all()
    return jsonify([r.to_dict() for r in items])


@money_bp.route("/recurring", methods=["POST"])
def create_recurring():
    data = request.get_json(force=True) or {}
    amount = data.get("amount")
    if amount is None or float(amount) <= 0:
        return jsonify({"error": "Amount must be greater than zero"}), 400

    freq = data.get("frequency", "monthly")
    if freq not in ("daily", "weekly", "monthly", "yearly"):
        return jsonify({"error": "Invalid frequency"}), 400

    next_date = data.get("next_date")
    if not next_date:
        return jsonify({"error": "Next date is required"}), 400

    rec = RecurringTransaction(
        user_id=1,
        amount=_amount_to_paise(amount),
        type=data.get("type", "expense"),
        category_id=data.get("category_id"),
        description=(data.get("description") or "").strip(),
        payment_method_id=data.get("payment_method_id"),
        frequency=freq,
        next_date=_parse_date(next_date),
    )
    db.session.add(rec)
    db.session.commit()
    return jsonify(rec.to_dict()), 201


@money_bp.route("/recurring/<int:rec_id>", methods=["PUT"])
def update_recurring(rec_id):
    rec = RecurringTransaction.query.get_or_404(rec_id)
    data = request.get_json(force=True) or {}

    if "amount" in data:
        rec.amount = _amount_to_paise(data["amount"])
    if "type" in data:
        rec.type = data["type"]
    if "category_id" in data:
        rec.category_id = data["category_id"]
    if "description" in data:
        rec.description = (data["description"] or "").strip()
    if "payment_method_id" in data:
        rec.payment_method_id = data["payment_method_id"]
    if "frequency" in data:
        rec.frequency = data["frequency"]
    if "next_date" in data:
        rec.next_date = _parse_date(data["next_date"])
    if "active" in data:
        rec.active = bool(data["active"])

    db.session.commit()
    return jsonify(rec.to_dict())


@money_bp.route("/recurring/<int:rec_id>", methods=["DELETE"])
def delete_recurring(rec_id):
    rec = RecurringTransaction.query.get_or_404(rec_id)
    db.session.delete(rec)
    db.session.commit()
    return jsonify({"deleted": True})


# ══════════════════════════════════════════════════════════════════════════════
#  EXPORT
# ══════════════════════════════════════════════════════════════════════════════

@money_bp.route("/export", methods=["GET"])
def export_transactions():
    fmt = request.args.get("format", "csv")

    # Build same query as get_transactions but without pagination
    q = Transaction.query

    txn_type = request.args.get("type")
    if txn_type:
        q = q.filter(Transaction.type == txn_type)
    category_id = request.args.get("category_id")
    if category_id:
        q = q.filter(Transaction.category_id == int(category_id))
    payment_id = request.args.get("payment_method_id")
    if payment_id:
        q = q.filter(Transaction.payment_method_id == int(payment_id))
    date_from = request.args.get("date_from")
    if date_from:
        q = q.filter(Transaction.transaction_date >= _parse_date(date_from))
    date_to = request.args.get("date_to")
    if date_to:
        q = q.filter(Transaction.transaction_date <= _parse_date(date_to))
    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)
    if month and year:
        days_in_m = cal.monthrange(year, month)[1]
        q = q.filter(
            Transaction.transaction_date >= date(year, month, 1),
            Transaction.transaction_date <= date(year, month, days_in_m),
        )

    q = q.order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
    txns = q.all()

    headers = ["Date", "Time", "Description", "Category", "Type", "Payment Method", "Amount (₹)", "Notes"]
    rows = []
    for t in txns:
        rows.append([
            t.transaction_date.isoformat() if t.transaction_date else "",
            t.transaction_time.strftime("%H:%M") if t.transaction_time else "",
            t.description or "",
            t.category.name if t.category else "",
            t.type,
            t.payment_method.name if t.payment_method else "",
            f"{t.amount / 100:.2f}",
            t.notes or "",
        ])

    if fmt == "xlsx":
        try:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Transactions"
            ws.append(headers)
            for row in rows:
                ws.append(row)
            # Auto-width columns
            for col in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 30)
            buf = io.BytesIO()
            wb.save(buf)
            buf.seek(0)
            return Response(
                buf.getvalue(),
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": "attachment; filename=transactions.xlsx"},
            )
        except ImportError:
            return jsonify({"error": "openpyxl not installed. Install with: pip install openpyxl"}), 500

    # Default: CSV
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=transactions.csv"},
    )


# ══════════════════════════════════════════════════════════════════════════════
#  RECURRING TRANSACTION TICKER (called by scheduler)
# ══════════════════════════════════════════════════════════════════════════════

def process_recurring_transactions():
    """Create transactions from active recurring rules whose next_date <= today.
    Advances next_date to the following period. Called by APScheduler."""
    today = date.today()
    due = RecurringTransaction.query.filter(
        RecurringTransaction.active == True,  # noqa: E712
        RecurringTransaction.next_date <= today,
    ).all()

    for rec in due:
        # Create the transaction
        txn = Transaction(
            user_id=rec.user_id,
            amount=rec.amount,
            type=rec.type,
            category_id=rec.category_id,
            description=rec.description,
            transaction_date=rec.next_date,
            payment_method_id=rec.payment_method_id,
            is_recurring=True,
            recurring_id=rec.id,
        )
        db.session.add(txn)

        # Advance next_date
        if rec.frequency == "daily":
            rec.next_date += timedelta(days=1)
        elif rec.frequency == "weekly":
            rec.next_date += timedelta(weeks=1)
        elif rec.frequency == "monthly":
            m = rec.next_date.month + 1
            y = rec.next_date.year
            if m > 12:
                m = 1
                y += 1
            d = min(rec.next_date.day, cal.monthrange(y, m)[1])
            rec.next_date = date(y, m, d)
        elif rec.frequency == "yearly":
            try:
                rec.next_date = rec.next_date.replace(year=rec.next_date.year + 1)
            except ValueError:  # Feb 29
                rec.next_date = date(rec.next_date.year + 1, 3, 1)

    db.session.commit()
    return len(due)
