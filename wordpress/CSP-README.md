# Content Security Policy (CSP) – Konfiguration & Dokumentation

## Übersicht

Diese Seite nutzt **eine einzige CSP-Quelle**: Den **Apache Webserver**.

- ✅ CSP wird gesetzt in: `/root/wordpress/apache/vhosts/vhost-ailinux.me.conf` (Zeile 44-64)
- ❌ CSP ist **DEAKTIVIERT** in: WordPress-Plugins (Complianz, Security-Plugins)
- ❌ CSP ist **DEAKTIVIERT** in: Cloudflare (falls aktiv)

**Wichtig**: Niemals CSP an mehreren Stellen gleichzeitig setzen! Das führt zu konkurrierenden Policies und unvorhersehbarem Verhalten.

---

## 1. Wo wird CSP gesetzt?

### Aktive Konfiguration: Apache

**Datei**: `/root/wordpress/apache/vhosts/vhost-ailinux.me.conf`

```apache
# Content Security Policy - Pragmatic & Functional
# NOTE: This is the ONLY place where CSP is set. Do NOT enable CSP in WordPress plugins.
Header always set Content-Security-Policy "\
default-src 'self'; \
script-src 'self' 'unsafe-inline' 'unsafe-eval' blob: \
  https://www.googletagmanager.com \
  https://www.gstatic.com \
  https://pagead2.googlesyndication.com \
  https://tpc.googlesyndication.com \
  https://www.googletagservices.com \
  https://widget.intercom.io \
  https://cdn.gtranslate.net \
  https://translate.google.com; \
style-src 'self' 'unsafe-inline' https:; \
img-src 'self' data: https:; \
font-src 'self' data: https:; \
connect-src 'self' https://api.ailinux.me:9000 https:; \
frame-src 'self' https://www.googletagmanager.com https://pagead2.googlesyndication.com; \
worker-src 'self' blob:; \
media-src 'self' data: https:; \
object-src 'none'; \
base-uri 'self'; \
form-action 'self';"
```

**Nach Änderungen**:
```bash
# Syntax-Check
docker compose exec apache apachectl configtest

# Restart
docker compose restart apache
```

---

## 2. Wie teste ich die CSP-Header?

### Variante A: Von außen (über Cloudflare)
```bash
curl -sI https://ailinux.me | grep -i content-security-policy
```

**Erwartete Ausgabe**:
```
content-security-policy: default-src 'self'; script-src 'self' 'unsafe-inline' ...
```

### Variante B: Lokal vom Docker-Host
```bash
curl -sI http://localhost | grep -i content-security-policy
# Oder für HTTPS:
curl -sIk https://localhost | grep -i content-security-policy
```

### Variante C: Browser DevTools
1. Öffne https://ailinux.me
2. DevTools → Network → Wähle die erste Anfrage (Dokument)
3. Schaue unter **Response Headers** nach `content-security-policy`

**Achtung**: Es darf **nur EIN** `Content-Security-Policy`-Header existieren.
Wenn du `Content-Security-Policy-Report-Only` siehst, läuft noch ein Plugin mit!

---

## 3. Erlaubte Domains und warum sie benötigt werden

| Domain | Zweck |
|--------|-------|
| `'self'` | Eigene Site (WordPress-Core, Theme, Plugins) |
| `blob:` | In-Memory URLs (z.B. für Medien-Upload, Service Worker) |
| `'unsafe-inline'` | Inline `<script>` und `<style>` (WordPress Standard, später härtbar via Nonces) |
| `'unsafe-eval'` | `eval()` für jQuery, Backbone, Plupload (WordPress-Core Abhängigkeit) |
| `www.googletagmanager.com` | Google Tag Manager (GTM) |
| `www.gstatic.com` | Google Static Resources (Analytics, Site Kit) |
| `pagead2.googlesyndication.com` | Google AdSense |
| `tpc.googlesyndication.com` | AdSense Tag Partner Container |
| `www.googletagservices.com` | Google Ad Services |
| `widget.intercom.io` | Intercom Support Chat (gtranslate nutzt das) |
| `cdn.gtranslate.net` | GTranslate Widget |
| `translate.google.com` | Google Translate API |
| `api.ailinux.me:9000` | Eigene API für NovaAI-Plugin |
| `data:` | Data-URIs für Fonts, Bilder (z.B. Base64-Fonts) |
| `https:` | Alle HTTPS-Quellen für Styles/Bilder/Fonts (pragmatisch, später einschränkbar) |

---

## 4. Report-Only Mode aktivieren (zum Testen)

Falls du eine neue, strengere CSP testen willst ohne die Site zu brechen:

