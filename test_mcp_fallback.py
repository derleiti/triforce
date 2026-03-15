
import asyncio
import httpx
import json

async def test_fallback():
    url = "http://localhost:9000/v1/mcp/messages"
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "llm.invoke",
            "arguments": {
                "model": "ollama/qwen2.5:14b",
                "messages": [{"role": "user", "content": "Say hello world briefly"}]
            }
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"Calling MCP with method 'llm.invoke' (should fallback to API)...")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                print("Response JSON:")
                print(json.dumps(resp.json(), indent=2))
            else:
                print(f"Error Body: {resp.text}")
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_fallback())
