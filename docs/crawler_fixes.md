# Crawler Robustness Fixes

## Übersicht der Änderungen

### 1. Timeout-Erhöhungen
- **Crawler-Timeout**: 60s → 300s (5 Minuten)
- **Grund**: Große Crawls brauchen mehr Zeit
- **Fallback**: Partial Complete Status bei Timeout

### 2. Besseres Error-Handling

#### Playwright-Fehler
```python
# Spezifische Playwright-Fehler separat behandeln
except playwright._impl._errors.Error as exc:
    logger.error("Playwright error: %s", exc, exc_info=True)
    job.status = "failed"
    job.error = f"Playwright error ({type(exc).__name__}): {str(exc)}"
```

#### Response-Validierung
```python
# Robustere Prüfung mit Try-Catch
try:
    if not context.response:
        logger.warning("No response - skipping")
        return

    status = context.response.status
    if status >= 500:
        logger.error("Server error (%d) - skipping", status)
        return
except Exception as exc:
    logger.error("Error checking response: %s", exc, exc_info=True)
    return
```

### 3. Cookie-Banner-Handling

Mehrere Selektoren probieren:
```python
cookie_selectors = [
    'button:has-text("Accept All")',
    'button:has-text("Alle akzeptieren")',
    'button[id*="accept"]',
    'button[class*="accept"]',
]
for selector in cookie_selectors:
    try:
        await context.page.click(selector, timeout=3000)
        logger.debug("Clicked: %s", selector)
        break
    except playwright._impl._errors.TimeoutError:
        continue
```

### 4. Content-Extraction mit Fehlerbehandlung

```python
try:
    html = await context.page.content()
    soup = BeautifulSoup(html, "html.parser")
    text_content = self._extract_text(soup)
except Exception as exc:
    logger.error("Error extracting content: %s", exc, exc_info=True)
    return
```

### 5. Ollama-Analyse mit Graceful Degradation

```python
if job.ollama_assisted and job.ollama_query:
    try:
        ollama_analysis = await self._ollama_analyze_content(...)
        if relevance_score > 0:
            score = (score + relevance_score) / 2.0
    except Exception as exc:
        logger.warning("Ollama analysis failed: %s", exc)
        # Weiter mit ursprünglichem Score
```

### 6. Link-Extraction mit Limits

```python
try:
    links = await self._extract_links(context, job)
    # Nur so viele Links wie max_pages erlaubt
    for link in links[:min(len(links), job.max_pages - job.pages_crawled)]:
        try:
            # Link enqueue
        except Exception as e:
            logger.warning("Failed to enqueue link: %s", e)
except Exception as exc:
    logger.error("Error extracting links: %s", exc, exc_info=True)
```

## Anwendung der Fixes

Die Änderungen sind in `manager_fixed.py` als Diff dokumentiert.

**Nächster Schritt**: HTTP-Client Retry-Logic hinzufügen.