**Apache** (`vhost-ailinux.me.conf`):
```apache
# Alte CSP auskommentieren:
# Header always set Content-Security-Policy "..."

# Neue Test-CSP als Report-Only:
Header always set Content-Security-Policy-Report-Only "\
default-src 'self'; \
script-src 'self' 'nonce-{REPLACE_WITH_DYNAMIC_NONCE}' 'strict-dynamic'; \
... \
report-uri https://ailinux.me/csp-report;"
```

Dann in der Browser-Konsole Violations beobachten, ohne dass Funktionen kaputt gehen.

---

## 5. WordPress-Plugins: CSP DEAKTIVIEREN

### Complianz GDPR
1. WordPress Admin → **Complianz** → Settings
2. Suche nach **"Content Security Policy"** oder **"CSP"**
3. Falls vorhanden: **Deaktivieren** oder auf **"Disabled"** setzen

### WP Cloudflare Page Cache
1. WordPress Admin → **Cloudflare** → Settings
2. **HTTP Response Headers** → Prüfe, ob CSP-Header dort gesetzt werden
3. Falls ja: **Entfernen**

### SEOPress / Security-Plugins
Falls weitere Security-Plugins CSP setzen: Deaktiviere die CSP-Funktion.

**Regel**: Nur **eine** Stelle darf CSP setzen!

---

## 6. Cloudflare: CSP-Header prüfen

Falls Cloudflare aktiv ist:

1. Cloudflare Dashboard → **Rules** → **Transform Rules**
2. Prüfe auf **Modify Response Header** Rules mit `Content-Security-Policy`
3. Falls vorhanden: **Deaktivieren**

---

## 7. Akzeptanztest (Funktioniert alles?)

Öffne https://ailinux.me in einem **frischen Browser-Profil ohne Ad-Blocker**.

### ✅ Folgende Komponenten müssen funktionieren:

- [ ] WordPress Admin-Bar sichtbar (oben)
- [ ] Medien hochladen (Media Library)
- [ ] jQuery, jQuery-UI funktioniert
- [ ] Theme-JavaScript lädt (app.js, mobile-menu.js, colorMode.js)
- [ ] NovaAI-Widget funktioniert
- [ ] Service Worker registriert (`/wp-content/plugins/nova-ai-frontend/assets/sw.js`)
- [ ] Google Tag Manager lädt
- [ ] Google Site Kit Dashboard funktioniert
- [ ] AdSense-Anzeigen erscheinen
- [ ] GTranslate Widget funktioniert
- [ ] Google Fonts laden

### ✅ Browser-Konsole darf KEINE zeigen:

```
Refused to load/execute ... because it violates the following Content Security Policy directive
```

### ℹ️ ERLAUBT (= nicht serverseitig fixbar):

```
GET ... net::ERR_BLOCKED_BY_CLIENT
```
→ Das ist der **Ad-Blocker** des Browsers, nicht die CSP.

---

## 8. Härtung (Optional, später)

Die aktuelle CSP nutzt `'unsafe-inline'` und `'unsafe-eval'`.
Das ist **pragmatisch** und ermöglicht volle Funktionalität, aber weniger sicher.

### Schritt 1: Nonce-basierte CSP (ohne unsafe-inline)

**Was ist ein Nonce?**
Ein kryptographisch zufälliger String, der pro Request generiert wird.

**Beispiel**:
```apache
# Apache (mit mod_unique_id oder PHP-generiert):
Header always set Content-Security-Policy "script-src 'self' 'nonce-%{UNIQUE_ID}e' 'strict-dynamic';"
```

**Problem**: Apache `UNIQUE_ID` ist **nicht** kryptographisch stark genug für Nonces.
→ **Empfehlung**: Nonce in PHP generieren (siehe `wp-content/mu-plugins/csp-nonce.php` weiter unten).

### Schritt 2: WordPress Inline-Skripte anpassen

WordPress nutzt viele Inline-`<script>`-Tags (z.B. `wp_localize_script()`).
Diese müssen umgestellt werden auf:

**Vorher** (Inline):
```html
<script>var myConfig = {...};</script>
```

**Nachher** (Nonce):
```html
<script nonce="abc123xyz">var myConfig = {...};</script>
```

**WordPress-Hook** (`functions.php` oder mu-plugin):
```php
add_filter('script_loader_tag', function ($tag, $handle, $src) {
    $nonce = wp_get_csp_nonce(); // siehe mu-plugin unten
    if (strpos($tag, 'nonce=') === false) {
        $tag = str_replace('<script', '<script nonce="' . esc_attr($nonce) . '"', $tag);
    }
    return $tag;
}, 10, 3);
```

### Schritt 3: Inline Event-Handler entfernen

**Vorher**:
```html
<a onclick="doSomething()">Click</a>
```

**Nachher**:
```html
<a id="myLink">Click</a>
<script nonce="abc123">
document.getElementById('myLink').addEventListener('click', doSomething);
</script>
```

