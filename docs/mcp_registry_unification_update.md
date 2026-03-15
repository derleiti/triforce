# MCP Registry Unification Update

## Was geändert wurde

1. Neue `app/mcp/tool_registry_unified.py`
   - führt v4 + v5 + Zusatztools in einer vereinheitlichten Sicht zusammen
   - dedupliziert Tooldefinitionen
   - ergänzt Inventar/Kategorien
   - bietet zentrale Tool-Namensauflösung für Calls

2. `tools/list` in `app/routes/mcp.py`
   - unterstützt jetzt:
     - `inventory=...`
     - `include_links=true`
     - `include_aliases=true`
     - `include_examples=true`
   - liefert zusätzlich eine `inventory`-Map zurück

3. `tools/call`
   - Toolnamen werden vor dem Dispatch zentral normalisiert/aufgelöst

4. MCP Mesh WebSocket
   - Host/Port nicht mehr hartcodiert
   - neue Settings:
     - `MCP_WS_HOST`
     - `MCP_WS_PORT`
     - `MCP_WS_PUBLIC_HOST`
     - `MCP_WS_PUBLIC_PORT`
     - `MCP_WS_ENABLE_IPV6`
   - Standardport jetzt: `58642`

## Warum das sinnvoll ist

- weniger Registry-Drift zwischen v3/v4/v5
- kleinere, thematisch gefilterte Toollisten für Modelle
- besseres Tool-Routing durch zentrale Alias-Auflösung
- Port-Änderungen ohne Codepatch möglich
- IPv6-/Bind-Verhalten sauberer steuerbar

## Offene Punkte

- `handle_tools_call` ist weiterhin groß und enthält viel Legacy-Logik
- `handlers_v4.py` enthält noch Stubs und Dopplungen
- die Unified Registry ist der erste Konsolidierungsschritt, nicht der Endzustand
