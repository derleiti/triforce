# WordPress Integration - Complete Guide

## 🎯 Was wurde implementiert

### WordPress Admin Dashboard

**Neue Dateien:**
1. `nova-ai-frontend/includes/class-nova-ai-admin-dashboard.php` - Admin UI
2. `nova-ai-frontend/assets/admin.js` - Dashboard JavaScript
3. `nova-ai-frontend/assets/admin.css` - Dashboard Styles
4. `nova-ai-frontend/nova-ai-frontend.php` - Updated Plugin Main File

**Features:**
- ✅ Live Dashboard mit Echtzeit-Stats
- ✅ Auto-Publisher Einstellungen
- ✅ Crawler Status Monitoring
- ✅ Manuelle Publish-Trigger
- ✅ Recent Posts Übersicht

## 📋 Installation

### 1. Plugin aktivieren

```bash
# Im WordPress Verzeichnis
cd wp-content/plugins/
# Plugin sollte bereits da sein in nova-ai-frontend/

# Im WordPress Admin:
Plugins → Nova AI Frontend → Aktivieren
```

### 2. Admin Dashboard aufrufen

Nach Aktivierung erscheint neues Menü:
```
WordPress Admin → Nova AI
  ├── Dashboard
  ├── Auto-Publisher
  └── Crawler Status
```

### 3. Auto-Publisher konfigurieren

```
WordPress Admin → Nova AI → Auto-Publisher

Einstellungen:
✅ Auto-Publishing aktiviert
📁 Standard-Kategorie: [Wählen]
💬 Standard-Forum: [Wählen] (bbPress)
👤 Autor für Posts: Administrator
```

### 4. Backend-Verbindung prüfen

Dashboard zeigt:
- ✅ Auto-Publisher: Aktiv
- 📊 Crawler: X aktive Jobs
- 📝 Posts Heute: X
- ⏳ Wartend: X Ergebnisse

## 🎨 Dashboard Features

### Live Stats

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Auto-Publisher  │  │ Crawler         │  │ Posts Heute     │
│ ✅ Aktiv        │  │ 2 aktive        │  │ 5               │
└─────────────────┘  └─────────────────┘  └─────────────────┘

┌─────────────────┐
│ Wartend         │
│ 12 Ergebnisse   │
└─────────────────┘
```

Auto-Refresh alle 30 Sekunden!

### Recent Posts Table

```
┌────────────────────────────────────────────────────────────┐
│ Kürzlich automatisch erstellt                             │
├──────────────────────┬────────┬─────────┬──────────┬───────┤
│ Titel                │ Score  │ Quelle  │ Erstellt │ Akt.  │
├──────────────────────┼────────┼─────────┼──────────┼───────┤
│ AI News: GPT-5       │ 0.85   │ Crawler │ 10:30    │ [>>]  │
│ Linux Kernel 6.8     │ 0.78   │ Crawler │ 09:45    │ [>>]  │
└──────────────────────┴────────┴─────────┴──────────┴───────┘
```

### Manueller Trigger

```
┌─────────────────────────────────────────┐
│ Manuelle Ausführung                     │
├─────────────────────────────────────────┤
│ Sofort neue Crawler-Ergebnisse prüfen  │
│ und veröffentlichen                     │
│                                         │
│ [Jetzt veröffentlichen]                 │
│                                         │
│ ✅ Auto-Publisher manuell getriggert    │
└─────────────────────────────────────────┘
```

## 🔧 Backend Integration

### WordPress REST API Calls

Dashboard nutzt folgende Backend-Endpoints:

```javascript
// Health Check
GET /health
→ {"ok": true, "ts": 1234567890}

// Crawler Jobs
GET /v1/crawler/jobs
→ [{id, status, pages_crawled, ...}]

// Search Results
POST /v1/crawler/search
{
  "query": "",
  "limit": 50,
  "min_score": 0.6
}
→ [{id, title, score, posted_at, ...}]
```

### WordPress AJAX Actions

```php
// Get Stats (WordPress-Seite)
do_action('wp_ajax_nova_ai_get_stats')
→ {posts_today, recent_posts, ...}

// Trigger Publish
do_action('wp_ajax_nova_ai_trigger_publish')
→ {success, message}
```

## 📊 Monitoring

### Dashboard Metriken

**Auto-Publisher Status:**
- ✅ Aktiv - Backend läuft und Publisher ist aktiv
- ❌ Offline - Backend nicht erreichbar
- ⚠️ Fehler - Verbindungsprobleme

**Crawler Status:**
- Anzahl aktiver Crawl-Jobs
- Wird live vom Backend geholt

**Posts Heute:**
- Anzahl automatisch erstellter Posts
- Nur Posts mit Meta: `_nova_ai_auto_created = 1`

**Wartende Ergebnisse:**
- Crawler-Ergebnisse > 0.6 Score
- Noch nicht als Post veröffentlicht

### Auto-Created Posts

Posts werden mit Meta-Daten markiert:

```php
// In Backend (app/services/auto_publisher.py)
// Nach WordPress Post-Erstellung:

