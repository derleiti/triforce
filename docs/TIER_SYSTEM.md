# AILinux Tier System

**Version:** 3.0  
**Stand:** Dezember 2025

---

## Übersicht

Das AILinux Tier-System bietet flexible Preismodelle für unterschiedliche Nutzungsanforderungen.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AILinux Tier System                          │
├─────────────┬─────────────┬─────────────┬─────────────┬────────────┤
│   GUEST     │ REGISTERED  │     PRO     │  UNLIMITED  │            │
│   (free)    │   (free)    │  18,99 €    │   59,99 €   │            │
├─────────────┼─────────────┼─────────────┼─────────────┤            │
│ 20 Modelle  │ 20 Modelle  │ 600+ Modelle│ 600+ Modelle│            │
│ 50k Tokens  │ 100k Tokens │ 250k/∞      │ Unlimited   │            │
│ Kein MCP    │ MCP ✓       │ MCP ✓       │ MCP ✓       │            │
└─────────────┴─────────────┴─────────────┴─────────────┴────────────┘
```

---

## Tier-Vergleich

| Feature | Guest | Registered | Pro | Unlimited |
|---------|-------|------------|-----|-----------|
| **Preis/Monat** | 0 € | 0 € | **18,99 €** | **59,99 €** |
| **Preis/Jahr** | - | - | 189,99 € | 599,99 € |
| **KI-Modelle** | 20 | 20 | 600+ | 600+ |
| **Tokens/Tag** | 50.000 | 100.000 | 250.000* | ∞ Unlimited |
| **MCP Tools** | ❌ | ✅ | ✅ | ✅ |
| **CLI Agents** | ❌ | ✅ | ✅ | ✅ |
| **Priority Queue** | ❌ | ❌ | ❌ | ✅ |
| **Support** | - | Community | Email | Priority |

\* Pro: 250k für Cloud-Modelle, **Ollama Modelle UNLIMITED**

---

## Detaillierte Beschreibung

### 🆓 Guest (Kostenlos)

**Für:** Gelegentliche Nutzer, Tester

**Enthält:**
- 20 Ollama Cloud-Modelle (DeepSeek, Qwen, Kimi, GPT-OSS, etc.)
- 50.000 Tokens pro Tag
- Basis-Chat Funktionalität
- 🐻 Brumo Assistent

**Nicht enthalten:**
- MCP Protocol Zugriff
- CLI Agent Integration
- Cloud-Provider Modelle

**Registrierung:** Keine erforderlich

---

### 📝 Registered (Kostenlos)

**Für:** Entwickler, Power-User die MCP nutzen wollen

**Enthält alles aus Guest, plus:**
- 100.000 Tokens pro Tag
- MCP Protocol Zugriff
- CLI Agent Integration (Claude, Codex, Gemini CLI)
- Community Support (Forum)

**Registrierung:** Email-Registrierung erforderlich

---

### ⭐ Pro (18,99 €/Monat)

**Für:** Professionelle Entwickler, Freelancer, kleine Teams

**Enthält alles aus Registered, plus:**
- **600+ KI-Modelle** aus allen Providern
- 250.000 Tokens/Tag für Cloud-Modelle
- **Ollama Modelle UNLIMITED** (kein Tageslimit!)
- Zugriff auf Premium-Modelle (Claude, GPT-4, Gemini Pro)
- Email Support

**Jahresabo:** 189,99 € (2 Monate gratis)

**Besonderheit Ollama Unlimited:**
```
Pro-User können Ollama-Modelle ohne jegliches Limit nutzen.
Das 250k Token-Limit gilt NUR für kostenpflichtige Cloud-Provider 
wie OpenRouter, Anthropic Direct, etc.

Ollama Cloud-Modelle = GRATIS & UNLIMITED für Pro-User!
```

---

### 🚀 Unlimited (59,99 €/Monat)

**Für:** Unternehmen, Heavy-User, Agenturen

**Enthält alles aus Pro, plus:**
- **Unlimited Tokens** (kein Tageslimit für alle Modelle)
- Priority Queue (schnellere Verarbeitung)
- Priority Support (garantierte Antwort < 24h)
- Alle zukünftigen Premium-Features

**Jahresabo:** 599,99 € (2 Monate gratis)

---

## Token-System

### Was sind Tokens?

Tokens sind die Maßeinheit für KI-Verarbeitung. Ungefähr:
- 1 Token ≈ 4 Zeichen (Englisch)
- 1 Token ≈ 2-3 Zeichen (Deutsch)
- 100 Wörter ≈ 75 Tokens

### Token-Verbrauch

| Aktion | Geschätzte Tokens |
|--------|-------------------|
| Kurze Frage | 50-100 |
| Code erklären | 200-500 |
| Code generieren | 500-2000 |
| Dokument zusammenfassen | 1000-3000 |
| Lange Konversation | 2000-5000 |

### Token-Tracking

Dein Token-Verbrauch wird pro Tag getrackt:

```bash
# Verbrauch prüfen
GET /v1/client/tier
X-User-ID: user@example.com

