"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-09-23

Creates all tables for the Daily Tracker + Money Manager application.
This migration is safe to run on an empty PostgreSQL database (Render) or
any fresh environment. It is idempotent via Alembic's revision tracking.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ── user ──────────────────────────────────────────────────────────────────
    op.create_table(
        'user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('default_task_duration', sa.Integer(), nullable=True),
        sa.Column('week_starts_monday', sa.Boolean(), nullable=True),
        sa.Column('theme', sa.String(length=20), nullable=True),
        sa.Column('notification_pref', sa.Boolean(), nullable=True),
        sa.Column('daily_goal', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('notif_browser', sa.Boolean(), nullable=True),
        sa.Column('notif_sound', sa.Boolean(), nullable=True),
        sa.Column('notif_in_app', sa.Boolean(), nullable=True),
        sa.Column('notif_overdue', sa.Boolean(), nullable=True),
        sa.Column('notif_daily_summary', sa.Boolean(), nullable=True),
        sa.Column('notif_reminder_offset', sa.Integer(), nullable=True),
        sa.Column('notif_summary_time', sa.String(length=5), nullable=True),
        sa.Column('push_subscription', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── category (task categories) ────────────────────────────────────────────
    op.create_table(
        'category',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=60), nullable=False),
        sa.Column('color', sa.String(length=20), nullable=True),
        sa.Column('icon', sa.String(length=40), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    # ── task ──────────────────────────────────────────────────────────────────
    op.create_table(
        'task',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('priority', sa.String(length=20), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('due_time', sa.Time(), nullable=True),
        sa.Column('time_block', sa.String(length=20), nullable=True),
        sa.Column('recurrence', sa.String(length=20), nullable=True),
        sa.Column('recurrence_days', sa.String(length=30), nullable=True),
        sa.Column('is_template', sa.Boolean(), nullable=True),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('reminder_time', sa.Time(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['category.id']),
        sa.ForeignKeyConstraint(['parent_id'], ['task.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_task_category_id'), 'task', ['category_id'])
    op.create_index(op.f('ix_task_due_date'), 'task', ['due_date'])
    op.create_index(op.f('ix_task_is_template'), 'task', ['is_template'])
    op.create_index(op.f('ix_task_parent_id'), 'task', ['parent_id'])
    op.create_index(op.f('ix_task_priority'), 'task', ['priority'])
    op.create_index(op.f('ix_task_status'), 'task', ['status'])

    # ── task_completion ───────────────────────────────────────────────────────
    op.create_table(
        'task_completion',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('completed_on', sa.Date(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['task.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_task_completion_completed_on'), 'task_completion', ['completed_on'])
    op.create_index(op.f('ix_task_completion_task_id'), 'task_completion', ['task_id'])

    # ── reminder ──────────────────────────────────────────────────────────────
    op.create_table(
        'reminder',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('remind_at', sa.DateTime(), nullable=False),
        sa.Column('seen', sa.Boolean(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('kind', sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['task.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_reminder_remind_at'), 'reminder', ['remind_at'])
    op.create_index(op.f('ix_reminder_status'), 'reminder', ['status'])
    op.create_index(op.f('ix_reminder_task_id'), 'reminder', ['task_id'])

    # ── habit ─────────────────────────────────────────────────────────────────
    op.create_table(
        'habit',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('target_frequency', sa.String(length=20), nullable=True),
        sa.Column('target_count', sa.Integer(), nullable=True),
        sa.Column('goal', sa.String(length=200), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── habit_completion ──────────────────────────────────────────────────────
    op.create_table(
        'habit_completion',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('habit_id', sa.Integer(), nullable=False),
        sa.Column('completed_on', sa.Date(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['habit_id'], ['habit.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('habit_id', 'completed_on', name='uq_habit_date'),
    )
    op.create_index(op.f('ix_habit_completion_completed_on'), 'habit_completion', ['completed_on'])
    op.create_index(op.f('ix_habit_completion_habit_id'), 'habit_completion', ['habit_id'])

    # ── expense_category ──────────────────────────────────────────────────────
    op.create_table(
        'expense_category',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=60), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('icon', sa.String(length=40), nullable=True),
        sa.Column('monthly_budget', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── payment_method ────────────────────────────────────────────────────────
    op.create_table(
        'payment_method',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=60), nullable=False),
        sa.Column('icon', sa.String(length=40), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── budget ────────────────────────────────────────────────────────────────
    op.create_table(
        'budget',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'month', 'year', name='uq_user_budget_month'),
    )
    op.create_index(op.f('ix_budget_user_id'), 'budget', ['user_id'])

    # ── budget_category ───────────────────────────────────────────────────────
    op.create_table(
        'budget_category',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('budget_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['budget_id'], ['budget.id']),
        sa.ForeignKeyConstraint(['category_id'], ['expense_category.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_budget_category_budget_id'), 'budget_category', ['budget_id'])

    # ── savings_goal ──────────────────────────────────────────────────────────
    op.create_table(
        'savings_goal',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('target_amount', sa.Integer(), nullable=False),
        sa.Column('current_amount', sa.Integer(), nullable=False),
        sa.Column('target_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_savings_goal_user_id'), 'savings_goal', ['user_id'])

    # ── savings_contribution ──────────────────────────────────────────────────
    op.create_table(
        'savings_contribution',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('goal_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('notes', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['goal_id'], ['savings_goal.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_savings_contribution_goal_id'), 'savings_contribution', ['goal_id'])

    # ── recurring_transaction ─────────────────────────────────────────────────
    op.create_table(
        'recurring_transaction',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.String(length=300), nullable=True),
        sa.Column('payment_method_id', sa.Integer(), nullable=True),
        sa.Column('frequency', sa.String(length=20), nullable=False),
        sa.Column('next_date', sa.Date(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['expense_category.id']),
        sa.ForeignKeyConstraint(['payment_method_id'], ['payment_method.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_recurring_transaction_active'), 'recurring_transaction', ['active'])
    op.create_index(op.f('ix_recurring_transaction_user_id'), 'recurring_transaction', ['user_id'])

    # ── transaction ───────────────────────────────────────────────────────────
    op.create_table(
        'transaction',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.String(length=300), nullable=True),
        sa.Column('transaction_date', sa.Date(), nullable=False),
        sa.Column('transaction_time', sa.Time(), nullable=True),
        sa.Column('payment_method_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_recurring', sa.Boolean(), nullable=True),
        sa.Column('recurring_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['expense_category.id']),
        sa.ForeignKeyConstraint(['payment_method_id'], ['payment_method.id']),
        sa.ForeignKeyConstraint(['recurring_id'], ['recurring_transaction.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_transaction_category_id'), 'transaction', ['category_id'])
    op.create_index(op.f('ix_transaction_payment_method_id'), 'transaction', ['payment_method_id'])
    op.create_index(op.f('ix_transaction_transaction_date'), 'transaction', ['transaction_date'])
    op.create_index(op.f('ix_transaction_user_id'), 'transaction', ['user_id'])


def downgrade():
    # Drop in reverse dependency order
    op.drop_index(op.f('ix_transaction_user_id'), table_name='transaction')
    op.drop_index(op.f('ix_transaction_transaction_date'), table_name='transaction')
    op.drop_index(op.f('ix_transaction_payment_method_id'), table_name='transaction')
    op.drop_index(op.f('ix_transaction_category_id'), table_name='transaction')
    op.drop_table('transaction')

    op.drop_index(op.f('ix_recurring_transaction_user_id'), table_name='recurring_transaction')
    op.drop_index(op.f('ix_recurring_transaction_active'), table_name='recurring_transaction')
    op.drop_table('recurring_transaction')

    op.drop_index(op.f('ix_savings_contribution_goal_id'), table_name='savings_contribution')
    op.drop_table('savings_contribution')

    op.drop_index(op.f('ix_savings_goal_user_id'), table_name='savings_goal')
    op.drop_table('savings_goal')

    op.drop_index(op.f('ix_budget_category_budget_id'), table_name='budget_category')
    op.drop_table('budget_category')

    op.drop_index(op.f('ix_budget_user_id'), table_name='budget')
    op.drop_table('budget')

    op.drop_table('payment_method')
    op.drop_table('expense_category')

    op.drop_index(op.f('ix_habit_completion_habit_id'), table_name='habit_completion')
    op.drop_index(op.f('ix_habit_completion_completed_on'), table_name='habit_completion')
    op.drop_table('habit_completion')
    op.drop_table('habit')

    op.drop_index(op.f('ix_reminder_task_id'), table_name='reminder')
    op.drop_index(op.f('ix_reminder_status'), table_name='reminder')
    op.drop_index(op.f('ix_reminder_remind_at'), table_name='reminder')
    op.drop_table('reminder')

    op.drop_index(op.f('ix_task_completion_task_id'), table_name='task_completion')
    op.drop_index(op.f('ix_task_completion_completed_on'), table_name='task_completion')
    op.drop_table('task_completion')

    op.drop_index(op.f('ix_task_status'), table_name='task')
    op.drop_index(op.f('ix_task_priority'), table_name='task')
    op.drop_index(op.f('ix_task_parent_id'), table_name='task')
    op.drop_index(op.f('ix_task_is_template'), table_name='task')
    op.drop_index(op.f('ix_task_due_date'), table_name='task')
    op.drop_index(op.f('ix_task_category_id'), table_name='task')
    op.drop_table('task')

    op.drop_table('category')
    op.drop_table('user')
