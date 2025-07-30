"""
MCP-Enhanced AI Service Integration with Tool Calling
Uses MCP financial data as tools that AI can call when needed
"""

import logging
from typing import List, Optional, Dict, Any, AsyncGenerator, Callable
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
import json
import re

from app.schemas.message import ChatMessage
from app.services.mcp_client import mcp_client, get_user_financial_context, enhance_persona_with_mcp_data
from app.services.enhanced_ai_simple import enhanced_ai_service
from app.services.user import get_user
from app.core.config import settings

logger = logging.getLogger(__name__)

class MCPFinancialTools:
    """MCP Financial Data Tools for AI Tool Calling"""
    
    def __init__(self, db: AsyncSession, user_id: UUID):
        self.db = db
        self.user_id = user_id
        self.user = None
        
    async def _get_user(self):
        """Lazy load user if not already loaded"""
        if not self.user:
            self.user = await get_user(self.db, self.user_id)
        return self.user
    
    async def get_net_worth(self) -> Dict[str, Any]:
        """Tool: Get user's net worth from Fi Money"""
        try:
            user = await self._get_user()
            if not user or not hasattr(user, 'phone_number') or not user.phone_number:
                return {"error": "No phone number available for Fi Money integration"}
            
            profile = await mcp_client.get_comprehensive_financial_profile(user.phone_number)
            
            if profile.net_worth:
                net_worth_data = profile.net_worth.get("netWorthResponse", {})
                total_net_worth = net_worth_data.get("totalNetWorthValue", {})
                
                return {
                    "total_net_worth": total_net_worth.get("units", 0),
                    "currency": total_net_worth.get("currencyCode", "INR"),
                    "assets": net_worth_data.get("assetValues", []),
                    "liabilities": net_worth_data.get("liabilityValues", []),
                    "status": "success"
                }
            else:
                return {"error": "Net worth data not available"}
                
        except Exception as e:
            logger.error(f"Error getting net worth: {e}")
            return {"error": f"Failed to retrieve net worth: {str(e)}"}
    
    async def get_credit_score(self) -> Dict[str, Any]:
        """Tool: Get user's credit score from Fi Money"""
        try:
            user = await self._get_user()
            if not user or not hasattr(user, 'phone_number') or not user.phone_number:
                return {"error": "No phone number available for Fi Money integration"}
            
            profile = await mcp_client.get_comprehensive_financial_profile(user.phone_number)
            
            if profile.credit_report:
                credit_data = profile.credit_report.get("creditReportResponse", {})
                credit_score = credit_data.get("creditScore", {})
                
                return {
                    "credit_score": credit_score.get("score", "N/A"),
                    "rating": self._get_credit_rating(credit_score.get("score", 0)),
                    "report_date": credit_data.get("reportDate", "Unknown"),
                    "status": "success"
                }
            else:
                return {"error": "Credit score data not available"}
                
        except Exception as e:
            logger.error(f"Error getting credit score: {e}")
            return {"error": f"Failed to retrieve credit score: {str(e)}"}
    
    async def get_bank_transactions(self, limit: int = 20) -> Dict[str, Any]:
        """Tool: Get recent bank transactions from Fi Money"""
        try:
            user = await self._get_user()
            if not user or not hasattr(user, 'phone_number') or not user.phone_number:
                return {"error": "No phone number available for Fi Money integration"}
            
            profile = await mcp_client.get_comprehensive_financial_profile(user.phone_number)
            
            if profile.bank_transactions:
                transactions = profile.bank_transactions[:limit]
                
                return {
                    "transactions": transactions,
                    "total_count": len(profile.bank_transactions),
                    "showing": len(transactions),
                    "status": "success"
                }
            else:
                return {"error": "Bank transaction data not available"}
                
        except Exception as e:
            logger.error(f"Error getting bank transactions: {e}")
            return {"error": f"Failed to retrieve transactions: {str(e)}"}
    
    async def get_investment_portfolio(self) -> Dict[str, Any]:
        """Tool: Get investment portfolio from Fi Money"""
        try:
            user = await self._get_user()
            if not user or not hasattr(user, 'phone_number') or not user.phone_number:
                return {"error": "No phone number available for Fi Money integration"}
            
            profile = await mcp_client.get_comprehensive_financial_profile(user.phone_number)
            
            if profile.investment_portfolio:
                return {
                    "portfolio": profile.investment_portfolio,
                    "status": "success"
                }
            elif profile.mutual_fund_transactions:
                return {
                    "portfolio": {"mutual_funds": profile.mutual_fund_transactions},
                    "status": "success"
                }
            else:
                return {"error": "Investment portfolio data not available"}
                
        except Exception as e:
            logger.error(f"Error getting investment portfolio: {e}")
            return {"error": f"Failed to retrieve portfolio: {str(e)}"}
    
    async def get_epf_details(self) -> Dict[str, Any]:
        """Tool: Get EPF (Employee Provident Fund) details from Fi Money"""
        try:
            user = await self._get_user()
            if not user or not hasattr(user, 'phone_number') or not user.phone_number:
                return {"error": "No phone number available for Fi Money integration"}
            
            profile = await mcp_client.get_comprehensive_financial_profile(user.phone_number)
            
            if profile.epf_details:
                return {
                    "epf_details": profile.epf_details,
                    "status": "success"
                }
            else:
                return {"error": "EPF details not available"}
                
        except Exception as e:
            logger.error(f"Error getting EPF details: {e}")
            return {"error": f"Failed to retrieve EPF details: {str(e)}"}
    
    def _get_credit_rating(self, score) -> str:
        """Convert credit score to rating"""
        try:
            score_num = int(score) if isinstance(score, str) else score
            if score_num >= 750:
                return "Excellent"
            elif score_num >= 700:
                return "Good"
            elif score_num >= 650:
                return "Fair"
            elif score_num >= 600:
                return "Poor"
            else:
                return "Very Poor"
        except (ValueError, TypeError):
            return "Unknown"
    
    def get_available_tools(self) -> Dict[str, Callable]:
        """Get all available MCP tools"""
        return {
            "get_net_worth": self.get_net_worth,
            "get_credit_score": self.get_credit_score,
            "get_bank_transactions": self.get_bank_transactions,
            "get_investment_portfolio": self.get_investment_portfolio,
            "get_epf_details": self.get_epf_details,
        }

