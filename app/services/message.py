from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Message
from app.schemas.message import ChatMessage, MessageCreate


async def create_message(
    db: AsyncSession,
    conversation_id: UUID,
    message_in: MessageCreate
) -> Message:
    """
    Create a new message in a conversation.
    """
    db_message = Message(
        conversation_id=conversation_id,
        role=message_in.role,
        content=message_in.content,
    )
    db.add(db_message)
    await db.commit()
    await db.refresh(db_message)
    return db_message


async def add_message_to_conversation(
    db: AsyncSession, conversation_id: UUID, role: str, content: str
) -> Message:
    """
    Add a message to a conversation.
    """
    db_message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
    )
    db.add(db_message)
    await db.commit()
    await db.refresh(db_message)
    return db_message


async def get_conversation_messages(
    db: AsyncSession, conversation_id: UUID, skip: int = 0, limit: int = 100
) -> List[ChatMessage]:
    """
    Get messages for a conversation.
    """
    result = await db.execute(
        select(Message)
        .filter(Message.conversation_id == conversation_id)
        .offset(skip)
        .limit(limit)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    
    return [
        ChatMessage(role=message.role, content=message.content)
        for message in messages
    ]
