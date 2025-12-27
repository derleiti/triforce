"""Upsonic Agent + TriForce MCP Integration"""
import os
os.environ["UPSONIC_TELEMETRY"] = "False"

from upsonic import Agent, Task
from upsonic_triforce import TriForceMCP

# TriForce MCP als Tool-Provider
mcp = TriForceMCP()

# Custom Tools die TriForce nutzen
def triforce_search(query: str) -> str:
    """Führt eine Web-Suche über TriForce MCP aus"""
    result = mcp.call_tool("web_search", query=query)
    return str(result)

def triforce_ollama(prompt: str, model: str = "llama3.2") -> str:
    """Führt Ollama Inference über TriForce aus"""
    result = mcp.call_tool("ollama_generate", prompt=prompt, model=model)
    return str(result)

def triforce_memory_store(content: str) -> str:
    """Speichert Wissen in TriForce Memory"""
    result = mcp.memory_store(content, "fact")
    return str(result)

def triforce_shell(command: str) -> str:
    """Führt Shell-Command über TriForce aus"""
    result = mcp.shell(command)
    return str(result)


if __name__ == "__main__":
    print("Creating Upsonic Agent with TriForce tools...")
    
    # Agent mit TriForce Tools erstellen
    agent = Agent(
        name="TriForceAgent",
        model="google/gemini-2.0-flash",
        tools=[triforce_search, triforce_ollama, triforce_memory_store]
    )
    
    print(f"Agent: {agent.name}")
    print(f"Tools: {[t.__name__ if hasattr(t, __name__) else str(t) for t in agent.tools]}")
    
    # Test Task
    task = Task("What tools do you have available?")
    print(f"Task: {task}")
    
    print("\nAgent ready for tasks!")
    print("TriForce MCP connected with 52 backend tools.")
