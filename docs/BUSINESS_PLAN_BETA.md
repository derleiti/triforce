# TriForce AI Platform - Business Plan & Beta Konzept

## Vision
**Dezentrales KI-Ökosystem**: Nutzer profitieren von Hub-Infrastruktur UND können eigene Hardware einbringen.

---

## 1. Architektur-Konzept

```
┌─────────────────────────────────────────────────────────────────────┐
│                    TRIFORCE FEDERATION                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐            │
│   │  HETZNER    │    │   BACKUP    │    │  ZOMBIE-PC  │            │
│   │  (Master)   │◄──►│   (Hub 2)   │◄──►│   (Hub 3)   │            │
│   │  20 Cores   │    │  12 Cores   │    │  16 Cores   │            │
│   │  62GB RAM   │    │  31GB RAM   │    │  30GB RAM   │            │
│   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘            │
│          │                  │                  │                    │
│          └──────────────────┼──────────────────┘                    │
│                             │                                       │
│                    ┌────────▼────────┐                              │
│                    │  UNIFIED API    │                              │
│                    │  api.ailinux.me │                              │
│                    └────────┬────────┘                              │
│                             │                                       │
├─────────────────────────────┼───────────────────────────────────────┤
│                             │                                       │
│   ┌─────────────────────────▼─────────────────────────────┐        │
│   │              CLIENT COMPUTE POOL                       │        │
│   ├────────────────────────────────────────────────────────┤        │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │        │
│   │  │ Client A │  │ Client B │  │ Client C │  │  ...   │ │        │
│   │  │ RTX 4090 │  │ 2x A100  │  │ Mac M3   │  │        │ │        │
│   │  │ 24GB     │  │ 160GB    │  │ 36GB     │  │        │ │        │
│   │  └──────────┘  └──────────┘  └──────────┘  └────────┘ │        │
│   │                                                        │        │
│   │  → Contribute compute = Earn credits                   │        │
│   │  → Use credits for Cloud APIs (Claude, GPT, Gemini)   │        │
│   └────────────────────────────────────────────────────────┘        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Tier-Modell (Überarbeitet)

### Free Tier (€0/Monat)
- Zugang zu Hub-Infrastruktur (rate-limited)
- 10k Tokens/Tag Cloud APIs
- Lokale Ollama-Modelle unbegrenzt
- **NEU**: Kann eigene Hardware registrieren

### Pro Tier (€17,99/Monat)
- 250k Tokens/Tag Cloud APIs
- Alle 630+ Modelle
- Priority Routing
- **NEU**: Hardware-Credits verdienen

### Unlimited Tier (€59,99/Monat)  
- Unbegrenzte Tokens
- Maximale Priority
- **NEU**: 2x Credit-Multiplikator für eigene Hardware

### Contributor Tier (€0 + Hardware)
- Stellt eigene GPU/Server bereit
- Verdient Credits für Rechenzeit
- Credits = Cloud API Zugang
- **Beispiel**: RTX 4090 läuft 8h/Tag → ~50k Token-Credits/Tag

---

## 3. Credit-System

### Earn Credits (Hardware beitragen)
```
┌────────────────────┬─────────────────┬──────────────────┐
│ Hardware           │ Credits/Stunde  │ ≈ Token-Wert     │
├────────────────────┼─────────────────┼──────────────────┤
│ RTX 3060 (12GB)    │ 10 Credits      │ ~5k Tokens       │
│ RTX 3080 (10GB)    │ 15 Credits      │ ~7.5k Tokens     │
│ RTX 4080 (16GB)    │ 25 Credits      │ ~12.5k Tokens    │
│ RTX 4090 (24GB)    │ 40 Credits      │ ~20k Tokens      │
│ A100 (40GB)        │ 100 Credits     │ ~50k Tokens      │
│ A100 (80GB)        │ 150 Credits     │ ~75k Tokens      │
│ Mac M2 Ultra       │ 30 Credits      │ ~15k Tokens      │
│ Mac M3 Max         │ 35 Credits      │ ~17.5k Tokens    │
└────────────────────┴─────────────────┴──────────────────┘
```

### Spend Credits (Cloud APIs nutzen)
```
┌────────────────────┬─────────────────┐
│ API                │ Credits/1k Tok  │
├────────────────────┼─────────────────┤
│ Ollama (lokal)     │ 0 (immer frei)  │
│ Groq               │ 1 Credit        │
│ Cerebras           │ 1 Credit        │
│ Mistral Small      │ 2 Credits       │
│ Gemini Flash       │ 2 Credits       │
│ Mistral Large      │ 5 Credits       │
│ Gemini Pro         │ 5 Credits       │
│ Claude Sonnet      │ 10 Credits      │
│ GPT-4o             │ 10 Credits      │
│ Claude Opus        │ 25 Credits      │
│ GPT-4 Turbo        │ 15 Credits      │
└────────────────────┴─────────────────┘
```

---

## 4. Client Hardware Integration

### Technische Umsetzung
```python
# Client registriert seine Hardware
POST /v1/contributor/register
{
    "hardware": {
        "gpu": "RTX 4090",
        "vram": 24,
        "cuda_version": "12.4"
    },
    "availability": {
        "hours_per_day": 8,
        "schedule": "18:00-02:00"  # Nachts
    },
    "models": ["llama3.1:70b", "qwen2.5:32b"]  # Kann große Modelle
}

