"""
Test script for the enhanced persona feature.
This script demonstrates the complete persona generation workflow.
"""

import asyncio
import logging
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.services.persona_engine import PersonaEngineService
from app.models.user import User
from app.models.bank_transaction import BankTransaction

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_persona_generation():
    """Test the complete persona generation workflow."""
    
    # Create async database connection
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # Find a user with transactions (you may need to adjust this query)
        from sqlalchemy import select
        
        # Get a user with some transactions
        user_stmt = select(User).limit(1)
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        if not user:
            logger.error("No users found in database. Please create a user first.")
            return
        
        logger.info(f"Testing persona generation for user: {user.id}")
        
        # Check if user has transactions
        trans_stmt = select(BankTransaction).filter(BankTransaction.user_id == user.id).limit(5)
        trans_result = await db.execute(trans_stmt)
        transactions = trans_result.scalars().all()
        
        logger.info(f"User has {len(transactions)} transactions")
        if len(transactions) == 0:
            logger.warning("User has no transactions. Persona will use mock data.")
        
        # Initialize persona service
        persona_service = PersonaEngineService(db)
        
        # Test entity extraction
        entities = await persona_service._get_transaction_entities(user)
        logger.info(f"Extracted entities: {entities}")
        
        # Test Qloo API call (will use mock data if API key not configured)
        qloo_data = await persona_service._call_qloo_api(entities[:5])
        if qloo_data:
            logger.info(f"Qloo data received: {qloo_data.get('data_source', 'unknown source')}")
            logger.info(f"Found entities: {len(qloo_data.get('found_entities', []))}")
        else:
            logger.warning("No Qloo data received")
        
        # Generate complete persona
        persona_profile = await persona_service.generate_persona_for_user(
            user, 
            force_regenerate=True
        )
        
        if persona_profile:
            logger.info("=" * 60)
            logger.info("PERSONA GENERATED SUCCESSFULLY!")
            logger.info("=" * 60)
            logger.info(f"Persona Name: {persona_profile.persona_name}")
            logger.info(f"Description: {persona_profile.persona_description}")
            logger.info(f"Key Traits: {persona_profile.key_traits}")
            logger.info(f"Lifestyle: {persona_profile.lifestyle_summary}")
            logger.info(f"Financial Tendencies: {persona_profile.financial_tendencies}")
            
            if hasattr(persona_profile, 'cultural_profile') and persona_profile.cultural_profile:
                logger.info(f"Cultural Profile: {json.dumps(persona_profile.cultural_profile, indent=2)}")
            
            if hasattr(persona_profile, 'financial_advice_style') and persona_profile.financial_advice_style:
                logger.info(f"Advice Style: {persona_profile.financial_advice_style}")
            
            logger.info("=" * 60)
        else:
            logger.error("Failed to generate persona")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_persona_generation())
