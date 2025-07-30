"""
MCP-Enhanced AI Service Integration
Bridges existing AI service with MCP financial data and enhanced frameworks
"""

import logging
from typing import List, Optional, Dict, Any, AsyncGenerator
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.message import ChatMessage
from app.services.mcp_client import mcp_client, get_user_financial_context, enhance_persona_with_mcp_data
from app.services.enhanced_ai import enhanced_ai_service
from app.services.user import get_user
from app.core.config import settings

logger = logging.getLogger(__name__)

class MCPIntegratedAIService:
    """
    MCP-integrated AI service that enhances the existing AI capabilities
    with comprehensive financial data and advanced conversation management
    """
    
    def __init__(self):
        self.use_enhanced_ai = hasattr(settings, 'DEFAULT_AI_MODEL')
        self.mcp_enabled = hasattr(settings, 'MCP_SERVER_URL')
        
    async def generate_enhanced_response(
        self,
        db: AsyncSession,
        user_id: UUID,
        messages: List[ChatMessage],
        use_persona: bool = False,
        model_id: Optional[int] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate AI response with MCP financial context and enhanced reasoning
        """
        try:
            # Get user for phone number
            user = await get_user(db, user_id)
            if not user:
                return "User not found"
            
            # Step 1: Gather comprehensive financial context from MCP
            financial_context = ""
            mcp_enhancement_data = {}
            
            if self.mcp_enabled and hasattr(user, 'phone_number') and user.phone_number:
                try:
                    financial_context = await get_user_financial_context(user_id, db)
                    mcp_enhancement_data = await enhance_persona_with_mcp_data(user_id, db)
                    logger.info(f"Retrieved MCP financial context for user {user_id}")
                except Exception as e:
                    logger.warning(f"MCP integration failed: {e}")
                    financial_context = "Financial context unavailable"
            
            # Step 2: Use enhanced AI service if available
            if self.use_enhanced_ai:
                try:
                    final_state = await enhanced_ai_service.process_conversation(
                        user_id, messages, db, use_persona
                    )
                    
                    if final_state.messages:
                        last_message = final_state.messages[-1]
                        return last_message.content
                except Exception as e:
                    logger.warning(f"Enhanced AI service failed, falling back: {e}")
            
            # Step 3: Fallback to enhanced prompt with existing service
            enhanced_messages = await self._enhance_messages_with_context(
                messages, financial_context, mcp_enhancement_data, user, use_persona, db
            )
            
            # Use existing AI service with enhanced context
            from app.services.ai import generate_ai_response
            return await generate_ai_response(
                db, user_id, None, enhanced_messages, model_id, temperature, max_tokens, use_persona
            )
            
        except Exception as e:
            logger.error(f"Error in enhanced AI response generation: {e}")
            return f"I apologize, but I encountered an error while processing your request: {str(e)}"
    
    async def stream_enhanced_response(
        self,
        db: AsyncSession,
        user_id: UUID,
        messages: List[ChatMessage],
        use_persona: bool = False,
        model_id: Optional[int] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream AI response with MCP financial context
        """
        try:
            # Get user
            user = await get_user(db, user_id)
            if not user:
                yield "User not found"
                return
            
            # Gather financial context
            financial_context = ""
            mcp_enhancement_data = {}
            
            if self.mcp_enabled and hasattr(user, 'phone_number') and user.phone_number:
                try:
                    financial_context = await get_user_financial_context(user_id, db)
                    mcp_enhancement_data = await enhance_persona_with_mcp_data(user_id, db)
                except Exception as e:
                    logger.warning(f"MCP integration failed: {e}")
            
            # Use enhanced AI streaming if available
            if self.use_enhanced_ai:
                try:
                    async for chunk in enhanced_ai_service.stream_response(
                        user_id, messages, db, use_persona
                    ):
                        yield chunk
                    return
                except Exception as e:
                    logger.warning(f"Enhanced streaming failed, falling back: {e}")
            
            # Fallback: enhance messages and use existing streaming
            enhanced_messages = await self._enhance_messages_with_context(
                messages, financial_context, mcp_enhancement_data, user, use_persona, db
            )
            
            # Stream using existing service (simulate streaming for now)
            from app.services.ai import generate_ai_response
            response = await generate_ai_response(
                db, user_id, None, enhanced_messages, model_id, temperature, max_tokens, use_persona
            )
            
            # Simulate streaming by yielding chunks
            words = response.split()
            for word in words:
                yield f"{word} "
                import asyncio
                await asyncio.sleep(0.05)
            
        except Exception as e:
            logger.error(f"Error in enhanced AI streaming: {e}")
            yield f"Error: {str(e)}"
    
    async def _enhance_messages_with_context(
        self,
        messages: List[ChatMessage],
        financial_context: str,
        mcp_enhancement_data: Dict[str, Any],
        user,
        use_persona: bool,
        db: AsyncSession
    ) -> List[ChatMessage]:
        """
        Enhance conversation messages with financial context and MCP data
        """
        try:
            # Build enhanced system prompt
            system_prompt_parts = [
                f"You are an advanced AI financial advisor for {user.first_name or 'the user'}."
            ]
            
            # Add MCP financial context
            if financial_context and financial_context != "Financial context unavailable":
                system_prompt_parts.append(f"""
COMPREHENSIVE FINANCIAL DATA (via Fi Money MCP):
{financial_context}

This is real-time financial data from the user's Fi Money account. Use this information to provide highly personalized advice.""")
            
            # Add MCP enhancement data
            if mcp_enhancement_data:
                system_prompt_parts.append(f"""
FINANCIAL PROFILE INSIGHTS:
- Net Worth Tier: {mcp_enhancement_data.get('net_worth_tier', 'unknown')}
- Investment Style: {mcp_enhancement_data.get('investment_style', 'unknown')}
- Debt Profile: {mcp_enhancement_data.get('debt_profile', 'unknown')}
- Credit Health: {mcp_enhancement_data.get('credit_health', 'unknown')}""")
            
            # Add persona context if requested
            if use_persona:
                try:
                    from app.services.persona_engine import PersonaEngineService
                    persona_service = PersonaEngineService(db)
                    persona_profile = await persona_service.get_existing_persona_for_user(user)
                    
                    if persona_profile:
                        system_prompt_parts.append(f"""
USER PERSONA: {persona_profile.persona_name}
{persona_profile.persona_description}

Cultural Profile:
- Music Taste: {persona_profile.cultural_profile.get('music_taste', 'Not specified')}
- Entertainment Style: {persona_profile.cultural_profile.get('entertainment_style', 'Not specified')}
- Fashion Sensibility: {persona_profile.cultural_profile.get('fashion_sensibility', 'Not specified')}
- Dining Philosophy: {persona_profile.cultural_profile.get('dining_philosophy', 'Not specified')}

Financial Advice Style: {getattr(persona_profile, 'financial_advice_style', 'Standard advisory approach')}""")
                except Exception as e:
                    logger.warning(f"Persona integration failed: {e}")
            
            system_prompt_parts.extend([
                """
ENHANCED CAPABILITIES:
- Access to real-time financial data via Fi Money MCP server
- Comprehensive transaction analysis and pattern recognition  
- Investment portfolio analysis with performance metrics
- Credit score monitoring and improvement recommendations
- Personalized budgeting and savings strategies
- Risk assessment and financial goal tracking

INSTRUCTIONS:
1. Always reference specific data points from the user's financial profile when available
2. Provide concrete, actionable advice based on their actual financial situation
3. Use their name naturally in conversation
4. Make connections between their spending patterns and financial goals
5. Offer specific recommendations with dollar amounts when possible
6. Ask clarifying questions about their financial goals and preferences
7. Be empathetic and understanding of their financial journey

Remember: You have access to comprehensive, real-time financial data. Use it to provide deeply personalized financial guidance."""
            ])
            
            # Create enhanced system message
            enhanced_system_message = ChatMessage(
                role="system",
                content="\n\n".join(system_prompt_parts)
            )
            
            # Return enhanced messages with system prompt first
            return [enhanced_system_message] + messages
            
        except Exception as e:
            logger.error(f"Error enhancing messages with context: {e}")
            return messages
    
    async def get_financial_insights_with_mcp(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Generate financial insights using MCP data
        """
        try:
            user = await get_user(db, user_id)
            if not user or not hasattr(user, 'phone_number') or not user.phone_number:
                return {"error": "No phone number available for MCP integration"}
            
            # Get comprehensive financial profile from MCP
            profile = await mcp_client.get_comprehensive_financial_profile(user.phone_number)
            
            insights = {
                "net_worth_analysis": {},
                "spending_patterns": {},
                "investment_performance": {},
                "credit_health": {},
                "recommendations": []
            }
            
            # Analyze net worth
            if profile.net_worth:
                net_worth_data = profile.net_worth.get("netWorthResponse", {})
                total_net_worth = net_worth_data.get("totalNetWorthValue", {})
                
                insights["net_worth_analysis"] = {
                    "total": total_net_worth.get("units", 0),
                    "currency": total_net_worth.get("currencyCode", "INR"),
                    "assets": net_worth_data.get("assetValues", []),
                    "liabilities": net_worth_data.get("liabilityValues", [])
                }
            
            # Analyze credit health
            if profile.credit_report:
                credit_data = profile.credit_report.get("creditReportResponse", {})
                credit_score = credit_data.get("creditScore", {})
                
                insights["credit_health"] = {
                    "score": credit_score.get("score", "N/A"),
                    "rating": "excellent" if int(credit_score.get("score", 0)) > 750 else "good"
                }
            
            # Generate recommendations based on MCP data
            recommendations = []
            
            if insights["net_worth_analysis"].get("total", 0) > 0:
                recommendations.append({
                    "type": "investment",
                    "title": "Diversification Opportunity",
                    "description": "Consider diversifying your investment portfolio based on your current net worth."
                })
            
            if insights["credit_health"].get("score", 0):
                score = int(insights["credit_health"]["score"])
                if score < 700:
                    recommendations.append({
                        "type": "credit",
                        "title": "Credit Score Improvement",
                        "description": f"Your credit score of {score} can be improved with strategic credit management."
                    })
            
            insights["recommendations"] = recommendations
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating MCP insights: {e}")
            return {"error": str(e)}

# Global MCP-integrated AI service instance
mcp_ai_service = MCPIntegratedAIService()
