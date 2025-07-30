"""
Enhanced AI Service with simplified implementation for stable functionality
Provides conversation management and financial context awareness without complex LangGraph dependencies
"""

import logging
from typing import List, Optional, Dict, Any, AsyncGenerator
from uuid import UUID
import json
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from app.core.config import settings
from app.schemas.message import ChatMessage
from app.services.mcp_client import get_user_financial_context, enhance_persona_with_mcp_data
from app.services.persona_engine import PersonaEngineService

logger = logging.getLogger(__name__)

@dataclass
class ConversationState:
    """Simplified state management for AI conversations"""
    messages: List[BaseMessage]
    user_id: Optional[UUID] = None
    persona_data: Optional[Dict[str, Any]] = None
    financial_context: Optional[str] = None
    conversation_summary: Optional[str] = None
    user_profile: Optional[Dict[str, Any]] = None
    current_topic: Optional[str] = None
    requires_financial_data: bool = False

class EnhancedAIService:
    """Enhanced AI service with conversation management and MCP integration"""
    
    def __init__(self):
        self.setup_models()
    
    def setup_models(self):
        """Setup different AI models"""
        self.models = {}
        
        # OpenAI models
        if settings.OPENAI_API_KEY:
            self.models['openai'] = ChatOpenAI(
                api_key=settings.OPENAI_API_KEY,
                model="gpt-4o",
                temperature=0.7
            )
            self.models['gpt4'] = self.models['openai']  # Alias
        
        # Anthropic models
        if hasattr(settings, 'ANTHROPIC_API_KEY') and settings.ANTHROPIC_API_KEY:
            self.models['anthropic'] = ChatAnthropic(
                api_key=settings.ANTHROPIC_API_KEY,
                model="claude-3-sonnet-20240229",
                temperature=0.7
            )
    
    async def analyze_user_intent(self, messages: List[ChatMessage]) -> str:
        """Analyze user intent from messages"""
        if not messages:
            return "general_chat"
        
        last_message = messages[-1].content.lower()
        
        # Simple intent analysis
        if any(word in last_message for word in ['invest', 'investment', 'stocks', 'portfolio']):
            return "investment_advice"
        elif any(word in last_message for word in ['budget', 'spending', 'expense', 'save']):
            return "budget_planning"
        elif any(word in last_message for word in ['credit', 'loan', 'debt', 'score']):
            return "credit_management"
        elif any(word in last_message for word in ['insurance', 'protect', 'coverage']):
            return "insurance_planning"
        elif any(word in last_message for word in ['tax', 'filing', 'deduction']):
            return "tax_planning"
        else:
            return "general_financial_advice"
    
    async def load_financial_context(self, db: AsyncSession, user_id: UUID) -> Optional[str]:
        """Load financial context using MCP if available"""
        try:
            # Try to get MCP financial context (note: function expects user_id, db as parameters)
            financial_context = await get_user_financial_context(user_id, db)
            if financial_context:
                logger.info(f"Loaded MCP financial context for user {user_id}")
                return financial_context
        except Exception as e:
            logger.warning(f"Failed to load MCP financial context: {e}")
        
        return None
    
    async def enhance_with_persona(self, db: AsyncSession, user_id: UUID, use_persona: bool = True) -> Optional[Dict[str, Any]]:
        """Load and enhance persona data"""
        if not use_persona:
            return None
            
        try:
            from app.services.user import get_user
            
            # Get user object first
            user = await get_user(db, user_id)
            if not user:
                logger.warning(f"User {user_id} not found")
                return None
            
            persona_service = PersonaEngineService(db)
            persona_profile = await persona_service.get_existing_persona_for_user(user)
            
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
                
                # Try to enhance with MCP data
                try:
                    enhanced_persona = await enhance_persona_with_mcp_data(user_id, db)
                    if enhanced_persona:
                        # Merge the enhanced data with existing persona data
                        persona_data.update(enhanced_persona)
                        return persona_data
                except Exception as e:
                    logger.warning(f"Failed to enhance persona with MCP data: {e}")
                
                return persona_data
        except Exception as e:
            logger.error(f"Failed to load persona: {e}")
        
        return None
    
    def build_enhanced_prompt(self, 
                            messages: List[ChatMessage], 
                            user_profile: Optional[Dict[str, Any]] = None,
                            persona_data: Optional[Dict[str, Any]] = None,
                            financial_context: Optional[str] = None,
                            intent: Optional[str] = None) -> List[BaseMessage]:
        """Build enhanced prompt with all available context"""
        
        # Start with system prompt
        system_parts = ["You are a highly knowledgeable AI financial advisor."]
        
        # Add user profile context
        if user_profile:
            system_parts.append(f"User Profile: {json.dumps(user_profile, indent=2)}")
        
        # Add persona context
        if persona_data:
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
            
            persona_context = f"""
PERSONA: {persona_data['persona_name']}
DESCRIPTION: {persona_data['persona_description']}
KEY TRAITS: {', '.join(persona_data.get('key_traits', []))}
LIFESTYLE: {persona_data.get('lifestyle_summary', '')}
FINANCIAL TENDENCIES: {persona_data.get('financial_tendencies', '')}
{cultural_context}
{advice_style}

IMPORTANT: Respond as if you truly understand this person's values, lifestyle, and cultural preferences. Reference their specific traits and interests when relevant to financial advice."""
            
            system_parts.append(persona_context)
        
        # Add financial context from MCP
        if financial_context:
            system_parts.append(f"REAL-TIME FINANCIAL DATA:\n{financial_context}")
            system_parts.append("Use this real-time financial data to provide specific, personalized advice based on the user's actual financial situation.")
        
        # Add intent-specific instructions
        if intent:
            intent_instructions = {
                "investment_advice": "Focus on investment strategies, portfolio analysis, and market insights.",
                "budget_planning": "Emphasize budgeting techniques, expense tracking, and saving strategies.",
                "credit_management": "Provide guidance on credit scores, debt management, and loan options.",
                "insurance_planning": "Discuss insurance needs, coverage options, and risk management.",
                "tax_planning": "Offer tax optimization strategies and filing guidance.",
                "general_financial_advice": "Provide comprehensive financial guidance tailored to the user's situation."
            }
            
            if intent in intent_instructions:
                system_parts.append(f"FOCUS AREA: {intent_instructions[intent]}")
        
        # Build final system prompt
        system_prompt = "\n\n".join(system_parts)
        
        # Convert messages to LangChain format
        langchain_messages = [SystemMessage(content=system_prompt)]
        
        for msg in messages:
            if msg.role == "user":
                langchain_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                langchain_messages.append(AIMessage(content=msg.content))
        
        return langchain_messages
    
    async def generate_enhanced_response(self,
                                       db: AsyncSession,
                                       user_id: UUID,
                                       messages: List[ChatMessage],
                                       use_persona: bool = True,
                                       model_id: str = "gpt4",
                                       temperature: float = 0.7,
                                       max_tokens: int = 1000) -> str:
        """Generate enhanced AI response with full context"""
        
        try:
            # Analyze user intent
            intent = await self.analyze_user_intent(messages)
            logger.info(f"Detected intent: {intent}")
            
            # Load financial context
            financial_context = await self.load_financial_context(db, user_id)
            
            # Load persona data
            persona_data = await self.enhance_with_persona(db, user_id, use_persona)
            
            # Build user profile (basic)
            user_profile = {
                "user_id": str(user_id),
                "intent": intent
            }
            
            # Build enhanced prompt
            enhanced_messages = self.build_enhanced_prompt(
                messages=messages,
                user_profile=user_profile,
                persona_data=persona_data,
                financial_context=financial_context,
                intent=intent
            )
            
            # Get the appropriate model
            model = self.models.get(model_id, self.models.get('gpt4', self.models.get('openai')))
            if not model:
                raise ValueError(f"Model {model_id} not available")
            
            # Update model parameters
            model.temperature = temperature
            model.max_tokens = max_tokens
            
            # Generate response
            response = await model.ainvoke(enhanced_messages)
            
            return response.content
            
        except Exception as e:
            logger.error(f"Error generating enhanced response: {e}")
            # Fallback to simple response
            return f"I apologize, but I encountered an error while processing your request. Please try again."
    
    async def stream_enhanced_response(self,
                                     db: AsyncSession,
                                     user_id: UUID,
                                     messages: List[ChatMessage],
                                     use_persona: bool = True,
                                     model_id: str = "gpt4",
                                     temperature: float = 0.7,
                                     max_tokens: int = 1000) -> AsyncGenerator[str, None]:
        """Stream enhanced AI response with full context"""
        
        try:
            # Analyze user intent
            intent = await self.analyze_user_intent(messages)
            logger.info(f"Detected intent for streaming: {intent}")
            
            # Load financial context
            financial_context = await self.load_financial_context(db, user_id)
            
            # Load persona data
            persona_data = await self.enhance_with_persona(db, user_id, use_persona)
            
            # Build user profile (basic)
            user_profile = {
                "user_id": str(user_id),
                "intent": intent
            }
            
            # Build enhanced prompt
            enhanced_messages = self.build_enhanced_prompt(
                messages=messages,
                user_profile=user_profile,
                persona_data=persona_data,
                financial_context=financial_context,
                intent=intent
            )
            
            # Get the appropriate model
            model = self.models.get(model_id, self.models.get('gpt4', self.models.get('openai')))
            if not model:
                raise ValueError(f"Model {model_id} not available")
            
            # Update model parameters
            model.temperature = temperature
            model.max_tokens = max_tokens
            
            # Stream response
            async for chunk in model.astream(enhanced_messages):
                if hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content
            
        except Exception as e:
            logger.error(f"Error streaming enhanced response: {e}")
            yield f"I apologize, but I encountered an error while processing your request. Please try again."

# Global instance
enhanced_ai_service = EnhancedAIService()
