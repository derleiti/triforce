"""TriForce MCP Tools als native Upsonic Tools - Sync Wrapper"""
import requests
import json
from typing import Any, Dict, List, Optional

class TriForceMCP:
    """Synchroner Wrapper für TriForce MCP API"""
    
    def __init__(self, base_url: str = "http://localhost:9000"):
        self.base_url = base_url
        self.session = requests.Session()
        self._tools_cache = None
    
    def _call_mcp(self, method: str, params: Dict = None) -> Any:
        payload = {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": 1}
        resp = self.session.post(f"{self.base_url}/v1/mcp", json=payload, timeout=30)
        data = resp.json()
        if "error" in data:
            raise Exception(f"MCP Error: {data[error]}")
        return data.get("result")
    
    def list_tools(self) -> List[Dict]:
        if self._tools_cache is None:
            result = self._call_mcp("tools/list")
            self._tools_cache = result.get("tools", [])
        return self._tools_cache
    
    def call_tool(self, name: str, **kwargs) -> Any:
        return self._call_mcp(name, kwargs)
    
    def search(self, query: str) -> str:
        return self._call_mcp("web_search", {"query": query})
    
    def chat(self, message: str, model: str = "gemini") -> str:
        return self._call_mcp("chat_smart", {"message": message, "model": model})
    
    def memory_store(self, content: str, mem_type: str = "fact") -> str:
        return self._call_mcp("tristar_memory_store", {"content": content, "type": mem_type})
    
    def memory_search(self, query: str) -> list:
        return self._call_mcp("tristar_memory_search", {"query": query})
    
    def shell(self, command: str) -> str:
        return self._call_mcp("tristar_shell_exec", {"command": command})
    
    def ollama_health(self) -> Dict:
        return self._call_mcp("ollama_health")


if __name__ == "__main__":
    mcp = TriForceMCP()
    print("Testing TriForce MCP...")
    tools = mcp.list_tools()
    print(f"Found {len(tools)} tools")
    for t in tools[:5]:
        print(f"  - {t.get('name', '?')}")
    result = mcp.ollama_health()
    print(f"Ollama: {result}")
    print("Done!")
