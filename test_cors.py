#!/usr/bin/env python3
"""
Simple script to test CORS configuration on the server.
"""
import requests
import json

def test_cors():
    """Test CORS configuration by making requests to the server."""
    base_url = "http://localhost:8000"
    
    print("Testing CORS configuration...")
    
    # Test 1: OPTIONS preflight request
    print("\n1. Testing OPTIONS preflight request:")
    try:
        response = requests.options(f"{base_url}/api/gaia/run")
        print(f"Status Code: {response.status_code}")
        print("Headers:")
        for header, value in response.headers.items():
            if 'access-control' in header.lower():
                print(f"  {header}: {value}")
    except requests.exceptions.ConnectionError:
        print("  ❌ Connection failed - server might not be running")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    
    # Test 2: Actual POST request
    print("\n2. Testing POST request:")
    try:
        headers = {
            'Content-Type': 'application/json',
            'Origin': 'https://fubea.cloud'  # Simulate the origin that was blocked
        }
        data = {
            "set_to_run": "validation",
            "run_name": "cors-test",
            "max_tasks": 1
        }
        
        response = requests.post(
            f"{base_url}/api/gaia/run", 
            headers=headers,
            json=data,
            timeout=10
        )
        print(f"Status Code: {response.status_code}")
        print("CORS Headers in Response:")
        for header, value in response.headers.items():
            if 'access-control' in header.lower():
                print(f"  {header}: {value}")
        
        if response.status_code == 200:
            print("  ✅ Request successful!")
        else:
            print(f"  ⚠️  Request returned status {response.status_code}")
            print(f"  Response: {response.text[:200]}...")
            
    except requests.exceptions.ConnectionError:
        print("  ❌ Connection failed - server might not be running")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_cors()
    if success:
        print("\n✅ CORS test completed successfully!")
    else:
        print("\n❌ CORS test failed!") 