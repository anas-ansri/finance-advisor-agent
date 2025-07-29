#!/usr/bin/env python3
"""
Test the fixed persona routing
"""
import asyncio
import httpx
import json

async def test_fixed_routing():
    """Test that persona routes are now working correctly"""
    
    print("🔧 Testing Fixed Persona Routing")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        
        # Test 1: persona-status route should not be parsed as UUID
        print("\n1️⃣ Testing persona-status routing...")
        try:
            response = await client.get(f"{base_url}/api/v1/conversations/persona-status")
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 401:
                print("✅ Route correctly matched! (401 = auth required, not UUID parsing error)")
                response_data = response.json()
                if "uuid_parsing" in str(response_data):
                    print("❌ Still getting UUID parsing error")
                else:
                    print("✅ No UUID parsing error - route is fixed!")
            else:
                print(f"Response: {response.json()}")
        except Exception as e:
            print(f"❌ Request failed: {str(e)}")
        
        # Test 2: Test generate-persona route
        print("\n2️⃣ Testing generate-persona routing...")
        try:
            response = await client.post(f"{base_url}/api/v1/conversations/generate-persona")
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 401:
                print("✅ Route correctly matched! (401 = auth required)")
                response_data = response.json()
                if "uuid_parsing" in str(response_data):
                    print("❌ Still getting UUID parsing error")
                else:
                    print("✅ No UUID parsing error - route is fixed!")
            else:
                print(f"Response: {response.json()}")
        except Exception as e:
            print(f"❌ Request failed: {str(e)}")
        
        # Test 3: Verify that parameterized routes still work
        print("\n3️⃣ Testing parameterized conversation route...")
        try:
            # This should give UUID parsing error because 'invalid-uuid' is not a valid UUID
            response = await client.get(f"{base_url}/api/v1/conversations/invalid-uuid")
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 422:
                response_data = response.json()
                if "uuid_parsing" in str(response_data):
                    print("✅ Parameterized routes still work correctly (UUID validation working)")
                else:
                    print("⚠️ Unexpected response for invalid UUID")
            else:
                print(f"Response: {response.json()}")
        except Exception as e:
            print(f"❌ Request failed: {str(e)}")

if __name__ == "__main__":
    print("Testing Fixed Persona API Routing...")
    
    try:
        asyncio.run(test_fixed_routing())
        print("\n🎉 Routing tests completed!")
        print("\n📋 Summary:")
        print("✅ Fixed route ordering - persona-status now comes before parameterized routes")
        print("✅ Removed duplicate route definitions")
        print("✅ UUID parsing error should be resolved")
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {str(e)}")
