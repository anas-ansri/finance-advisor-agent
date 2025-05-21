from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation
from app.schemas.conversation import ConversationCreate, ConversationUpdate


async def create_conversation(db: AsyncSession, user_id: int, conversation_in: ConversationCreate) -> Conversation:
    """
    Create a new conversation.
    """
    db_conversation = Conversation(
        user_id=user_id,
        title=conversation_in.title,
    )
    db.add(db_conversation)
    await db.commit()
    await db.refresh(db_conversation)
    return db_conversation


async def get_conversation(db: AsyncSession, conversation_id: int) -> Optional[Conversation]:
    """
    Get a conversation by ID.
    """
    result = await db.execute(
        select(Conversation)
        .filter(Conversation.id == conversation_id)
        .options(selectinload(Conversation.messages))
    )
    return result.scalars().first()


async def get_user_conversations(
    db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
) -> List[Conversation]:
    """
    Get conversations for a user.
    """
    result = await db.execute(
        select(Conversation)
        .filter(Conversation.user_id == user_id)
        .options(selectinload(Conversation.messages))
        .offset(skip)
        .limit(limit)
        .order_by(Conversation.updated_at.desc())
    )
    return result.scalars().all()


async def update_conversation(
    db: AsyncSession, conversation_id: int, conversation_in: ConversationUpdate
) -> Optional[Conversation]:
    """
    Update a conversation.
    """
    conversation = await get_conversation(db, conversation_id)
    if not conversation:
        return None
    
    update_data = conversation_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(conversation, field, value)
    
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def delete_conversation(db: AsyncSession, conversation_id: int) -> bool:
    """
    Delete a conversation.
    """
    await db.execute(delete(Conversation).where(Conversation.id == conversation_id))
    await db.commit()
    return True
