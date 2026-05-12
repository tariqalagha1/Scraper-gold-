import asyncio
import httpx

async def run():
    async with httpx.AsyncClient() as client:
        resp = await client.post("http://127.0.0.1:8001/api/v1/auth/login", data={"username": "test@example.com", "password": "Password123!"})
        token = resp.json().get("access_token")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "X-API-Key": "dev-api-key-change-me"
        }
        
        # trigger export
        resp = await client.post("http://127.0.0.1:8001/api/v1/exports", headers=headers, json={"run_id": "761a753e-f024-41bb-9052-8d979bb4fa45", "format": "excel"})
        print("Export:", resp.status_code, resp.text)
        

asyncio.run(run())
