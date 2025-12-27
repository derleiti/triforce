"""TriForce Native Agent - nutzt Ollama direkt"""
import os
import requests
os.environ["UPSONIC_TELEMETRY"] = "False"

class TriForceAgent:
    def __init__(self, name="TriForceAgent", model="ministral-3:3b"):
        self.name = name
        self.model = model
        self.ollama_url = "http://localhost:11434"
        self.tools = []
        
    def add_tool(self, func):
        self.tools.append(func)
        
    def do(self, task):
        prompt = task
        if self.tools:
            prompt += "\n\nTools: " + ", ".join(t.__name__ for t in self.tools)
        
        # Direkt Ollama aufrufen
        resp = requests.post(
            f"{self.ollama_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=120
        )
        data = resp.json()
        return data.get("response", str(data))

if __name__ == "__main__":
    print("Creating TriForce Native Agent...")
    agent = TriForceAgent(name="TestAgent", model="ministral-3:3b")
    print(f"Agent: {agent.name}, Model: {agent.model}")
    print("Running task...")
    result = agent.do("Sag Hallo auf Deutsch, nur ein kurzer Satz.")
    print(f"Result: {result}")
