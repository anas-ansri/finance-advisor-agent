import asyncio
import os
from typing import List
import uuid
from dotenv import load_dotenv
from supabase import create_client, Client
from gotrue.errors import AuthApiError

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.db.database import get_db, Base, engine
from app.models.user import User
from app.models.conversation import Conversation
from app.schemas.message import ChatMessage, ChatRequest
from app.schemas.user import UserCreate
from app.schemas.conversation import ConversationCreate
from app.services.ai import generate_ai_response
from app.services.conversation import create_conversation
from app.services.message import create_message
from app.services.user import create_user

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL", ""),
    os.getenv("SUPABASE_KEY", "")
)

# Create async session factory
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def setup_test_user(db: AsyncSession) -> User:
    """Create a test user with API key"""
    # First, create the user in Supabase
    email = f"anasalansari4@gmail.com"
    password = "TestPassword123!"
    
    try:
        # Sign up the user in Supabase
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        
        # Check if we have a user in the response
        if not auth_response.user:
            raise Exception("Failed to create user in Supabase: No user returned")
        
        # Get the user ID from Supabase
        user_id = auth_response.user.id
        
        # Create the user in our database
        user_create = UserCreate(
            email=email,
            first_name="Test",
            last_name="User",
            language="en",
            timezone="UTC",
            currency="USD"
        )
        test_user = await create_user(db, user_create)
        
        # Update the user with API key
        test_user.openai_api_key = os.getenv("OPENAI_API_KEY")
        await db.commit()
        await db.refresh(test_user)
        
        return test_user
        
    except AuthApiError as e:
        print(f"Supabase authentication error: {str(e)}")
        raise
    except Exception as e:
        print(f"Error creating test user: {str(e)}")
        raise

async def process_query(db: AsyncSession, user: User, conversation: Conversation, query: str) -> None:
    """Process a single query in the conversation"""
    print(f"\n{'='*50}")
    print(f"User: {query}")
    
    try:
        # Create chat request
        chat_request = ChatRequest(
            conversation_id=conversation.id,
            messages=[ChatMessage(role="user", content=query)]
        )
        
        # Get AI response
        response = await generate_ai_response(
            db=db,
            user_id=user.id,
            conversation_id=conversation.id,
            messages=chat_request.messages
        )
        
        print(f"AI: {response}")
        
    except Exception as e:
        print(f"Error processing query '{query}': {str(e)}")

async def test_conversation():
    """Test the conversation system with various queries"""
    async with async_session() as db:
        try:
            # Create test user
            user = await setup_test_user(db)
            
            # Create a new conversation
            conversation = await create_conversation(
                db,
                user_id=user.id,
                conversation_in=ConversationCreate(title="Test Conversation")
            )
            
            # Test queries
            test_queries = [
                # Financial queries
                "How much money did I spend last month?",
                "What are my current financial goals?",
                "Can you analyze my spending patterns?",
                
                # Non-financial queries
                "What's the weather like today?",
                "Tell me a joke",
                "What's the capital of France?",
                
                # Mixed context
                "I want to save money for a vacation to Paris. How much should I save?",
                "Can you help me plan my budget for next month?",
                "What's the best way to invest my savings?"
            ]
            
            # Process each query
            for query in test_queries:
                await process_query(db, user, conversation, query)
                # Add a small delay between requests
                await asyncio.sleep(1)
                
        except Exception as e:
            print(f"Error during test: {str(e)}")
            raise
        finally:
            await db.close()

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_conversation()) 