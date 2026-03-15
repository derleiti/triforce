# MCP Hosted Safe Mode

## Hintergrund
Gehostete Clients wie ChatGPT blockieren direkte Write-/Mutation-Toolcalls oft bereits vor dem eigentlichen Backend.

## Verhalten
- Read-only Tools bleiben direkt ausführbar
- Write-Tools liefern zuerst ein Proposal / Preview
- Der eigentliche Commit/Write wird als separater Schritt behandelt

## Aktuelle Hinweise
- Federation-Fehler `Invalid token for peer: hetzner` ist ein separates Node-/Token-Problem
- Gemini API kann aktuell 400 liefern, wenn kein gültiger API-Key konfiguriert ist
- Alte Gemini/Login- oder API-Login-URLs in Doku entfernen bzw. aktualisieren
