#!/usr/bin/env python3
"""
Test script for Persona API endpoints
"""
import asyncio
import httpx
import json
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_USER_ID = "test-user-123"
TEST_CONVERSATION_ID = "test-conv-456"

async def test_persona_endpoints():
    """Test the persona API endpoints directly"""
    
    print("🧪 Testing Persona API Endpoints")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        
        # Test 1: Check persona status
        print("\n1️⃣ Testing persona status endpoint...")
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/conversations/persona-status",
                params={"user_id": TEST_USER_ID}
            )
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                persona_data = response.json()
                print(f"✅ Persona Status Response:")
                print(json.dumps(persona_data, indent=2))
            else:
                print(f"❌ Error: {response.text}")
        except Exception as e:
            print(f"❌ Request failed: {str(e)}")
        
        # Test 2: Generate general persona
        print("\n2️⃣ Testing general persona generation...")
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/conversations/generate-persona",
                json={"user_id": TEST_USER_ID}
            )
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Persona Generation Result:")
                print(json.dumps(result, indent=2))
            else:
                print(f"❌ Error: {response.text}")
        except Exception as e:
            print(f"❌ Request failed: {str(e)}")
        
        # Test 3: Check persona status after generation
        print("\n3️⃣ Re-checking persona status...")
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/conversations/persona-status",
                params={"user_id": TEST_USER_ID}
            )
            if response.status_code == 200:
                persona_data = response.json()
                print(f"✅ Updated Persona Status:")
                print(f"Has Persona: {persona_data.get('has_persona')}")
                if persona_data.get('persona'):
                    persona = persona_data['persona']
                    print(f"Persona Name: {persona.get('persona_name')}")
                    print(f"Description: {persona.get('description', '')[:100]}...")
                    if persona.get('cultural_profile'):
                        print(f"Cultural Profile Keys: {list(persona['cultural_profile'].keys())}")
        except Exception as e:
            print(f"❌ Request failed: {str(e)}")

if __name__ == "__main__":
    print("Starting Persona API Tests...")
    print("Make sure the FastAPI server is running on http://localhost:8000")
    
    try:
        asyncio.run(test_persona_endpoints())
        print("\n🎉 API endpoint tests completed!")
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {str(e)}")
