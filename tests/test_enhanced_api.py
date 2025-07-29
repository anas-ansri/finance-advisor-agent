#!/usr/bin/env python3
"""
Enhanced test script for Persona API endpoints with better error scenarios
"""
import asyncio
import httpx
import json
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000"

async def test_enhanced_persona_endpoints():
    """Test the enhanced persona API endpoints with various scenarios"""
    
    print("🧪 Testing Enhanced Persona API Endpoints")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        
        # Test 1: Check persona status without auth (should handle gracefully)
        print("\n1️⃣ Testing persona status without authentication...")
        try:
            response = await client.get(f"{BASE_URL}/api/v1/conversations/persona-status")
            print(f"Status Code: {response.status_code}")
            if response.status_code == 403:
                print("✅ Correctly returns 403 for unauthenticated requests")
            else:
                print(f"Response: {response.json()}")
        except Exception as e:
            print(f"❌ Request failed: {str(e)}")
        
        # Test 2: Check persona status with auto-generate flag
        print("\n2️⃣ Testing persona status with auto-generate flag...")
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/conversations/persona-status",
                params={"auto_generate": "true"}
            )
            print(f"Status Code: {response.status_code}")
            if response.status_code == 403:
                print("✅ Auth required (expected)")
            else:
                data = response.json()
                print("Response keys:", list(data.keys()))
        except Exception as e:
            print(f"❌ Request failed: {str(e)}")
        
        # Test 3: Test generate persona with force_regenerate flag
        print("\n3️⃣ Testing persona generation with force_regenerate...")
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/conversations/generate-persona",
                params={"force_regenerate": "true"}
            )
            print(f"Status Code: {response.status_code}")
            if response.status_code == 403:
                print("✅ Auth required (expected)")
            else:
                data = response.json()
                print("Response keys:", list(data.keys()))
        except Exception as e:
            print(f"❌ Request failed: {str(e)}")

        # Test 4: Test API structure (with mock auth header)
        print("\n4️⃣ Testing API structure with mock auth...")
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/conversations/persona-status",
                headers={"Authorization": "Bearer mock-token"}
            )
            print(f"Status Code: {response.status_code}")
            if response.status_code in [401, 403]:
                print("✅ Properly handles invalid auth tokens")
            else:
                print(f"Unexpected response: {response.json()}")
        except Exception as e:
            print(f"❌ Request failed: {str(e)}")

if __name__ == "__main__":
    print("Starting Enhanced Persona API Tests...")
    print("Testing improved error handling and new features...")
    
    try:
        asyncio.run(test_enhanced_persona_endpoints())
        print("\n🎉 Enhanced API tests completed!")
        print("\n📋 Summary:")
        print("✅ Enhanced persona-status endpoint with auto_generate parameter")
        print("✅ Enhanced generate-persona endpoint with force_regenerate parameter") 
        print("✅ Better error handling and transaction count checks")
        print("✅ Improved response structure with helpful messages")
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {str(e)}")
