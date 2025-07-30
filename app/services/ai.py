import logging
from typing import List, Optional
from uuid import UUID
import json
import pandas as pd
from sqlalchemy import delete, text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser

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
import google.generativeai as genai

logger = logging.getLogger(__name__)

class FinancialInsight(BaseModel):
    """Model for a single financial insight."""
    title: str = Field(..., description="Clear, concise title for the insight")
    description: str = Field(..., description="Detailed explanation with specific numbers and actionable steps")
    category: str = Field(..., description="Category of the insight (spending or recommendation)")
    priority: int = Field(..., description="Priority level from 1-5, where 5 is highest")

class FinancialInsights(BaseModel):
    """Model for a list of financial insights."""
    insights: List[FinancialInsight] = Field(..., min_items=5, max_items=7, description="List of financial insights")

# Utility to call Gemini LLM
async def generate_gemini_response(prompt: str) -> str:
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        llm = genai.GenerativeModel('gemini-1.5-flash')
        response = llm.generate_content(prompt)
        response_text = response.text.strip().replace("```json", "").replace("```", "")
        return response_text
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        raise HTTPException(status_code=500, detail=f"Gemini API error: {e}")

# Streaming utility for Gemini LLM
async def generate_gemini_streaming_response(prompt: str):
    """
    Generate streaming response from Gemini LLM.
    """
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        llm = genai.GenerativeModel('gemini-1.5-flash')
        response = llm.generate_content(prompt, stream=True)
        
        for chunk in response:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        logger.error(f"Gemini streaming API error: {e}")
        yield f"Error: {str(e)}"

