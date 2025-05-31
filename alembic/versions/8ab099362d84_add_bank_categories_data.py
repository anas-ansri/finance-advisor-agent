"""add bank categories data

Revision ID: 8ab099362d84
Revises: f1d29d08689a
Create Date: 2024-03-31 19:22:12.391527

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision: str = '8ab099362d84'
down_revision: Union[str, None] = 'f1d29d08689a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_unique_constraint("uq_bank_categories_name", "bank_categories", ["name"])
    # Insert bank categories data
    op.execute("""
        INSERT INTO bank_categories (id, name, description, icon, color)
        VALUES
            (gen_random_uuid(), 'HOUSING', 'Housing and accommodation expenses', 'home', 'bg-blue-500'),
            (gen_random_uuid(), 'TRANSPORTATION', 'Transportation and travel expenses', 'car', 'bg-green-500'),
            (gen_random_uuid(), 'FOOD_DINING', 'Food, groceries, and dining expenses', 'utensils', 'bg-yellow-500'),
            (gen_random_uuid(), 'ENTERTAINMENT', 'Entertainment and leisure expenses', 'film', 'bg-purple-500'),
            (gen_random_uuid(), 'SHOPPING', 'Shopping and retail expenses', 'shopping-cart', 'bg-pink-500'),
            (gen_random_uuid(), 'UTILITIES', 'Utility bills and services', 'bolt', 'bg-orange-500'),
            (gen_random_uuid(), 'HEALTH_MEDICAL', 'Healthcare and medical expenses', 'heart', 'bg-red-500'),
            (gen_random_uuid(), 'PERSONAL_CARE', 'Personal care and grooming', 'user', 'bg-indigo-500'),
            (gen_random_uuid(), 'EDUCATION', 'Education and learning expenses', 'graduation-cap', 'bg-teal-500'),
            (gen_random_uuid(), 'TRAVEL', 'Travel and vacation expenses', 'plane', 'bg-cyan-500'),
            (gen_random_uuid(), 'GIFTS_DONATIONS', 'Gifts and charitable donations', 'gift', 'bg-rose-500'),
            (gen_random_uuid(), 'INCOME', 'Income and earnings', 'money-bill', 'bg-emerald-500'),
            (gen_random_uuid(), 'INVESTMENTS', 'Investment and savings', 'chart-line', 'bg-violet-500'),
            (gen_random_uuid(), 'SAVINGS', 'Savings and deposits', 'piggy-bank', 'bg-lime-500'),
            (gen_random_uuid(), 'FEES_CHARGES', 'Fees and charges', 'receipt', 'bg-gray-500'),
            (gen_random_uuid(), 'ATM_CASH', 'ATM and cash withdrawals', 'money-bill-wave', 'bg-slate-500'),
            (gen_random_uuid(), 'TRANSFERS', 'Transfers between accounts', 'exchange-alt', 'bg-zinc-500'),
            (gen_random_uuid(), 'INSURANCE', 'Insurance payments', 'shield-alt', 'bg-stone-500'),
            (gen_random_uuid(), 'TAXES', 'Tax payments', 'file-invoice-dollar', 'bg-neutral-500'),
            (gen_random_uuid(), 'OTHER', 'Other expenses', 'ellipsis-h', 'bg-gray-400')
        ON CONFLICT (name) DO NOTHING;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove bank categories data
    op.execute("""
        DELETE FROM bank_categories 
        WHERE name IN (
            'HOUSING', 'TRANSPORTATION', 'FOOD_DINING', 'ENTERTAINMENT', 'SHOPPING',
            'UTILITIES', 'HEALTH_MEDICAL', 'PERSONAL_CARE', 'EDUCATION', 'TRAVEL',
            'GIFTS_DONATIONS', 'INCOME', 'INVESTMENTS', 'SAVINGS', 'FEES_CHARGES',
            'ATM_CASH', 'TRANSFERS', 'INSURANCE', 'TAXES', 'OTHER'
        );
    """)