# Response enthält:
{
  "daily_token_limit": 250000,
  "tokens_used_today": 12345,
  "tokens_remaining": 237655
}
```

---

## Modell-Zugriff

### Guest & Registered: Ollama Cloud (20 Modelle)

| Kategorie | Modelle |
|-----------|---------|
| **Code** | qwen3-coder:480b, devstral-2:123b |
| **Reasoning** | deepseek-v3.1:671b, kimi-k2-thinking |
| **General** | gpt-oss:120b, gemini-3-pro |
| **Fast** | ministral-3:3b, gpt-oss:20b |

### Pro & Unlimited: Alle Modelle (600+)

| Provider | Beispiel-Modelle |
|----------|-----------------|
| **OpenRouter** | claude-3-opus, gpt-4-turbo, llama-3.1-405b |
| **Anthropic** | claude-3-sonnet, claude-3-haiku |
| **Google** | gemini-pro, gemini-ultra |
| **Mistral** | mistral-large, codestral |
| **DeepSeek** | deepseek-coder-v2, deepseek-chat |

---

## MCP Protocol Zugriff

### Was ist MCP?

Das Model Context Protocol ermöglicht die Integration von KI-Modellen in CLI-Tools.

### Unterstützte Tools

| Tool | Beschreibung | Tier |
|------|-------------|------|
| Claude CLI | Anthropic's CLI | Registered+ |
| Codex CLI | OpenAI Codex | Registered+ |
| Gemini CLI | Google AI CLI | Registered+ |

### Konfiguration

```json
// ~/.claude.json
{
  "mcpServers": {
    "ailinux": {
      "url": "https://api.ailinux.me/v1/mcp"
    }
  }
}
```

---

## Upgrade & Downgrade

### Upgrade durchführen

1. Login auf https://ailinux.me/account
2. "Upgrade" wählen
3. Zahlungsmethode eingeben
4. Sofort aktiv

### Downgrade

- Am Ende der Abrechnungsperiode
- Keine Erstattung für angebrochene Monate
- Modell-Zugriff wird eingeschränkt

### Kündigung

- Jederzeit möglich
- Wirksam zum Ende der Abrechnungsperiode
- Daten werden 30 Tage aufbewahrt

---

## Test-Accounts

Für Entwicklung und Tests sind folgende Accounts vorkonfiguriert:

| Email | Tier | Passwort |
|-------|------|----------|
| guest@ailinux.me | Guest | guest123 |
| registered@ailinux.me | Registered | reg123 |
| mrksleitermann@gmail.com | Pro | *** |
| admin@ailinux.me | Unlimited | *** |

---

## API Endpoints

### Tier Info abrufen

```bash
GET /v1/client/tier
X-User-ID: user@example.com
```

### Alle Tiers anzeigen

```bash
GET /v1/tiers
```

### Modell-Zugriff prüfen

```bash
GET /v1/tiers/user/{user_id}/check/{model_id}
```

---

## FAQ

### Kann ich kostenlos starten?

Ja! Guest und Registered sind dauerhaft kostenlos.

### Was passiert wenn mein Token-Limit erreicht ist?

Du erhältst einen 429 Fehler. Das Limit wird um Mitternacht UTC zurückgesetzt.

### Sind Ollama-Modelle wirklich unlimited für Pro?

Ja! Das Token-Limit gilt nur für kostenpflichtige Cloud-Provider. Ollama-Modelle sind für Pro-User ohne Limit nutzbar.

### Kann ich zwischen Modellen wechseln?

Ja, jederzeit. Wähle einfach ein anderes Modell in deiner Anfrage.

### Gibt es eine API für automatisches Tier-Upgrade?

Noch nicht. Kontaktiere support@ailinux.me für Enterprise-Anfragen.

---

## Kontakt

**Fragen zu Tiers:** billing@ailinux.me  
**Technischer Support:** support@ailinux.me  
**Enterprise-Anfragen:** enterprise@ailinux.me

---

*Preise inkl. MwSt. Stand: Dezember 2025*

🐻 *"Pro lohnt sich. Wie ein Bär im Honigfass."* - Brumo
