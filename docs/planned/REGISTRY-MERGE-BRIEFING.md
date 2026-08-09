# Registry-Merge — Briefing fuer eigene Session

**Status:** geplant, NICHT begonnen. Hochrisiko. Kein akuter Bug — 145 Tools
werden korrekt ausgeliefert. Ziel: Vereinfachung, nicht Fehlerbehebung.

## Ist-Zustand (2026-07-11): FUENF Registry-Dateien
| Datei | Zeilen | Rolle | Aufrufer |
|---|---|---|---|
| tool_registry_v3.py | 1625 | volle Liste (132) | mcp.py:1549 |
| tool_registry_v4.py | 967 | "optimized" (52) | handlers_v4.py:16, mcp.py:1613 |
| tool_registry_v5.py | - | Dedup (_v5_dedup_tools, 6 Dubletten) | api_agent.py |
| tool_registry_unified.py | - | HAT AUCH _dedupe_tools (169) - Rolle klaeren! | ? |
| Ergebnis | - | 145 via tools/list | - |

## Kritische Aufrufer
    mcp.py:54-55  import ... tool_registry_v3 as registry_v3_get_all_tools
    mcp.py:60-61  import ... tool_registry_v4 as registry_v4_get_all_tools
    mcp.py:1549   tools = registry_v3_get_all_tools()   # ein Pfad
    mcp.py:1613   tools = registry_v4_get_all_tools()   # anderer Pfad
    handlers_v4.py:16  from app.mcp.tool_registry_v4 import (...)

## Vorgehen
1. Klaeren WARUM zwei Pfade in mcp.py (1549 vs 1613) - unter welcher Bedingung welcher?
2. tool_registry_unified.py verstehen - ist der Merge halb passiert?
3. Baseline: tools/list VOR Merge dumpen (145 Namen) -> /tmp/tools-before.txt
4. Schrittweise pro Aufrufer. Nach jedem: Restart, .pyc loeschen(!), tools/list diffen.
5. Erst wenn alle Aufrufer umgebogen: v3/v4 entfernen.

## Fallen (heute gelernt)
- .pyc-Cache: nach code_edit `find app -name '<datei>*.pyc' -delete`, sonst alter Bytecode.
- Mehrere Agenten: vor Start `git fetch` + ahead/behind.
- Restart kappt MCP-Verbindung (SIGTERM) - normal, kurz warten.

## Definition of Done
- EIN Registry-Pfad, alle Aufrufer dorthin.
- tools/list == Baseline (145, gleiche Namen).
- Backend startet sauber, shell/code_edit ok.
- v3/v4 entfernt, Startup zeigt nur EINE Registry-Zahl.
