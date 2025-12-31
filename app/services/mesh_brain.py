#!/usr/bin/env python3
"""
AILinux Mesh Brain v1.0
=======================

Verteiltes KI-Gehirn über mehrere Server-Nodes.
Orchestriert lokale Ollama-Instanzen zu einem kollektiven Brain.

Strategien:
- parallel: Alle Nodes antworten, beste wird gewählt
- consensus: Mehrere Antworten, Voting/Merge
- split: Aufgabe aufteilen, Ergebnisse zusammenführen
- fallback: Primary → Secondary bei Failure
- round_robin: Load Balancing zwischen Nodes
"""
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Literal
from enum import Enum
import httpx

logger = logging.getLogger("mesh_brain")

# =============================================================================
# Configuration
# =============================================================================

class Strategy(str, Enum):
    PARALLEL = "parallel"      # Alle gleichzeitig, beste Antwort
    CONSENSUS = "consensus"    # Mehrere Antworten, zusammenführen
    SPLIT = "split"           # Aufgabe aufteilen
    FALLBACK = "fallback"     # Primary → Secondary
    ROUND_ROBIN = "round_robin"  # Abwechselnd
    FASTEST = "fastest"       # Erste Antwort gewinnt

@dataclass
class BrainNode:
    """Ein Node im Mesh Brain"""
    node_id: str
    host: str
    port: int = 11434
    models: List[str] = field(default_factory=list)
    priority: int = 1  # Höher = bevorzugt
    healthy: bool = True
    last_latency_ms: float = 0
    
    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"
    
    async def check_health(self) -> bool:
        """Prüfe ob Node erreichbar"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                start = time.time()
                resp = await client.get(f"{self.base_url}/api/tags")
                self.last_latency_ms = (time.time() - start) * 1000
                
                if resp.status_code == 200:
                    data = resp.json()
                    self.models = [m["name"] for m in data.get("models", [])]
                    self.healthy = True
                    return True
        except Exception as e:
            logger.warning(f"Node {self.node_id} unhealthy: {e}")
        
        self.healthy = False
        return False
    
    async def generate(self, model: str, prompt: str, system: str = None, 
                      stream: bool = False, **kwargs) -> Dict[str, Any]:
        """Generiere Antwort von diesem Node"""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            **kwargs
        }
        if system:
            payload["system"] = system
        
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                start = time.time()
                resp = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                elapsed = (time.time() - start) * 1000
                self.last_latency_ms = elapsed
                
                if resp.status_code == 200:
                    result = resp.json()
                    result["_node_id"] = self.node_id
                    result["_latency_ms"] = elapsed
                    return result
                else:
                    return {"error": f"HTTP {resp.status_code}", "_node_id": self.node_id}
        
        except Exception as e:
            return {"error": str(e), "_node_id": self.node_id}

# =============================================================================
# Mesh Brain
# =============================================================================

class MeshBrain:
    """Verteiltes KI-Gehirn"""
    
    def __init__(self):
        self.nodes: Dict[str, BrainNode] = {}
        self._round_robin_index = 0
        self._initialized = False
        
        # Default Nodes
        self._default_nodes = [
            BrainNode("hetzner", "127.0.0.1", 11434, priority=2),
            BrainNode("backup", "10.10.0.3", 11434, priority=1),
        ]
    
    async def initialize(self):
        """Initialisiere alle Nodes"""
        if self._initialized:
            return
        
        logger.info("Mesh Brain initializing...")
        
        for node in self._default_nodes:
            if await node.check_health():
                self.nodes[node.node_id] = node
                logger.info(f"Node {node.node_id}: {len(node.models)} models, {node.last_latency_ms:.0f}ms")
        
        self._initialized = True
        logger.info(f"Mesh Brain ready: {len(self.nodes)} nodes active")
    
    def get_healthy_nodes(self) -> List[BrainNode]:
        """Alle gesunden Nodes"""
        return [n for n in self.nodes.values() if n.healthy]
    
    def find_model(self, model: str) -> List[BrainNode]:
        """Finde Nodes die ein Model haben"""
        nodes = []
        for node in self.get_healthy_nodes():
            # Exakter Match oder Prefix-Match (llama3.2 → llama3.2:3b)
            for m in node.models:
                if m == model or m.startswith(model):
                    nodes.append(node)
                    break
        return sorted(nodes, key=lambda n: -n.priority)
    
    async def think(self, prompt: str, model: str = None, system: str = None,
                   strategy: Strategy = Strategy.FALLBACK, **kwargs) -> Dict[str, Any]:
        """
        Denke nach - verteilt über das Mesh.
        
        Args:
            prompt: Die Eingabe
            model: Gewünschtes Model (oder auto-select)
            system: System-Prompt
            strategy: Ausführungsstrategie
        
        Returns:
            Antwort mit Metadaten
        """
        await self.initialize()
        
        if not self.nodes:
            return {"error": "No healthy nodes available"}
        
        # Model auswählen falls nicht angegeben
        if not model:
            model = self._select_default_model()
        
        # Nodes finden die das Model haben
        nodes = self.find_model(model)
        if not nodes:
            # Fallback: irgendein Model auf irgendeinem Node
            nodes = self.get_healthy_nodes()
            if nodes and nodes[0].models:
                model = nodes[0].models[0]
                logger.info(f"Model not found, using fallback: {model}")
        
        if not nodes:
            return {"error": f"No nodes have model {model}"}
        
        # Strategie ausführen
        if strategy == Strategy.PARALLEL:
            return await self._think_parallel(nodes, model, prompt, system, **kwargs)
        elif strategy == Strategy.FASTEST:
            return await self._think_fastest(nodes, model, prompt, system, **kwargs)
        elif strategy == Strategy.CONSENSUS:
            return await self._think_consensus(nodes, model, prompt, system, **kwargs)
        elif strategy == Strategy.ROUND_ROBIN:
            return await self._think_round_robin(nodes, model, prompt, system, **kwargs)
        else:  # FALLBACK
            return await self._think_fallback(nodes, model, prompt, system, **kwargs)
    
    def _select_default_model(self) -> str:
        """Wähle bestes verfügbares Model"""
        # Präferenz-Liste
        preferred = ["qwen2.5-coder:7b", "mistral:7b", "llama3.2:3b", "phi3:3.8b"]
        
        for model in preferred:
            if self.find_model(model):
                return model
        
        # Fallback: erstes verfügbares Model
        for node in self.get_healthy_nodes():
            if node.models:
                return node.models[0]
        
        return "llama3.2:3b"
    
    async def _think_fallback(self, nodes: List[BrainNode], model: str, 
                              prompt: str, system: str, **kwargs) -> Dict[str, Any]:
        """Primary → Secondary bei Failure"""
        for node in nodes:
            result = await node.generate(model, prompt, system, **kwargs)
            if "error" not in result:
                return result
            logger.warning(f"Node {node.node_id} failed, trying next...")
        
        return {"error": "All nodes failed"}
    
    async def _think_parallel(self, nodes: List[BrainNode], model: str,
                              prompt: str, system: str, **kwargs) -> Dict[str, Any]:
        """Alle gleichzeitig, wähle beste Antwort"""
        tasks = [node.generate(model, prompt, system, **kwargs) for node in nodes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter erfolgreiche
        valid = [r for r in results if isinstance(r, dict) and "error" not in r]
        
        if not valid:
            return {"error": "All parallel requests failed"}
        
        # Wähle längste/beste Antwort (einfache Heuristik)
        best = max(valid, key=lambda r: len(r.get("response", "")))
        best["_strategy"] = "parallel"
        best["_candidates"] = len(valid)
        return best
    
    async def _think_fastest(self, nodes: List[BrainNode], model: str,
                             prompt: str, system: str, **kwargs) -> Dict[str, Any]:
        """Erste Antwort gewinnt"""
        tasks = [
            asyncio.create_task(node.generate(model, prompt, system, **kwargs))
            for node in nodes
        ]
        
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        
        # Cancel pending
        for task in pending:
            task.cancel()
        
        for task in done:
            result = task.result()
            if "error" not in result:
                result["_strategy"] = "fastest"
                return result
        
        return {"error": "Fastest strategy failed"}
    
    async def _think_consensus(self, nodes: List[BrainNode], model: str,
                               prompt: str, system: str, **kwargs) -> Dict[str, Any]:
        """Mehrere Antworten, zusammenführen"""
        tasks = [node.generate(model, prompt, system, **kwargs) for node in nodes[:3]]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid = [r for r in results if isinstance(r, dict) and "error" not in r]
        
        if not valid:
            return {"error": "Consensus failed - no valid responses"}
        
        if len(valid) == 1:
            return valid[0]
        
        # Merge: Nimm die häufigsten Kernaussagen
        responses = [r.get("response", "") for r in valid]
        
        # Einfacher Consensus: längste Antwort + Info über Übereinstimmung
        best = max(valid, key=lambda r: len(r.get("response", "")))
        best["_strategy"] = "consensus"
        best["_responses"] = len(valid)
        best["_nodes"] = [r.get("_node_id") for r in valid]
        return best
    
    async def _think_round_robin(self, nodes: List[BrainNode], model: str,
                                 prompt: str, system: str, **kwargs) -> Dict[str, Any]:
        """Abwechselnd zwischen Nodes"""
        self._round_robin_index = (self._round_robin_index + 1) % len(nodes)
        node = nodes[self._round_robin_index]
        
        result = await node.generate(model, prompt, system, **kwargs)
        result["_strategy"] = "round_robin"
        return result
    
    async def get_status(self) -> Dict[str, Any]:
        """Status aller Nodes"""
        await self.initialize()
        
        # Refresh health
        for node in self.nodes.values():
            await node.check_health()
        
        return {
            "brain_version": "1.0",
            "total_nodes": len(self.nodes),
            "healthy_nodes": len(self.get_healthy_nodes()),
            "nodes": {
                node_id: {
                    "healthy": node.healthy,
                    "host": node.host,
                    "models": node.models,
                    "latency_ms": round(node.last_latency_ms, 2),
                    "priority": node.priority
                }
                for node_id, node in self.nodes.items()
            },
            "available_models": list(set(
                m for n in self.nodes.values() for m in n.models
            ))
        }

# =============================================================================
# Singleton
# =============================================================================

mesh_brain = MeshBrain()

# =============================================================================
# Test
# =============================================================================

async def test_brain():
    """Test das Mesh Brain"""
    brain = MeshBrain()
    
    print("=== Mesh Brain Status ===")
    status = await brain.get_status()
    print(json.dumps(status, indent=2))
    
    print("\n=== Test: Fallback Strategy ===")
    result = await brain.think(
        "Was ist 2+2? Antworte kurz.",
        strategy=Strategy.FALLBACK
    )
    print(f"Node: {result.get('_node_id')}")
    print(f"Response: {result.get('response', result.get('error'))[:200]}")
    
    print("\n=== Test: Parallel Strategy ===")
    result = await brain.think(
        "Erkläre Python in einem Satz.",
        strategy=Strategy.PARALLEL
    )
    print(f"Node: {result.get('_node_id')}, Candidates: {result.get('_candidates')}")
    print(f"Response: {result.get('response', result.get('error'))[:200]}")

if __name__ == "__main__":
    asyncio.run(test_brain())
