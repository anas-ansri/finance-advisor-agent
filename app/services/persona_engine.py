import httpx
import google.generativeai as genai
import logging
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession  # Add this import
from sqlalchemy import select  # Add this import
from typing import List, Dict, Any, Optional
import json

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

    def __init__(self, db: AsyncSession):  # Change to AsyncSession
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
        """
        stmt = select(BankTransaction).filter(BankTransaction.user_id == user.id).limit(100)
        result = await self.db.execute(stmt)
        transactions = result.scalars().all()
        
        entities = set()
        for trans in transactions:
            words = trans.description.split()
            for word in words:
                if word.isupper() and len(word) > 2 and word.isalpha():
                    entities.add(word.lower().capitalize())
        
        logger.info(f"Extracted {len(entities)} entities for user {user.id}: {list(entities)[:10]}")
        return list(entities)[:20]

    async def _call_qloo_api(self, entities: List[str]) -> Optional[Dict[str, Any]]:
        """
        Calls the Qloo Insights API for taste analysis using entity inputs.
        Uses the proper /v2/insights endpoint with signal.interests.entities parameter
        for taste-based insights and recommendations.
        """
        if not entities:
            logger.warning("No entities provided to Qloo API.")
            return None

        # Check if API key is properly configured
        if not settings.QLOO_API_KEY or settings.QLOO_API_KEY.strip() == "" or settings.QLOO_API_KEY == "your_qloo_api_key_here":
            logger.warning(f"QLOO_API_KEY is not properly configured. Value: '{settings.QLOO_API_KEY}'. Skipping Qloo API call.")
            return None

        api_key = settings.QLOO_API_KEY.strip()
        headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json"
        }
        
        logger.info(f"Using Qloo API key of length: {len(api_key)}")

        async with httpx.AsyncClient() as client:
            try:
                # First, search for entity IDs to use in insights call
                search_url = "https://hackathon.api.qloo.com/search"
                found_entity_ids = []
                found_entities = []
                
                for entity in entities[:5]:  # Limit to first 5 entities
                    search_params = {"query": entity}
                    logger.info(f"Searching for entity: {entity}")
                    
                    search_response = await client.get(search_url, params=search_params, headers=headers, timeout=15.0)
                    if search_response.status_code == 200:
                        search_result = search_response.json()
                        if "results" in search_result and search_result["results"]:
                            # Take the first (most relevant) result
                            best_match = search_result["results"][0]
                            entity_id = best_match.get("entity_id")
                            if entity_id:
                                found_entity_ids.append(entity_id)
                                found_entities.append({
                                    "original_query": entity,
                                    "name": best_match.get("name"),
                                    "entity_id": entity_id,
                                    "types": best_match.get("types", []),
                                    "properties": best_match.get("properties", {}),
                                    "tags": best_match.get("tags", [])[:10],
                                    "popularity": best_match.get("popularity", 0)
                                })
                                logger.info(f"Found entity ID {entity_id} for {entity}: {best_match.get('name')}")
                
                if not found_entity_ids:
                    logger.warning("No entity IDs found from search")
                    return None
                
                # Now call insights API with the found entity IDs
                insights_url = "https://hackathon.api.qloo.com/v2/insights"
                insights_params = {
                    "signal.interests.entities": ",".join(found_entity_ids),
                    "filter.type": "urn:entity",  # Get entity recommendations
                    "limit": 20  # Limit results for better performance
                }
                
                logger.info(f"Calling insights API with entity IDs: {found_entity_ids}")
                insights_response = await client.get(insights_url, params=insights_params, headers=headers, timeout=15.0)
                
                if insights_response.status_code == 200:
                    insights_result = insights_response.json()
                    
                    # Build comprehensive taste profile
                    taste_profile = {
                        "input_entities": entities,
                        "found_entities": found_entities,
                        "insights_data": insights_result,
                        "taste_analysis": self._analyze_insights_response(insights_result, found_entities),
                        "data_source": "qloo_insights",
                        "entity_count": len(found_entities)
                    }
                    
                    logger.info(f"Qloo Insights API call successful for {len(found_entity_ids)} entities")
                    return taste_profile
                else:
                    logger.warning(f"Insights API call failed with status {insights_response.status_code}: {insights_response.text}")
                    # Fallback to search-based analysis
                    taste_profile = {
                        "input_entities": entities,
                        "found_entities": found_entities,
                        "taste_analysis": self._analyze_taste_profile(found_entities),
                        "data_source": "qloo_search_fallback",
                        "entity_count": len(found_entities)
                    }
                    return taste_profile
                    
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error calling Qloo API: {e.response.status_code} - {e.response.text}")
                return None
            except ValueError as e:
                logger.error(f"Invalid header value error calling Qloo API: {e}")
                logger.error(f"Headers were: {headers}")
                return None
            except Exception as e:
                logger.error(f"An unexpected error occurred calling Qloo API: {e}")
                logger.error(f"Error type: {type(e).__name__}")
                return None

    def _analyze_taste_profile(self, found_entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze the found entities to extract taste insights.
        """
        if not found_entities:
            return {}
        
        # Extract categories from entity types and tags
        categories = {}
        tags_by_type = {}
        locations = []
        
        for entity in found_entities:
            # Analyze entity types
            for entity_type in entity.get("types", []):
                if entity_type not in categories:
                    categories[entity_type] = 0
                categories[entity_type] += 1
            
            # Analyze tags
            for tag in entity.get("tags", []):
                tag_type = tag.get("type", "unknown")
                if tag_type not in tags_by_type:
                    tags_by_type[tag_type] = []
                tags_by_type[tag_type].append(tag.get("name", "unknown"))
            
            # Extract location info
            properties = entity.get("properties", {})
            if "geocode" in properties:
                geocode = properties["geocode"]
                location_info = f"{geocode.get('city', '')}, {geocode.get('country', '')}"
                if location_info.strip(", "):
                    locations.append(location_info.strip(", "))
        
        return {
            "entity_categories": categories,
            "common_tags": tags_by_type,
            "locations": list(set(locations)),
            "insights": self._generate_insights_from_tags(tags_by_type)
        }
    
    def _generate_insights_from_tags(self, tags_by_type: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        Generate lifestyle insights from tag patterns.
        """
        insights = {
            "dining_preferences": [],
            "lifestyle_traits": [],
            "interests": [],
            "values": []
        }
        
        # Map tag types to insight categories
        tag_mapping = {
            "urn:tag:offerings": "dining_preferences",
            "urn:tag:dining_options": "dining_preferences", 
            "urn:tag:genre": "interests",
            "urn:tag:category": "interests",
            "urn:tag:inclusivity": "values",
            "urn:tag:amenity": "lifestyle_traits"
        }
        
        for tag_type, tag_names in tags_by_type.items():
            insight_category = tag_mapping.get(tag_type)
            if insight_category:
                insights[insight_category].extend(tag_names[:3])  # Limit to 3 per category
        
        return insights

    def _generate_persona_prompt(self, qloo_data: Dict[str, Any]) -> str:
        """
        Creates a detailed prompt for the Gemini LLM to generate a structured, detailed persona.
        """
        prompt = f"""
        You are "Persona," a sophisticated AI financial wellness expert who understands lifestyle and culture.
        Your task is to analyze the following user taste profile data to create a warm, insightful, and empowering "Persona" profile.

        Follow these instructions precisely:
        1.  **Analyze the Data**: Review the JSON data below to understand the user's core tastes.
        2.  **Format the Output**: Your final output MUST be a single, valid JSON object. Do not add any text or explanation outside of this JSON object.
        3.  **JSON Structure**: The JSON object must contain the following keys:
            - "persona_name": A catchy, evocative persona name (e.g., "The Urban Explorer," "The Mindful Creative").
            - "persona_description": A 2-paragraph summary of the persona. The tone should be positive, insightful, and slightly aspirational.
            - "key_traits": A JSON array of 3-5 single-word strings that describe the core personality traits (e.g., ["Curious", "Authentic", "Adventurous"]).
            - "lifestyle_summary": A detailed paragraph describing their likely day-to-day habits, weekend activities, and what they value in experiences.
            - "financial_tendencies": A detailed paragraph analyzing their likely financial behavior, mindset towards money, and what they prioritize spending on.

        Here is the user's taste profile data:
        ```json
        {json.dumps(qloo_data, indent=2)}
        ```

        Now, generate the complete JSON output.
        """
        return prompt

    def _call_gemini_api(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Calls the Gemini API and validates the structured JSON response.
        """
        if not self.llm:
            logger.error("Gemini model not initialized.")
            return None
        try:
            response = self.llm.generate_content(prompt)
            response_text = response.text.strip().replace("```json", "").replace("```", "")
            
            persona_data = json.loads(response_text)
            
            # --- Validate the new detailed structure ---
            required_keys = ["persona_name", "persona_description", "key_traits", "lifestyle_summary", "financial_tendencies"]
            if all(key in persona_data for key in required_keys):
                logger.info(f"Gemini API call successful. Generated Persona: {persona_data['persona_name']}")
                return persona_data
            else:
                logger.error(f"Gemini response was missing one or more required keys: {response_text}")
                return None

        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"An error occurred calling or parsing Gemini API response: {e}")
            logger.error(f"Failed on response text: {response.text if 'response' in locals() else 'N/A'}")
            return None

    async def _save_persona_profile(self, user: User, persona_data: Dict[str, Any], qloo_data: Dict[str, Any]) -> PersonaProfile:
        """
        Saves or updates the user's detailed Persona Profile in the database.
        """
        stmt = select(PersonaProfile).filter(PersonaProfile.user_id == user.id)
        result = await self.db.execute(stmt)
        existing_profile = result.scalar_one_or_none()
        
        if existing_profile:
            # Update existing profile with new detailed fields
            existing_profile.persona_name = persona_data["persona_name"]
            existing_profile.persona_description = persona_data["persona_description"]
            existing_profile.key_traits = persona_data["key_traits"]
            existing_profile.lifestyle_summary = persona_data["lifestyle_summary"]
            existing_profile.financial_tendencies = persona_data["financial_tendencies"]
            existing_profile.source_qloo_data = qloo_data
            await self.db.commit()
            await self.db.refresh(existing_profile)
            logger.info(f"Updated Persona Profile for user {user.id}")
            return existing_profile
        else:
            # Create new profile with new detailed fields
            new_profile = PersonaProfile(
                user_id=user.id,
                persona_name=persona_data["persona_name"],
                persona_description=persona_data["persona_description"],
                key_traits=persona_data["key_traits"],
                lifestyle_summary=persona_data["lifestyle_summary"],
                financial_tendencies=persona_data["financial_tendencies"],
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
        entities = await self._get_transaction_entities(user)  # Add await
        if not entities:
            logger.warning(f"Could not generate Persona for user {user.id}: No transaction entities found.")
            return None

        qloo_data = None
        # Using Qloo Hackathon API server
        qloo_api_enabled = True  # Re-enabled with correct hackathon server URL
        
        if (qloo_api_enabled and 
            settings.QLOO_API_KEY and 
            settings.QLOO_API_KEY.strip() and 
            settings.QLOO_API_KEY != "your_qloo_api_key_here"):
            logger.info(f"Calling Qloo Hackathon API for user {user.id} with entities: {entities}")
            qloo_data = await self._call_qloo_api(entities)
            if not qloo_data:
                logger.warning(f"Qloo API call failed for user {user.id}. This could be due to an invalid API key, API quota exceeded, or service unavailable.")
        else:
            logger.info(f"Qloo API disabled or not configured. Using mock data for user {user.id}.")
        
        if not qloo_data:
            logger.warning("Qloo API call failed or was skipped. Using mock data for MVP.")
            qloo_data = {"mock_data": True, "input_entities": entities, "correlated_tastes": {"music": ["Indie Pop", "Lo-fi Beats"], "film": ["A24 Movies", "Documentaries"], "fashion": ["Streetwear", "Vintage"]}}

        prompt = self._generate_persona_prompt(qloo_data)
        persona_data = self._call_gemini_api(prompt)
        
        if not persona_data:
            logger.error(f"Could not generate Persona for user {user.id}: Gemini API call failed.")
            return None

        profile = await self._save_persona_profile(user, persona_data, qloo_data)  # Add await
        
        return profile

