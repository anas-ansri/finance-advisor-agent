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
        # Persona integration
        if use_persona:
            from app.services.persona_engine import PersonaEngineService
            persona_service = PersonaEngineService(db)
            persona_profile = await persona_service.generate_persona_for_user(user)
            if persona_profile and getattr(persona_profile, 'persona_description', None):
                persona_system_prompt = f"You are responding as the user's financial persona: {persona_profile.persona_name}. {persona_profile.persona_description}\nKey Traits: {persona_profile.key_traits}\nLifestyle: {persona_profile.lifestyle_summary}\nFinancial Tendencies: {persona_profile.financial_tendencies}"
                messages = [ChatMessage(role="system", content=persona_system_prompt)] + messages
        # Compose prompt from messages
        prompt = "\n".join([f"{m.role}: {m.content}" for m in messages])
        return await generate_gemini_response(prompt)
    except Exception as e:
        logger.exception(f"Error generating Gemini response: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating Gemini response: {str(e)}")

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
