"""Financial models: transactions, budgets, savings goals, recurring expenses."""
from datetime import datetime, date as date_cls
from models import db


# ── Default data ──────────────────────────────────────────────────────────────

DEFAULT_EXPENSE_CATEGORIES = [
    # Needs
    ("Food", "need", "fa-utensils", 5000),
    ("Groceries", "need", "fa-cart-shopping", 3000),
    ("Rent", "need", "fa-house", 0),
    ("Utilities", "need", "fa-bolt", 2000),
    ("Transportation", "need", "fa-bus", 2000),
    ("Medical", "need", "fa-kit-medical", 1000),
    ("Education", "need", "fa-graduation-cap", 2000),
    # Lifestyle
    ("Shopping", "lifestyle", "fa-bag-shopping", 3000),
    ("Entertainment", "lifestyle", "fa-film", 1500),
    ("Eating Out", "lifestyle", "fa-burger", 2000),
    ("Travel", "lifestyle", "fa-plane", 0),
    ("Subscriptions", "lifestyle", "fa-rotate", 1000),
    # Personal
    ("Family", "personal", "fa-people-roof", 0),
    ("Personal Care", "personal", "fa-spa", 1000),
    ("Fitness", "personal", "fa-dumbbell", 500),
    ("Other", "personal", "fa-ellipsis", 0),
]

DEFAULT_INCOME_SOURCES = [
    ("Salary", "income", "fa-money-bill-wave"),
    ("Freelance", "income", "fa-laptop-code"),
    ("Internship", "income", "fa-building"),
    ("Business", "income", "fa-store"),
    ("Interest", "income", "fa-piggy-bank"),
    ("Gift", "income", "fa-gift"),
    ("Other Income", "income", "fa-coins"),
]

DEFAULT_PAYMENT_METHODS = [
    ("Cash", "fa-money-bill", True),
    ("UPI", "fa-mobile-screen", True),
    ("Debit Card", "fa-credit-card", True),
    ("Credit Card", "fa-credit-card", True),
    ("Bank Transfer", "fa-building-columns", True),
    ("Other", "fa-ellipsis", True),
]


# ── Models ────────────────────────────────────────────────────────────────────

class ExpenseCategory(db.Model):
    """Category for expenses or income sources."""
    __tablename__ = "expense_category"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), nullable=False)
    type = db.Column(db.String(20), nullable=False, default="need")  # need / lifestyle / personal / income
    icon = db.Column(db.String(40), default="fa-circle")
    monthly_budget = db.Column(db.Integer, default=0)  # stored in paise (₹1 = 100)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transactions = db.relationship("Transaction", backref="category", lazy=True)

    def __init__(self, name, type="need", icon="fa-circle", monthly_budget=0):
        self.name = name
        self.type = type
        self.icon = icon
        self.monthly_budget = monthly_budget

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "icon": self.icon,
            "monthly_budget": self.monthly_budget / 100,  # return as rupees
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PaymentMethod(db.Model):
    """Payment method for transactions."""
    __tablename__ = "payment_method"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), nullable=False)
    icon = db.Column(db.String(40), default="fa-circle")
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transactions = db.relationship("Transaction", backref="payment_method", lazy=True)

    def __init__(self, name, icon="fa-circle", is_default=False):
        self.name = name
        self.icon = icon
        self.is_default = is_default

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "is_default": self.is_default,
        }


