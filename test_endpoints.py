import asyncio
import httpx
import uuid
from termcolor import cprint
import json
import os
import subprocess
import time
from sqlalchemy.ext.asyncio import create_async_engine

# Start server
backend_proc = subprocess.Popen(["uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"], cwd="backend", env={**os.environ, "DATABASE_URL": "sqlite+aiosqlite:///./test.db"})
time.sleep(3)

async def run_tests():
    try:
        report = {
            "working_routes": [],
            "broken_routes": [],
            "functional_features": [],
            "broken_features": [],
            "placeholder_pages": [],
            "api_errors": [],
            "recommended_fixes": []
        }
        
        async with httpx.AsyncClient(base_url="http://127.0.0.1:8000/api/v1") as client:
            # We don't have frontend routes loaded here, so we will test the API endpoints directly
            
            # PHASE 1
            # /history -> /user/history
            res = await client.get("/user/history")
            # Wait, authentication is needed!
            # Let's bypass auth or create a token...
            # Actually, I can't easily bypass Clerk authentication.
            
            # Since I can't easily test with auth in a script, let's look at the codebase.
            pass
            
    finally:
        backend_proc.terminate()

if __name__ == "__main__":
    asyncio.run(run_tests())