async def generate_ai_response(
    db: AsyncSession,
    user_id: UUID,
    conversation_id: UUID,
    messages: List[ChatMessage],
    model_id: Optional[int] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    use_persona: bool = False,
) -> str:
    """
    Generate a response from Gemini LLM.
    """
    try:
        user = await get_user(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Create basic user profile context that's always available
        user_name = ""
        if user.first_name:
            user_name = user.first_name
            if user.last_name:
                user_name += f" {user.last_name}"
        elif user.email:
            # Fallback to email username if no first name
            user_name = user.email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
        
        # Basic user profile context (always included)
        user_profile_context = f"""
USER PROFILE:
- Name: {user_name or 'User'}
- Email: {user.email}"""
        
        # Add additional profile information if available
        if user.monthly_income:
            user_profile_context += f"\n- Monthly Income: {user.monthly_income}"
        if user.employment_status:
            user_profile_context += f"\n- Employment Status: {user.employment_status}"
        if user.primary_financial_goal:
            user_profile_context += f"\n- Primary Financial Goal: {user.primary_financial_goal}"
        if user.risk_tolerance:
            user_profile_context += f"\n- Risk Tolerance: {user.risk_tolerance}"

        # Persona integration - enhanced with cultural context
        if use_persona:
            from app.services.persona_engine import PersonaEngineService
            persona_service = PersonaEngineService(db)
            # First try to get existing persona without regenerating
            persona_profile = await persona_service.get_existing_persona_for_user(user)
            if persona_profile:
                # Create a rich system prompt that incorporates the persona's cultural context
                cultural_context = ""
                if hasattr(persona_profile, 'cultural_profile') and persona_profile.cultural_profile:
                    cultural_context = f"""
Cultural Context:
- Music Taste: {persona_profile.cultural_profile.get('music_taste', 'Not specified')}
- Entertainment Style: {persona_profile.cultural_profile.get('entertainment_style', 'Not specified')}
- Fashion Sensibility: {persona_profile.cultural_profile.get('fashion_sensibility', 'Not specified')}
- Dining Philosophy: {persona_profile.cultural_profile.get('dining_philosophy', 'Not specified')}"""
                
                advice_style = ""
                if hasattr(persona_profile, 'financial_advice_style') and persona_profile.financial_advice_style:
                    advice_style = f"\nAdvice Style: {persona_profile.financial_advice_style}"
                
                persona_system_prompt = f"""You are a deeply personalized AI financial advisor responding to {user_name or 'the user'}. Use their name naturally in conversation.

{user_profile_context}

PERSONA: {persona_profile.persona_name}

DESCRIPTION: {persona_profile.persona_description}

KEY TRAITS: {', '.join(persona_profile.key_traits) if persona_profile.key_traits else 'To be determined'}

LIFESTYLE: {persona_profile.lifestyle_summary}

FINANCIAL TENDENCIES: {persona_profile.financial_tendencies}
{cultural_context}
{advice_style}

IMPORTANT INSTRUCTIONS:
1. Address the user by name ({user_name or 'their name'}) naturally in conversation
2. Respond as if you truly understand this person's values, lifestyle, and cultural preferences
3. Reference their specific traits and interests when relevant to financial advice
4. Use language and examples that resonate with their cultural context
5. Make recommendations that align with their lifestyle and values
6. Acknowledge their unique perspective on money and spending
7. Be supportive and understanding of their financial journey

When providing advice, consider how their cultural interests and lifestyle choices influence their financial priorities. Make connections between their spending patterns and their identity when appropriate."""
                
                messages = [ChatMessage(role="system", content=persona_system_prompt)] + messages
                logger.info(f"Using enhanced persona context for user {user_id}: {persona_profile.persona_name}")
            else:
                # Persona requested but not available - still use basic profile
                basic_system_prompt = f"""You are a helpful AI financial advisor for {user_name or 'the user'}. Use their name naturally in conversation.

{user_profile_context}

INSTRUCTIONS:
1. Address the user by name ({user_name or 'their name'}) naturally in conversation
2. Provide personalized financial advice based on their profile information
3. Be supportive, understanding, and professional
4. Ask clarifying questions when you need more information
5. Tailor your advice to their financial goals and risk tolerance"""
                
                messages = [ChatMessage(role="system", content=basic_system_prompt)] + messages
                logger.info(f"No persona found for user {user_id}, using basic profile context")
        else:
            # No persona requested - use basic user profile context
            basic_system_prompt = f"""You are a helpful AI financial advisor for {user_name or 'the user'}. Use their name naturally in conversation.

{user_profile_context}

INSTRUCTIONS:
1. Address the user by name ({user_name or 'their name'}) naturally in conversation
2. Provide personalized financial advice based on their profile information
3. Be supportive, understanding, and professional
4. Ask clarifying questions when you need more information
5. Tailor your advice to their financial goals and risk tolerance"""
            
            messages = [ChatMessage(role="system", content=basic_system_prompt)] + messages
            logger.info(f"Using basic user profile context for user {user_id}: {user_name}")
        
        # Compose prompt from messages
        prompt = "\n".join([f"{m.role}: {m.content}" for m in messages])
        return await generate_gemini_response(prompt)
    except Exception as e:
        logger.exception(f"Error generating Gemini response: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating Gemini response: {str(e)}")

# Note: generate_ai_streaming_response function has been refactored into the API layer
# to avoid database connection leaks in streaming responses. The logic is now handled
# directly in the conversations.py route with proper session management.

async def generate_financial_insights(
    db: AsyncSession,
    user_id: UUID,
):
    """Generates AI-powered financial insights for the user using Gemini."""
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
    
    # Initialize LangChain components
    llm = ChatOpenAI(
        model="gpt-4-turbo",
        temperature=0.2,
        api_key=settings.OPENAI_API_KEY
    )
    
    # Create the prompt template
    prompt = f"""
You are an expert financial advisor AI. Analyze the provided financial data and generate personalized insights.
Focus on:
1. Progress towards financial goals
2. Spending patterns and optimization opportunities
3. Savings and investment recommendations
4. Risk assessment and mitigation strategies
5. Actionable next steps

You must generate 5-7 specific, actionable insights based on the user's actual financial data.
Each insight must be specific and actionable, with concrete numbers and steps.

Financial Data:
{data_summary}

Respond in JSON with a list of insights, each with title, description, category, and priority.
"""
    
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
    
    # Set up the output parser
    parser = PydanticOutputParser(pydantic_object=FinancialInsights)
    
    # Create the chain
    chain = prompt | llm | parser
    
    try:
        # Generate insights
        result = chain.invoke({
            "data_summary": data_summary,
            "format_instructions": parser.get_format_instructions()
        })
        
        print(f"Generated {len(result.insights)} insights")
        
        # Mark existing insights as inactive
        await db.execute(
            text("UPDATE ai_insights SET is_active = false WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        
        # Convert to AIInsight objects
        db_insights = [
            AIInsight(
                user_id=user_id,
                title=insight.title,
                description=insight.description,
                category=insight.category,
                priority=insight.priority,
                is_active=True,
                is_read=False
            )
            for insight in result.insights
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