class MCPIntegratedAIService:
    """
    MCP-integrated AI service that provides financial data through tool calling
    AI can call specific financial data tools when needed during conversation
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
        model_id: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate AI response with MCP tools available for financial data
        """
        try:
            # Get user
            user = await get_user(db, user_id)
            if not user:
                return "User not found"
            
            # Create MCP tools for this conversation
            mcp_tools = MCPFinancialTools(db, user_id) if self.mcp_enabled else None
            
            # Build system prompt with tool descriptions
            enhanced_messages = await self._build_tool_enhanced_messages(
                messages, user, use_persona, db, mcp_tools
            )
            
            # Use enhanced AI service if available
            if self.use_enhanced_ai:
                try:
                    response = await enhanced_ai_service.generate_enhanced_response(
                        db, user_id, enhanced_messages, use_persona, model_id, temperature, max_tokens
                    )
                    
                    # Check if response contains tool calls and execute them
                    final_response = await self._process_tool_calls(response, mcp_tools)
                    return final_response
                    
                except Exception as e:
                    logger.warning(f"Enhanced AI service failed, falling back: {e}")
            
            # Fallback to existing AI service
            from app.services.ai import generate_ai_response
            response = await generate_ai_response(
                db, user_id, None, enhanced_messages, model_id, temperature, max_tokens, use_persona
            )
            
            # Process tool calls in fallback response too
            final_response = await self._process_tool_calls(response, mcp_tools)
            return final_response
            
        except Exception as e:
            logger.error(f"Error in enhanced AI response generation: {e}")
            return f"I apologize, but I encountered an error while processing your request: {str(e)}"
    
    async def stream_enhanced_response(
        self,
        db: AsyncSession,
        user_id: UUID,
        messages: List[ChatMessage],
        use_persona: bool = False,
        model_id: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream AI response with MCP tools available for financial data
        """
        try:
            # Get user
            user = await get_user(db, user_id)
            if not user:
                yield "User not found"
                return
            
            # Create MCP tools for this conversation
            mcp_tools = MCPFinancialTools(db, user_id) if self.mcp_enabled else None
            
            # Build enhanced messages with tool descriptions
            enhanced_messages = await self._build_tool_enhanced_messages(
                messages, user, use_persona, db, mcp_tools
            )
            
            # Use enhanced AI streaming if available
            if self.use_enhanced_ai:
                try:
                    response_chunks = []
                    async for chunk in enhanced_ai_service.stream_enhanced_response(
                        db, user_id, enhanced_messages, use_persona, model_id, temperature, max_tokens
                    ):
                        response_chunks.append(chunk)
                        yield chunk
                    
                    # Process any tool calls in the complete response
                    full_response = "".join(response_chunks)
                    if mcp_tools and self._contains_tool_calls(full_response):
                        tool_results = await self._execute_tool_calls(full_response, mcp_tools)
                        if tool_results:
                            yield f"\n\n{tool_results}"
                    
                    return
                except Exception as e:
                    logger.warning(f"Enhanced streaming failed, falling back: {e}")
            
            # Fallback: use existing AI service
            from app.services.ai import generate_ai_response
            response = await generate_ai_response(
                db, user_id, None, enhanced_messages, model_id, temperature, max_tokens, use_persona
            )
            
            # Process tool calls and stream the result
            final_response = await self._process_tool_calls(response, mcp_tools)
            
            # Simulate streaming by yielding chunks
            words = final_response.split()
            for word in words:
                yield f"{word} "
                import asyncio
                await asyncio.sleep(0.05)
            
        except Exception as e:
            logger.error(f"Error in enhanced AI streaming: {e}")
            yield f"Error: {str(e)}"
    
    async def _build_tool_enhanced_messages(
        self,
        messages: List[ChatMessage],
        user,
        use_persona: bool,
        db: AsyncSession,
        mcp_tools: Optional[MCPFinancialTools]
    ) -> List[ChatMessage]:
        """
        Build messages with tool descriptions for AI to use
        """
        try:
            # Build enhanced system prompt with tool capabilities
            system_prompt_parts = [
                f"You are an advanced AI financial advisor for {user.first_name or 'the user'}."
            ]
            
            # Add tool descriptions if MCP is enabled
            if mcp_tools and hasattr(user, 'phone_number') and user.phone_number:
                system_prompt_parts.append("""
AVAILABLE FINANCIAL DATA TOOLS:
You can call the following tools to get real-time financial data from the user's Fi Money account:

1. get_net_worth() - Get complete net worth including assets and liabilities
2. get_credit_score() - Get current credit score and rating
3. get_bank_transactions(limit=20) - Get recent bank transactions  
4. get_investment_portfolio() - Get investment portfolio details
5. get_epf_details() - Get EPF (Employee Provident Fund) details

TOOL CALLING FORMAT:
To use a tool, include in your response: [TOOL_CALL:tool_name(parameters)]
Example: [TOOL_CALL:get_net_worth()]
Example: [TOOL_CALL:get_bank_transactions(limit=10)]

The tool results will be automatically fetched and included in your response.
""")
            else:
                system_prompt_parts.append("""
Note: Fi Money integration is not available (no phone number linked).
You can still provide general financial advice based on the conversation.
""")
            
            # Add persona context if requested
            if use_persona:
                try:
                    from app.services.persona_engine import PersonaEngineService
                    persona_service = PersonaEngineService(db)
                    persona_profile = await persona_service.get_existing_persona_for_user(user)
                    
                    if persona_profile:
                        cultural_profile = persona_profile.cultural_profile if hasattr(persona_profile, 'cultural_profile') else {}
                        system_prompt_parts.append(f"""
USER PERSONA: {persona_profile.persona_name}
{persona_profile.persona_description}

Cultural Profile:
- Music Taste: {cultural_profile.get('music_taste', 'Not specified')}
- Entertainment Style: {cultural_profile.get('entertainment_style', 'Not specified')}
- Fashion Sensibility: {cultural_profile.get('fashion_sensibility', 'Not specified')}
- Dining Philosophy: {cultural_profile.get('dining_philosophy', 'Not specified')}

Financial Advice Style: {getattr(persona_profile, 'financial_advice_style', 'Standard advisory approach')}""")
                except Exception as e:
                    logger.warning(f"Persona integration failed: {e}")
            
            system_prompt_parts.extend([
                """
INSTRUCTIONS:
1. Assess what financial information you need based on the user's question
2. Use the appropriate tools to gather specific financial data when relevant
3. Provide concrete, actionable advice based on actual financial data when available
4. Use the user's name naturally in conversation
5. Ask clarifying questions when you need more context
6. Be empathetic and understanding of their financial journey

IMPORTANT: Only call tools when you actually need the financial data to answer the user's question. 
Don't call all tools at once - be selective based on the conversation context.
"""
            ])
            
            # Create enhanced system message
            enhanced_system_message = ChatMessage(
                role="system",
                content="\n\n".join(system_prompt_parts)
            )
            
            # Return enhanced messages with system prompt first
            return [enhanced_system_message] + messages
            
        except Exception as e:
            logger.error(f"Error building tool-enhanced messages: {e}")
            return messages
    
    async def _process_tool_calls(self, response: str, mcp_tools: Optional[MCPFinancialTools]) -> str:
        """
        Process tool calls in AI response and return enhanced response
        """
        if not mcp_tools or not self._contains_tool_calls(response):
            return response
        
        try:
            tool_results = await self._execute_tool_calls(response, mcp_tools)
            if tool_results:
                # Replace tool calls with results or append results
                return f"{response}\n\n{tool_results}"
            return response
        except Exception as e:
            logger.error(f"Error processing tool calls: {e}")
            return response
    
    def _contains_tool_calls(self, response: str) -> bool:
        """Check if response contains tool call patterns"""
        return "[TOOL_CALL:" in response
    
    async def _execute_tool_calls(self, response: str, mcp_tools: MCPFinancialTools) -> str:
        """
        Execute tool calls found in response and return formatted results
        """
        # Pattern to match tool calls: [TOOL_CALL:function_name(params)]
        tool_pattern = r'\[TOOL_CALL:(\w+)\(([^)]*)\)\]'
        tool_calls = re.findall(tool_pattern, response)
        
        if not tool_calls:
            return ""
        
        results = []
        available_tools = mcp_tools.get_available_tools()
        
        for tool_name, params in tool_calls:
            if tool_name in available_tools:
                try:
                    # Execute the tool
                    tool_func = available_tools[tool_name]
                    
                    # Parse parameters if any
                    if params.strip():
                        # Simple parameter parsing (can be enhanced)
                        if "limit=" in params:
                            limit_match = re.search(r'limit=(\d+)', params)
                            if limit_match:
                                result = await tool_func(limit=int(limit_match.group(1)))
                            else:
                                result = await tool_func()
                        else:
                            result = await tool_func()
                    else:
                        result = await tool_func()
                    
                    # Format result for display
                    if result.get("status") == "success":
                        formatted_result = self._format_tool_result(tool_name, result)
                        results.append(formatted_result)
                    else:
                        results.append(f"⚠️ {tool_name}: {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    logger.error(f"Error executing tool {tool_name}: {e}")
                    results.append(f"⚠️ Error executing {tool_name}: {str(e)}")
        
        return "\n\n".join(results) if results else ""
    
    def _format_tool_result(self, tool_name: str, result: Dict[str, Any]) -> str:
        """Format tool result for display"""
        if tool_name == "get_net_worth":
            total_net_worth = result.get('total_net_worth', 0)
            # Convert to int/float for formatting
            try:
                total_num = float(total_net_worth) if isinstance(total_net_worth, str) else total_net_worth
                return f"""💰 **Net Worth Summary**
Total: {total_num:,.0f} {result.get('currency', 'INR')}
Assets: {len(result.get('assets', []))} items
Liabilities: {len(result.get('liabilities', []))} items"""
            except (ValueError, TypeError):
                return f"""💰 **Net Worth Summary**
Total: {total_net_worth} {result.get('currency', 'INR')}
Assets: {len(result.get('assets', []))} items
Liabilities: {len(result.get('liabilities', []))} items"""
        
        elif tool_name == "get_credit_score":
            score = result.get('credit_score', 'N/A')
            rating = result.get('rating', 'Unknown')
            return f"""📊 **Credit Score**
Score: {score}
Rating: {rating}
Report Date: {result.get('report_date', 'Unknown')}"""
        
        elif tool_name == "get_bank_transactions":
            count = result.get('showing', 0)
            total = result.get('total_count', 0)
            return f"""🏦 **Recent Transactions**
Showing: {count} of {total} transactions
(Transaction details available for analysis)"""
        
        elif tool_name == "get_investment_portfolio":
            return f"""📈 **Investment Portfolio**
Portfolio data retrieved successfully
(Available for detailed analysis)"""
        
        elif tool_name == "get_epf_details":
            return f"""🏛️ **EPF Details**
EPF information retrieved successfully
(Available for retirement planning analysis)"""
        
        else:
            return f"✅ {tool_name}: Data retrieved successfully"

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
