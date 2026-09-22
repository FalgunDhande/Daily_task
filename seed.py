"""Seed default categories, payment methods, and a default user — no sample data."""
from models import db
from models.task import Category, DEFAULT_CATEGORIES
from models.user import User
from models.money import (
    ExpenseCategory, PaymentMethod,
    DEFAULT_EXPENSE_CATEGORIES, DEFAULT_INCOME_SOURCES, DEFAULT_PAYMENT_METHODS,
)


def run_seed():
    # Create default user if none exists
    if not User.query.first():
        db.session.add(User())
        db.session.commit()

    # Seed default task categories only
    if Category.query.first() is None:
        for name, color, icon in DEFAULT_CATEGORIES:
            db.session.add(Category(name=name, color=color, icon=icon))
        db.session.commit()

    # ── Money module defaults ─────────────────────────────────────────────
    _seed_expense_categories()
    _seed_payment_methods()


def _seed_expense_categories():
    """Seed default expense categories and income sources if none exist."""
    if ExpenseCategory.query.first() is not None:
        return

    for name, cat_type, icon, budget in DEFAULT_EXPENSE_CATEGORIES:
        db.session.add(ExpenseCategory(
            name=name,
            type=cat_type,
            icon=icon,
            monthly_budget=budget * 100,  # convert rupees to paise
        ))
    for name, cat_type, icon in DEFAULT_INCOME_SOURCES:
        db.session.add(ExpenseCategory(
            name=name,
            type=cat_type,
            icon=icon,
            monthly_budget=0,
        ))
    db.session.commit()


def _seed_payment_methods():
    """Seed default payment methods if none exist."""
    if PaymentMethod.query.first() is not None:
        return

    for name, icon, is_default in DEFAULT_PAYMENT_METHODS:
        db.session.add(PaymentMethod(name=name, icon=icon, is_default=is_default))
    db.session.commit()
