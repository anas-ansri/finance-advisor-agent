"""
MCP Financial Insights API Endpoints
Provides comprehensive financial insights using MCP server data
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.db.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.mcp_ai_integration import mcp_ai_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/mcp-insights")
async def get_mcp_financial_insights(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get comprehensive financial insights using MCP server data
    """
    try:
        insights = await mcp_ai_service.get_financial_insights_with_mcp(db, current_user.id)
        
        return {
            "success": True,
            "insights": insights,
            "message": "Financial insights generated successfully using MCP data"
        }
    
    except Exception as e:
        logger.error(f"Error generating MCP insights for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate financial insights: {str(e)}"
        )

@router.get("/mcp-status")
async def get_mcp_integration_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Check MCP integration status for the current user
    """
    try:
        from app.services.mcp_client import mcp_client
        from app.services.user import get_user
        
        user = await get_user(db, current_user.id)
        
        # Check if user has phone number for MCP integration
        has_phone = hasattr(user, 'phone_number') and user.phone_number is not None
        
        if not has_phone:
            return {
                "mcp_enabled": False,
                "reason": "no_phone_number",
                "message": "Phone number required for MCP integration",
                "setup_required": True
            }
        
        # Test MCP connection
        try:
            # Try to authenticate with MCP server
            auth_success = await mcp_client.authenticate(user.phone_number)
            
            if auth_success:
                return {
                    "mcp_enabled": True,
                    "phone_number": user.phone_number,
                    "message": "MCP integration active and working",
                    "features_available": [
                        "Real-time net worth data",
                        "Credit score monitoring", 
                        "Investment portfolio analysis",
                        "EPF account details",
                        "Bank transaction analysis"
                    ]
                }
            else:
                return {
                    "mcp_enabled": False,
                    "reason": "authentication_failed",
                    "message": "Unable to authenticate with Fi Money MCP server",
                    "phone_number": user.phone_number
                }
        
        except Exception as mcp_error:
            return {
                "mcp_enabled": False,
                "reason": "connection_error",
                "message": f"MCP server connection failed: {str(mcp_error)}",
                "phone_number": user.phone_number
            }
    
    except Exception as e:
        logger.error(f"Error checking MCP status for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check MCP status: {str(e)}"
        )

@router.post("/setup-mcp")
async def setup_mcp_integration(
    phone_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Setup MCP integration for the user with their phone number
    """
    try:
        from app.services.user import update_user
        
        # Update user's phone number
        update_data = {"phone_number": phone_number}
        updated_user = await update_user(db, current_user.id, update_data)
        
        if not updated_user:
            raise HTTPException(status_code=400, detail="Failed to update user phone number")
        
        # Test MCP connection
        from app.services.mcp_client import mcp_client
        auth_success = await mcp_client.authenticate(phone_number)
        
        if auth_success:
            return {
                "success": True,
                "message": "MCP integration setup successfully",
                "phone_number": phone_number,
                "features_enabled": [
                    "Enhanced financial insights",
                    "Real-time portfolio data",
                    "Personalized investment advice",
                    "Credit score integration"
                ]
            }
        else:
            return {
                "success": False,
                "message": "Phone number updated but MCP authentication failed",
                "phone_number": phone_number,
                "note": "Please ensure this phone number is registered with Fi Money"
            }
    
    except Exception as e:
        logger.error(f"Error setting up MCP for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to setup MCP integration: {str(e)}"
        )

@router.get("/financial-summary")
async def get_comprehensive_financial_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get comprehensive financial summary from MCP server
    """
    try:
        from app.services.mcp_client import get_user_financial_context
        
        # Get detailed financial context
        financial_context = await get_user_financial_context(current_user.id, db)
        
        if financial_context == "No phone number available for MCP integration":
            return {
                "success": False,
                "message": "MCP integration not setup. Please add your phone number first.",
                "setup_required": True
            }
        
        if financial_context == "Unable to retrieve financial context":
            return {
                "success": False,
                "message": "Unable to retrieve financial data from Fi Money",
                "error": "mcp_connection_failed"
            }
        
        return {
            "success": True,
            "financial_summary": financial_context,
            "message": "Financial summary retrieved successfully",
            "last_updated": "Real-time from Fi Money"
        }
    
    except Exception as e:
        logger.error(f"Error getting financial summary for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get financial summary: {str(e)}"
        )
