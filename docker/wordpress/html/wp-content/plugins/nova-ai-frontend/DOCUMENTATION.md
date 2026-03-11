# Nova AI Frontend Plugin - Dokumentation

Diese Dokumentation basiert auf einer Code-Analyse des Plugins und beschreibt Aufbau, Funktionen,
Login-Flow und Konfiguration. Sie ist bewusst kompakt und praxisnah gehalten.

## Ueberblick

Das Plugin stellt fuer WordPress ein Frontend und Admin-Interface fuer AILinux bereit:
- Frontend: Chat/Playground, Downloads-Browser, Early-Access-Registrierung, Discuss-Overlay, Chat-Widget
- Admin: Dashboard mit Systemstatus, Agenten, Models, Settings, Memory-Tools
- Auth: Unified Login via login.ailinux.me mit Sync in WordPress
- MCP: Proxy fuer MCP-Server und Modellverwaltung

## Projektstruktur

- `nova-ai-frontend.php`: Plugin Bootstrap, Defines, Aktivierung/Defaults
- `core/Plugin.php`: zentrale Initialisierung, Shortcodes, Assets, Admin-Menue
- `services/`:
  - `AuthService.php`: Unified Auth, REST Sync, Shortcodes
  - `MenuAuthService.php`: Login/Logout Button im Menu
  - `ChatProxy.php`: Proxy zu /v1/chat und Modell-Listen
  - `VisionProxy.php`: Vision-Modelle und Bild-Handling
  - `McpProxy.php`: MCP-Proxy fuer Admin-Requests
  - `DownloadsService.php`: Downloads-Browser, AJAX Navigation
  - `EarlyAccessService.php`: Beta-Registrierung und Slot-Tracking
- `templates/`: Frontend-UI fuer Shortcodes (Playground, Early Access, Downloads, Widget, Discuss)
- `frontend/`: JS/CSS fuer Frontend
- `admin/`: Admin Dashboard UI + Assets
- `assets/`: Auth-Skripte
- `includes/adsense-blocker.php`: optionales Blocking

## Konfiguration (Option `nov_ai_settings`)

Wichtige Defaults (gesetzt bei Aktivierung):
- `api_endpoint`: `https://api.ailinux.me`
- `mcp_endpoint`: `http://localhost:9000`
- `downloads_path`: `ABSPATH . "downloads"`
- `default_model`: `gemini/gemini-2.0-flash`
- `discuss_button_enabled`: `true`
- Chat-Widget Settings: `widget_enabled`, `widget_position`, `widget_color`, `widget_title`, `widget_icon`, `widget_welcome`
- Auth Settings: `use_unified_login`, `login_url`

## Shortcodes (Frontend)

- `[ailinux_downloads]`  
  Dateibrowser fuer den Downloads-Pfad.
- `[ailinux_ai_playground]`  
  Chat + Vision Playground.
- `[ailinux_pass]`  
  Early-Access/Beta-Registrierung.
- `[ailinux_chat_widget]`  
  Floating Chat Widget.
- `[ailinux_login]`  
  Unified Login (Button, Form oder Iframe).
  - `style="button|form|iframe"`
  - `redirect="admin|dashboard|/ziel|https://..."`  
    Beispiel: `[ailinux_login style="form" redirect="admin"]`
- `[ailinux_account]`  
  Account-Box fuer eingeloggte User.
- `[ailinux_register]`  
  Registrierungs-Button.
- `[ailinux_auth_button]`  
  Login/Account Toggle (Menu/Inline).

## Auth und Login-Flow

### Unified Login
1. Login erfolgt ueber AILinux (Token).
2. Token wird lokal gespeichert.
3. `POST /wp-json/nova-ai/v1/auth/sync` legt ggf. einen WP-User an und setzt das Auth-Cookie.
4. Danach Redirect auf die Ziel-URL.

### WordPress Admin Login ueber Login-Funktion
Der Login-Form-Flow kann nun auch ins WordPress Admin Dashboard leiten.
Damit das funktioniert:
- den Login-Shortcode mit `redirect="admin"` verwenden
- der WordPress-User muss bereits Admin-Rechte haben (keine automatische Rechte-Eskalation)

Beispiel:
```
[ailinux_login style="form" redirect="admin"]
```

### Beta-Account (AILinux)
Der Sync speichert (falls von AILinux geliefert) Tier/Plan und Client-ID in User-Meta:
- `nova_tier`
- `nova_client_id`
- `nova_ailinux_email`

Damit sind WordPress-Account und Beta-Account logisch verknuepft.

## REST/AJAX Endpoints (Auszug)

- `GET /wp-json/nova-ai/v1/auth/status`  
  Auth-Status (WP + AILinux).
- `POST /wp-json/nova-ai/v1/auth/sync`  
  Token-Validierung und WP-Login.
- `POST admin-ajax.php?action=nov_ai_chat`  
  Chat Proxy (`/v1/chat`).
- `POST admin-ajax.php?action=nov_ai_models`  
  Modell-Liste.
- `POST admin-ajax.php?action=nov_ai_register`  
  Early-Access-Registrierung.
- `POST admin-ajax.php?action=nov_ai_browse`  
  Downloads-Browser.
- `POST admin-ajax.php?action=nov_ai_mcp`  
  MCP Proxy fuer Admin Dashboard.

## Admin Dashboard

Admin-Menue: `Nova AI`  
Tabs:
- Dashboard: Status, Slots, Models
- Settings: Endpoints, Widget, Defaults
- System: MCP/Health
- Agents: MCP Agenten
- Memory: MCP Memory-Tools
- Widget: Chat-Widget Settings

## Sicherheit und Hinweise

- Login-Redirects werden validiert, `admin`/`dashboard` wird auf `admin_url()` gemappt.
- Token-Validierung laeuft gegen `/v1/auth/verify`.
- Neue User werden ohne Admin-Rechte erstellt.
- Keine Secrets im Code; Konfiguration nur via WP-Optionen/.env.

## Typische Konfiguration

1. Plugin aktivieren (Defaults werden gesetzt)
2. Settings im Admin Dashboard pruefen
3. Shortcodes in Pages einbauen
4. Optional: Unified Login fuer WordPress Admin via `[ailinux_login ...]`

