from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from sqlalchemy import select

from app.models.bank_transaction import BankTransaction

async def get_all_transactions(
    db: AsyncSession,
    user_id: UUID
) -> List[BankTransaction]:
    """Get all transactions for a user."""
    print(f"Fetching all transactions for user {user_id}")
    stmt = select(BankTransaction).where(BankTransaction.user_id == user_id)
    result = await db.execute(stmt)
    transactions = result.scalars().all()
    print(f"Found {len(transactions)} transactions for user {user_id}")
    return list(transactions)