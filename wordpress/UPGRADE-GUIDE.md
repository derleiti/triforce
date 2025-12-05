# 🚀 WordPress Infrastruktur Upgrade-Guide

Dieses Dokument beschreibt die Implementierung der verbesserten Infrastruktur mit Cache-Busting, Traefik und erhöhter Robustheit.

## 📋 Übersicht der Verbesserungen

### ✅ 1. Service Worker - BEREITS GELÖST
- Service Worker ist deaktiviert (`sw.js.disabled`)
- Cleanup-Script deregistriert automatisch alle Service Worker
- Keine schwarzen Seiten mehr

### ⚡ 2. Vite Build mit Hash-basiertem Cache-Busting
- Automatische Content-Hash-Generierung für JS/CSS
- Manifest-Dateien für WordPress-Integration
- PHP Asset-Loader für intelligentes Asset-Management

### 🐳 3. Docker mit Traefik Reverse Proxy
- Automatisches HTTPS via Let's Encrypt
- Healthchecks für alle Services
- Ressourcenlimits und Auto-Restart
- Zero-Downtime Deploy-Ready
- FastAPI Backend integriert

### 🔒 4. Verbesserte Security & CSP
- Strikte Content Security Policy
- Separate CSP für verschiedene Bereiche
- Fehlerbehandlung im Frontend

---

## 🛠️ Installation

### Schritt 1: Theme Asset-Loader integrieren

```bash
cd /home/zombie/wordpress/html/wp-content/themes/ailinux-nova-dark
```

**1.1 Asset-Loader in functions.php einbinden:**

```php
// In functions.php nach den Theme-Konstanten hinzufügen
require_once AILINUX_NOVA_DARK_DIR . 'includes/class-asset-loader.php';
```

**1.2 Asset-Enqueuing aktualisieren:**

Ersetze die bestehenden `wp_enqueue_script()` und `wp_enqueue_style()` Aufrufe:

```php
// ALT:
wp_enqueue_style('ailinux-nova-dark-style', get_template_directory_uri() . '/dist/style.css', [], ailinux_nova_dark_get_asset_version('dist/style.css'));

// NEU:
Ailinux_Nova_Dark_Asset_Loader::enqueue_style(
    'ailinux-nova-dark-style',
    'style',           // Asset-Name im Manifest
    'style.css'        // Fallback für alte Builds
);

// Für JavaScript:
// ALT:
wp_enqueue_script('ailinux-nova-dark-app', get_template_directory_uri() . '/dist/app.js', ['swup'], ailinux_nova_dark_get_asset_version('dist/app.js'), true);

// NEU:
Ailinux_Nova_Dark_Asset_Loader::enqueue_script(
    'ailinux-nova-dark-app',
    'app',             // Asset-Name im Manifest
    'app.js',          // Fallback
    ['swup'],          // Dependencies
    true               // In Footer
);
```

### Schritt 2: Vite-Build aktualisieren

```bash
cd html/wp-content/themes/ailinux-nova-dark

# Backup der alten Konfiguration
cp vite.config.js vite.config.js.backup

# Neue Konfiguration aktivieren
cp vite.config.improved.js vite.config.js

# Dependencies installieren (falls nicht vorhanden)
npm install

# Build mit neuer Konfiguration
npm run build
```

**Ergebnis:**
- `dist/manifest.json` - JSON-Manifest für JavaScript
- `dist/manifest.php` - PHP-Manifest für WordPress
- `dist/app.[hash].js` - Cache-gebustete Assets
- `dist/style.[hash].css` - Cache-gebustete Styles

### Schritt 3: Docker-Infrastruktur upgraden (OPTIONAL)

**⚠️ WICHTIG:** Dieser Schritt ist optional und sollte nur durchgeführt werden, wenn du zu Traefik migrieren möchtest.

**3.1 Backup erstellen:**

```bash
# Manuelles Backup triggern
docker compose restart wordpress_backup

# Warten bis Backup fertig ist (ca. 30 Sekunden)
ls -lh backups/

# Services stoppen
docker compose down
```

**3.2 Traefik Netzwerk erstellen:**

```bash
# Wenn wordpress_network noch nicht existiert:
docker network create wordpress_wordpress_network

# Flarum-Netzwerk existiert bereits (external: true)
```

**3.3 .env erweitern:**

```bash
# In .env hinzufügen:
echo "DOMAIN=ailinux.me" >> .env
echo "ACME_EMAIL=admin@ailinux.me" >> .env
echo "BACKUP_INTERVAL_SECONDS=86400" >> .env
echo "RETENTION_DAYS=14" >> .env
```

**3.4 Upgrade durchführen:**

```bash
# Option A: Test mit neuer Konfiguration (empfohlen)
docker compose -f docker-compose.improved.yml up -d

# Option B: Alte Konfiguration komplett ersetzen
cp docker-compose.yml docker-compose.yml.backup
cp docker-compose.improved.yml docker-compose.yml
docker compose up -d
```

**3.5 Traefik Dashboard prüfen:**

```
http://localhost:8080
```

### Schritt 4: CSP Headers aktualisieren (Apache)

```bash
# In apache/vhosts/vhost-ailinux.me.conf aktualisieren
# Siehe CSP-SECURITY.md für Details
```

---

## 🧪 Testing

### Test 1: Theme Assets

```bash
# Prüfen ob Manifest generiert wurde
ls -la html/wp-content/themes/ailinux-nova-dark/dist/manifest.*

# Manifest-Inhalt prüfen
cat html/wp-content/themes/ailinux-nova-dark/dist/manifest.json
```

