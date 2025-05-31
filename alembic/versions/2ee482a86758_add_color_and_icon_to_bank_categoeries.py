"""add color and icon to bank_categoeries

Revision ID: 2ee482a86758
Revises: 65cc58d64553
Create Date: 2025-05-31 17:55:22.082650

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2ee482a86758'
down_revision: Union[str, None] = '65cc58d64553'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create foreign key constraints
    op.create_foreign_key(None, 'bank_transactions', 'bank_categories', ['category_id'], ['id'])
    op.create_foreign_key(None, 'expenses', 'bank_categories', ['category_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop foreign key constraints
    op.drop_constraint(None, 'expenses', type_='foreignkey')
    op.drop_constraint(None, 'bank_transactions', type_='foreignkey')
