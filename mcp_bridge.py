#!/usr/bin/env python3
"""
TriForce MCP Bridge

Bridges stdio-based MCP protocol to TriForce HTTP API.
Usage: python mcp_bridge.py [--port 9000] [--host localhost]
"""

import sys
import json
import argparse
import requests
from typing import Any

class TriForceMCPBridge:
    def __init__(self, host: str = "localhost", port: int = 9000):
        self.base_url = f"http://{host}:{port}/v1/mcp"
        self.request_id = 0
    
    def call_triforce(self, method: str, params: dict = None) -> dict:
        """Call TriForce MCP endpoint"""
        self.request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": self.request_id
        }
        try:
            response = requests.post(self.base_url, json=payload, timeout=120)
            return response.json()
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32000, "message": str(e)},
                "id": self.request_id
            }
    
    def handle_request(self, request: dict) -> dict:
        """Handle incoming MCP request"""
        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id")
        
        # Forward to TriForce
        result = self.call_triforce(method, params)
        
        # Preserve original request ID
        if req_id is not None:
            result["id"] = req_id
        
        return result
    
    def run(self):
        """Main loop - read from stdin, write to stdout"""
        sys.stderr.write(f"TriForce MCP Bridge started -> {self.base_url}\n")
        sys.stderr.flush()
        
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            
            try:
                request = json.loads(line)
                response = self.handle_request(request)
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
            except json.JSONDecodeError as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32700, "message": f"Parse error: {e}"},
                    "id": None
                }
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()
            except Exception as e:
                sys.stderr.write(f"Error: {e}\n")
                sys.stderr.flush()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TriForce MCP Bridge")
    parser.add_argument("--host", default="localhost", help="TriForce host")
    parser.add_argument("--port", type=int, default=9000, help="TriForce port")
    args = parser.parse_args()
    
    bridge = TriForceMCPBridge(host=args.host, port=args.port)
    bridge.run()
