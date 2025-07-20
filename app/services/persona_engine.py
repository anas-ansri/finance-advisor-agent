import httpx
import google.generativeai as genai
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.models.user import User
from app.models.bank_transaction import BankTransaction
from app.models.persona_profile import PersonaProfile
from app.schemas.persona import PersonaProfileCreate

# Configure logging
logger = logging.getLogger(__name__)

class PersonaEngineService:
    """
    Service to generate and manage user Persona Profiles.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        # Configure the Gemini API client
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.llm = genai.GenerativeModel('gemini-1.5-flash')
        except Exception as e:
            logger.error(f"Failed to configure Gemini API: {e}")
            self.llm = None

    async def _get_transaction_entities(self, user: User) -> List[str]:
        """
        Fetches and cleans transaction descriptions to get unique, usable entities.
        For the MVP, we'll extract capitalized words, which often represent brands.
        A more robust solution would use NER or a dedicated cleaning service.
        """
        stmt = select(BankTransaction).where(BankTransaction.user_id == user.id).limit(100)
        result = await self.db.execute(stmt)
        transactions = result.scalars().all()
        
        entities = set()
        for trans in transactions:
            # Simple entity extraction: find capitalized words in the description
            words = trans.description.split()
            for word in words:
                if word.isupper() and len(word) > 2 and word.isalpha():
                    entities.add(word.lower().capitalize()) # Normalize the entity name
        
        logger.info(f"Extracted {len(entities)} entities for user {user.id}: {list(entities)[:10]}")
        return list(entities)[:20] # Limit to 20 entities to stay within API limits

    async def _call_qloo_api(self, entities: List[str]) -> Optional[Dict[str, Any]]:
        """
        Calls the Qloo API for taste correlation.
        """
        if not entities:
            logger.warning("No entities provided to Qloo API.")
            return None

        qloo_api_url = "https://api.qloo.com/v2/discover/taste-profile"
        headers = {
            "Authorization": f"Bearer {settings.QLOO_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "tastes": [{"type": "brand", "name": entity} for entity in entities]
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(qloo_api_url, json=payload, headers=headers, timeout=20.0)
                response.raise_for_status()
                logger.info(f"Qloo API call successful for entities: {entities}")
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error calling Qloo API: {e.response.status_code} - {e.response.text}")
                return None
            except Exception as e:
                logger.error(f"An unexpected error occurred calling Qloo API: {e}")
                return None

    def _generate_persona_prompt(self, qloo_data: Dict[str, Any]) -> str:
        """
        Creates a detailed prompt for the Gemini LLM based on Qloo's output.
        """
        prompt = f"""
        You are "Persona," a sophisticated AI financial wellness expert who understands lifestyle and culture.
        Your task is to analyze the following user taste profile data, which is derived from their spending habits and enriched by the Qloo cultural AI.
        Based on this data, you will create a warm, insightful, and empowering "Persona" profile for the user.

        Follow these instructions precisely:
        1.  **Analyze the Data**: Review the JSON data below to understand the user's core tastes across different domains like music, film, fashion, and dining.
        2.  **Create a Persona Name**: Synthesize the findings into a catchy, evocative persona name. Examples: "The Urban Explorer," "The Mindful Creative," "The Classic Connoisseur," "The Trendsetting Futurist." The name should be enclosed in double quotes.
        3.  **Write the Description**: Write a 2-paragraph description of this persona. The tone should be positive, insightful, and slightly aspirational. It should feel like a personalized reading that makes the user feel understood.
        4.  **Format the Output**: Your final output MUST be a JSON object with two keys: "persona_name" and "persona_description". Do not add any other text or explanation outside of this JSON object.

        Here is the user's taste profile data:
        ```json
        {qloo_data}
        ```

        Now, generate the JSON output.
        """
        return prompt

    def _call_gemini_api(self, prompt: str) -> Optional[Dict[str, str]]:
        """
        Calls the Gemini API to generate the narrative persona.
        """
        if not self.llm:
            logger.error("Gemini model not initialized.")
            return None
        try:
            response = self.llm.generate_content(prompt)
            response_text = response.text.strip().replace("```json", "").replace("```", "")
            
            import json
            persona_data = json.loads(response_text)
            
            if "persona_name" in persona_data and "persona_description" in persona_data:
                logger.info(f"Gemini API call successful. Generated Persona: {persona_data['persona_name']}")
                return persona_data
            else:
                logger.error(f"Gemini response did not contain required keys: {response_text}")
                return None

        except Exception as e:
            logger.error(f"An error occurred calling Gemini API: {e}")
            logger.error(f"Failed on response text: {response.text if 'response' in locals() else 'N/A'}")
            return None

    async def _save_persona_profile(self, user: User, persona_data: Dict[str, str], qloo_data: Dict[str, Any]) -> PersonaProfile:
        """
        Saves or updates the user's Persona Profile in the database.
        """
        stmt = select(PersonaProfile).where(PersonaProfile.user_id == user.id)
        result = await self.db.execute(stmt)
        existing_profile = result.scalar_one_or_none()
        
        if existing_profile:
            existing_profile.persona_name = persona_data["persona_name"]
            existing_profile.persona_description = persona_data["persona_description"]
            existing_profile.source_qloo_data = qloo_data
            await self.db.commit()
            await self.db.refresh(existing_profile)
            logger.info(f"Updated Persona Profile for user {user.id}")
            return existing_profile
        else:
            new_profile = PersonaProfile(
                user_id=user.id,
                persona_name=persona_data["persona_name"],
                persona_description=persona_data["persona_description"],
                source_qloo_data=qloo_data
            )
            self.db.add(new_profile)
            await self.db.commit()
            await self.db.refresh(new_profile)
            logger.info(f"Created new Persona Profile for user {user.id}")
            return new_profile

    async def generate_persona_for_user(self, user: User) -> Optional[PersonaProfile]:
        """
        The main orchestration method to generate a Persona Profile for a given user.
        """
        entities = await self._get_transaction_entities(user)
        if not entities:
            logger.warning(f"Could not generate Persona for user {user.id}: No transaction entities found.")
            return None

        qloo_data = None
        if settings.QLOO_API_KEY != "your_qloo_api_key_here":
            qloo_data = await self._call_qloo_api(entities)
        
        if not qloo_data:
            logger.warning("Qloo API call failed or was skipped. Using mock data for MVP.")
            qloo_data = {"mock_data": True, "input_entities": entities, "correlated_tastes": {"music": ["Indie Pop", "Lo-fi Beats"], "film": ["A24 Movies", "Documentaries"], "fashion": ["Streetwear", "Vintage"]}}

        prompt = self._generate_persona_prompt(qloo_data)
        persona_data = self._call_gemini_api(prompt)
        
        if not persona_data:
            logger.error(f"Could not generate Persona for user {user.id}: Gemini API call failed.")
            return None

        profile = await self._save_persona_profile(user, persona_data, qloo_data)
        
        return profile
