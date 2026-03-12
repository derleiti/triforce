# AILinux Client Project

Version: `v4.8.0-beta` (Client) mit TriForce Backend `v0.7.0-beta`

Diese Seite beschreibt das Client-Projekt als eigenstaendige Software, nicht nur als "Frontend".

## Projektprofil

Der AILinux Client ist eine PyQt6-Desktop-App mit lokalem Runtime-Fokus:

- GUI + Terminal + Browser-Komponenten
- direkte Backend-Integration ueber `https://api.ailinux.me`
- MCP-Faehigkeiten (Tool-Listing, Tool-Calls, Node/WebSocket)
- lokales Betriebs-Tooling (Updater, Syslogger, Tier-Manager, verschluesselte Settings)

## Relevante Code-Bausteine

- `ailinux_client/core/api_client.py`
  - Login (`/v1/auth/login`)
  - Chat (`/v1/client/chat`)
  - Modelle (`/v1/client/models`)
  - MCP Tool APIs (`/v1/client/mcp/tools`, `/v1/client/mcp/call`)
- `ailinux_client/core/mcp_node_client.py`
  - WebSocket-Verbindung zu `/v1/mcp/node/connect`
- `ailinux_client/core/mcp_stdio_server.py`
  - MCP-Bridge fuer lokale/remote Nutzung
- `ailinux_client/core/updater.py`
  - Update-Check via `/v1/client/update/version`

## Architekturgedanke

Der Client ist bewusst "fett" genug, um lokal robust zu laufen, aber schlank genug, um Kernintelligenz im Backend zu halten.

- Vorteil: zentrale Governance, zentrale Modelle, zentrale Limits
- Vorteil: lokale UX bleibt schnell und erweiterbar
- Tradeoff: starke Abhaengigkeit von API-Stabilitaet und sauberer Versionierung

## Funktionale Schwerpunkte

- produktiver Multi-Model Chat
- Tool-gestuetzte Workflows ueber MCP
- Contributor/Federation-Modi fuer verteilte Nutzung
- Tier-basierte Modellsteuerung (Free/Pro/Enterprise)

## Einordnung

Meine Meinung: Der Client ist nicht "nur ein Fenster zur API". Er ist die operative Nutzeroberflaeche fuer das gesamte TriForce-Oekosystem und sollte deshalb wie ein eigenes Produkt mit eigener Release-Qualitaet behandelt werden.

## Weiterlesen

- [Client Setup Guide](../guides/CLIENT_SETUP.md)
- [Client-Server Architecture](../CLIENT_SERVER_ARCHITECTURE.md)
- [TriForce Backend Project](./TRIFORCE_BACKEND_PROJECT.md)
