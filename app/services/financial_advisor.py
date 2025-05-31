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
   - Use the financial data provided in the context to give personalized insights
   - If no data is available, respond with "I don't have any financial data to analyze"
   - Base your advice on the actual transaction patterns and financial goals shown
   - Use specific numbers and patterns from the data to support your recommendations

2. Response Rules:
   - For greetings, respond with a friendly greeting and ask how you can help
   - When analyzing data, highlight specific patterns and trends you observe
   - If asked about something not in the data, explain what data would be needed
   - Provide actionable insights based on the available transaction history
   - Keep responses clear and focused on the data available

3. What to do:
   - Analyze spending patterns and suggest potential areas for optimization
   - Identify recurring expenses and their impact
   - Point out investment opportunities based on current investment behavior
   - Suggest financial goals based on income and spending patterns
   - Provide specific, data-backed recommendations"""

    def _is_greeting(self, text: str) -> bool:
        """Check if the input is a greeting"""
        greetings = [
            "hi",
            "hello",
            "hey",
            "greetings",
            "good morning",
            "good afternoon",
            "good evening",
        ]
        return text.lower().strip() in greetings

    async def _get_financial_data(
        self, db: AsyncSession, user_id: UUID
    ) -> Tuple[bool, str]:
        """Get financial data from the database"""
        try:
            # Get transactions
            result = await db.execute(
                text("SELECT * FROM bank_transactions WHERE user_id = :user_id"),
                {"user_id": user_id},
            )
            transactions = result.fetchall()
            print(f"Retrieved {len(transactions)} transactions for user {user_id}")

            if not transactions:
                return False, "No financial data available"

            df = pd.DataFrame(transactions)

            # Get financial goals
            goals_result = await db.execute(
                text("SELECT * FROM financial_goals WHERE user_id = :user_id"),
                {"user_id": user_id},
            )
            goals = goals_result.fetchall()
            goals_df = pd.DataFrame(goals) if goals else pd.DataFrame()

            # Calculate basic metrics
            total_transactions = len(df)
            total_income = df[df["amount"] > 0]["amount"].sum()
            total_expenses = abs(df[df["amount"] < 0]["amount"].sum())

            # Initialize data summary
            data_summary = f"""
Available Financial Data:
- Total Transactions: {total_transactions}
- Total Income: ₹{total_income:,.2f}
- Total Expenses: ₹{total_expenses:,.2f}
- Net Savings: ₹{(total_income - total_expenses):,.2f}
"""

            # Add category analysis if category field exists
            if "category" in df.columns:
                category_expenses = (
                    df[df["amount"] < 0].groupby("category")["amount"].sum().abs()
                )
                category_expenses = category_expenses.sort_values(ascending=False)
                data_summary += f"\nExpense Categories (Top 5):\n{category_expenses.head().to_string()}\n"

            # Add monthly trends if date field exists
            if "date" in df.columns:
                try:
                    df["month"] = pd.to_datetime(df["date"]).dt.to_period("M")
                    monthly_income = (
                        df[df["amount"] > 0].groupby("month")["amount"].sum()
                    )
                    monthly_expenses = (
                        df[df["amount"] < 0].groupby("month")["amount"].sum().abs()
                    )
                    data_summary += f"\nMonthly Trends (Last 3 months):\nIncome: {monthly_income.tail(3).to_string()}\nExpenses: {monthly_expenses.tail(3).to_string()}\n"
                except Exception as e:
                    logger.warning(f"Could not process monthly trends: {str(e)}")

            # Add investment analysis if category field exists
            if "category" in df.columns:
                investment_transactions = df[df["category"] == "INVESTMENTS"]
                if not investment_transactions.empty:
                    data_summary += f"\nInvestment Activity:\n{investment_transactions[['date', 'description', 'amount']].to_string()}\n"

            # Add recent transactions
            recent_cols = ["date", "description", "amount"]
            if "category" in df.columns:
                recent_cols.append("category")

            recent_transactions = df.sort_values("date", ascending=False).head(5)[
                recent_cols
            ]
            data_summary += (
                f"\nRecent Transactions:\n{recent_transactions.to_string()}\n"
            )

            # Add financial goals
            if not goals_df.empty:
                data_summary += f"\nFinancial Goals:\n{goals_df[['name', 'target', 'current']].to_string()}\n"

            logger.info(f"Financial data summary for user {user_id}:\n{data_summary}")
            return True, data_summary

        except Exception as e:
            logger.error(f"Error getting financial data: {str(e)}")
            await db.rollback()
            return False, "Error retrieving financial data"

    async def get_advice(
        self, db: AsyncSession, user_id: UUID, conversation_id: UUID, query: str
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
            print(f"Generated prompt for LLM:\n{prompt}")
            # Get response from LLM
            result = self.llm.invoke(prompt)
            return result

        except Exception as e:
            logger.error(f"Error getting advice: {str(e)}", exc_info=True)
            await db.rollback()
            return "I apologize, but I encountered an error. Please try again or contact support if the issue persists."
