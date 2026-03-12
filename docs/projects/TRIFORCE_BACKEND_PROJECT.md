# Project TriForce Backend (AILinux)

Version: `v0.7.0-beta`

Diese Seite ist als Einstieg für Menschen gedacht, die nicht nur "API nutzen", sondern verstehen wollen, wie der TriForce-Backend-Stack in der Praxis aufgebaut ist.

## Was TriForce im Kern ist

TriForce ist ein FastAPI-basiertes Backend, das drei Ebenen gleichzeitig verbindet:

- API-Layer fuer Web/Client-Apps (`app/main.py`, `app/routes/*`)
- Orchestrierung mehrerer KI-Provider und lokaler Compute-Backends (`app/services/*`)
- Tooling-Layer ueber MCP fuer Agenten, Automationen und Admin-Aufgaben (`app/routes/mcp.py`, `app/mcp/*`)

Das Projekt ist damit nicht nur "Chat-API", sondern eine Betriebsplattform fuer AI-Workloads.

## Architektur in der Implementierung

Die konkrete Runtime startet ueber `app/main.py` und initialisiert unter anderem:

- Redis-basiertes Rate-Limiting
- Model-Registry-Refresh
- TriStar Services (Memory, Model Init, Agent Controller, Settings)
- Mesh Coordinator
- Federation Manager mit Locking
- Distributed Compute Manager
- MCP Brain + MCP WebSocket Server

Das ist bewusst als zusammengesetztes System gebaut: ein einzelner Prozess stellt API, Tooling, Agent-Orchestrierung und Monitoring bereit.

## Wichtige Schnittstellen

- `POST /v1/chat/completions`: OpenAI-kompatible Chat-Route
- `POST /v1/mcp`: interner MCP JSON-RPC Einstieg
- `GET/POST /mcp`: Remote-Connector/OAuth-Pfad
- `/v1/client/*`: Endpunkte fuer Desktop-/Mobile-Clients
- `/v1/mesh/*`, `/v1/federation/*`: Knoten- und Clustersteuerung
- `/v1/agents/*`, `/v1/tristar/*`: Agenten- und Workflow-Steuerung

## Implementierte Software-Bausteine

- Multi-Provider Router (Cloud + lokal)
- MCP Tool Registry und Handler-Schicht
- Agent Router / Tasking / Skill-Mapping
- Memory-Index und persistente Wissensfunktionen
- Remote-Admin und Federation-Control
- Notification-, Mail- und WordPress-Integrationen
- Performance-/Telemetry-Layer fuer MCP Calls

## Warum diese Architektur sinnvoll ist

TriForce kombiniert drei Anforderungen, die in vielen Projekten getrennt enden:

- Produktive API fuer Apps
- Operatives Steuerzentrum fuer Infrastruktur
- Agent-freundliche Tool-Schnittstelle

Meine klare Meinung: Genau diese Vereinigung ist die Staerke des Projekts. Sie macht die Plattform komplexer, aber auch deutlich maechtiger als ein klassischer "nur LLM Proxy".

## Weiterlesen

- [System Architecture](../ARCHITECTURE.md)
- [REST API](../api/REST.md)
- [MCP Tools](../api/MCP.md)
- [AILinux Client Project](./AILINUX_CLIENT_PROJECT.md)
