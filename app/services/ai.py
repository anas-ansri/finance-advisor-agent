import logging
from typing import List, Optional
from uuid import UUID

from openai import AsyncOpenAI
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.schemas.message import ChatMessage
from app.services.ai_model import get_ai_model
from app.services.ai_preference import get_ai_preference_by_user_id
from app.services.financial_advisor import FinancialAdvisor
from app.services.user import get_user
from app.models.ai_insight import AIInsight
from app.schemas.ai_insight import AIInsightCreate
from app.services.transaction import get_all_transactions
from app.models.bank_transaction import BankTransaction

logger = logging.getLogger(__name__)

async def generate_ai_response(
    db: AsyncSession,
    user_id: UUID,
    conversation_id: UUID,
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
        # Get user and check API key
        user = await get_user(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not user.openai_api_key:
            raise HTTPException(
                status_code=400,
                detail="OpenAI API key not set. Please set your API key in your profile settings."
            )
        
        # Get user preferences
        user_preferences = await get_ai_preference_by_user_id(db, user_id=user_id)
        
        # Get the latest user message
        latest_user_message = next((m for m in reversed(messages) if m.role == "user"), None)
        if not latest_user_message:
            raise ValueError("No user message found in the conversation")
        
        # Check if this is a financial query
        is_financial_query = any(keyword in latest_user_message.content.lower() for keyword in [
            "money", "finance", "budget", "expense", "income", "saving", "investment",
            "spending", "cost", "price", "salary", "wage", "debt", "loan", "credit",
            "bank", "account", "transaction", "balance", "wealth", "asset", "liability",
            "cash", "payment", "bill", "tax", "interest", "profit", "loss", "revenue",
            "expense", "financial", "monetary", "economic", "fiscal", "budgetary"
        ])
        
        if is_financial_query:
            # Use financial advisor for financial queries
            advisor = FinancialAdvisor(user.openai_api_key)
            return await advisor.get_advice(
                db=db,
                user_id=user_id,
                conversation_id=conversation_id,
                query=latest_user_message.content
            )
        
        # For non-financial queries, use the regular AI model
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
                max_tokens_to_use,
                user.openai_api_key
            )
        elif model_provider == "anthropic":
            if not user.anthropic_api_key:
                raise HTTPException(
                    status_code=400,
                    detail="Anthropic API key not set. Please set your API key in your profile settings."
                )
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
    api_key: str = None,
) -> str:
    """
    Generate a response using the OpenAI API.
    """
    try:
        # Initialize OpenAI client
        client = AsyncOpenAI(api_key=api_key)
        
        # Prepare request parameters
        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        
        if max_tokens:
            params["max_tokens"] = max_tokens
        
        # Make API request
        response = await client.chat.completions.create(**params)
        
        # Extract and return the generated text
        return response.choices[0].message.content
    
    except Exception as e:
        logger.exception(f"OpenAI API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")

async def generate_financial_insights(
    db: AsyncSession,
    user_id: UUID,
    # Optional: provide the new statement ID if insights should focus on it
    # new_statement_id: Optional[UUID] = None
):
    """Generates AI-powered financial insights for the user."""
    print(f"Generating insights for user: {user_id}")

    # Fetch all transactions for the user
    transactions: List[BankTransaction] = await get_all_transactions(db, user_id)
    print(f"Fetched {len(transactions)} transactions for insight generation.")

    # TODO: Process transactions and generate insights using an AI model
    # This is where you would integrate your AI model logic.
    # Example structure for processing:
    # - Analyze spending patterns (e.g., identify unusual spending, subscriptions)
    # - Identify savings opportunities
    # - Generate financial recommendations (e.g., budget, debt repayment, retirement)
    # - Format the AI response into AIInsightCreate objects

    # For now, keeping the simulated insights for demonstration
    simulated_insights = [
        AIInsightCreate(title="Unusual Spending", description="Your restaurant spending was 35% higher than your monthly average. Consider setting a dining budget.", category="spending"),
        AIInsightCreate(title="Subscription Audit", description="You have 8 active subscriptions totaling $92.45/month. 3 haven't been used in 30 days.", category="spending"),
        AIInsightCreate(title="Savings Opportunity", description="Switching to a different cell phone plan could save you $25/month based on your usage patterns.", category="spending"),
        AIInsightCreate(title="Emergency Fund", description="Based on your monthly expenses, aim for $12,000 in your emergency fund. You're currently at 54%.", category="recommendation"),
        AIInsightCreate(title="Debt Repayment", description="Paying an extra $200/month toward your highest interest credit card would save $340 in interest.", category="recommendation"),
        AIInsightCreate(title="Retirement Savings", description="Increasing your 401(k) contribution by 2% would significantly improve your retirement outlook.", category="recommendation"),
    ]

    # Clear existing insights for simplicity in this example (in a real app, you'd update/add)
    # await db.execute(delete(AIInsight).where(AIInsight.user_id == user_id))

    # Save generated (or simulated) insights to the database
    db_insights = [
        AIInsight(user_id=user_id, title=insight.title, description=insight.description, category=insight.category)
        for insight in simulated_insights
    ]

    # Clear existing insights before adding new ones (optional, depends on desired behavior)
    # await db.execute(delete(AIInsight).where(AIInsight.user_id == user_id))

    db.add_all(db_insights)
    await db.commit()

    print(f"Saved {len(db_insights)} insights for user {user_id}.")