class Transaction(db.Model):
    """A single financial transaction (income or expense)."""
    __tablename__ = "transaction"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), default=1, index=True)
    amount = db.Column(db.Integer, nullable=False)  # stored in paise
    type = db.Column(db.String(20), nullable=False, default="expense")  # expense / income
    category_id = db.Column(db.Integer, db.ForeignKey("expense_category.id"), index=True)
    description = db.Column(db.String(300), default="")
    transaction_date = db.Column(db.Date, nullable=False, index=True)
    transaction_time = db.Column(db.Time, nullable=True)
    payment_method_id = db.Column(db.Integer, db.ForeignKey("payment_method.id"), nullable=True, index=True)
    notes = db.Column(db.Text, default="")
    is_recurring = db.Column(db.Boolean, default=False)
    recurring_id = db.Column(db.Integer, db.ForeignKey("recurring_transaction.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", backref="transactions")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "amount": self.amount / 100,  # return as rupees
            "amount_paise": self.amount,
            "type": self.type,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else None,
            "category_icon": self.category.icon if self.category else "fa-circle",
            "category_type": self.category.type if self.category else None,
            "description": self.description or "",
            "transaction_date": self.transaction_date.isoformat() if self.transaction_date else None,
            "transaction_time": self.transaction_time.strftime("%H:%M") if self.transaction_time else None,
            "payment_method_id": self.payment_method_id,
            "payment_method_name": self.payment_method.name if self.payment_method else None,
            "payment_method_icon": self.payment_method.icon if self.payment_method else None,
            "notes": self.notes or "",
            "is_recurring": self.is_recurring,
            "recurring_id": self.recurring_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Budget(db.Model):
    """Monthly budget for a user."""
    __tablename__ = "budget"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), default=1, index=True)
    month = db.Column(db.Integer, nullable=False)  # 1-12
    year = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Integer, nullable=False, default=0)  # stored in paise
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    category_budgets = db.relationship("BudgetCategory", backref="budget", lazy=True,
                                       cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint("user_id", "month", "year", name="uq_user_budget_month"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "month": self.month,
            "year": self.year,
            "amount": self.amount / 100,
            "category_budgets": [cb.to_dict() for cb in self.category_budgets],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class BudgetCategory(db.Model):
    """Per-category budget allocation within a monthly budget."""
    __tablename__ = "budget_category"

    id = db.Column(db.Integer, primary_key=True)
    budget_id = db.Column(db.Integer, db.ForeignKey("budget.id"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("expense_category.id"), nullable=False)
    amount = db.Column(db.Integer, nullable=False, default=0)  # stored in paise

    category = db.relationship("ExpenseCategory")

    def to_dict(self):
        return {
            "id": self.id,
            "budget_id": self.budget_id,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else None,
            "category_icon": self.category.icon if self.category else None,
            "amount": self.amount / 100,
        }


class SavingsGoal(db.Model):
    """A savings target with deadline."""
    __tablename__ = "savings_goal"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), default=1, index=True)
    name = db.Column(db.String(120), nullable=False)
    target_amount = db.Column(db.Integer, nullable=False, default=0)  # paise
    current_amount = db.Column(db.Integer, nullable=False, default=0)  # paise
    target_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default="active")  # active / completed / paused
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contributions = db.relationship("SavingsContribution", backref="goal", lazy=True,
                                    cascade="all, delete-orphan")

    def to_dict(self):
        pct = round(self.current_amount / self.target_amount * 100, 1) if self.target_amount else 0
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "target_amount": self.target_amount / 100,
            "current_amount": self.current_amount / 100,
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "status": self.status,
            "progress_pct": pct,
            "remaining": (self.target_amount - self.current_amount) / 100,
            "contributions": [c.to_dict() for c in self.contributions],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SavingsContribution(db.Model):
    """Individual contribution toward a savings goal."""
    __tablename__ = "savings_contribution"

    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey("savings_goal.id"), nullable=False, index=True)
    amount = db.Column(db.Integer, nullable=False)  # paise
    date = db.Column(db.Date, nullable=False, default=date_cls.today)
    notes = db.Column(db.String(200), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "goal_id": self.goal_id,
            "amount": self.amount / 100,
            "date": self.date.isoformat() if self.date else None,
            "notes": self.notes or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RecurringTransaction(db.Model):
    """A template for automatically generated transactions."""
    __tablename__ = "recurring_transaction"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), default=1, index=True)
    amount = db.Column(db.Integer, nullable=False)  # paise
    type = db.Column(db.String(20), nullable=False, default="expense")
    category_id = db.Column(db.Integer, db.ForeignKey("expense_category.id"), nullable=True)
    description = db.Column(db.String(300), default="")
    payment_method_id = db.Column(db.Integer, db.ForeignKey("payment_method.id"), nullable=True)
    frequency = db.Column(db.String(20), nullable=False, default="monthly")  # daily/weekly/monthly/yearly
    next_date = db.Column(db.Date, nullable=False)
    active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    category = db.relationship("ExpenseCategory")
    payment = db.relationship("PaymentMethod")
    generated_transactions = db.relationship("Transaction", backref="recurring_source", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "amount": self.amount / 100,
            "type": self.type,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else None,
            "category_icon": self.category.icon if self.category else None,
            "description": self.description or "",
            "payment_method_id": self.payment_method_id,
            "payment_method_name": self.payment.name if self.payment else None,
            "frequency": self.frequency,
            "next_date": self.next_date.isoformat() if self.next_date else None,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