// WordPress Seite:
update_post_meta($post_id, '_nova_ai_auto_created', '1');
update_post_meta($post_id, '_nova_ai_created_at', current_time('mysql'));
update_post_meta($post_id, '_nova_ai_source_url', $result->url);
update_post_meta($post_id, '_nova_ai_score', $result->score);
```

### WordPress Helper Functions

```php
// Get all auto-created posts
$posts = \NovaAI\get_auto_created_posts([
  'date_query' => [
    ['after' => 'today']
  ]
]);

// Mark post as auto-created (Backend-Integration)
\NovaAI\mark_post_auto_created($post_id);
```

## 🎨 Admin UI Customization

### Styles anpassen

In `admin.css`:

```css
/* Custom Brand Colors */
.nova-ai-stat-card .stat-value {
  color: #your-brand-color;
}

/* Dashboard Grid Layout */
.nova-ai-stats-grid {
  grid-template-columns: repeat(4, 1fr);
  /* oder repeat(auto-fit, minmax(250px, 1fr)) */
}
```

### JavaScript Events

In `admin.js`:

```javascript
// Custom Event Hook
$(document).on('nova-ai-stats-loaded', function(e, data) {
  console.log('Stats loaded:', data);
});

// Trigger nach Stats-Load
NovaAIAdmin.loadDashboardStats().then(data => {
  $(document).trigger('nova-ai-stats-loaded', [data]);
});
```

## 🔐 Permissions

### Required Capabilities

```php
// Dashboard Zugriff
current_user_can('manage_options')

// Empfohlen: Nur Administrator
is_admin() && current_user_can('administrator')
```

### Custom Capability (Optional)

```php
// In functions.php
add_action('admin_init', function() {
  $role = get_role('administrator');
  $role->add_cap('manage_nova_ai');
});

// In Plugin
if (!current_user_can('manage_nova_ai')) {
  wp_die('Unauthorized');
}
```

## 🧪 Testing

### Dashboard UI Test

1. WordPress Admin → Nova AI → Dashboard
2. Prüfe Live-Stats werden geladen (Spinner → Daten)
3. Click "Jetzt veröffentlichen"
4. Prüfe Erfolgs-Nachricht

### Backend Connection Test

```javascript
// Browser Console (Admin Dashboard)
await fetch('https://api.ailinux.me:9100/health')
  .then(r => r.json())
  .then(console.log);
```

Expected:
```json
{"ok": true, "ts": 1234567890}
```

### AJAX Test

```javascript
// Browser Console (Admin Dashboard)
jQuery.post(ajaxurl, {
  action: 'nova_ai_get_stats',
  nonce: novaAIAdmin.nonce
}, console.log);
```

Expected:
```json
{
  "success": true,
  "data": {
    "posts_today": 5,
    "recent_posts": [...]
  }
}
```

## 🐛 Troubleshooting

### Dashboard zeigt "Offline"

**Diagnose:**
```bash
# Prüfe Backend läuft
curl https://api.ailinux.me:9100/health

# Prüfe CORS
curl -I https://api.ailinux.me:9100/health \
  -H "Origin: https://ailinux.me"
```

**Lösung:**
1. Backend starten: `uvicorn app.main:app --host 0.0.0.0 --port 9100`
2. CORS prüfen in `app/main.py`
3. API_BASE URL prüfen in WordPress Settings

### Stats werden nicht geladen

**Diagnose:**
```javascript
// Browser Console
console.log(novaAIAdmin);
```

Expected:
```javascript
{
  apiBase: "https://api.ailinux.me:9100",
  ajaxUrl: "/wp-admin/admin-ajax.php",
  nonce: "abc123..."
}
```

**Lösung:**
1. Plugin neu aktivieren
2. Cache leeren
3. JavaScript Fehler prüfen (F12 Console)

### Posts erscheinen nicht in "Recent"

**Diagnose:**
```sql
-- WordPress Datenbank
SELECT post_id, meta_key, meta_value
FROM wp_postmeta
WHERE meta_key = '_nova_ai_auto_created';
```

**Lösung:**
Posts müssen Meta-Daten haben. Backend muss nach WordPress Post-Erstellung Meta setzen.

Integration in `app/services/auto_publisher.py`:

```python
# Nach wp_result = await wordpress_service.create_post(...)
post_id = wp_result.get("id")

# Set Meta via REST API
meta_url = f"{wordpress_url}/wp-json/wp/v2/posts/{post_id}"
await client.post(meta_url, json={
  "meta": {
    "_nova_ai_auto_created": "1",
    "_nova_ai_source_url": result.url,
    "_nova_ai_score": result.score,
  }
})
```

## 📈 Next Steps

- [ ] Custom Post Meta UI (Edit Post Screen)
- [ ] Bulk Actions (Approve/Reject Crawler Results)
- [ ] Category Auto-Mapping (AI-based)
- [ ] Featured Image Auto-Upload
- [ ] SEO Meta-Tags Generation
- [ ] Social Media Auto-Sharing

## 🆘 Support

Bei Problemen:
1. Browser Console prüfen (F12)
2. WordPress Debug Log: `wp-content/debug.log`
3. Backend Logs: `/var/log/uvicorn.log`
4. Plugin neu aktivieren

**Viel Erfolg! 🚀**
