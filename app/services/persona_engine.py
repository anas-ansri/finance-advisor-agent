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
        Fetches and intelligently extracts meaningful entities from transaction descriptions.
        Focuses on brands, restaurants, and spending categories that reveal lifestyle preferences.
        """
        stmt = select(BankTransaction).filter(BankTransaction.user_id == user.id).limit(200)
        result = await self.db.execute(stmt)
        transactions = result.scalars().all()
        
        entities = set()
        
        # Known patterns for different entity types
        restaurant_patterns = ['RESTAURANT', 'CAFE', 'BAR', 'GRILL', 'KITCHEN', 'EATERY', 'DINER', 'BISTRO']
        retail_patterns = ['STORE', 'SHOP', 'OUTLET', 'MARKET', 'RETAIL', 'BOUTIQUE']
        service_patterns = ['SERVICES', 'SALON', 'SPA', 'GYM', 'FITNESS']
        
        for trans in transactions:
            description = trans.description.upper()
            words = description.split()
            
            # Extract potential brand/business names (capitalized sequences)
            for i, word in enumerate(words):
                if word.isupper() and len(word) > 2 and word.isalpha():
                    # Check if it's followed by a business type indicator
                    context_words = words[i:i+3] if i+3 <= len(words) else words[i:]
                    
                    # Prioritize restaurants and food establishments
                    if any(pattern in ' '.join(context_words) for pattern in restaurant_patterns):
                        entities.add(word.lower().capitalize())
                    # Then retail and shopping
                    elif any(pattern in ' '.join(context_words) for pattern in retail_patterns):
                        entities.add(word.lower().capitalize())
                    # Services and lifestyle
                    elif any(pattern in ' '.join(context_words) for pattern in service_patterns):
                        entities.add(word.lower().capitalize())
                    # Generic brand names (single meaningful words)
                    elif len(word) > 3 and word not in ['DEBIT', 'CREDIT', 'CARD', 'PAYMENT', 'TRANSFER', 'FROM', 'TO']:
                        entities.add(word.lower().capitalize())
            
            # Also extract from transaction categories if available
            if hasattr(trans, 'category') and trans.category:
                category_words = trans.category.replace('_', ' ').split()
                for word in category_words:
                    if len(word) > 3:
                        entities.add(word.lower().capitalize())
        
        # Filter out common banking terms and keep most relevant entities
        filtered_entities = []
        banking_terms = {'Transfer', 'Payment', 'Debit', 'Credit', 'Card', 'Bank', 'ATM', 'Fee', 'Charge'}
        
        for entity in entities:
            if entity not in banking_terms and len(entity) > 2:
                filtered_entities.append(entity)
        
        # Prioritize entities that appear multiple times (regular spending)
        entity_counts = {}
        for entity in filtered_entities:
            entity_counts[entity] = entity_counts.get(entity, 0) + 1
        
        # Sort by frequency and take top entities
        sorted_entities = sorted(entity_counts.keys(), key=lambda x: entity_counts[x], reverse=True)
        
        logger.info(f"Extracted {len(sorted_entities)} entities for user {user.id}: {sorted_entities[:10]}")
        return sorted_entities[:25]  # Increased limit for better Qloo matching

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

    def _analyze_insights_response(self, insights_result: Dict[str, Any], found_entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze the Qloo Insights API response to extract rich cultural connections.
        This method maps spending patterns to broader cultural interests.
        """
        analysis = {
            "cultural_connections": {},
            "taste_categories": {},
            "correlated_interests": {
                "music": [],
                "film": [],
                "fashion": [],
                "food": [],
                "lifestyle": []
            },
            "personality_indicators": []
        }
        
        # Process insights recommendations
        if "results" in insights_result:
            for result in insights_result["results"]:
                entity_name = result.get("name", "")
                entity_types = result.get("types", [])
                popularity = result.get("popularity", 0)
                tags = result.get("tags", [])
                
                # Categorize by entity types
                for entity_type in entity_types:
                    category = self._map_entity_type_to_category(entity_type)
                    if category:
                        if category not in analysis["taste_categories"]:
                            analysis["taste_categories"][category] = []
                        analysis["taste_categories"][category].append({
                            "name": entity_name,
                            "popularity": popularity
                        })
                
                # Extract cultural interests from tags
                for tag in tags:
                    tag_name = tag.get("name", "")
                    tag_type = tag.get("type", "")
                    
                    # Map tags to cultural categories
                    cultural_category = self._map_tag_to_cultural_category(tag_type, tag_name)
                    if cultural_category and tag_name:
                        analysis["correlated_interests"][cultural_category].append(tag_name)
        
        # Generate personality indicators from spending patterns
        analysis["personality_indicators"] = self._generate_personality_indicators(found_entities, analysis["taste_categories"])
        
        # Create cultural connections narrative
        analysis["cultural_connections"] = self._create_cultural_narrative(analysis["correlated_interests"])
        
        return analysis

    def _map_entity_type_to_category(self, entity_type: str) -> Optional[str]:
        """Map Qloo entity types to our cultural categories."""
        type_mapping = {
            "urn:entity:restaurant": "dining",
            "urn:entity:brand": "retail",
            "urn:entity:movie": "film",
            "urn:entity:music": "music",
            "urn:entity:person": "influencer",
            "urn:entity:book": "literature",
            "urn:entity:venue": "lifestyle",
            "urn:entity:product": "products"
        }
        return type_mapping.get(entity_type)

    def _map_tag_to_cultural_category(self, tag_type: str, tag_name: str) -> Optional[str]:
        """Map Qloo tags to cultural interest categories."""
        tag_mapping = {
            "urn:tag:genre": "music" if any(keyword in tag_name.lower() for keyword in ["pop", "rock", "hip", "jazz", "electronic"]) else "film",
            "urn:tag:style": "fashion",
            "urn:tag:cuisine": "food",
            "urn:tag:category": "lifestyle",
            "urn:tag:mood": "lifestyle"
        }
        return tag_mapping.get(tag_type)

    def _generate_personality_indicators(self, found_entities: List[Dict[str, Any]], taste_categories: Dict[str, Any]) -> List[str]:
        """Generate personality indicators from spending and taste patterns."""
        indicators = []
        
        # Analyze spending patterns
        if "dining" in taste_categories:
            dining_count = len(taste_categories["dining"])
            if dining_count > 3:
                indicators.append("Social and Experience-Oriented")
        
        if "retail" in taste_categories:
            retail_brands = taste_categories["retail"]
            premium_count = sum(1 for brand in retail_brands if brand.get("popularity", 0) > 50)
            if premium_count > 2:
                indicators.append("Quality-Conscious")
        
        # Analyze entity diversity
        entity_types = set()
        for entity in found_entities:
            entity_types.update(entity.get("types", []))
        
        if len(entity_types) > 5:
            indicators.append("Diverse Interests")
        
        return indicators[:5]  # Limit to top 5 indicators

    def _create_cultural_narrative(self, correlated_interests: Dict[str, List[str]]) -> Dict[str, str]:
        """Create narrative connections between spending and cultural interests."""
        narratives = {}
        
        if correlated_interests["music"]:
            narratives["music_connection"] = f"Your spending patterns suggest an affinity for {', '.join(correlated_interests['music'][:3])} music genres."
        
        if correlated_interests["film"]:
            narratives["film_connection"] = f"Based on your lifestyle choices, you likely enjoy {', '.join(correlated_interests['film'][:3])} films."
        
        if correlated_interests["fashion"]:
            narratives["fashion_connection"] = f"Your purchasing behavior indicates interest in {', '.join(correlated_interests['fashion'][:3])} fashion styles."
        
        return narratives

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
        Creates a detailed prompt for the Gemini LLM to generate a rich, culturally-aware persona.
        Uses Qloo's cultural mapping to create deeper, more nuanced financial profiles.
        """
        prompt = f"""
        You are "Persona," a sophisticated AI financial wellness expert who understands the deep connections between lifestyle, culture, and financial behavior.
        
        Your task is to analyze rich financial and cultural data to create a highly personalized "Persona" profile that captures not just spending patterns, but the cultural identity and values that drive those patterns.

        **CRITICAL INSTRUCTIONS:**
        1. **Analyze Holistically**: Consider spending patterns AND cultural correlations to understand the whole person
        2. **Cultural Context**: Use the correlated interests (music, film, fashion) to inform financial personality
        3. **Output Format**: Your response MUST be a single, valid JSON object with NO additional text
        4. **Depth Over Breadth**: Create insights that feel like they come from a personal advisor who truly knows the user

        **Required JSON Structure:**
        {{
            "persona_name": "A compelling persona name that captures their essence (e.g., 'The Conscious Curator', 'The Urban Wellness Seeker')",
            "persona_description": "Two rich paragraphs that weave together spending patterns and cultural identity. First paragraph: their lifestyle and values. Second paragraph: how this manifests in their relationship with money and financial decisions.",
            "key_traits": ["3-5 personality traits that blend financial behavior with cultural identity"],
            "lifestyle_summary": "A detailed paragraph describing their daily habits, weekend activities, cultural preferences, and what they value in experiences. Connect their spending to their lifestyle choices.",
            "financial_tendencies": "A comprehensive paragraph analyzing their financial mindset, spending priorities, and money philosophy. Explain WHY they spend the way they do based on their cultural identity and values.",
            "cultural_profile": {{
                "music_taste": "Brief description of their likely music preferences based on spending patterns",
                "entertainment_style": "What type of films, shows, or entertainment they gravitate toward",
                "fashion_sensibility": "Their approach to personal style and shopping",
                "dining_philosophy": "Their relationship with food and dining experiences"
            }},
            "financial_advice_style": "How this persona would prefer to receive financial advice (formal vs casual, data-driven vs story-based, etc.)"
        }}

        **Data Analysis:**
        Here is the comprehensive user profile data combining financial behavior and cultural correlations:

        ```json
        {json.dumps(qloo_data, indent=2)}
        ```

        **Context for Analysis:**
        - Input entities represent brands/places where the user spends money
        - Found entities show successful matches in Qloo's cultural database
        - Taste analysis reveals correlated interests across music, film, fashion, and lifestyle
        - Cultural connections map spending patterns to broader identity markers

        Generate the complete JSON persona profile that captures both their financial behavior AND cultural identity:
        """
        return prompt

    def _call_gemini_api(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Calls the Gemini API and validates the rich persona JSON response.
        """
        if not self.llm:
            logger.error("Gemini model not initialized.")
            return None
        try:
            response = self.llm.generate_content(prompt)
            response_text = response.text.strip().replace("```json", "").replace("```", "")
            
            persona_data = json.loads(response_text)
            
            # Validate the enhanced persona structure
            required_keys = [
                "persona_name", "persona_description", "key_traits", 
                "lifestyle_summary", "financial_tendencies", "cultural_profile", 
                "financial_advice_style"
            ]
            
            # Validate main structure
            if not all(key in persona_data for key in required_keys):
                missing_keys = [key for key in required_keys if key not in persona_data]
                logger.error(f"Gemini response missing keys: {missing_keys}")
                # Fallback to basic structure for backward compatibility
                basic_keys = ["persona_name", "persona_description", "key_traits", "lifestyle_summary", "financial_tendencies"]
                if all(key in persona_data for key in basic_keys):
                    logger.info("Using basic persona structure as fallback")
                    # Add missing fields with defaults
                    if "cultural_profile" not in persona_data:
                        persona_data["cultural_profile"] = {
                            "music_taste": "Eclectic and varied based on mood",
                            "entertainment_style": "Enjoys both mainstream and niche content",
                            "fashion_sensibility": "Practical with touches of personal style",
                            "dining_philosophy": "Values both convenience and quality experiences"
                        }
                    if "financial_advice_style" not in persona_data:
                        persona_data["financial_advice_style"] = "Prefers practical, actionable advice with clear explanations"
                else:
                    logger.error(f"Gemini response missing core required keys: {response_text}")
                    return None
            
            # Validate cultural_profile structure if present
            if "cultural_profile" in persona_data:
                cultural_keys = ["music_taste", "entertainment_style", "fashion_sensibility", "dining_philosophy"]
                if not all(key in persona_data["cultural_profile"] for key in cultural_keys):
                    logger.warning("Cultural profile incomplete, filling with defaults")
                    for key in cultural_keys:
                        if key not in persona_data["cultural_profile"]:
                            persona_data["cultural_profile"][key] = "To be determined based on further data"
            
            logger.info(f"Gemini API call successful. Generated Persona: {persona_data['persona_name']}")
            return persona_data

        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"An error occurred calling or parsing Gemini API response: {e}")
            logger.error(f"Failed on response text: {response.text if 'response' in locals() else 'N/A'}")
            return None

    async def _save_persona_profile(self, user: User, persona_data: Dict[str, Any], qloo_data: Dict[str, Any]) -> PersonaProfile:
        """
        Saves or updates the user's detailed Persona Profile with enhanced cultural data.
        """
        stmt = select(PersonaProfile).filter(PersonaProfile.user_id == user.id)
        result = await self.db.execute(stmt)
        existing_profile = result.scalar_one_or_none()
        
        if existing_profile:
            # Update existing profile with enhanced fields
            existing_profile.persona_name = persona_data["persona_name"]
            existing_profile.persona_description = persona_data["persona_description"]
            existing_profile.key_traits = persona_data["key_traits"]
            existing_profile.lifestyle_summary = persona_data["lifestyle_summary"]
            existing_profile.financial_tendencies = persona_data["financial_tendencies"]
            existing_profile.cultural_profile = persona_data.get("cultural_profile")
            existing_profile.financial_advice_style = persona_data.get("financial_advice_style")
            existing_profile.source_qloo_data = qloo_data
            await self.db.commit()
            await self.db.refresh(existing_profile)
            logger.info(f"Updated enhanced Persona Profile for user {user.id}: {existing_profile.persona_name}")
            return existing_profile
        else:
            # Create new profile with enhanced fields
            new_profile = PersonaProfile(
                user_id=user.id,
                persona_name=persona_data["persona_name"],
                persona_description=persona_data["persona_description"],
                key_traits=persona_data["key_traits"],
                lifestyle_summary=persona_data["lifestyle_summary"],
                financial_tendencies=persona_data["financial_tendencies"],
                cultural_profile=persona_data.get("cultural_profile"),
                financial_advice_style=persona_data.get("financial_advice_style"),
                source_qloo_data=qloo_data
            )
            self.db.add(new_profile)
            await self.db.commit()
            await self.db.refresh(new_profile)
            logger.info(f"Created new enhanced Persona Profile for user {user.id}: {new_profile.persona_name}")
            return new_profile

    async def get_existing_persona_for_user(self, user: User) -> Optional[PersonaProfile]:
        """
        Get existing persona profile for user without regenerating.
        """
        stmt = select(PersonaProfile).filter(PersonaProfile.user_id == user.id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def generate_persona_for_user(self, user: User, force_regenerate: bool = False) -> Optional[PersonaProfile]:
        """
        The main orchestration method to generate a Persona Profile for a given user.
        """
        # Check if persona already exists and force_regenerate is False
        if not force_regenerate:
            existing_profile = await self.get_existing_persona_for_user(user)
            if existing_profile:
                logger.info(f"Using existing persona profile for user {user.id}")
                return existing_profile

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
            logger.warning("Qloo API call failed or was skipped. Using enhanced mock data for development.")
            # Create more sophisticated mock data that mimics the expected structure
            qloo_data = {
                "input_entities": entities,
                "found_entities": [
                    {
                        "original_query": entities[0] if entities else "Starbucks",
                        "name": "Starbucks Coffee Company", 
                        "entity_id": "mock_001",
                        "types": ["urn:entity:restaurant", "urn:entity:brand"],
                        "properties": {"geocode": {"city": "Multiple", "country": "US"}},
                        "tags": [
                            {"name": "Coffee", "type": "urn:tag:category"},
                            {"name": "Quick Service", "type": "urn:tag:dining_options"},
                            {"name": "Urban", "type": "urn:tag:lifestyle"}
                        ],
                        "popularity": 85
                    }
                ],
                "taste_analysis": {
                    "entity_categories": {"dining": [{"name": "Starbucks", "popularity": 85}]},
                    "correlated_interests": {
                        "music": ["Indie Pop", "Lo-fi Hip Hop", "Alternative Rock"],
                        "film": ["Independent Films", "Documentaries", "Drama"],
                        "fashion": ["Casual Chic", "Streetwear", "Minimalist"],
                        "food": ["Artisanal Coffee", "Healthy Options", "International Cuisine"],
                        "lifestyle": ["Urban Living", "Work-Life Balance", "Sustainability"]
                    },
                    "personality_indicators": ["Quality-Conscious", "Urban Professional", "Experience-Oriented"],
                    "cultural_connections": {
                        "music_connection": "Your coffee shop preferences suggest an appreciation for indie and alternative music scenes.",
                        "lifestyle_connection": "Your spending indicates a preference for quality experiences over quantity."
                    }
                },
                "data_source": "mock_enhanced_data",
                "entity_count": len(entities)
            }

        prompt = self._generate_persona_prompt(qloo_data)
        persona_data = self._call_gemini_api(prompt)
        
        if not persona_data:
            logger.error(f"Could not generate Persona for user {user.id}: Gemini API call failed.")
            return None

        profile = await self._save_persona_profile(user, persona_data, qloo_data)  # Add await
        
        return profile

    async def _get_transaction_count(self, user_id: str) -> int:
        """
        Get the count of transactions for a user.
        """
        try:
            stmt = select(BankTransaction).filter(BankTransaction.user_id == user_id)
            result = await self.db.execute(stmt)
            transactions = result.scalars().all()
            return len(transactions)
        except Exception as e:
            logger.error(f"Error getting transaction count for user {user_id}: {str(e)}")
            return 0

