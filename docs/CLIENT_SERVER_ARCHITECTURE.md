# AILinux Client-Server Architecture v3.0

> Dokumentation für die Client-Server-Architektur mit API Key Vault, Task Spawner und einheitlichem SDK.
> Stand: 2025-12-13

---

## Übersicht

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         api.ailinux.me (MCP Server)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────────┐   │
│  │  API Key Vault   │    │  Task Spawner    │    │  Agent Registry      │   │
│  │  (verschlüsselt) │───▶│                  │───▶│                      │   │
│  │                  │    │  Entschlüsselt   │    │  claude-task-abc123  │   │
│  │  • OpenAI        │    │  Keys temporär   │    │  codex-task-def456   │   │
│  │  • Anthropic     │    │  für Task-Dauer  │    │  gemini-task-ghi789  │   │
│  │  • Google        │    │                  │    │                      │   │
│  │  • Mistral       │    │  Spawnt Agent    │    │  Keys im RAM         │   │
│  └──────────────────┘    │  als Subprocess  │    │  (nicht auf Disk!)   │   │
│                          └──────────────────┘    └──────────────────────┘   │
│                                                                              │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────────┐   │
│  │  Ollama Local    │    │  API Proxy       │    │  Chat Router         │   │
│  │  (115+ Models)   │    │  (Cloud APIs)    │    │  (Model Selection)   │   │
│  └──────────────────┘    └──────────────────┘    └──────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
         ▲                           ▲                          │
         │                           │                          │
    Client Auth                 Task Request                    ▼
    (AUSGEHEND!)               (AUSGEHEND!)              Task Result
         │                           │                          │
┌────────┴───────────────────────────┴──────────────────────────┴─────────────┐
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ CLI Agent   │  │ CLI Agent   │  │ Desktop     │  │ Mobile Client       │ │
│  │ (claude)    │  │ (codex)     │  │ Client      │  │ (später)            │ │
│  │ Server-Side │  │ Server-Side │  │ User-PC     │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│                                                                              │
│  Alle Clients verbinden sich AUSGEHEND zum Server (keine Ports freigeben!)  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Kernprinzipien

### 1.1 Ausgehende Verbindungen
- **Client → Server** (nicht umgekehrt!)
- Keine Ports freigeben nötig
- Keine DynDNS, keine Firewall-Regeln
- WebSocket/Long-Poll für bidirektionale Kommunikation

### 1.2 API Keys zentral auf Server
- Verschlüsselt im Vault gespeichert
- Client hat KEINE API Keys
- Keys werden nur temporär für Task-Dauer entschlüsselt
- Nach Task-Ende: Keys aus RAM gelöscht

### 1.3 Einheitliches SDK
- CLI Agents und Desktop Clients nutzen gleiches SDK
- Lokale Tools laufen auf dem jeweiligen System
- Zentrale Koordination durch Server

---

## 2. API Key Vault

### 2.1 Konzept
```
Master Password → PBKDF2 (480.000 Iterations) → Fernet Key → Verschlüsselung
```

### 2.2 Speicherort
```
/home/zombie/triforce/.vault/
├── api_keys.enc    # Verschlüsselte Keys
└── salt            # PBKDF2 Salt
```

### 2.3 Unterstützte Provider
| Provider | Env-Variable | Verwendung |
|----------|--------------|------------|
| OpenAI | `OPENAI_API_KEY` | GPT-4, Codex |
| Anthropic | `ANTHROPIC_API_KEY` | Claude |
| Google | `GOOGLE_API_KEY` / `GEMINI_API_KEY` | Gemini |
| Mistral | `MISTRAL_API_KEY` | Mistral Large |
| Groq | `GROQ_API_KEY` | Schnelle Inference |
| Cerebras | `CEREBRAS_API_KEY` | Ultraschnelle Inference |

### 2.4 Implementation
```python
# app/services/api_vault.py

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class APIVault:
    def initialize(self, master_password: str) -> bool:
        """Vault erstmalig initialisieren"""
        
    def unlock(self, master_password: str) -> bool:
        """Vault entsperren (nach Server-Neustart)"""
        
    def lock(self):
        """Vault sperren - Keys aus RAM löschen"""
        
    def add_key(self, provider: str, api_key: str, key_id: str = "main") -> str:
        """API Key hinzufügen (verschlüsselt)"""
        
    def get_key(self, provider: str, key_id: str = "main") -> Optional[str]:
        """API Key entschlüsseln (temporär)"""
        
    def get_temp_env(self, providers: List[str]) -> Dict[str, str]:
        """Environment-Dict für Subprocess (Keys im RAM)"""
```