---

## 9. Alternative: CSP per WordPress (statt Apache)

Falls du CSP lieber in WordPress setzen willst (nicht empfohlen, aber möglich):

**Datei**: `/root/wordpress/html/wp-content/mu-plugins/csp.php`

```php
<?php
/**
 * Plugin Name: CSP Header Manager
 * Description: Sets Content-Security-Policy header (USE ONLY IF APACHE CSP IS DISABLED!)
 */

add_action('send_headers', function () {
    // Remove competing headers
    header_remove('Content-Security-Policy');
    header_remove('Content-Security-Policy-Report-Only');

    // Set CSP
    header("Content-Security-Policy: " .
        "default-src 'self'; " .
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' blob: " .
        "https://www.googletagmanager.com https://www.gstatic.com " .
        "https://pagead2.googlesyndication.com https://tpc.googlesyndication.com " .
        "https://www.googletagservices.com https://widget.intercom.io " .
        "https://cdn.gtranslate.net https://translate.google.com; " .
        "style-src 'self' 'unsafe-inline' https:; " .
        "img-src 'self' data: https:; " .
        "font-src 'self' data: https:; " .
        "connect-src 'self' https://api.ailinux.me:9000 https:; " .
        "frame-src 'self' https://www.googletagmanager.com https://pagead2.googlesyndication.com; " .
        "worker-src 'self' blob:; " .
        "media-src 'self' data: https:; " .
        "object-src 'none'; " .
        "base-uri 'self'; " .
        "form-action 'self';"
    );
}, 1000);
```

**WICHTIG**: Falls du diese Variante nutzt, **MUSST** du die CSP in Apache entfernen!

---

## 10. Nginx-Variante (Referenz)

Falls du später auf Nginx umsteigst:

```nginx
server {
    listen 443 ssl http2;
    server_name ailinux.me;

    # Remove competing headers (requires headers-more module)
    # more_clear_headers "Content-Security-Policy";
    # more_clear_headers "Content-Security-Policy-Report-Only";

    # CSP Header
    add_header Content-Security-Policy "
        default-src 'self';
        script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:
            https://www.googletagmanager.com
            https://www.gstatic.com
            https://pagead2.googlesyndication.com
            https://tpc.googlesyndication.com
            https://www.googletagservices.com
            https://widget.intercom.io
            https://cdn.gtranslate.net
            https://translate.google.com;
        style-src 'self' 'unsafe-inline' https:;
        img-src 'self' data: https:;
        font-src 'self' data: https:;
        connect-src 'self' https://api.ailinux.me:9000 https:;
        frame-src 'self' https://www.googletagmanager.com https://pagead2.googlesyndication.com;
        worker-src 'self' blob:;
        media-src 'self' data: https:;
        object-src 'none';
        base-uri 'self';
        form-action 'self';
    " always;

    # ... rest of config
}
```

**Test**:
```bash
sudo nginx -t && sudo systemctl reload nginx
curl -sI https://ailinux.me | grep -i content-security-policy
```

---

## 11. Troubleshooting

### Problem: "Refused to execute inline script" trotz CSP
**Ursache**: Zweite CSP (Report-Only) läuft noch.
**Lösung**:
```bash
# Check ob Report-Only Header existiert:
curl -sI https://ailinux.me | grep -i report-only

# Falls ja: WordPress-Plugin CSP deaktivieren oder Cloudflare prüfen.
```

### Problem: Google Translate lädt nicht
**Ursache**: `translate.google.com` fehlt in script-src.
**Lösung**: Bereits in aktueller CSP enthalten (Zeile 54).

### Problem: Service Worker registriert nicht
**Ursache**: `worker-src` fehlt oder zu restriktiv.
**Lösung**: `worker-src 'self' blob:` ist gesetzt (Zeile 60).

### Problem: Medien-Upload hängt
**Ursache**: `blob:` fehlt in script-src oder connect-src.
**Lösung**: `blob:` ist in script-src enthalten (Zeile 46).

---

## 12. Nächste Schritte (Härtung)

1. **Report-Only testen**: Neue CSP als Report-Only setzen, Violations sammeln.
2. **Nonces einführen**: PHP-basierte Nonce-Generierung + `script_loader_tag` Hook.
3. **Inline-Scripts auslagern**: Inline-JS in separate Dateien verschieben.
4. **unsafe-eval entfernen**: jQuery-Abhängigkeiten prüfen (schwierig bei WordPress).
5. **Domains einschränken**: `https:` für img-src/font-src/style-src auf konkrete Domains begrenzen.

**Aber**: Erst wenn die aktuelle CSP stabil läuft (1-2 Wochen), dann härten!

---

**Erstellt am**: 2025-10-04
**Letzte Änderung**: 2025-10-04
**Maintainer**: Brumo / Claude Code
