"""
Enhanced AI Service with LangGraph State Management and MCP Integration
Provides sophisticated conversation state management and financial context awareness
"""

import logging
from typing import List, Optional, Dict, Any, AsyncGenerator
from uuid import UUID
import json
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

# LangGraph imports for state management
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.core.config import settings
from app.schemas.message import ChatMessage
from app.services.mcp_client import get_user_financial_context, enhance_persona_with_mcp_data
from app.services.persona_engine import PersonaEngineService

logger = logging.getLogger(__name__)

class ConversationState(BaseModel):
    """State management for AI conversations"""
    messages: List[BaseMessage] = Field(default_factory=list)
    user_id: Optional[UUID] = None
    persona_data: Optional[Dict[str, Any]] = None
    financial_context: Optional[str] = None
    conversation_summary: Optional[str] = None
    user_profile: Optional[Dict[str, Any]] = None
    current_topic: Optional[str] = None
    requires_financial_data: bool = False

class EnhancedAIService:
    """Enhanced AI service with LangGraph state management and MCP integration"""
    
    def __init__(self):
        self.state_graph = None
        self.setup_models()
        self.setup_tools()
        self.build_conversation_graph()
    
    def setup_models(self):
        """Initialize multiple AI models"""
        self.models = {}
        
        # OpenAI GPT-4
        if settings.OPENAI_API_KEY:
            self.models['gpt4'] = ChatOpenAI(
                model="gpt-4-turbo-preview",
                temperature=0.7,
                api_key=settings.OPENAI_API_KEY
            )
        
        # Anthropic Claude
        if hasattr(settings, 'ANTHROPIC_API_KEY') and settings.ANTHROPIC_API_KEY:
            self.models['claude'] = ChatAnthropic(
                model="claude-3-opus-20240229",
                temperature=0.7,
                anthropic_api_key=settings.ANTHROPIC_API_KEY
            )
        
        # Google Gemini (optional)
        if hasattr(settings, 'GEMINI_API_KEY') and settings.GEMINI_API_KEY:
            self.models['gemini'] = ChatGoogleGenerativeAI(
                model="gemini-1.5-pro",
                temperature=0.7,
                google_api_key=settings.GEMINI_API_KEY
            )
        
        # Default model - prefer OpenAI
        self.default_model_key = 'gpt4' if 'gpt4' in self.models else list(self.models.keys())[0]
    
    def setup_tools(self):
        """Setup tools for the AI agent"""
        
        @tool
        def get_financial_summary(user_id: str) -> str:
            """Get comprehensive financial summary for the user from MCP server"""
            try:
                # This would be called within the graph execution
                return "Financial summary retrieved"
            except Exception as e:
                return f"Error retrieving financial data: {e}"
        
        @tool
        def analyze_spending_patterns(transactions: str) -> str:
            """Analyze user's spending patterns and provide insights"""
            try:
                # Implement spending pattern analysis
                return "Spending pattern analysis complete"
            except Exception as e:
                return f"Error analyzing spending: {e}"
        
        @tool
        def get_investment_recommendations(risk_profile: str, financial_goals: str) -> str:
            """Get personalized investment recommendations"""
            try:
                # Implement investment recommendation logic
                return "Investment recommendations generated"
            except Exception as e:
                return f"Error generating recommendations: {e}"
        
        self.tools = [get_financial_summary, analyze_spending_patterns, get_investment_recommendations]
        self.tool_executor = ToolExecutor(self.tools)
    
    def build_conversation_graph(self):
        """Build the conversation state graph"""
        
        # Define the graph
        workflow = StateGraph(ConversationState)
        
        # Add nodes
        workflow.add_node("load_context", self.load_user_context)
        workflow.add_node("analyze_intent", self.analyze_user_intent)
        workflow.add_node("enhance_with_persona", self.enhance_with_persona)
        workflow.add_node("generate_response", self.generate_ai_response)
        workflow.add_node("tool_execution", self.execute_tools)
        
        # Define edges
        workflow.set_entry_point("load_context")
        workflow.add_edge("load_context", "analyze_intent")
        workflow.add_conditional_edges(
            "analyze_intent",
            self.should_use_tools,
            {
                True: "tool_execution",
                False: "enhance_with_persona"
            }
        )
        workflow.add_edge("tool_execution", "enhance_with_persona")
        workflow.add_edge("enhance_with_persona", "generate_response")
        workflow.add_edge("generate_response", END)
        
        self.state_graph = workflow.compile()
    
    async def load_user_context(self, state: ConversationState) -> ConversationState:
        """Load user context including financial data and persona"""
        try:
            if state.user_id:
                # This would need db session - for now, simulate
                logger.info(f"Loading context for user {state.user_id}")
                
                # Simulate loading user profile
                state.user_profile = {
                    "name": "User",
                    "preferences": {},
                    "financial_goals": []
                }
                
                # Load financial context if needed
                if state.requires_financial_data:
                    state.financial_context = "Comprehensive financial context loaded"
                
        except Exception as e:
            logger.error(f"Error loading user context: {e}")
        
        return state
    
    async def analyze_user_intent(self, state: ConversationState) -> ConversationState:
        """Analyze user intent to determine response strategy"""
        try:
            if state.messages:
                last_message = state.messages[-1]
                if isinstance(last_message, HumanMessage):
                    content = last_message.content.lower()
                    
                    # Determine if financial tools are needed
                    financial_keywords = [
                        'investment', 'portfolio', 'budget', 'spending', 
                        'savings', 'loan', 'credit', 'net worth', 'analysis'
                    ]
                    
                    state.requires_financial_data = any(
                        keyword in content for keyword in financial_keywords
                    )
                    
                    # Set current topic
                    if 'investment' in content:
                        state.current_topic = 'investment_advice'
                    elif 'budget' in content or 'spending' in content:
                        state.current_topic = 'budget_planning'
                    elif 'credit' in content or 'loan' in content:
                        state.current_topic = 'credit_management'
                    else:
                        state.current_topic = 'general_financial_advice'
        
        except Exception as e:
            logger.error(f"Error analyzing intent: {e}")
        
        return state
    
    def should_use_tools(self, state: ConversationState) -> bool:
        """Determine if tools should be used based on the conversation state"""
        return state.requires_financial_data and state.current_topic in [
            'investment_advice', 'budget_planning', 'credit_management'
        ]
    
    async def execute_tools(self, state: ConversationState) -> ConversationState:
        """Execute relevant tools based on user intent"""
        try:
            if state.current_topic == 'investment_advice':
                # Execute investment-related tools
                logger.info("Executing investment analysis tools")
            elif state.current_topic == 'budget_planning':
                # Execute budgeting tools
                logger.info("Executing budget analysis tools")
            elif state.current_topic == 'credit_management':
                # Execute credit analysis tools
                logger.info("Executing credit analysis tools")
        
        except Exception as e:
            logger.error(f"Error executing tools: {e}")
        
        return state
    
    async def enhance_with_persona(self, state: ConversationState) -> ConversationState:
        """Enhance response with persona data"""
        try:
            if state.user_id and not state.persona_data:
                # Load persona data if available
                logger.info(f"Loading persona for user {state.user_id}")
                # Simulate persona loading
                state.persona_data = {
                    "persona_name": "The Conscious Investor",
                    "traits": ["analytical", "long-term focused"],
                    "communication_style": "detailed and educational"
                }
        
        except Exception as e:
            logger.error(f"Error enhancing with persona: {e}")
        
        return state
    
    async def generate_ai_response(self, state: ConversationState) -> ConversationState:
        """Generate AI response using the selected model"""
        try:
            # Select model based on topic or user preference
            model_key = self.default_model_key
            model = self.models[model_key]
            
            # Build enhanced system prompt
            system_prompt = self.build_enhanced_system_prompt(state)
            
            # Prepare messages
            messages = [SystemMessage(content=system_prompt)]
            messages.extend(state.messages)
            
            # Generate response
            response = await model.ainvoke(messages)
            
            # Add response to conversation state
            state.messages.append(response)
        
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            # Add error message
            error_response = AIMessage(content=f"I apologize, but I encountered an error: {e}")
            state.messages.append(error_response)
        
        return state
    
    def build_enhanced_system_prompt(self, state: ConversationState) -> str:
        """Build enhanced system prompt with all available context"""
        prompt_parts = [
            "You are an advanced AI financial advisor with access to comprehensive user data."
        ]
        
        # Add user profile context
        if state.user_profile:
            prompt_parts.append(f"User Profile: {json.dumps(state.user_profile, indent=2)}")
        
        # Add financial context from MCP
        if state.financial_context:
            prompt_parts.append(f"Financial Context: {state.financial_context}")
        
        # Add persona context
        if state.persona_data:
            prompt_parts.append(f"User Persona: {json.dumps(state.persona_data, indent=2)}")
        
        # Add topic-specific instructions
        if state.current_topic:
            topic_instructions = {
                'investment_advice': "Focus on providing personalized investment recommendations based on the user's risk profile and financial goals.",
                'budget_planning': "Analyze spending patterns and provide actionable budgeting advice.",
                'credit_management': "Provide guidance on credit optimization and debt management.",
                'general_financial_advice': "Provide comprehensive financial guidance tailored to the user's situation."
            }
            prompt_parts.append(topic_instructions.get(state.current_topic, ""))
        
        prompt_parts.extend([
            "Always:",
            "1. Use the user's name naturally in conversation",
            "2. Reference specific data points when available",
            "3. Provide actionable, personalized advice",
            "4. Be empathetic and understanding",
            "5. Ask clarifying questions when needed",
            "6. Maintain conversation context and continuity"
        ])
        
        return "\n\n".join(prompt_parts)
    
    async def process_conversation(
        self, 
        user_id: UUID,
        messages: List[ChatMessage],
        db: AsyncSession,
        use_persona: bool = False,
        model_preference: str = None
    ) -> ConversationState:
        """Process a conversation through the state graph"""
        
        # Convert ChatMessage to LangChain messages
        lc_messages = []
        for msg in messages:
            if msg.role == "user":
                lc_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                lc_messages.append(AIMessage(content=msg.content))
            elif msg.role == "system":
                lc_messages.append(SystemMessage(content=msg.content))
        
        # Initialize state
        initial_state = ConversationState(
            messages=lc_messages,
            user_id=user_id,
            requires_financial_data=True  # Always try to get financial context
        )
        
        # Process through graph
        final_state = await self.state_graph.ainvoke(initial_state)
        
        return final_state
    
    async def stream_response(
        self,
        user_id: UUID,
        messages: List[ChatMessage],
        db: AsyncSession,
        use_persona: bool = False,
        model_preference: str = None
    ) -> AsyncGenerator[str, None]:
        """Stream AI response with enhanced context"""
        
        try:
            # Process conversation state
            state = await self.process_conversation(
                user_id, messages, db, use_persona, model_preference
            )
            
            # Get the final AI response
            if state.messages and isinstance(state.messages[-1], AIMessage):
                response_content = state.messages[-1].content
                
                # Stream the response word by word for better UX
                words = response_content.split()
                for i, word in enumerate(words):
                    if i == 0:
                        yield word
                    else:
                        yield f" {word}"
                    
                    # Add small delay for streaming effect
                    import asyncio
                    await asyncio.sleep(0.05)
            else:
                yield "I apologize, but I couldn't generate a response at this time."
        
        except Exception as e:
            logger.error(f"Error in stream_response: {e}")
            yield f"Error: {str(e)}"

# Global enhanced AI service instance
enhanced_ai_service = EnhancedAIService()
