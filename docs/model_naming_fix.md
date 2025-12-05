# Model Naming Inconsistencies - Fix

## Problem

Es gibt mehrere inkonsistente Varianten des GPT-OSS Model-Namens:

1. `gpt-oss:cloud` (config.py, crawler_summary_model)
2. `gpt-oss:120b-cloud` (config.py, crawler_ollama_model)
3. `gpt-oss:cloud/120b` (model_registry.py, posts.py)
4. `gpt-oss:latest` (.env, GPT_OSS_MODEL)

## Lösung: Standardisierung auf `gpt-oss:cloud/120b`

### 1. Config Update (app/config.py)

```python
# ZEILE 45-46:
# VORHER:
crawler_summary_model: Optional[str] = "gpt-oss:cloud"
crawler_ollama_model: Optional[str] = "gpt-oss:120b-cloud"

# NACHHER:
crawler_summary_model: Optional[str] = "gpt-oss:cloud/120b"
crawler_ollama_model: Optional[str] = "gpt-oss:cloud/120b"
```

### 2. Model Registry bleibt korrekt

`app/services/model_registry.py` Zeile 136 ist bereits korrekt:
```python
hosted.append(ModelInfo(id="gpt-oss:cloud/120b", provider="gpt-oss", capabilities=["chat"]))
```

### 3. Posts Service bleibt korrekt

`app/services/posts.py` Zeile 21 ist bereits korrekt:
```python
model_id = "gpt-oss:cloud/120b"
```

### 4. Environment Variable Update

`.env` Datei:
```bash
# VORHER:
GPT_OSS_MODEL=gpt-oss:latest

# NACHHER:
GPT_OSS_MODEL=gpt-oss:cloud/120b
CRAWLER_SUMMARY_MODEL=gpt-oss:cloud/120b
```

## Anwendung

```bash
# 1. Config.py aktualisieren
# Zeilen 45-46 ändern

# 2. .env aktualisieren
echo "GPT_OSS_MODEL=gpt-oss:cloud/120b" >> .env
echo "CRAWLER_SUMMARY_MODEL=gpt-oss:cloud/120b" >> .env

# 3. Server neu starten
uvicorn app.main:app --reload
```
