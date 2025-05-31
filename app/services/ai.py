import logging
from typing import List, Optional
from uuid import UUID
import json
import pandas as pd
from sqlalchemy import delete, text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from openai import AsyncOpenAI
from fastapi import HTTPException

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

    # Fetch all transactions for the user with category eagerly loaded
    stmt = select(BankTransaction).options(
        joinedload(BankTransaction.category)
    ).where(BankTransaction.user_id == user_id)
    result = await db.execute(stmt)
    transactions = result.scalars().all()
    print(f"Fetched {len(transactions)} transactions for insight generation.")

    # Fetch user's financial goals
    goals_result = await db.execute(
        text("SELECT * FROM financial_goals WHERE user_id = :user_id"),
        {"user_id": user_id},
    )
    goals = goals_result.fetchall()
    
    # Convert transactions to DataFrame for analysis
    df = pd.DataFrame([{
        'date': t.date,
        'amount': t.amount,
        'description': t.description,
        'category': str(t.category.name) if t.category else 'Uncategorized'
    } for t in transactions])
    
    # Initialize OpenAI client
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    # Prepare data summary for AI analysis
    data_summary = f"""
Financial Data Summary:
- Total Transactions: {len(df)}
- Total Income: ₹{df[df['amount'] > 0]['amount'].sum():,.2f}
- Total Expenses: ₹{abs(df[df['amount'] < 0]['amount'].sum()):,.2f}
- Net Savings: ₹{(df[df['amount'] > 0]['amount'].sum() - abs(df[df['amount'] < 0]['amount'].sum())):,.2f}

Expense Categories:
{df[df['amount'] < 0].groupby('category')['amount'].sum().abs().sort_values(ascending=False).to_string()}

Financial Goals:
{chr(10).join([f"- {g.name}: Current: ₹{g.current:,.2f} / Target: ₹{g.target:,.2f} ({g.current/g.target*100:.1f}%)" for g in goals])}
"""
    
    # Generate insights using AI
    prompt = f"""As a financial advisor AI, analyze the following financial data and generate personalized insights. 
Focus on:
1. Progress towards financial goals
2. Spending patterns and optimization opportunities
3. Savings and investment recommendations
4. Risk assessment and mitigation strategies
5. Actionable next steps

Financial Data:
{data_summary}

Generate 5-7 specific, actionable insights that are personalized to this user's situation and goals.
You must respond with a valid JSON array of objects. Each object must have these exact fields:
- title: string
- description: string
- category: string (one of: "spending", "recommendation")
- priority: number (1-5, where 5 is highest)

Example response format:
[
    {
        "title": "Reduce Dining Out Expenses",
        "description": "Consider reducing dining out expenses by 20% to save ₹2,000 monthly.",
        "category": "spending",
        "priority": 4
    },
    {
        "title": "Increase Emergency Fund",
        "description": "Aim to increase your emergency fund to cover 6 months of expenses.",
        "category": "recommendation",
        "priority": 5
    }
]

Remember: Your response must be a valid JSON array containing only the specified fields."""

    try:
        response = await client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.2,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )

        print(f"AI response: {response.choices[0].message.content}")
        
        # Parse AI response into insights
        insights_text = response.choices[0].message.content
        try:
            insights_data = json.loads(insights_text)
            if not isinstance(insights_data, list):
                insights_data = [insights_data]  # Handle single object response
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from AI: {insights_text}")
            raise HTTPException(
                status_code=500,
                detail="Failed to generate valid insights format"
            )
        
        # Validate insight structure
        required_fields = {'title', 'description', 'category', 'priority'}
        valid_categories = {'spending', 'saving', 'investment', 'goal', 'risk', 'recommendation'}
        
        for insight in insights_data:
            if not all(field in insight for field in required_fields):
                raise HTTPException(
                    status_code=500,
                    detail="Invalid insight structure: missing required fields"
                )
            if insight['category'] not in valid_categories:
                raise HTTPException(
                    status_code=500,
                    detail=f"Invalid category: {insight['category']}"
                )
            if not isinstance(insight['priority'], int) or not 1 <= insight['priority'] <= 5:
                raise HTTPException(
                    status_code=500,
                    detail=f"Invalid priority: {insight['priority']}"
                )
        
        # Mark existing insights as inactive
        await db.execute(
            text("UPDATE ai_insights SET is_active = false WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        
        # Convert to AIInsight objects
        db_insights = [
            AIInsight(
                user_id=user_id,
                title=insight['title'],
                description=insight['description'],
                category=insight['category'],
                priority=insight['priority'],
                is_active=True,
                is_read=False
            )
            for insight in insights_data
        ]
        
        # Save new insights
        db.add_all(db_insights)
        await db.commit()
        
        print(f"Generated and saved {len(db_insights)} personalized insights for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error generating insights: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate financial insights: {str(e)}"
        )