### 2.5 MCP Tools für Vault
```
vault_init          - Vault initialisieren (einmalig)
vault_unlock        - Vault entsperren
vault_lock          - Vault sperren
vault_add_key       - Key hinzufügen
vault_list_keys     - Keys auflisten (ohne Werte!)
vault_remove_key    - Key entfernen
vault_status        - Status prüfen
```

---

## 3. Task Spawner

### 3.1 Konzept
```
1. Client sendet Task-Request
2. Server holt API Keys aus Vault
3. Server spawnt Agent als Subprocess
4. Agent bekommt Keys nur im Environment (nicht auf Disk!)
5. Agent arbeitet autonom
6. Agent beendet sich → Keys weg
7. Result an Client
```

### 3.2 Agent Types
| Agent | Command | Provider | Stärken |
|-------|---------|----------|---------|
| claude | `claude --print` | Anthropic | Allrounder, Code |
| codex | `codex exec --full-auto` | OpenAI | Code-Optimierung |
| gemini | `gemini` | Google | Recherche, Analyse |
| opencode | `opencode run` | OpenAI+Anthropic | Multi-Model |

### 3.3 Implementation
```python
# app/services/task_spawner.py

class TaskSpawner:
    async def spawn_task(
        self,
        client_id: str,
        description: str,
        agent_type: AgentType = AgentType.CLAUDE,
        target_host: Optional[str] = None,
        additional_context: Dict[str, Any] = None
    ) -> SpawnedTask:
        """
        Spawnt autonomen Agent für Task
        - Holt Keys aus Vault
        - Setzt Keys in Environment
        - Startet Agent-Subprocess
        - Sammelt Output
        - Meldet Result
        """
```

### 3.4 MCP Tools für Tasks
```
client_request_task    - Task einreichen
client_task_status     - Status abfragen
client_task_output     - Live-Output holen
client_list_tasks      - Meine Tasks auflisten
client_cancel_task     - Task abbrechen
```

---

## 4. Client Authentication

### 4.1 Rollen
| Rolle | Beschreibung | Berechtigungen |
|-------|--------------|----------------|
| `admin` | Du (Markus) | Alles |
| `cli_agent` | Server-Side Agents | Server-Tools, Code |
| `desktop` | Desktop Clients | Chat, Tasks, lokale Tools |
| `mobile` | Mobile Clients | Chat, eingeschränkt |

### 4.2 Client Auth Flow
```
1. Client sendet: client_id + client_secret
2. Server prüft gegen Registry
3. Server generiert JWT Token
4. Client nutzt Token für alle Requests
```

### 4.3 Client darf NICHT
- `codebase.edit` (Server-Code ändern)
- `restart_backend`
- `tristar_shell_exec`
- `vault_*` (außer Status)
- Admin-Tools

### 4.4 Implementation
```python
# app/routes/client_auth.py

@router.post("/v1/auth/client")
async def client_auth(request: ClientAuthRequest):
    """Client authentifizieren"""
    
    # Prüfen
    client = CLIENT_REGISTRY.get(request.client_id)
    if not verify_secret(request.client_secret, client.secret_hash):
        raise HTTPException(401)
    
    # Token generieren
    token = create_jwt_token(client_id, role="desktop")
    
    return {
        "access_token": token,
        "role": client.role,
        "allowed_tools": client.allowed_tools
    }
```

---

## 5. Einheitliches Agent/Client SDK

### 5.1 Basis-Klasse
```python
# ailinux_sdk/base_agent.py

class BaseAgent(ABC):
    """Basis für alle Agents/Clients"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.local_tools = {}
        self._register_default_tools()
    
    async def connect(self) -> bool:
        """Ausgehende Verbindung zum Server"""
        
    async def listen_for_tasks(self):
        """Lauscht auf Tasks vom Server (Long-Poll)"""
        
    # Lokale Tools (laufen auf DIESEM System)
    async def _tool_bash(self, params) -> dict
    async def _tool_file_read(self, params) -> dict
    async def _tool_file_write(self, params) -> dict
    async def _tool_logs_collect(self, params) -> dict
    async def _tool_logs_analyze(self, params) -> dict
    async def _tool_system_info(self, params) -> dict
```

### 5.2 Lokale Tools
| Tool | Funktion | Sicherheit |
|------|----------|------------|
| `local_bash` | Shell-Commands | Blocklist, Timeout |
| `local_file_read` | Dateien lesen | Pfad-Whitelist |
| `local_file_write` | Dateien schreiben | Pfad-Whitelist |
| `local_file_list` | Verzeichnis listen | Pfad-Whitelist |
| `local_logs_collect` | journalctl/dmesg | - |
| `local_logs_analyze` | Fehler erkennen | - |
| `local_logs_search` | In Logs suchen | - |
| `local_system_info` | CPU, RAM, Disk | - |
| `local_process_list` | ps aux | - |

