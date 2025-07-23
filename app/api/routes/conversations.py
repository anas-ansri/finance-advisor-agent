from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.conversation import Conversation, ConversationCreate, ConversationUpdate
from app.schemas.message import ChatMessage, ChatRequest, ChatResponse
from app.services.conversation import (
    create_conversation,
    delete_conversation,
    get_conversation,
    get_user_conversations,
    update_conversation,
)
from app.services.message import add_message_to_conversation, get_conversation_messages
from app.services.ai import generate_ai_response

router = APIRouter()


@router.post("", response_model=Conversation)
async def create_new_conversation(
    conversation_in: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Create a new conversation.
    """
    conversation = await create_conversation(db, user_id=current_user.id, conversation_in=conversation_in)
    return conversation


@router.get("", response_model=List[Conversation])
async def read_conversations(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Retrieve conversations.
    """
    conversations = await get_user_conversations(db, user_id=current_user.id, skip=skip, limit=limit)
    return conversations


@router.get("/{conversation_id}", response_model=Conversation)
async def read_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get a specific conversation by id.
    """
    conversation = await get_conversation(db, conversation_id=conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return conversation


@router.put("/{conversation_id}", response_model=Conversation)
async def update_conversation_title(
    conversation_id: int,
    conversation_in: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Update a conversation title.
    """
    conversation = await get_conversation(db, conversation_id=conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    conversation = await update_conversation(db, conversation_id=conversation_id, conversation_in=conversation_in)
    return conversation


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation_by_id(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Delete a conversation.
    """
    conversation = await get_conversation(db, conversation_id=conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    await delete_conversation(db, conversation_id=conversation_id)


@router.get("/{conversation_id}/messages", response_model=List[ChatMessage])
async def read_conversation_messages(
    conversation_id: int,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get messages for a specific conversation.
    """
    conversation = await get_conversation(db, conversation_id=conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    messages = await get_conversation_messages(db, conversation_id=conversation_id, skip=skip, limit=limit)
    return messages


@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(
    chat_request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Chat with AI and get a response.
    
    If conversation_id is provided, the message will be added to that conversation.
    Otherwise, a new conversation will be created.
    """
    conversation_id = chat_request.conversation_id
    
    # Check if conversation exists and belongs to user
    if conversation_id:
        conversation = await get_conversation(db, conversation_id=conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conversation.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not enough permissions")
    else:
        # Create a new conversation
        title = chat_request.messages[0].content[:50] + "..." if len(chat_request.messages[0].content) > 50 else chat_request.messages[0].content
        conversation = await create_conversation(
            db,
            user_id=current_user.id,
            conversation_in=ConversationCreate(title=title)
        )
        conversation_id = conversation.id
    
    # Add user message to conversation
    user_message = chat_request.messages[-1]
    await add_message_to_conversation(
        db,
        conversation_id=conversation_id,
        role=user_message.role,
        content=user_message.content
    )
    
    # Generate AI response
    ai_response = await generate_ai_response(
        db,
        user_id=current_user.id,
        conversation_id=conversation_id,
        messages=chat_request.messages,
        model_id=chat_request.model_id,
        temperature=chat_request.temperature,
        max_tokens=chat_request.max_tokens,
        use_persona=chat_request.use_persona
    )
    
    # Add AI response to conversation
    await add_message_to_conversation(
        db,
        conversation_id=conversation_id,
        role="assistant",
        content=ai_response
    )
    
    return ChatResponse(
        conversation_id=conversation_id,
        message=ChatMessage(role="assistant", content=ai_response)
    )
