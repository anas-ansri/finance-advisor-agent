"""add_phone_number_to_users

Revision ID: 8949cd076703
Revises: 9e029bbeb95e
Create Date: 2025-07-30 19:34:16.711635

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8949cd076703'
down_revision: Union[str, None] = '9e029bbeb95e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add phone_number column to users table for MCP integration."""
    op.add_column('users', sa.Column('phone_number', sa.String(), nullable=True))


def downgrade() -> None:
    """Remove phone_number column from users table."""
    op.drop_column('users', 'phone_number')
