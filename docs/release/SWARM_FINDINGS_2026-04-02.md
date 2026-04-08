# Swarm Findings — 2026-04-02

Session: `swarm-6a09ee82`

## Kurzfazit
Der Swarm lieferte verwertbare Produktsignale, aber das Ranking nahm noch ungeeignete Modelle und Fehlerantworten mit in die Top-Ergebnisse.

## Harte Ableitungen
- Swarm funktioniert technisch wieder über getrennte Calls.
- Ranking/Filtering ist noch nicht releasefest.
- Modellzulassung muss produktorientiert und nicht nur technisch verfügbar gedacht werden.
- Produktkern muss vor weiterem Ausbau eingefroren werden.

## Wichtigste Punkte aus der Auswertung
- Produktkern definieren und alles Nicht-Kernige aus Release 1 drängen.
- API-/MCP-Verträge und Fehlerformate stabilisieren.
- Auth, Rate Limits und Billing-relevante Wege vor Release härten.
- Multi-Agent- und Swarm-Kernpfade als kritische Regressionen behandeln.
- Observability, Rollback und kuratierte Provider-Fallbacks vor Release absichern.

## Zusätzlicher Hinweis
Die reine Existenz vieler Services ist kein Release-Kriterium. Für Release zählt die Zuverlässigkeit weniger harter Pfade.