### 5.3 Log-Analyse mit Auto-Fix
```python
# Bekannte Fehlermuster mit Lösungsvorschlägen
ERROR_PATTERNS = {
    r"amdgpu.*timeout": {
        "category": "gpu",
        "suggestion": "GPU Recovery aktivieren",
        "auto_fix": "echo 'options amdgpu gpu_recovery=1' | sudo tee /etc/modprobe.d/amdgpu.conf"
    },
    r"pulseaudio.*connection refused": {
        "category": "audio",
        "suggestion": "PulseAudio neustarten",
        "auto_fix": "systemctl --user restart pulseaudio"
    },
    # ... mehr Patterns
}
```

---

## 6. Chat Router (Lokal + API)

### 6.1 Konzept
```
User Message
     │
     ▼
┌─────────────────┐
│  Chat Router    │
│                 │
│  Entscheidet:   │
│  • Lokal?       │
│  • API?         │
│  • Welches      │
│    Model?       │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐ ┌───────┐
│Ollama │ │ API   │
│Local  │ │ Proxy │
│       │ │       │
│qwen   │ │GPT-4  │
│llama  │ │Claude │
│mixtral│ │Gemini │
└───────┘ └───────┘
```

### 6.2 Model Selection
```python
# app/services/chat_router.py

class ChatRouter:
    def route_message(self, message: str, preferences: dict = None) -> str:
        """Wählt bestes Model für Anfrage"""
        
        # Explizite Wahl?
        if preferences.get("model"):
            return preferences["model"]
        
        # Schnelle Fragen → Lokal
        if len(message) < 100 and not self._needs_cloud(message):
            return "ollama/qwen2.5:14b"
        
        # Code → Claude oder Codex
        if self._is_code_task(message):
            return "anthropic/claude-sonnet-4"
        
        # Recherche → Gemini
        if self._needs_search(message):
            return "gemini/gemini-2.5-flash"
        
        # Default → Lokal
        return "ollama/llama3.2:latest"
```

### 6.3 API Proxy
```python
# app/services/api_proxy.py

class APIProxy:
    """Proxy für Cloud APIs - nutzt Keys aus Vault"""
    
    async def chat(self, model: str, messages: list) -> str:
        provider = model.split("/")[0]
        
        # Key aus Vault holen
        api_key = api_vault.get_key(provider)
        if not api_key:
            raise RuntimeError(f"No API key for {provider}")
        
        # Request je nach Provider
        if provider == "openai":
            return await self._openai_chat(api_key, model, messages)
        elif provider == "anthropic":
            return await self._anthropic_chat(api_key, model, messages)
        elif provider == "gemini":
            return await self._gemini_chat(api_key, model, messages)
        # ...
```

---

## 7. Client .env Konfiguration

### 7.1 Desktop Client
```bash
# ~/.config/ailinux/.env

# === Auth ===
AILINUX_CLIENT_ID=desktop-markus-abc123
AILINUX_CLIENT_SECRET=super_geheimer_client_key

# === Server ===
AILINUX_SERVER=https://api.ailinux.me

# === Device ===
AILINUX_DEVICE_NAME=Markus Gaming PC
AILINUX_DEVICE_TYPE=desktop

# === Lokale Berechtigungen ===
ALLOW_BASH=true
ALLOW_FILE_READ=true
ALLOW_FILE_WRITE=false
ALLOW_LOGS=true

# === Pfade ===
ALLOWED_PATHS=/home/zombie,/tmp,/var/log
BLOCKED_PATHS=/etc/shadow,/root,~/.ssh

# === UI ===
THEME=dark
WINDOW_SIZE=1400x900
```

### 7.2 CLI Agent (Server-Side)
```bash
# /home/zombie/triforce/agents/.env.claude

AILINUX_AGENT_ID=claude-mcp
AILINUX_AGENT_SECRET=agent_secret_key
AILINUX_ROLE=cli_agent
AILINUX_SERVER=http://localhost:9000

ALLOW_BASH=true
ALLOW_FILES=true
ALLOW_LOGS=true
ALLOWED_PATHS=/home/zombie/triforce,/tmp,/var/log
BLOCKED_PATHS=/etc/shadow,/root/.ssh
```

---

## 8. Desktop Client (PyQt6 + Chromium)

### 8.1 Struktur
```
ailinux-client/
├── main.py                 # Hauptfenster
├── requirements.txt        # Dependencies
├── setup.py               # Installation
│
├── ailinux_sdk/           # SDK (shared mit Server-Agents)
│   ├── __init__.py
│   ├── base_agent.py      # Basis-Klasse
│   ├── client.py          # Desktop Client
│   └── config.py          # Konfiguration
│
├── services/
│   ├── mcp_bridge.py      # WebSocket zu Server
│   ├── log_collector.py   # System-Logs sammeln
│   └── local_tools.py     # Bash, Files auf Client
│
├── ui/
│   ├── browser.py         # QWebEngine (Chromium)
│   ├── chat_panel.py      # Chat-Interface
│   └── tray_icon.py       # System Tray
│
├── config/
│   └── .env.example       # Template
│
└── installer.sh           # Setup-Script
```

