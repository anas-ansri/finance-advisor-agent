#!/usr/bin/env python3
"""
Simple connectivity test for the persona endpoints
"""
import asyncio
import httpx
import json

async def test_connectivity():
    """Test basic connectivity to the API"""
    
    print("🔗 Testing API Connectivity")
    print("=" * 40)
    
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        
        # Test 1: Basic server health
        print("\n1️⃣ Testing server health...")
        try:
            response = await client.get(f"{base_url}/")
            print(f"✅ Server responds: {response.status_code}")
        except Exception as e:
            print(f"❌ Server unreachable: {str(e)}")
            return
            
        # Test 2: Check if persona endpoint exists
        print("\n2️⃣ Testing persona endpoint accessibility...")
        try:
            response = await client.get(f"{base_url}/api/v1/conversations/persona-status")
            print(f"✅ Endpoint accessible: {response.status_code}")
            if response.status_code in [401, 403]:
                print("   (Auth required - this is expected)")
        except Exception as e:
            print(f"❌ Endpoint error: {str(e)}")
            
        # Test 3: Check CORS headers
        print("\n3️⃣ Testing CORS headers...")
        try:
            response = await client.options(f"{base_url}/api/v1/conversations/persona-status")
            headers = response.headers
            cors_headers = {k: v for k, v in headers.items() if 'access-control' in k.lower()}
            if cors_headers:
                print("✅ CORS headers present:")
                for header, value in cors_headers.items():
                    print(f"   {header}: {value}")
            else:
                print("⚠️  No CORS headers found")
        except Exception as e:
            print(f"❌ CORS test failed: {str(e)}")
            
        # Test 4: Check OpenAPI spec
        print("\n4️⃣ Testing OpenAPI documentation...")
        try:
            response = await client.get(f"{base_url}/openapi.json")
            if response.status_code == 200:
                openapi_data = response.json()
                persona_paths = [path for path in openapi_data.get('paths', {}).keys() if 'persona' in path]
                print(f"✅ OpenAPI accessible. Found {len(persona_paths)} persona endpoints:")
                for path in persona_paths:
                    print(f"   {path}")
            else:
                print(f"❌ OpenAPI not accessible: {response.status_code}")
        except Exception as e:
            print(f"❌ OpenAPI test failed: {str(e)}")

if __name__ == "__main__":
    print("Starting API Connectivity Tests...")
    
    try:
        asyncio.run(test_connectivity())
        print("\n🎉 Connectivity tests completed!")
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {str(e)}")
