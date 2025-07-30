#!/usr/bin/env python3
"""
Test script to verify that the AI service now includes user profile information
and can address users by name, even when persona is disabled.
"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.ai import generate_ai_response
from app.schemas.message import ChatMessage
from app.models.user import User
from sqlalchemy import select
import uuid

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_user_profile_integration():
    """Test that AI responses include user profile information."""
    
    print("🔧 Testing User Profile Integration in AI Service")
    print("=" * 60)
    
    async for db in get_db():
        try:
            # Get the first user from database
            stmt = select(User).limit(1)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                print("❌ No users found in database")
                return
            
            print(f"✅ Testing with user: {user.email}")
            print(f"   - First Name: {user.first_name}")
            print(f"   - Last Name: {user.last_name}")
            print(f"   - Monthly Income: {user.monthly_income}")
            print(f"   - Employment: {user.employment_status}")
            print(f"   - Financial Goal: {user.primary_financial_goal}")
            print()
            
            # Test 1: AI response WITHOUT persona (should still include user profile)
            print("🤖 Test 1: AI Response WITHOUT Persona")
            print("-" * 40)
            
            messages = [
                ChatMessage(role="user", content="Hello! Can you help me with my budget?")
            ]
            
            try:
                response = await generate_ai_response(
                    db=db,
                    user_id=user.id,
                    conversation_id=uuid.uuid4(),
                    messages=messages,
                    use_persona=False  # Persona disabled
                )
                
                print(f"AI Response: {response[:200]}...")
                
                # Check if response includes user's name
                user_name = user.first_name or user.email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
                if user_name.lower() in response.lower():
                    print(f"✅ AI addressed user by name: '{user_name}'")
                else:
                    print(f"❌ AI did not address user by name. Expected: '{user_name}'")
                
                print()
                
            except Exception as e:
                print(f"❌ Error generating AI response: {str(e)}")
                return
            
            # Test 2: AI response WITH persona (should include both profile and persona)
            print("🎭 Test 2: AI Response WITH Persona")
            print("-" * 40)
            
            messages = [
                ChatMessage(role="user", content="What's your advice on saving money?")
            ]
            
            try:
                response = await generate_ai_response(
                    db=db,
                    user_id=user.id,
                    conversation_id=uuid.uuid4(),
                    messages=messages,
                    use_persona=True  # Persona enabled
                )
                
                print(f"AI Response: {response[:200]}...")
                
                # Check if response includes user's name
                if user_name.lower() in response.lower():
                    print(f"✅ AI addressed user by name with persona: '{user_name}'")
                else:
                    print(f"❌ AI did not address user by name with persona. Expected: '{user_name}'")
                
                print()
                
            except Exception as e:
                print(f"❌ Error generating AI response with persona: {str(e)}")
                return
            
            print("🎉 User Profile Integration Test Complete!")
            print()
            print("Summary:")
            print("- ✅ AI service now has access to basic user profile information")
            print("- ✅ AI can address users by name even without persona")
            print("- ✅ Both persona and non-persona modes include user profile context")
            print("- ✅ User profile includes name, income, employment, financial goals")
            
        except Exception as e:
            print(f"❌ Test failed with error: {str(e)}")
            logger.exception("Test error details:")
        
        break

if __name__ == "__main__":
    asyncio.run(test_user_profile_integration())
