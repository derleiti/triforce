# TriForce / AILinux Product Release Hardening Plan

_Date: 2026-04-02_

## Ziel
TriForce von einer mächtigen Infrastruktur zu einem belastbaren, releasefähigen Produkt führen.

## Produktkern
Für den ersten echten Release zählt nur ein harter Kern:
- stabiler Client/API/MCP Kernfluss
- reproduzierbare Modellantworten mit definierten Fallbacks
- belastbare Multi-Agent-Flows
- Auth, Limits und Billing-relevante Wege
- observierbarer Betrieb mit Rollback

## Die 10 wichtigsten Lücken bis Release
1. Produktkern einfrieren. Definiere den einen Release-Path, den Nutzer wirklich kaufen und täglich verwenden.
2. API- und MCP-Verträge stabilisieren. Antwortformate, Fehlerformate und Tool-Garantien müssen fixiert werden.
3. Auth, Rate Limits und Abgrenzung der Pläne hart machen. Kostenlos, bezahlt, intern dürfen nicht verschwimmen.
4. Fallback-Matrix für Modelle kuratieren. Nicht jedes verfügbare Modell darf produktiv routbar sein.
5. Swarm-Scoring und Modellfilter härten. Fehlerantworten und ungeeignete Modelle dürfen nicht in Top-Ergebnisse rutschen.
6. Multi-Agent-End-to-End-Pfade testen. Group Chat und Swarm müssen in ihren Kernflüssen reproduzierbar grün sein.
7. Release-Observability aufbauen. Fehler, Latenzen, Provider-Ausfälle, Tool-Failures und Persistenzfehler müssen sichtbar sein.
8. Deployment und Rollback standardisieren. Ein Release darf den Betrieb nicht unkontrolliert zerschießen.
9. Dokumentation für reale Nutzung schreiben. Setup, API-Nutzung, Limits, bekannte Fehlerbilder und Recovery-Pfade.
10. Nicht-kritische Flächen aus dem ersten Release herausdrücken. Forum, Content, Publisher, exotische Pfade nur wenn sie den Kern nicht gefährden.

## Größte Solo-Shipping-Risiken in 4–8 Wochen
1. Zu breiter Scope statt gefrorenem Release-Kern.
2. Infrastruktur frisst Zeit, während der Nutzerfluss nicht sauber fertig wird.
3. Provider-/Modell-Probleme schlagen mitten im Release durch.
4. Fehlende Regressionstests für Orchestrierung und Persistenz.
5. Zu viele intern starke Features ohne klaren kommerziellen Fokus.

## Sinnvolle Reihenfolge
### Phase 1 — Release-Kern fixieren
- Core-User-Journey definieren
- stabile Toolliste und API-Verträge festschreiben
- nicht-kritische Services aus Release 1 ausblenden

### Phase 2 — Kern härten
- Fallbacks und Modellzulassung härten
- Group Chat / Swarm / Chat Router als kritische Flows absichern
- Observability, Error Buckets, Release-Dashboards ergänzen

### Phase 3 — Release-fähig machen
- Deploy/Rollback standardisieren
- Billing-/Plan-Grenzen prüfen
- Nutzerdoku, API-Doku, Known-Issues und Runbooks fertigstellen

## Produktnah vs. infra-lastig
### Bereits produktnah
- Chat- und Router-Schicht
- MCP-Ökosystem
- Subscription-/Tier-Richtung
- Grundidee von Group Chat / Swarm

### Noch eher infra-lastig
- zu breite Service-Landschaft
- Modell-/Provider-Fläche ohne harte Kuratierung
- Orchestrierung noch zu anfällig für edge cases
- Teile des Ökosystems wirken eher intern als release-notwendig

## Zwingende Release-Gates
1. Core User Journey vollständig grün.
2. Group-Chat-Kernfluss grün: create → ask → responses → consolidate → assign.
3. Swarm-Kernfluss grün: broadcast → status → top_results → consolidated, inklusive Filter gegen Modellmüll.
4. Auth / Limits / Billing-relevante Wege grün.
5. Deployment + Rollback unter realistischen Bedingungen grün.

## Direkt empfohlene nächste Änderungen
- Modellzulassung im Swarm strenger machen.
- Fehlerantworten im Scoring hart abstrafen oder vor Ranking ausschließen.
- Release-Scope schriftlich fixieren.
- End-to-End-Tests für Group Chat und Swarm in die kritische Testmatrix aufnehmen.
- Ollama-Status bewusst entscheiden: produktiver Pfad mit Fallback oder explizit nicht Teil von Release 1.
