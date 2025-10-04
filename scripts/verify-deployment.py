#!/usr/bin/env python3
"""
Deployment verification script for ExoSense Railway API.
Checks that the Railway backend deployment is working correctly.
"""

import asyncio
import sys

import httpx


async def check_api_health(api_url: str) -> bool:
    """Check if the API is healthy using /health endpoint."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{api_url}/health", timeout=30.0)
            if response.status_code == 200:
                data = response.json()
                return data.get("status") == "ok"
            return False
    except Exception as e:
        print(f"API health check failed: {e}")
        return False


async def check_api_root(api_url: str) -> bool:
    """Check if the API root endpoint is accessible."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, timeout=30.0)
            if response.status_code == 200:
                data = response.json()
                return "message" in data
            return False
    except Exception as e:
        print(f"API root check failed: {e}")
        return False


async def main():
    """Main deployment verification for Railway API."""
    # Replace with your actual Railway deployment URL
    API_URL = "https://your-railway-app.up.railway.app"
    
    print("🚀 ExoSense Railway API Verification")
    print("=" * 50)
    print(f"Target: {API_URL}")
    print("=" * 50)
    
    # Check API health endpoint
    print("\n1. Checking /health endpoint...")
    health_ok = await check_api_health(API_URL)
    print(f"   Status: {'✅ OK' if health_ok else '❌ FAILED'}")
    
    # Check API root endpoint
    print("\n2. Checking / (root) endpoint...")
    root_ok = await check_api_root(API_URL)
    print(f"   Status: {'✅ OK' if root_ok else '❌ FAILED'}")
    
    # Summary
    print("\n" + "=" * 50)
    if health_ok and root_ok:
        print("✅ Railway API deployment is healthy!")
        print("\nNext steps:")
        print("  - Test /analyze endpoint with sample data")
        print("  - Deploy frontend to Vercel")
        print("  - Update CORS origins in api/main.py")
        sys.exit(0)
    else:
        print("❌ Railway API deployment has issues!")
        print("\nTroubleshooting:")
        print("  - Check Railway logs for errors")
        print("  - Verify environment variables are set")
        print("  - Ensure dependencies installed correctly")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())