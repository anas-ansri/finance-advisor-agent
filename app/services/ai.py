import logging
from typing import List, Optional

import openai
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.schemas.message import ChatMessage
from app.services.ai_model import get_ai_model
from app.services.ai_preference import get_ai_preference_by_user_id

logger = logging.getLogger(__name__)


async def generate_ai_response(
    db: AsyncSession,
    user_id: int,
    conversation_id: int,
    messages: List[ChatMessage],
    model_id: Optional[int] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """
    Generate a response from an AI model.
    
    Args:
        db: Database session
        user_id: User ID
        conversation_id: Conversation ID
        messages: List of messages in the conversation
        model_id: ID of the AI model to use (optional)
        temperature: Temperature parameter for generation (optional)
        max_tokens: Maximum tokens to generate (optional)
        
    Returns:
        Generated response text
    """
    try:
        # Get user preferences
        user_preferences = await get_ai_preference_by_user_id(db, user_id=user_id)
        
        # Determine which model to use
        model_to_use = None
        if model_id:
            model_to_use = await get_ai_model(db, model_id=model_id)
        elif user_preferences and user_preferences.preferred_model_id:
            model_to_use = await get_ai_model(db, model_id=user_preferences.preferred_model_id)
        
        # If no model is specified, use the default
        if not model_to_use:
            # Use default OpenAI model
            model_provider = "openai"
            model_id_str = settings.DEFAULT_MODEL
        else:
            model_provider = model_to_use.provider
            model_id_str = model_to_use.model_id
        
        # Determine temperature
        if temperature is not None:
            temp_to_use = temperature
        elif user_preferences and user_preferences.temperature is not None:
            temp_to_use = float(user_preferences.temperature)
        elif model_to_use and model_to_use.temperature is not None:
            temp_to_use = model_to_use.temperature
        else:
            temp_to_use = 0.7  # Default temperature
        
        # Determine max tokens
        if max_tokens is not None:
            max_tokens_to_use = max_tokens
        elif model_to_use and model_to_use.max_tokens is not None:
            max_tokens_to_use = model_to_use.max_tokens
        else:
            max_tokens_to_use = None  # Let the API decide
        
        # Add system prompt if available and not already present
        if user_preferences and user_preferences.system_prompt and not any(m.role == "system" for m in messages):
            messages = [ChatMessage(role="system", content=user_preferences.system_prompt)] + messages
        
        # Format messages for the API
        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]
        
        # Generate response based on provider
        if model_provider == "openai":
            return await generate_openai_response(
                formatted_messages,
                model_id_str,
                temp_to_use,
                max_tokens_to_use
            )
        elif model_provider == "anthropic":
            # Implement Anthropic API integration
            raise NotImplementedError("Anthropic API integration not implemented yet")
        elif model_provider == "local":
            # Implement local model integration
            raise NotImplementedError("Local model integration not implemented yet")
        else:
            raise ValueError(f"Unsupported model provider: {model_provider}")
    
    except Exception as e:
        logger.exception(f"Error generating AI response: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating AI response: {str(e)}")


async def generate_openai_response(
    messages: List[dict],
    model: str,
    temperature: float,
    max_tokens: Optional[int] = None,
) -> str:
    """
    Generate a response using the OpenAI API.
    """
    try:
        # Set API key
        openai.api_key = settings.OPENAI_API_KEY
        
        # Prepare request parameters
        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        
        if max_tokens:
            params["max_tokens"] = max_tokens
        
        # Make API request
        response = await openai.ChatCompletion.acreate(**params)
        
        # Extract and return the generated text
        return response.choices[0].message.content
    
    except Exception as e:
        logger.exception(f"OpenAI API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")
