"""
MCP Client Service for Financial Data Integration
Integrates with Fi MCP server to provide comprehensive financial context to AI
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import httpx
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class FinancialProfile:
    """Comprehensive financial profile from MCP server"""
    net_worth: Optional[Dict[str, Any]] = None
    credit_report: Optional[Dict[str, Any]] = None
    mutual_fund_transactions: Optional[List[Dict[str, Any]]] = None
    epf_details: Optional[Dict[str, Any]] = None
    bank_transactions: Optional[List[Dict[str, Any]]] = None
    investment_portfolio: Optional[Dict[str, Any]] = None

class MCPClient:
    """Client for interacting with Fi MCP server"""
    
    def __init__(self, mcp_server_url: str = None):
        self.server_url = mcp_server_url or getattr(settings, 'MCP_SERVER_URL', 'http://localhost:8080')
        self.session_id = None
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def authenticate(self, phone_number: str) -> bool:
        """Authenticate with MCP server using phone number"""
        try:
            # Generate session ID
            import uuid
            self.session_id = f"mcp-session-{uuid.uuid4()}"
            
            # Login request
            login_data = {
                "sessionId": self.session_id,
                "phoneNumber": phone_number
            }
            
            response = await self.client.post(
                f"{self.server_url}/login",
                data=login_data
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully authenticated with MCP server for phone: {phone_number}")
                return True
            else:
                logger.error(f"Authentication failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments or {}
                }
            }
            
            headers = {
                "Content-Type": "application/json",
                "X-Session-ID": self.session_id
            }
            
            response = await self.client.post(
                f"{self.server_url}/mcp/stream",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Tool call failed: {response.status_code} - {response.text}")
                return {"error": f"Tool call failed: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Tool call error: {e}")
            return {"error": str(e)}
    
    async def get_comprehensive_financial_profile(self, phone_number: str) -> FinancialProfile:
        """Get comprehensive financial profile from MCP server"""
        
        # Authenticate first
        if not await self.authenticate(phone_number):
            return FinancialProfile()
        
        profile = FinancialProfile()
        
        # Fetch net worth
        try:
            net_worth_response = await self.call_tool("fetch_net_worth")
            if "error" not in net_worth_response:
                profile.net_worth = net_worth_response.get("result", {})
        except Exception as e:
            logger.error(f"Error fetching net worth: {e}")
        
        # Fetch credit report
        try:
            credit_response = await self.call_tool("fetch_credit_report")
            if "error" not in credit_response:
                profile.credit_report = credit_response.get("result", {})
        except Exception as e:
            logger.error(f"Error fetching credit report: {e}")
        
        # Fetch mutual fund transactions
        try:
            mf_response = await self.call_tool("fetch_mutual_fund_transactions")
            if "error" not in mf_response:
                profile.mutual_fund_transactions = mf_response.get("result", {})
        except Exception as e:
            logger.error(f"Error fetching mutual fund transactions: {e}")
        
        # Fetch EPF details
        try:
            epf_response = await self.call_tool("fetch_epf_details")
            if "error" not in epf_response:
                profile.epf_details = epf_response.get("result", {})
        except Exception as e:
            logger.error(f"Error fetching EPF details: {e}")
        
        # Fetch bank transactions
        try:
            bank_response = await self.call_tool("fetch_bank_transactions")
            if "error" not in bank_response:
                profile.bank_transactions = bank_response.get("result", {})
        except Exception as e:
            logger.error(f"Error fetching bank transactions: {e}")
        
        return profile
    
    async def get_financial_summary_context(self, phone_number: str) -> str:
        """Get formatted financial context for AI prompts"""
        profile = await self.get_comprehensive_financial_profile(phone_number)
        
        context_parts = ["COMPREHENSIVE FINANCIAL PROFILE:"]
        
        # Net Worth Summary
        if profile.net_worth:
            net_worth_data = profile.net_worth.get("netWorthResponse", {})
            total_net_worth = net_worth_data.get("totalNetWorthValue", {})
            if total_net_worth:
                context_parts.append(f"Total Net Worth: ₹{total_net_worth.get('units', 'N/A')}")
            
            # Assets breakdown
            assets = net_worth_data.get("assetValues", [])
            if assets:
                context_parts.append("ASSETS:")
                for asset in assets:
                    asset_type = asset.get("netWorthAttribute", "")
                    value = asset.get("value", {}).get("units", 0)
                    context_parts.append(f"  - {asset_type}: ₹{value}")
            
            # Liabilities breakdown
            liabilities = net_worth_data.get("liabilityValues", [])
            if liabilities:
                context_parts.append("LIABILITIES:")
                for liability in liabilities:
                    liability_type = liability.get("netWorthAttribute", "")
                    value = liability.get("value", {}).get("units", 0)
                    context_parts.append(f"  - {liability_type}: ₹{value}")
        
        # Credit Score
        if profile.credit_report:
            credit_data = profile.credit_report.get("creditReportResponse", {})
            credit_score = credit_data.get("creditScore", {})
            if credit_score:
                score = credit_score.get("score", "N/A")
                context_parts.append(f"Credit Score: {score}")
        
        # Investment Portfolio Summary
        if profile.mutual_fund_transactions:
            mf_data = profile.mutual_fund_transactions.get("mutualFundTransactionsResponse", {})
            if mf_data:
                context_parts.append("MUTUAL FUND PORTFOLIO:")
                # Add MF portfolio analysis here
        
        # EPF Details
        if profile.epf_details:
            epf_data = profile.epf_details.get("epfDetailsResponse", {})
            if epf_data:
                context_parts.append("EPF ACCOUNT:")
                # Add EPF analysis here
        
        return "\n".join(context_parts)
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

# Global MCP client instance
mcp_client = MCPClient()

async def get_user_financial_context(user_id: UUID, db: AsyncSession) -> str:
    """
    Get comprehensive financial context for a user from MCP server
    This integrates with the user's Fi Money account via phone number
    """
    try:
        # Get user's phone number from database
        from app.services.user import get_user
        user = await get_user(db, user_id)
        
        if not user or not hasattr(user, 'phone_number') or not user.phone_number:
            return "No phone number available for MCP integration"
        
        # Get financial context from MCP server
        financial_context = await mcp_client.get_financial_summary_context(user.phone_number)
        
        return financial_context
        
    except Exception as e:
        logger.error(f"Error getting financial context for user {user_id}: {e}")
        return "Unable to retrieve financial context"

async def enhance_persona_with_mcp_data(user_id: UUID, db: AsyncSession) -> Dict[str, Any]:
    """
    Enhance persona generation with real financial data from MCP server
    """
    try:
        from app.services.user import get_user
        user = await get_user(db, user_id)
        
        if not user or not hasattr(user, 'phone_number') or not user.phone_number:
            return {}
        
        # Get comprehensive financial profile
        profile = await mcp_client.get_comprehensive_financial_profile(user.phone_number)
        
        # Extract key data points for persona enhancement
        enhancement_data = {
            "net_worth_tier": "high" if profile.net_worth and 
                             int(profile.net_worth.get("netWorthResponse", {}).get("totalNetWorthValue", {}).get("units", "0")) > 1000000 
                             else "medium",
            "investment_style": "aggressive" if profile.mutual_fund_transactions else "conservative",
            "debt_profile": "high" if profile.net_worth and 
                           profile.net_worth.get("netWorthResponse", {}).get("liabilityValues") else "low",
            "credit_health": "excellent" if profile.credit_report and 
                            int(profile.credit_report.get("creditReportResponse", {}).get("creditScore", {}).get("score", "0")) > 750
                            else "good"
        }
        
        return enhancement_data
        
    except Exception as e:
        logger.error(f"Error enhancing persona with MCP data: {e}")
        return {}
