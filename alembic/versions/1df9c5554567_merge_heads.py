"""merge_heads

Revision ID: 1df9c5554567
Revises: 119ff60d4906, 8ab099362d84
Create Date: 2025-05-31 18:29:14.244851

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1df9c5554567'
down_revision: Union[str, None] = ('119ff60d4906', '8ab099362d84')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
