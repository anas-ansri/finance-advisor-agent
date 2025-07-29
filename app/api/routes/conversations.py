from typing import Any, List, Optional
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
import asyncio
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
from app.services.ai import generate_ai_response, generate_ai_streaming_response

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/persona-status")
async def get_persona_status(
    auto_generate: bool = Query(False, description="Automatically generate persona if not found"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Check if user has an existing persona profile and return rich persona information.
    Optionally auto-generate persona if not found.
    """
    try:
        from app.services.persona_engine import PersonaEngineService
        persona_service = PersonaEngineService(db)
        
        persona_profile = await persona_service.get_existing_persona_for_user(current_user)
        
        # If no persona and auto_generate is True, try to generate one
        if not persona_profile and auto_generate:
            logger.info(f"Auto-generating persona for user {current_user.id}")
            try:
                persona_profile = await persona_service.generate_persona_for_user(
                    current_user, 
                    force_regenerate=False
                )
            except Exception as gen_error:
                logger.warning(f"Auto-generation failed for user {current_user.id}: {str(gen_error)}")
                # Continue to return no-persona response
        
        if persona_profile:
            cultural_profile = {}
            if hasattr(persona_profile, 'cultural_profile') and persona_profile.cultural_profile:
                cultural_profile = persona_profile.cultural_profile
            
            return {
                "has_persona": True,
                "persona": {
                    "persona_name": persona_profile.persona_name,
                    "persona_description": persona_profile.persona_description,
                    "key_traits": persona_profile.key_traits or [],
                    "lifestyle_summary": persona_profile.lifestyle_summary,
                    "financial_tendencies": persona_profile.financial_tendencies,
                    "cultural_profile": cultural_profile,
                    "financial_advice_style": getattr(persona_profile, 'financial_advice_style', None),
                    "created_at": persona_profile.created_at.isoformat() if persona_profile.created_at else None,
                    "updated_at": persona_profile.updated_at.isoformat() if persona_profile.updated_at else None
                },
                "message": "Persona profile loaded successfully"
            }
        else:
            # Check if user has transaction data for helpful messaging
            transaction_count = await persona_service._get_transaction_count(current_user.id)
            
            if transaction_count == 0:
                message = "No transaction data found. Please connect your bank account or add some transactions to generate a persona."
            elif transaction_count < 10:
                message = f"Found {transaction_count} transactions. Add more transaction data for a richer persona profile."
            else:
                message = f"Found {transaction_count} transactions. Click 'Generate My Persona' to create your financial personality profile."
            
            return {
                "has_persona": False,
                "transaction_count": transaction_count,
                "message": message,
                "can_generate": transaction_count >= 5  # Minimum transactions needed
            }
    except Exception as e:
        logger.error(f"Error checking persona status: {str(e)}")
        return {
            "has_persona": False,
            "error": "Unable to check persona status",
            "message": "There was an error checking your persona. Please try again later.",
            "can_generate": False
        }


@router.post("/generate-persona")
async def generate_persona_for_user(
    force_regenerate: bool = Query(False, description="Force regenerate even if persona exists"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate or regenerate persona for the user.
    This can be called separately to generate persona without needing a conversation.
    """
    try:
        from app.services.persona_engine import PersonaEngineService
        persona_service = PersonaEngineService(db)
        
        # Check if user already has a persona and force_regenerate is False
        if not force_regenerate:
            existing_persona = await persona_service.get_existing_persona_for_user(current_user)
            if existing_persona:
                cultural_profile = {}
                if hasattr(existing_persona, 'cultural_profile') and existing_persona.cultural_profile:
                    cultural_profile = existing_persona.cultural_profile
                    
                return {
                    "success": True,
                    "message": "Using existing persona profile",
                    "persona": {
                        "persona_name": existing_persona.persona_name,
                        "persona_description": existing_persona.persona_description,
                        "key_traits": existing_persona.key_traits or [],
                        "lifestyle_summary": existing_persona.lifestyle_summary,
                        "financial_tendencies": existing_persona.financial_tendencies,
                        "cultural_profile": cultural_profile,
                        "financial_advice_style": getattr(existing_persona, 'financial_advice_style', None),
                        "created_at": existing_persona.created_at.isoformat() if existing_persona.created_at else None,
                        "updated_at": existing_persona.updated_at.isoformat() if existing_persona.updated_at else None
                    }
                }
        
        # Check if user has sufficient transaction data
        transaction_count = await persona_service._get_transaction_count(current_user.id)
        if transaction_count < 5:
            return {
                "success": False,
                "message": f"Need at least 5 transactions to generate a persona. Found {transaction_count}. Please add more transaction data.",
                "transaction_count": transaction_count,
                "error_type": "insufficient_data"
            }
        
        # Generate persona
        logger.info(f"Generating persona for user {current_user.id} with {transaction_count} transactions")
        persona_profile = await persona_service.generate_persona_for_user(
            current_user, 
            force_regenerate=True
        )
        
        if persona_profile:
            cultural_profile = {}
            if hasattr(persona_profile, 'cultural_profile') and persona_profile.cultural_profile:
                cultural_profile = persona_profile.cultural_profile
                
            return {
                "success": True,
                "message": "Persona generated successfully",
                "persona": {
                    "persona_name": persona_profile.persona_name,
                    "persona_description": persona_profile.persona_description,
                    "key_traits": persona_profile.key_traits or [],
                    "lifestyle_summary": persona_profile.lifestyle_summary,
                    "financial_tendencies": persona_profile.financial_tendencies,
                    "cultural_profile": cultural_profile,
                    "financial_advice_style": getattr(persona_profile, 'financial_advice_style', None),
                    "created_at": persona_profile.created_at.isoformat() if persona_profile.created_at else None,
                    "updated_at": persona_profile.updated_at.isoformat() if persona_profile.updated_at else None
                }
            }
        else:
            return {
                "success": False,
                "message": "Failed to generate persona. This could be due to insufficient transaction variety or API limitations.",
                "error_type": "generation_failed",
                "transaction_count": transaction_count
            }
    except Exception as e:
        logger.error(f"Error generating persona for user {current_user.id}: {str(e)}")
        return {
            "success": False,
            "message": f"An error occurred while generating your persona: {str(e)}",
            "error_type": "system_error"
        }


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
    conversation_id: UUID,
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
    conversation_id: UUID,
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
    conversation_id: UUID,
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



# Streaming generator for AI response
async def ai_response_streamer(db, user_id, conversation_id, messages, model_id, temperature, max_tokens, use_persona):
    """
    Stream AI response using Gemini's streaming API for real-time response.
    """
    print("Starting AI streaming response...")
    
    try:
        # Use the new streaming AI response function
        async for chunk in generate_ai_streaming_response(
            db,
            user_id=user_id,
            conversation_id=conversation_id,
            messages=messages,
            model_id=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            use_persona=use_persona
        ):
            yield chunk
    except Exception as e:
        logger.error(f"Error in AI streaming: {str(e)}")
        yield f"Error: {str(e)}"

@router.post("/chat")
async def chat_with_ai(
    chat_request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Chat with AI and get a response.
    If conversation_id is provided, the message will be added to that conversation.
    Otherwise, a new conversation will be created.
    If stream=True, response will be streamed as plain text.
    """
    conversation_id = chat_request.conversation_id
    print(f"Chat request: {chat_request}")
    
    # Prepare messages for AI - include conversation history if conversation exists
    ai_messages = chat_request.messages.copy()
    
    # Check if conversation exists and belongs to user
    if conversation_id:
        conversation = await get_conversation(db, conversation_id=conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conversation.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        
        # Get existing conversation history and merge with new messages
        # Only include history if the request doesn't already contain full history
        if len(chat_request.messages) == 1:  # Only current message sent
            existing_messages = await get_conversation_messages(db, conversation_id=conversation_id)
            ai_messages = existing_messages + chat_request.messages
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
    logger.info(f"Messages being sent to AI (count: {len(ai_messages)}): {[f'{m.role}: {m.content[:50]}...' for m in ai_messages]}")
    await add_message_to_conversation(
        db,
        conversation_id=conversation_id,
        role=user_message.role,
        content=user_message.content
    )
    if chat_request.stream:
        # For streaming, we need to collect the full response and save it after streaming
        collected_response = []
        
        async def stream_and_collect():
            async for chunk in ai_response_streamer(
                db,
                user_id=current_user.id,
                conversation_id=conversation_id,
                messages=ai_messages,
                model_id=chat_request.model_id,
                temperature=chat_request.temperature,
                max_tokens=chat_request.max_tokens,
                use_persona=chat_request.use_persona
            ):
                collected_response.append(chunk)
                yield chunk
            
            # Save the complete response to the conversation after streaming
            full_response = "".join(collected_response)
            try:
                await add_message_to_conversation(
                    db,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_response
                )
            except Exception as e:
                logger.error(f"Error saving streamed response to conversation: {str(e)}")
        
        # Stream the AI response as plain text with conversation ID in headers
        response = StreamingResponse(
            stream_and_collect(),
            media_type="text/plain"
        )
        # Add conversation ID to response headers so frontend can access it
        response.headers["X-Conversation-ID"] = str(conversation_id)
        return response
    else:
        # Generate AI response as before
        ai_response = await generate_ai_response(
            db,
            user_id=current_user.id,
            conversation_id=conversation_id,
            messages=ai_messages,
            model_id=chat_request.model_id,
            temperature=chat_request.temperature,
            max_tokens=chat_request.max_tokens,
            use_persona=chat_request.use_persona
        )
        await add_message_to_conversation(
            db,
            conversation_id=conversation_id,
            role="assistant",
            content=ai_response
        )
        return {
            "conversation_id": conversation_id,
            "message": {"role": "assistant", "content": ai_response}
        }


@router.post("/{conversation_id}/generate-persona")
async def generate_persona_for_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate or regenerate persona for the user.
    This can be called separately to pre-generate persona without affecting chat performance.
    """
    # Check if conversation exists and belongs to user
    conversation = await get_conversation(db, conversation_id=conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    try:
        from app.services.persona_engine import PersonaEngineService
        persona_service = PersonaEngineService(db)
        
        # Force regenerate persona
        persona_profile = await persona_service.generate_persona_for_user(
            current_user, 
            force_regenerate=True
        )
        
        if persona_profile:
            return {
                "success": True,
                "message": "Persona generated successfully",
                "persona_name": persona_profile.persona_name
            }
        else:
            return {
                "success": False,
                "message": "Failed to generate persona. Please ensure you have sufficient transaction data."
            }
    except Exception as e:
        logger.error(f"Error generating persona: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error generating persona: {str(e)}"
        )