**Erwartetes Ergebnis:**
```json
{
  "app": {
    "file": "app.abc123def.js",
    "type": "js"
  },
  "style": {
    "file": "style.xyz789abc.css",
    "type": "css"
  }
}
```

### Test 2: WordPress Asset-Loading

1. WordPress-Seite im Browser öffnen
2. DevTools → Network Tab
3. Seite neu laden
4. Prüfen: Assets haben Hash in URL (`app.abc123.js`)
5. Theme neu builden: `npm run build`
6. Browser Hard-Refresh: Neue Hashes in URLs

### Test 3: Docker Healthchecks

```bash
# Alle Services prüfen
docker compose ps

# Erwartete Ausgabe:
# All services should show "healthy"

# Einzelne Healthchecks prüfen
docker inspect wordpress_fpm --format='{{.State.Health.Status}}'
# Output: healthy
```

### Test 4: Traefik Routing (falls upgradet)

```bash
# HTTPS-Weiterleitung testen
curl -I http://ailinux.me
# Erwartete Ausgabe: 301/302 → https://ailinux.me

# HTTPS-Zugriff testen
curl -I https://ailinux.me
# Erwartete Ausgabe: 200 OK

# API-Zugriff testen
curl -I https://api.ailinux.me
# Erwartete Ausgabe: 200 OK
```

---

## 🔄 Rollback-Plan

### Theme Rollback

```bash
cd html/wp-content/themes/ailinux-nova-dark

# Alte Vite-Konfiguration wiederherstellen
cp vite.config.js.backup vite.config.js

# Rebuild
npm run build

# functions.php: Asset-Loader Zeile entfernen oder auskommentieren
# require_once AILINUX_NOVA_DARK_DIR . 'includes/class-asset-loader.php';
```

### Docker Rollback

```bash
# Services stoppen
docker compose -f docker-compose.improved.yml down

# Alte Konfiguration aktivieren
docker compose -f docker-compose.yml.backup up -d

# Alternativ: Traefik-Container löschen
docker rm -f wordpress_traefik
docker volume rm traefik_certs

# Original docker-compose.yml wiederherstellen
cp docker-compose.yml.backup docker-compose.yml
docker compose up -d
```

---

## 📊 Performance-Vergleich

### Vorher (ohne Cache-Busting):
- Browser cached veraltete Assets
- Benutzer mussten Hard-Refresh machen
- CDN/Cloudflare cached alte Versionen
- Entwickler mussten manuell Versionsnummern pflegen

### Nachher (mit Cache-Busting):
- Automatische Cache-Invalidierung bei jedem Build
- Keine Hard-Refreshes mehr nötig
- CDN cached neue Versionen automatisch
- Zero-Config für Entwickler

---

## 🐛 Troubleshooting

### Problem: Manifest nicht gefunden

**Symptom:**
```
PHP Warning: include(/path/to/manifest.php): failed to open stream
```

**Lösung:**
```bash
cd html/wp-content/themes/ailinux-nova-dark
npm run build

# Prüfen:
ls -la dist/manifest.php
```

### Problem: Assets laden nicht

**Symptom:** Seite ohne Styling, JS-Fehler in Console

**Lösung:**
```bash
# Browser-Cache leeren
# Manifest regenerieren
cd html/wp-content/themes/ailinux-nova-dark
rm -rf dist/
npm run build

# WordPress Object-Cache leeren
docker compose run --rm -u www-data wpcli wp cache flush
```

### Problem: Traefik startet nicht

**Symptom:**
```
Error: network wordpress_wordpress_network not found
```

**Lösung:**
```bash
# Netzwerk manuell erstellen
docker network create wordpress_wordpress_network

# Service neu starten
docker compose up -d traefik
```

### Problem: Let's Encrypt Zertifikat nicht generiert

**Symptom:** `NET::ERR_CERT_AUTHORITY_INVALID`

**Lösung:**
```bash
# ACME_EMAIL in .env prüfen
grep ACME_EMAIL .env

# Traefik Logs prüfen
docker compose logs traefik | grep acme

# acme.json Permissions prüfen
docker exec wordpress_traefik ls -la /letsencrypt/acme.json
# Sollte: -rw------- (600)
```

---

## 📚 Weitere Dokumentation

- `CSP-SECURITY.md` - Content Security Policy Konfiguration
- `FRONTEND-ROBUSTNESS.md` - JavaScript Error Handling
- `CSS-PLUS-PLUS.md` - CSS++ Engine Dokumentation (optional)
- `CLAUDE.md` - Haupt-Entwicklungsdokumentation

---

## ✅ Checkliste

- [ ] Asset-Loader in functions.php integriert
- [ ] Vite-Konfiguration aktualisiert
- [ ] Theme neu gebaut (`npm run build`)
- [ ] Manifest-Dateien generiert
- [ ] WordPress-Seite im Browser getestet
- [ ] Assets haben Hashes in URLs
- [ ] Nach erneutem Build ändern sich Hashes
- [ ] (Optional) Docker auf Traefik upgradet
- [ ] (Optional) Traefik Dashboard erreichbar
- [ ] (Optional) HTTPS funktioniert
- [ ] (Optional) API-Endpunkt erreichbar
- [ ] Backup vor Upgrade erstellt
- [ ] Rollback-Plan gelesen und verstanden

---

**Erstellt:** 2025-01-25
**Version:** 1.0.0
**Autor:** Claude Code AI Assistant
