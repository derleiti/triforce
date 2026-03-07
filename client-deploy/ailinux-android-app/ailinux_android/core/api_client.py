"""
AILinux Android API Client
==========================
"""
import json
import logging
from typing import Optional, Dict, Any, List

import httpx

from .storage import SecureStorage

logger = logging.getLogger("ailinux.api")


class APIClient:
    """HTTP client for AILinux API"""

    BASE_URL = "https://api.ailinux.me"

    def __init__(self):
        self.base_url = self.BASE_URL
        self.user_id = ""
        self.token = ""
        self.tier = "free"
        self.client_id = ""
        self.storage = SecureStorage()
        self._load_credentials()

    def _load_credentials(self):
        """Load saved credentials"""
        try:
            data = self.storage.load("credentials")
            if data:
                self.user_id = data.get("user_id", "")
                self.token = data.get("token", "")
                self.tier = data.get("tier", "free")
                self.client_id = data.get("client_id", "")
        except Exception as e:
            logger.warning(f"Failed to load credentials: {e}")

    def _save_credentials(self):
        """Save credentials"""
        self.storage.save("credentials", {
            "user_id": self.user_id,
            "token": self.token,
            "tier": self.tier,
            "client_id": self.client_id,
        })

    def logout(self):
        """Clear credentials"""
        self.user_id = ""
        self.token = ""
        self.tier = "free"
        self.client_id = ""
        self.storage.delete("credentials")

    def _headers(self) -> Dict[str, str]:
        """Request headers"""
        headers = {
            "Content-Type": "application/json",
            "X-User-ID": self.user_id,
            "X-Client-ID": self.client_id,
            "X-Client-Platform": "android",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Dict = None,
        timeout: float = 60.0
    ) -> Dict[str, Any]:
        """Make HTTP request"""
        url = f"{self.base_url}{endpoint}"
        with httpx.Client(timeout=timeout, verify=True) as client:
            response = client.request(method, url, headers=self._headers(), json=data)
            response.raise_for_status()
            return response.json()

    def login(self, email: str, password: str) -> bool:
        """Login with email/password"""
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.base_url}/v1/auth/login",
                    json={"email": email, "password": password}
                )
                response.raise_for_status()
                result = response.json()

            self.user_id = result.get("user_id", "")
            self.token = result.get("token", "")
            self.tier = result.get("tier", "free")
            self.client_id = result.get("client_id", "")
            self._save_credentials()
            return True
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    def is_authenticated(self) -> bool:
        return bool(self.token)

    def chat(
        self,
        message: str,
        model: str = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """Send chat message"""
        data = {"message": message, "temperature": temperature}
        if model:
            data["model"] = model
        return self._request("POST", "/v1/client/chat", data, timeout=120.0)

    def get_models(self) -> Dict[str, Any]:
        """Get available models"""
        try:
            return self._request("GET", "/v1/client/models")
        except:
            return {"tier": "free", "model_count": 0, "models": []}

    def list_mcp_tools(self) -> List[Dict]:
        """List MCP tools"""
        try:
            result = self._request("GET", "/v1/client/mcp/tools")
            return result.get("tools", [])
        except:
            return []

    def call_mcp_tool(self, tool: str, params: Dict = None) -> Dict[str, Any]:
        """Call MCP tool"""
        return self._request("POST", "/v1/client/mcp/call", {
            "tool": tool, "params": params or {}
        })

    def register(self, email: str, password: str, name: str = None, beta_code: str = None) -> Dict[str, Any]:
        """Register new user"""
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.base_url}/v1/auth/register",
                    json={
                        "email": email,
                        "password": password,
                        "name": name,
                        "beta_code": beta_code
                    }
                )
                response.raise_for_status()
                result = response.json()
            
            # Auto-login nach Registrierung
            if result.get("success"):
                return self.login(email, password)
            return result
        except httpx.HTTPStatusError as e:
            error_detail = "Registration failed"
            try:
                error_detail = e.response.json().get("detail", str(e))
            except:
                pass
            logger.error(f"Registration failed: {error_detail}")
            return {"success": False, "error": error_detail}
        except Exception as e:
            logger.error(f"Registration failed: {e}")
            return {"success": False, "error": str(e)}
