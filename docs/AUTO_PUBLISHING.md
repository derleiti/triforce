# Automatisches WordPress Publishing System

## Übersicht

Das System crawlt automatisch interessante Tech-News und postet sie:
1. **WordPress Blog Posts** - Professionelle Artikel
2. **bbPress Forum Topics** - Diskussionsthemen

## Features

### ✅ Automatischer Crawler
- Läuft 24/7 im Hintergrund
- Crawlt AI-, Linux-, Windows-, Tech-News
- Indiziert mit BM25 für semantische Suche
- Speichert Ergebnisse mit Relevanz-Score

### ✅ Auto-Publisher
- Prüft **stündlich** auf neue hochqualitative Ergebnisse
- Postet max. **3 Artikel pro Stunde**
- Minimum Relevanz-Score: **0.6** (60%)
- Generiert professionelle Artikel mit GPT-OSS (120B)

### ✅ WordPress Integration
- Erstellt Blog-Posts mit generiertem Inhalt
- Fügt Quellenangabe hinzu
- Postet als Administrator
- Markiert Posts als "published"

### ✅ bbPress Forum Integration
- Erstellt Forum Topics
- Mit Link zum Original-Artikel
- Automatische Tags aus Crawler-Labels
- Forum ID konfigurierbar

## Konfiguration

### Environment Variables (.env)

```bash
# WordPress Zugangsdaten (Administrator)
WORDPRESS_URL=https://ailinux.me
WORDPRESS_USERNAME=admin
WORDPRESS_PASSWORD=your_secure_password

# GPT-OSS Model für Artikel-Generierung
GPT_OSS_API_KEY=your_api_key
GPT_OSS_BASE_URL=https://your-api-endpoint.com
CRAWLER_SUMMARY_MODEL=gpt-oss:cloud/120b

# Crawler Einstellungen
CRAWLER_ENABLED=true
CRAWLER_FLUSH_INTERVAL=3600  # 1 Stunde
CRAWLER_MAX_MEMORY_BYTES=536870912  # 512 MB

# Optional: bbPress Forum ID
BBPRESS_FORUM_ID=1  # Standard "General" Forum
```

### Auto-Publisher Einstellungen

In `app/services/auto_publisher.py`:

```python
self._interval = 3600  # Prüf-Intervall (1 Stunde)
self._min_score = 0.6  # Minimum Relevanz-Score (60%)
self._max_posts_per_hour = 3  # Max Posts pro Stunde
```

## Workflow

```
1. Crawler läuft 24/7
   └─> Crawlt Tech-News Sites
   └─> Bewertet Relevanz (BM25 + Keywords)
   └─> Speichert Ergebnisse mit Score

2. Auto-Publisher (stündlich)
   └─> Holt Top 20 ungepostete Ergebnisse
   └─> Filtert nach Score >= 0.6
   └─> Sortiert nach Score
   └─> Postet Top 3:
       ├─> Generiert Artikel (GPT-OSS 120B)
       ├─> Erstellt WordPress Post
       ├─> Erstellt bbPress Topic
       └─> Markiert als gepostet

3. WordPress
   └─> Neuer Blog-Post erscheint
   └─> Neues Forum-Topic erscheint
   └─> Nutzer können diskutieren
```

## Startup

Der Auto-Publisher startet automatisch mit dem FastAPI Server:

```python
# In app/main.py
if settings.crawler_enabled:
    @app.on_event("startup")
    async def _start_crawler():
        await crawler_manager.start()
        await auto_publisher.start()  # <-- Auto-Publisher

    @app.on_event("shutdown")
    async def _stop_crawler():
        await crawler_manager.stop()
        await auto_publisher.stop()  # <-- Clean shutdown
```

## Logs

```bash
# Tail Logs
tail -f /var/log/uvicorn.log

# Wichtige Log-Einträge:
# - "Starting auto-publisher (interval: 3600 seconds)"
# - "Auto-publisher: Processing hourly crawl results..."
# - "Published result: [title] (score: 0.85)"
# - "Created WordPress post: [title] (ID: 123)"
# - "Created bbPress topic: [title] (ID: 456)"
```

## Testing

### Manueller Test

```python
# Python Console
import asyncio
from app.services.auto_publisher import auto_publisher

# Einmaliger Run
asyncio.run(auto_publisher._process_hourly())
```

### API Test

```bash
# Check Crawler Results
curl http://localhost:9100/v1/crawler/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "",
    "limit": 10,
    "min_score": 0.6
  }'

# Check Jobs
curl http://localhost:9100/v1/crawler/jobs
```

## Troubleshooting

### Posts werden nicht erstellt

1. **Check WordPress Credentials**:
```bash
grep WORDPRESS .env
```

2. **Check Model verfügbar**:
```bash
curl http://localhost:9100/v1/models | jq '.data[] | select(.id | contains("gpt-oss"))'
```

3. **Check Crawler Results**:
```bash
# Logs prüfen
grep "high-quality results" /var/log/uvicorn.log
```

4. **Check Auto-Publisher läuft**:
```bash
# In Logs nach "Starting auto-publisher" suchen
grep "auto-publisher" /var/log/uvicorn.log
```

### bbPress Topics werden nicht erstellt

**Problem**: bbPress hat keine offizielle REST API

**Lösung 1**: Custom Post Type nutzen
```php
// In WordPress: Register bbPress als Custom Post Type
register_post_type('topic', [
    'show_in_rest' => true,
    // ...
]);
```

**Lösung 2**: bbPress REST API Plugin installieren
```bash
# Im WordPress Admin:
Plugins -> Add New -> "bbPress REST API"
```

**Lösung 3**: Nur WordPress Posts (kein Forum)
```python
# In auto_publisher.py
async def _create_forum_topic(self, result):
    logger.info("Forum posting disabled")
    return  # Skip forum posting
```

## Monitoring

### Metriken

```python
# In auto_publisher.py hinzufügen:
self._stats = {
    "posts_created": 0,
    "topics_created": 0,
    "errors": 0,
    "last_run": None,
}
```

### Health Check Endpoint

```python
# In app/main.py hinzufügen:
@app.get("/v1/auto-publisher/status")
async def auto_publisher_status():
    return {
        "running": auto_publisher._task is not None,
        "interval": auto_publisher._interval,
        "stats": auto_publisher._stats,
    }
```

## Security

### WordPress Admin Permissions

Der konfigurierte User **MUSS Administrator sein**:

```bash
# WordPress CLI:
wp user add-role admin administrator

# Oder in WordPress Admin:
Users -> [username] -> Role -> Administrator
```

### API Key Security

```bash
# .env File Permissions
chmod 600 .env

# Nie commiten!
echo ".env" >> .gitignore
```

## Roadmap

- [ ] Category Mapping (Tech, AI, Linux, etc.)
- [ ] Automatic Image Upload (Featured Images)
- [ ] Multi-Forum Support (verschiedene Topics)
- [ ] User Interaction (Crawler-Feedback)
- [ ] A/B Testing für Artikel-Prompts
- [ ] SEO Optimization (Meta-Tags)
- [ ] Social Media Integration

## Support

Bei Problemen:
1. Logs prüfen: `/var/log/uvicorn.log`
2. `.env` konfigurieren
3. WordPress Permissions prüfen
4. Model verfügbar prüfen
