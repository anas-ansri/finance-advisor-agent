from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Message
from app.schemas.message import ChatMessage


async def add_message_to_conversation(
    db: AsyncSession, conversation_id: int, role: str, content: str
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
    db: AsyncSession, conversation_id: int, skip: int = 0, limit: int = 100
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