# Federation routet Anfragen
→ Kleine Modelle: Hub-Infrastruktur
→ Große Modelle: Client-Pool (wenn verfügbar)
→ Cloud-Fallback: Wenn keine Kapazität
```

### Client-Software
```
AILinux Client v5.0 (geplant)
├── Contributor Mode (Hardware teilen)
│   ├── Ollama läuft im Hintergrund
│   ├── Akzeptiert Federation-Requests
│   ├── Credit-Tracking
│   └── Bandwidth-Limit einstellbar
│
├── Consumer Mode (Standard)
│   ├── Nutzt Hub + Cloud APIs
│   ├── Eigene Ollama-Instanz (optional)
│   └── Credit-Verbrauch Tracking
│
└── Hybrid Mode
    ├── Beides gleichzeitig
    └── Net-positive möglich (mehr verdienen als verbrauchen)
```

---

## 5. Beta-Phasen

### Phase 1: Closed Alpha (Januar 2025)
- [ ] Nur interne Tests (3 Hubs)
- [ ] Federation stabilisieren
- [ ] Credit-System Grundgerüst
- [ ] 5-10 ausgewählte Tester

### Phase 2: Private Beta (Februar 2025)
- [ ] 50 eingeladene Nutzer
- [ ] Contributor Mode Beta
- [ ] Credit-System live
- [ ] Feedback-Integration

### Phase 3: Open Beta (März 2025)
- [ ] Öffentliche Registrierung
- [ ] Full Feature Set
- [ ] Payment Integration (Stripe)
- [ ] Mobile App Beta

### Phase 4: Launch (Q2 2025)
- [ ] Stable Release
- [ ] Enterprise Tier
- [ ] SLA-Garantien
- [ ] 24/7 Support

---

## 6. Revenue Streams

```
┌─────────────────────────────────────────────────────────────┐
│                    REVENUE MODEL                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. SUBSCRIPTIONS (Recurring)                               │
│     ├── Pro:       €17,99/Monat                            │
│     ├── Unlimited: €59,99/Monat                            │
│     └── Enterprise: €299+/Monat (custom)                   │
│                                                             │
│  2. PAY-AS-YOU-GO (Usage)                                   │
│     ├── Credit-Pakete kaufen                               │
│     ├── €5 = 500 Credits (~250k Tokens)                    │
│     ├── €20 = 2500 Credits (~1.25M Tokens)                 │
│     └── €50 = 7500 Credits (~3.75M Tokens)                 │
│                                                             │
│  3. ENTERPRISE SERVICES                                     │
│     ├── Dedicated Nodes                                    │
│     ├── Custom Model Training                              │
│     ├── On-Premise Installation                            │
│     └── Priority Support                                   │
│                                                             │
│  4. MARKETPLACE (Future)                                    │
│     ├── Custom Prompts/Agents                              │
│     ├── Fine-tuned Models                                  │
│     └── Integrations                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Wettbewerbsvorteile

| Feature              | TriForce        | OpenRouter | Together.ai | Replicate |
|----------------------|-----------------|------------|-------------|-----------|
| Multi-Provider       | ✅ 9 Provider   | ✅         | ❌          | ❌        |
| Lokale Modelle       | ✅ Ollama       | ❌         | ❌          | ❌        |
| Eigene Hardware      | ✅ Contributor  | ❌         | ❌          | ❌        |
| Federation           | ✅ 3+ Nodes     | ❌         | ❌          | ❌        |
| MCP Tools            | ✅ 134 Tools    | ❌         | ❌          | ❌        |
| Self-Hosted Option   | ✅              | ❌         | ❌          | ❌        |
| Credit-System        | ✅              | ❌         | ❌          | ❌        |
| Open Source          | ✅              | ❌         | ❌          | ❌        |

---

## 8. Technische Anforderungen (Contributor)

### Minimum
- 8GB VRAM GPU (RTX 3060, etc.)
- 16GB RAM
- 100 Mbit/s Upload
- Linux/macOS/Windows
- Docker oder native Ollama

### Recommended
- 24GB+ VRAM (RTX 4090, A100)
- 32GB+ RAM
- 500 Mbit/s Upload
- Linux (für Stabilität)
- Dedizierter Server

---

## 9. Nächste Schritte

### Sofort (diese Woche)
1. [ ] Credit-System Datenmodell (Prisma)
2. [ ] Contributor API Endpoints
3. [ ] Hardware-Detection Script

### Kurzfristig (Januar)
4. [ ] Client v5.0 Contributor Mode
5. [ ] Credit-Tracking Dashboard
6. [ ] Beta-Invite System

### Mittelfristig (Q1)
7. [ ] Payment Integration
8. [ ] Mobile App
9. [ ] Marketing-Website

---

## 10. Risiken & Mitigationen

| Risiko                        | Mitigation                              |
|-------------------------------|-----------------------------------------|
| Zu wenig Contributors         | Attraktive Credit-Raten, Gamification   |
| Unreliable Client-Hardware    | Fallback zu Hub, Redundanz              |
| Missbrauch (Mining, etc.)     | Hardware-Verifizierung, Rate-Limits     |
| Rechtliche Fragen (EU)        | DSGVO-konform, klare ToS                |
| Konkurrenz                    | First-Mover, Community-Fokus            |

---

*Stand: 2024-12-31*
*Version: 0.1-draft*