### 8.2 Features
- **Chromium Browser** für Web-UI
- **Chat Panel** für Nova
- **System Tray** für Background
- **Log Viewer** mit KI-Analyse
- **Task Monitor** für laufende Tasks

---

## 9. Server-Änderungen (TODO)

### 9.1 Neue Services
- [ ] `app/services/api_vault.py` - Verschlüsselter Key-Speicher
- [ ] `app/services/task_spawner.py` - Agent-Spawner mit temp Keys
- [ ] `app/services/agent_registry.py` - Verbundene Agents verwalten
- [ ] `app/services/chat_router.py` - Model-Auswahl (lokal/API)
- [ ] `app/services/api_proxy.py` - Cloud API Proxy

### 9.2 Neue Routes
- [ ] `app/routes/client_auth.py` - Client-Authentifizierung
- [ ] `app/routes/client_tasks.py` - Task-Management für Clients

### 9.3 Neue MCP Tools
```python
# Vault Tools
vault_init, vault_unlock, vault_lock
vault_add_key, vault_list_keys, vault_remove_key, vault_status

# Client Tools
client_request_task, client_task_status, client_task_output
client_list_tasks, client_cancel_task

# Chat Tools (erweitert)
chat_with_model      # Explizite Model-Wahl
chat_smart           # Automatische Model-Wahl
chat_local           # Nur lokale Models
chat_cloud           # Nur Cloud APIs
```

### 9.4 Datenbank-Erweiterungen
```sql
-- Client Registry
CREATE TABLE clients (
    client_id VARCHAR(64) PRIMARY KEY,
    secret_hash VARCHAR(256) NOT NULL,
    role VARCHAR(32) DEFAULT 'desktop',
    device_name VARCHAR(128),
    created_at TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP
);

-- Task History
CREATE TABLE tasks (
    task_id VARCHAR(64) PRIMARY KEY,
    client_id VARCHAR(64) REFERENCES clients(client_id),
    agent_type VARCHAR(32),
    description TEXT,
    status VARCHAR(32),
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    result JSONB
);
```

---

## 10. Sicherheit

### 10.1 API Keys
- Verschlüsselt mit Fernet (AES-128-CBC + HMAC)
- Master-Password mit PBKDF2 (480.000 Iterations)
- Keys nie auf Disk bei Agents
- Keys nur im RAM während Task läuft

### 10.2 Client Auth
- client_secret wird gehasht gespeichert (SHA-256)
- JWT Tokens mit Expiry (1h)
- Role-Based Access Control

### 10.3 Lokale Tools
- Pfad-Whitelist für File-Operationen
- Command-Blocklist für Bash
- Timeouts für alle Operationen

### 10.4 Blocklisten
```python
# Gefährliche Commands
BLOCKED_COMMANDS = [
    "rm -rf /",
    "dd if=",
    "mkfs",
    ":(){",           # Fork Bomb
    "chmod -R 777 /",
    "> /dev/sd",
]

# Verbotene Pfade
BLOCKED_PATHS = [
    "/etc/shadow",
    "/etc/passwd",
    "/root",
    "~/.ssh",
    "/boot",
]
```

---

## 11. Beispiel-Flow

### User: "Nova, optimiere meinen PC für Gaming"

```
1. Desktop Client sendet Request
   → POST /v1/auth/client (falls noch nicht authentifiziert)
   → POST /v1/mcp { method: "client_request_task", params: {...} }

2. Server empfängt Request
   → Prüft Client-Auth
   → Sammelt Kontext (System-Info, Logs vom Client)

3. Server spawnt Agent
   → Holt ANTHROPIC_API_KEY aus Vault
   → Startet: claude --print "Optimiere Gaming PC..."
   → Keys nur im Environment (nicht auf Disk!)

4. Agent arbeitet autonom
   → SSH zum Client (falls remote)
   → Analysiert System
   → Führt Optimierungen durch
   → Berichtet Fortschritt

5. Agent beendet sich
   → Exit Code 0
   → Keys automatisch aus RAM entfernt

6. Server sendet Result an Client
   → Task-Status: completed
   → Output-Buffer mit allen Logs
```

---

## 12. Brumo

🐻 *„Keys im Tresor. Agent holt. Arbeitet. Vergisst. So einfach."*

---

## Changelog

| Datum | Version | Änderung |
|-------|---------|----------|
| 2025-12-13 | 3.0 | Initial Draft - Client-Server-Architektur |

