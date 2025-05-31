"""update relations

Revision ID: f1d29d08689a
Revises: 2ee482a86758
Create Date: 2025-05-31 18:22:12.391527

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f1d29d08689a'
down_revision: Union[str, None] = '2ee482a86758'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add icon and color columns if they don't exist
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                         WHERE table_name = 'bank_categories' AND column_name = 'icon') THEN
                ALTER TABLE bank_categories ADD COLUMN icon VARCHAR DEFAULT 'circle';
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                         WHERE table_name = 'bank_categories' AND column_name = 'color') THEN
                ALTER TABLE bank_categories ADD COLUMN color VARCHAR DEFAULT 'bg-gray-500';
            END IF;
        END $$;
    """)

    # Create the enum type first
    transaction_category_enum = postgresql.ENUM(
        'HOUSING', 'TRANSPORTATION', 'FOOD_DINING', 'ENTERTAINMENT', 'SHOPPING',
        'UTILITIES', 'HEALTH_MEDICAL', 'PERSONAL_CARE', 'EDUCATION', 'TRAVEL',
        'GIFTS_DONATIONS', 'INCOME', 'INVESTMENTS', 'SAVINGS', 'FEES_CHARGES',
        'ATM_CASH', 'TRANSFERS', 'INSURANCE', 'TAXES', 'OTHER',
        name='transactioncategoryenum'
    )
    transaction_category_enum.create(op.get_bind())

    # Update the column with USING clause
    op.execute("""
        ALTER TABLE bank_categories 
        ALTER COLUMN name TYPE transactioncategoryenum 
        USING CASE name
            WHEN 'Housing' THEN 'HOUSING'::transactioncategoryenum
            WHEN 'Transportation' THEN 'TRANSPORTATION'::transactioncategoryenum
            WHEN 'Food & Dining' THEN 'FOOD_DINING'::transactioncategoryenum
            WHEN 'Entertainment' THEN 'ENTERTAINMENT'::transactioncategoryenum
            WHEN 'Shopping' THEN 'SHOPPING'::transactioncategoryenum
            WHEN 'Utilities' THEN 'UTILITIES'::transactioncategoryenum
            WHEN 'Health & Medical' THEN 'HEALTH_MEDICAL'::transactioncategoryenum
            WHEN 'Personal Care' THEN 'PERSONAL_CARE'::transactioncategoryenum
            WHEN 'Education' THEN 'EDUCATION'::transactioncategoryenum
            WHEN 'Travel' THEN 'TRAVEL'::transactioncategoryenum
            WHEN 'Gifts & Donations' THEN 'GIFTS_DONATIONS'::transactioncategoryenum
            WHEN 'Income' THEN 'INCOME'::transactioncategoryenum
            WHEN 'Investments' THEN 'INVESTMENTS'::transactioncategoryenum
            WHEN 'Savings' THEN 'SAVINGS'::transactioncategoryenum
            WHEN 'Fees & Charges' THEN 'FEES_CHARGES'::transactioncategoryenum
            WHEN 'ATM & Cash' THEN 'ATM_CASH'::transactioncategoryenum
            WHEN 'Transfers' THEN 'TRANSFERS'::transactioncategoryenum
            WHEN 'Insurance' THEN 'INSURANCE'::transactioncategoryenum
            WHEN 'Taxes' THEN 'TAXES'::transactioncategoryenum
            ELSE 'OTHER'::transactioncategoryenum
        END
    """)

    # Make icon and color nullable
    op.execute("""
        ALTER TABLE bank_categories 
        ALTER COLUMN icon DROP NOT NULL,
        ALTER COLUMN color DROP NOT NULL
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Convert back to VARCHAR
    op.execute("""
        ALTER TABLE bank_categories 
        ALTER COLUMN name TYPE VARCHAR 
        USING name::text
    """)

    # Drop the enum type
    op.execute('DROP TYPE transactioncategoryenum')

    # Make icon and color not nullable
    op.execute("""
        ALTER TABLE bank_categories 
        ALTER COLUMN icon SET NOT NULL,
        ALTER COLUMN color SET NOT NULL
    """)
