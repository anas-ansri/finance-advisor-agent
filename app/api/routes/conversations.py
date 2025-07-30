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
from app.services.ai import generate_ai_response, generate_openai_streaming_response

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
    request: Optional[dict] = None,
    force_regenerate: bool = Query(False, description="Force regenerate even if persona exists"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate or regenerate persona for the user.
    Accepts optional user preferences for customization.
    """
    try:
        from app.services.persona_engine import PersonaEngineService
        from app.schemas.persona import UserPreferences
        
        persona_service = PersonaEngineService(db)
        
        # Parse user preferences if provided
        user_preferences = None
        if request and 'user_preferences' in request:
            try:
                user_preferences = UserPreferences(**request['user_preferences'])
                logger.info(f"Received user preferences for user {current_user.id}: {user_preferences}")
            except Exception as e:
                logger.warning(f"Failed to parse user preferences: {str(e)}")
        
        # Check if user already has a persona and force_regenerate is False
        if not force_regenerate and not user_preferences:
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
        
        # Check if user has sufficient transaction data (unless using custom preferences)
        transaction_count = await persona_service._get_transaction_count(current_user.id)
        if transaction_count < 5 and not user_preferences:
            return {
                "success": False,
                "message": f"Need at least 5 transactions to generate a persona. Found {transaction_count}. Please add more transaction data or use custom preferences.",
                "transaction_count": transaction_count,
                "error_type": "insufficient_data"
            }
        
        # Generate persona with optional user preferences
        logger.info(f"Generating persona for user {current_user.id} with {transaction_count} transactions" + 
                   (f" and custom preferences" if user_preferences else ""))
        
        persona_profile = await persona_service.generate_persona_for_user(
            current_user, 
            force_regenerate=True,
            user_preferences=user_preferences
        )
        
        if persona_profile:
            cultural_profile = {}
            if hasattr(persona_profile, 'cultural_profile') and persona_profile.cultural_profile:
                cultural_profile = persona_profile.cultural_profile
                
            return {
                "success": True,
                "message": "Persona generated successfully" + (" with custom preferences" if user_preferences else ""),
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
async def ai_response_streamer(user_data, persona_data, messages, model_id, temperature, max_tokens, use_persona):
    """
    Stream AI response using OpenAI's streaming API for real-time response.
    This function doesn't use database connections to avoid connection leaks.
    """
    print("Starting AI streaming response...")
    
    try:
        # Build system prompt based on pre-loaded user and persona data
        if use_persona and persona_data:
            # Use persona-enhanced prompt
            cultural_context = ""
            if persona_data.get('cultural_profile'):
                cultural_context = f"""
Cultural Context:
- Music Taste: {persona_data['cultural_profile'].get('music_taste', 'Not specified')}
- Entertainment Style: {persona_data['cultural_profile'].get('entertainment_style', 'Not specified')}
- Fashion Sensibility: {persona_data['cultural_profile'].get('fashion_sensibility', 'Not specified')}
- Dining Philosophy: {persona_data['cultural_profile'].get('dining_philosophy', 'Not specified')}"""
            
            advice_style = ""
            if persona_data.get('financial_advice_style'):
                advice_style = f"\nAdvice Style: {persona_data['financial_advice_style']}"
            
            persona_system_prompt = f"""You are a deeply personalized AI financial advisor responding to {user_data['name']}. Use their name naturally in conversation.

{user_data['profile_context']}

PERSONA: {persona_data['persona_name']}

DESCRIPTION: {persona_data['persona_description']}

KEY TRAITS: {', '.join(persona_data.get('key_traits', []))}

LIFESTYLE: {persona_data.get('lifestyle_summary', '')}

FINANCIAL TENDENCIES: {persona_data.get('financial_tendencies', '')}
{cultural_context}
{advice_style}

IMPORTANT INSTRUCTIONS:
1. Address the user by name ({user_data['name']}) naturally in conversation
2. Respond as if you truly understand this person's values, lifestyle, and cultural preferences
3. Reference their specific traits and interests when relevant to financial advice
4. Use language and examples that resonate with their cultural context
5. Make recommendations that align with their lifestyle and values
6. Acknowledge their unique perspective on money and spending
7. Be supportive and understanding of their financial journey

When providing advice, consider how their cultural interests and lifestyle choices influence their financial priorities. Make connections between their spending patterns and their identity when appropriate."""
            
            messages = [ChatMessage(role="system", content=persona_system_prompt)] + messages
        else:
            # Use basic user profile prompt
            basic_system_prompt = f"""You are a helpful AI financial advisor for {user_data['name']}. Use their name naturally in conversation.

{user_data['profile_context']}

INSTRUCTIONS:
1. Address the user by name ({user_data['name']}) naturally in conversation
2. Provide personalized financial advice based on their profile information
3. Be supportive, understanding, and professional
4. Ask clarifying questions when you need more information
5. Tailor your advice to their financial goals and risk tolerance"""
            
            messages = [ChatMessage(role="system", content=basic_system_prompt)] + messages
        
        # Compose prompt from messages
        prompt = "\n".join([f"{m.role}: {m.content}" for m in messages])
        
        # Stream the response using OpenAI
        async for chunk in generate_openai_streaming_response(prompt):
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
    Chat with AI and get a response with MCP financial context integration.
    If conversation_id is provided, the message will be added to that conversation.
    Otherwise, a new conversation will be created.
    If stream=True, response will be streamed as plain text.
    """
    conversation_id = chat_request.conversation_id
    print(f"Chat request: {chat_request}")
    
    # Try MCP-enhanced AI service first
    try:
        from app.services.mcp_ai_integration import mcp_ai_service
        
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
        logger.info(f"Messages being sent to MCP-enhanced AI (count: {len(ai_messages)}): {[f'{m.role}: {m.content[:50]}...' for m in ai_messages]}")
        await add_message_to_conversation(
            db,
            conversation_id=conversation_id,
            role=user_message.role,
            content=user_message.content
        )
        
        if chat_request.stream:
            # Use MCP-enhanced streaming
            collected_response = []
            
            async def mcp_stream_and_collect():
                async for chunk in mcp_ai_service.stream_enhanced_response(
                    db,
                    current_user.id,
                    ai_messages,
                    chat_request.use_persona,
                    chat_request.model_id,
                    chat_request.temperature,
                    chat_request.max_tokens
                ):
                    collected_response.append(chunk)
                    yield chunk
                
                # Save AI response after streaming completes
                full_response = "".join(collected_response)
                from app.db.database import async_session_factory
                async with async_session_factory() as save_db:
                    await add_message_to_conversation(
                        save_db,
                        conversation_id=conversation_id,
                        role="assistant",
                        content=full_response
                    )
                    await save_db.commit()
            
            return StreamingResponse(
                mcp_stream_and_collect(),
                media_type="text/plain",
                headers={"X-Conversation-ID": str(conversation_id)}
            )
        else:
            # Non-streaming MCP-enhanced response
            ai_response = await mcp_ai_service.generate_enhanced_response(
                db,
                current_user.id,
                ai_messages,
                chat_request.use_persona,
                chat_request.model_id,
                chat_request.temperature,
                chat_request.max_tokens
            )
            
            # Add AI response to conversation
            await add_message_to_conversation(
                db,
                conversation_id=conversation_id,
                role="assistant",
                content=ai_response
            )
            
            return {
                "conversation_id": conversation_id,
                "response": ai_response,
                "enhanced_with_mcp": True
            }
    
    except Exception as mcp_error:
        logger.warning(f"MCP-enhanced AI failed, falling back to original: {mcp_error}")
        
        # Fallback to original implementation
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
        # Prepare user and persona data before streaming to avoid database connection issues
        
        # Prepare user profile data
        user_name = ""
        if current_user.first_name:
            user_name = current_user.first_name
        elif current_user.email:
            user_name = current_user.email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
        
        user_profile_context = f"""
USER PROFILE:
- Name: {user_name or 'User'}
- Email: {current_user.email}"""
        
        if current_user.monthly_income:
            user_profile_context += f"\n- Monthly Income: {current_user.monthly_income}"
        if current_user.employment_status:
            user_profile_context += f"\n- Employment Status: {current_user.employment_status}"
        if current_user.primary_financial_goal:
            user_profile_context += f"\n- Primary Financial Goal: {current_user.primary_financial_goal}"
        if current_user.risk_tolerance:
            user_profile_context += f"\n- Risk Tolerance: {current_user.risk_tolerance}"
        
        user_data = {
            'name': user_name or 'User',
            'profile_context': user_profile_context
        }
        
        # Prepare persona data if needed
        persona_data = None
        if chat_request.use_persona:
            from app.services.persona_engine import PersonaEngineService
            persona_service = PersonaEngineService(db)
            persona_profile = await persona_service.get_existing_persona_for_user(current_user)
            if persona_profile:
                persona_data = {
                    'persona_name': persona_profile.persona_name,
                    'persona_description': persona_profile.persona_description,
                    'key_traits': persona_profile.key_traits or [],
                    'lifestyle_summary': persona_profile.lifestyle_summary,
                    'financial_tendencies': persona_profile.financial_tendencies,
                    'cultural_profile': persona_profile.cultural_profile if hasattr(persona_profile, 'cultural_profile') else {},
                    'financial_advice_style': getattr(persona_profile, 'financial_advice_style', None)
                }
        
        # For streaming, we need to collect the full response and save it after streaming
        collected_response = []
        
        async def stream_and_collect():
            async for chunk in ai_response_streamer(
                user_data,
                persona_data,
                ai_messages,
                chat_request.model_id,
                chat_request.temperature,
                chat_request.max_tokens,
                chat_request.use_persona
            ):
                collected_response.append(chunk)
                yield chunk
            
            # Save the complete response to the conversation after streaming
            full_response = "".join(collected_response)
            try:
                # Create a new database session for saving the response
                from app.db.database import async_session_factory
                async with async_session_factory() as session:
                    await add_message_to_conversation(
                        session,
                        conversation_id=conversation_id,
                        role="assistant",
                        content=full_response
                    )
                    await session.commit()
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
