from sqlalchemy import Boolean, Column, DateTime, String, func, Numeric, Date, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.db.database import Base
from app.models.ai_insight import AIInsight
from app.models.account import Account
from app.models.expense import Expense
from app.models.financial_goal import FinancialGoal
from app.models.ai_preference import AIPreference


class User(Base):
    """
    User model for storing user data.
    Authentication is handled by Supabase.
    """
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    openai_api_key = Column(String)
    anthropic_api_key = Column(String)
    ollama_host = Column(String, server_default="http://localhost:11434")
    ollama_model = Column(String, server_default="llama3")
    preferred_ai_advisor = Column(String, server_default="gpt4")
    preferred_categorization_model = Column(String, server_default="gpt35")
    first_name = Column(String)
    last_name = Column(String)
    date_of_birth = Column(Date)
    monthly_income = Column(Numeric)
    employment_status = Column(String)
    monthly_expenses = Column(Numeric)
    primary_financial_goal = Column(String)
    financial_goal_timeline = Column(String)
    risk_tolerance = Column(String)
    is_onboarding_done = Column(Boolean, server_default="false")
    bio = Column(String)
    language = Column(Enum('en', 'es', 'fr', 'de', 'ja', 'hi', name='Languages'))
    timezone = Column(String)
    currency = Column(String)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    insights = relationship("AIInsight", back_populates="user", cascade="all, delete-orphan")
    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="user", cascade="all, delete-orphan")
    financial_goals = relationship("FinancialGoal", back_populates="user", cascade="all, delete-orphan")
    ai_preferences = relationship("AIPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
    statements = relationship("BankStatement", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("BankTransaction", back_populates="user", cascade="all, delete-orphan")
    persona_profile = relationship("PersonaProfile", back_populates="user", uselist=False)

# Import at the bottom to avoid circular imports
from app.models.conversation import Conversation
from app.models.bank_statement import BankStatement
from app.models.persona_profile import PersonaProfile

