from typing import Optional, Tuple
import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from langchain_openai import OpenAI
import pandas as pd
from app.models.conversation import Message
from app.models.user import User
from app.services.conversation import get_conversation

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FinancialAdvisor:
    """Financial Advisor that integrates with the conversation system"""
    
    def __init__(self, openai_api_key: str):
        logger.info("Initializing Financial Advisor...")
        self.llm = OpenAI(temperature=0.1, openai_api_key=openai_api_key)
        
        # Define the system prompt
        self.system_prompt = """You are a financial advisor AI. Your responses must follow these rules:

1. Data Rules:
   - ONLY use the financial data provided in the context
   - If no data is available, respond with "I don't have any financial data to analyze"
   - NEVER make assumptions about the user's financial situation
   - NEVER provide generic financial advice without specific data

2. Response Rules:
   - For greetings, only respond with a simple greeting
   - When analyzing data, only use numbers that are explicitly provided
   - If asked about something not in the data, say "I don't have that information"
   - Keep responses concise and focused on available data

3. What NOT to do:
   - DO NOT make assumptions about risk profile
   - DO NOT suggest emergency funds without expense data
   - DO NOT discuss investments without investment data
   - DO NOT provide generic financial advice
   - DO NOT make statements about financial health without metrics"""

    def _is_greeting(self, text: str) -> bool:
        """Check if the input is a greeting"""
        greetings = ['hi', 'hello', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening']
        return text.lower().strip() in greetings

    async def _get_financial_data(self, db: AsyncSession, user_id: UUID) -> Tuple[bool, str]:
        """Get financial data from the database"""
        try:
            # Get transactions
            result = await db.execute(
                text("SELECT * FROM transactions WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            transactions = result.fetchall()
            
            if not transactions:
                return False, "No financial data available"
            
            df = pd.DataFrame(transactions)
            
            # Get financial goals
            goals_result = await db.execute(
                text("SELECT * FROM financial_goals WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            goals = goals_result.fetchall()
            goals_df = pd.DataFrame(goals) if goals else pd.DataFrame()
            
            # Calculate metrics
            total_transactions = len(df)
            total_income = df[df['amount'] > 0]['amount'].sum()
            total_expenses = abs(df[df['amount'] < 0]['amount'].sum())
            
            # Check if we have any real data
            if total_transactions == 0 and goals_df.empty:
                return False, "No financial data available"
            
            # Get recent transactions
            recent_transactions = df.sort_values('date', ascending=False).head(5)
            
            # Format the data summary
            data_summary = f"""
Available Financial Data:
- Total Transactions: {total_transactions}
- Total Income: ₹{total_income:,.2f}
- Total Expenses: ₹{total_expenses:,.2f}

Recent Transactions:
{recent_transactions[['date', 'description', 'amount']].to_string() if not recent_transactions.empty else 'No recent transactions'}

Financial Goals:
{goals_df[['name', 'target', 'current']].to_string() if not goals_df.empty else 'No financial goals set'}
"""
            return True, data_summary
            
        except Exception as e:
            logger.error(f"Error getting financial data: {str(e)}")
            await db.rollback()
            return False, "Error retrieving financial data"

    async def get_advice(
        self,
        db: AsyncSession,
        user_id: UUID,
        conversation_id: UUID,
        query: str
    ) -> Optional[str]:
        """Get financial advice based on available data and conversation context"""
        try:
            # Get conversation history
            conversation = await get_conversation(db, conversation_id)
            if not conversation:
                return None

            # Handle greetings
            if self._is_greeting(query):
                return "Hello! I'm your financial advisor. How can I help you today?"
            
            # Get financial data
            has_data, data_summary = await self._get_financial_data(db, user_id)
            if not has_data:
                return "I don't have any financial data to analyze. Please add some transactions or set up financial goals first."
            
            # Get conversation history for context
            conversation_history = []
            for message in conversation.messages:
                conversation_history.append(f"{message.role}: {message.content}")
            
            # Create the prompt
            prompt = f"""{self.system_prompt}

{data_summary}

Conversation History:
{chr(10).join(conversation_history[-5:]) if conversation_history else 'No previous messages'}

User Query: {query}

Remember: Only use the data provided above. If you don't have the specific data needed, say "I don't have enough information to answer that".
"""
            
            # Get response from LLM
            result = self.llm.invoke(prompt)
            return result
            
        except Exception as e:
            logger.error(f"Error getting advice: {str(e)}", exc_info=True)
            await db.rollback()
            return "I apologize, but I encountered an error. Please try again or contact support if the issue persists." 