#!/usr/bin/env python3
"""
Deployment verification script for ExoSense.
Checks that Railway (API) and Vercel (frontend) deployments are working.
"""

import asyncio
import sys
from typing import Optional

import httpx


async def check_api_health(api_url: str) -> bool:
    """Check if the API is healthy."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{api_url}/healthz", timeout=30.0)
            if response.status_code == 200:
                data = response.json()
                return data.get("status") == "ok"
            return False
    except Exception as e:
        print(f"API health check failed: {e}")
        return False


async def check_frontend(frontend_url: str) -> bool:
    """Check if the frontend is accessible."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(frontend_url, timeout=30.0)
            return response.status_code == 200
    except Exception as e:
        print(f"Frontend check failed: {e}")
        return False


async def main():
    """Main deployment verification."""
    # Replace with your actual deployment URLs
    API_URL = "https://your-railway-app.up.railway.app"
    FRONTEND_URL = "https://your-vercel-app.vercel.app"
    
    print("🚀 ExoSense Deployment Verification")
    print("=" * 40)
    
    # Check API
    print("Checking API health...")
    api_ok = await check_api_health(API_URL)
    print(f"API Status: {'✅ OK' if api_ok else '❌ FAILED'}")
    
    # Check frontend
    print("Checking frontend...")
    frontend_ok = await check_frontend(FRONTEND_URL)
    print(f"Frontend Status: {'✅ OK' if frontend_ok else '❌ FAILED'}")
    
    # Summary
    print("\n" + "=" * 40)
    if api_ok and frontend_ok:
        print("✅ All deployments are healthy!")
        sys.exit(0)
    else:
        print("❌ Some deployments have issues!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())