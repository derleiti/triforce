# Komplette Setup-Anleitung - WordPress Auto-Publishing

## 🎯 Was wurde implementiert

### Backend-Komponenten

1. **Model Naming Fix** ✅
   - Standardisiert auf `gpt-oss:cloud/120b`
   - Konsistent in allen Services

2. **Robustness Fixes** ✅
   - HTTP Client mit Retry-Logic
   - Crawler Timeout 60s → 300s
   - Bessere Fehlerbehandlung überall

3. **Auto-Publisher** ✅
   - Stündliche Prüfung neuer Crawler-Ergebnisse
   - Generiert Artikel mit GPT-OSS 120B
   - Postet zu WordPress & bbPress

4. **bbPress Integration** ✅
   - Forum Topic Creation
   - Reply Support
   - Tag Support

## 📋 Setup Checklist

### 1. Backend Dependencies

```bash
# Install tenacity for retry logic
pip install tenacity>=8.2.0

# Update requirements.txt
echo "tenacity>=8.2.0" >> requirements.txt
```

### 2. Environment Configuration

Erstelle/Update `.env`:

```bash
# WordPress Admin Credentials (MUST BE ADMINISTRATOR!)
WORDPRESS_URL=https://ailinux.me
WORDPRESS_USERNAME=admin
WORDPRESS_PASSWORD=your_secure_password

# GPT-OSS API Configuration
GPT_OSS_API_KEY=your_api_key_here
GPT_OSS_BASE_URL=https://your-gpt-endpoint.com
GPT_OSS_MODEL=gpt-oss:cloud/120b

# Crawler Settings
CRAWLER_ENABLED=true
CRAWLER_SUMMARY_MODEL=gpt-oss:cloud/120b
CRAWLER_MAX_MEMORY_BYTES=536870912
CRAWLER_FLUSH_INTERVAL=3600
CRAWLER_RETENTION_DAYS=30

# Optional: bbPress Forum ID
BBPRESS_FORUM_ID=1
```

### 3. Verify File Permissions

```bash
chmod 600 .env
chown www-data:www-data .env  # Adjust user as needed
```

### 4. Apply Crawler Fixes (Optional)

```bash
# Apply fixes from docs/crawler_fixes.md
# Manually integrate changes from:
cat docs/crawler_fixes.md
# Into: app/services/crawler/manager.py
```

### 5. WordPress Configuration

#### a) User Permissions

Der konfigurierte User **MUSS Administrator sein**:

```bash
# Option 1: WordPress CLI
wp user add-role YOUR_USERNAME administrator

# Option 2: WordPress Admin UI
Users → [username] → Role → Administrator → Save
```

#### b) bbPress Setup (Optional)

Wenn bbPress Topics nicht funktionieren:

**Option A**: bbPress REST API Plugin installieren
```
WordPress Admin → Plugins → Add New
Search: "bbPress REST API"
Install & Activate
```

**Option B**: Custom Post Type registrieren

In `functions.php`:
```php
add_filter('register_post_type_args', function($args, $post_type) {
    if ($post_type === 'topic' || $post_type === 'reply') {
        $args['show_in_rest'] = true;
    }
    return $args;
}, 10, 2);
```

**Option C**: Forum Posting deaktivieren

In `app/services/auto_publisher.py` Zeile 202:
```python
async def _create_forum_topic(self, result):
    logger.info("Forum posting disabled")
    return
```

### 6. Start Server

```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 9100

# Production
uvicorn app.main:app --host 0.0.0.0 --port 9100 --workers 4
```

## 🧪 Testing

### Test 1: Model verfügbar

```bash
curl http://localhost:9100/v1/models | jq '.data[] | select(.id | contains("gpt-oss"))'
```

Expected Output:
```json
{
  "id": "gpt-oss:cloud/120b",
  "provider": "gpt-oss",
  "capabilities": ["chat"]
}
```

### Test 2: WordPress Connection

```bash
# Python Console
python3 << EOF
import asyncio
from app.services.wordpress import wordpress_service

async def test():
    categories = await wordpress_service.list_categories()
    print(f"Found {len(categories)} categories")

asyncio.run(test())
EOF
```

### Test 3: Crawler Running

```bash
curl http://localhost:9100/v1/crawler/jobs
```

Expected: Liste von Crawl-Jobs

### Test 4: Auto-Publisher Manual Run

```python
# Python Console
import asyncio
from app.services.auto_publisher import auto_publisher

asyncio.run(auto_publisher._process_hourly())
```

Check logs for:
- "Auto-publisher: Processing hourly crawl results..."
- "Published result: [title]"

## 📊 Monitoring

### Logs ansehen

```bash
# Tail logs
tail -f /var/log/uvicorn.log

# Filter Auto-Publisher
grep "auto-publisher" /var/log/uvicorn.log

# Filter Crawler
grep "crawler" /var/log/uvicorn.log
```

### Health Check

```bash
curl http://localhost:9100/health
```

Expected:
```json
{"ok": true, "ts": 1234567890}
```

## 🔧 Troubleshooting

### Problem: Posts werden nicht erstellt

**Diagnose:**
```bash
# 1. Check WordPress credentials
curl -u $WORDPRESS_USERNAME:$WORDPRESS_PASSWORD \
  $WORDPRESS_URL/wp-json/wp/v2/categories

# 2. Check GPT-OSS API
curl -H "Authorization: Bearer $GPT_OSS_API_KEY" \
  $GPT_OSS_BASE_URL/v1/models

# 3. Check Crawler results
curl http://localhost:9100/v1/crawler/search \
  -H "Content-Type: application/json" \
  -d '{"query": "", "limit": 10, "min_score": 0.6}'
```

**Lösungen:**
1. WordPress User Permissions prüfen
2. GPT-OSS API Key validieren
3. Crawler Score-Threshold anpassen (in `auto_publisher.py`)

### Problem: bbPress Topics nicht erstellt

**Diagnose:**
```bash
# Check bbPress REST API
curl -u $WORDPRESS_USERNAME:$WORDPRESS_PASSWORD \
  $WORDPRESS_URL/wp-json/wp/v2/topic
```

**Lösungen:**
1. bbPress REST API Plugin installieren
2. Custom Post Type registrieren (siehe oben)
3. Forum Posting temporär deaktivieren

### Problem: Crawler findet keine Ergebnisse

**Diagnose:**
```bash
# Check Crawler Jobs
curl http://localhost:9100/v1/crawler/jobs

# Check Spool Directory
ls -lah data/crawler_spool/train/
```

**Lösungen:**
1. Crawler Seeds erweitern (in `crawler/manager.py` Zeile 763)
2. Relevance Threshold senken (in `auto_publisher.py` Zeile 29)
3. Manuellen Crawl-Job starten:

```bash
curl -X POST http://localhost:9100/v1/crawler/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["ai", "linux"],
    "seeds": ["https://techcrunch.com"],
    "max_depth": 2,
    "max_pages": 50
  }'
```

## 📈 Performance Optimization

### Auto-Publisher Einstellungen anpassen

In `app/services/auto_publisher.py`:

```python
# Zeile 28-30
self._interval = 3600  # Stündlich (Default)
self._min_score = 0.6  # Min. 60% Relevanz
self._max_posts_per_hour = 3  # Max 3 Posts/Stunde

# Aggressiver (mehr Posts):
self._interval = 1800  # Alle 30 Minuten
self._min_score = 0.5  # Min. 50% Relevanz
self._max_posts_per_hour = 5

# Konservativer (weniger Posts):
self._interval = 7200  # Alle 2 Stunden
self._min_score = 0.7  # Min. 70% Relevanz
self._max_posts_per_hour = 2
```

### Crawler Seeds erweitern

In `app/services/crawler/manager.py` Zeile 763:

```python
seeds = [
    # AI News
    "https://www.artificialintelligence-news.com/",
    "https://www.technologyreview.com/tag/artificial-intelligence/",
    "https://venturebeat.com/category/ai/",

    # Linux News
    "https://www.phoronix.com/",
    "https://www.linuxtoday.com/",
    "https://itsfoss.com/",

    # General Tech
    "https://techcrunch.com/",
    "https://www.theverge.com/tech",
    "https://arstechnica.com/",

    # Developer News
    "https://news.ycombinator.com/",
    "https://dev.to/",
]
```

## 🎓 Best Practices

### 1. Artikel-Qualität

Prompt in `auto_publisher.py` Zeile 146 anpassen:

```python
prompt = f"""Schreibe einen professionellen Tech-Artikel auf Deutsch.

Stil:
- Sachlich und objektiv
- Technisch präzise
- Für Entwickler und IT-Profis
- Mit konkreten Beispielen

Struktur:
- Einleitung (Was ist passiert?)
- Hauptteil (Details & Kontext)
- Auswirkungen (Was bedeutet das?)
- Fazit (Zusammenfassung)

Quellen:
Titel: {result.title}
URL: {result.url}
Inhalt: {result.content[:2000]}
"""
```

### 2. Category Mapping

In `auto_publisher.py` nach Zeile 185 hinzufügen:

```python
# Intelligentes Category Mapping
def get_category_ids(result):
    categories = []

    # AI/ML Category
    if any(kw in result.content.lower() for kw in ["ai", "machine learning", "neural"]):
        categories.append(5)  # AI Category ID

    # Linux Category
    if any(kw in result.content.lower() for kw in ["linux", "ubuntu", "debian"]):
        categories.append(3)  # Linux Category ID

    # Windows Category
    if any(kw in result.content.lower() for kw in ["windows", "microsoft"]):
        categories.append(4)  # Windows Category ID

    return categories or [1]  # Default: Uncategorized

# Usage in create_post():
wp_result = await wordpress_service.create_post(
    title=result.title,
    content=article_content,
    status="publish",
    categories=get_category_ids(result),  # <-- Add this
)
```

### 3. Featured Images

In `auto_publisher.py` erweitern:

```python
# Nach Artikel-Generierung
if result.image_url:
    # Download & Upload Image
    async with httpx.AsyncClient() as client:
        img_response = await client.get(result.image_url)
        if img_response.status_code == 200:
            media = await wordpress_service.upload_media(
                filename="featured.jpg",
                file_content=img_response.content,
                content_type="image/jpeg",
            )
            featured_media = media.get("id")
```

## 📝 Next Steps

1. ✅ Server starten und Logs überwachen
2. ✅ Nach 1 Stunde ersten Post prüfen
3. ⏳ Category Mapping hinzufügen
4. ⏳ Featured Images implementieren
5. ⏳ SEO Optimization (Meta-Tags)
6. ⏳ Social Media Auto-Sharing

## 🆘 Support

Bei Fragen/Problemen:
1. Logs prüfen: `tail -f /var/log/uvicorn.log`
2. Dokumentation: `docs/AUTO_PUBLISHING.md`
3. Troubleshooting: Diese Datei, Abschnitt "Troubleshooting"

**Viel Erfolg! 🚀**
