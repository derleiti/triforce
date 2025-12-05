# Monitoring Setup - TriStar Multi-LLM System

Dieses Setup richtet ein komplettes Monitoring für das AILinux Backend ein.
Es nutzt **Prometheus** für Metriken, **Grafana** für Dashboards und einen erweiterten **Audit-Logger** für Compliance.

## 1. Übersicht

- Prometheus sammelt Metriken vom FastAPI Backend
- Grafana visualisiert LLM-Performance, Request-Raten und Circuit Breaker Status
- Enhanced Audit Logger protokolliert alle Aktionen für SIEM-Export

## 2. Voraussetzungen

- Python 3.11+
- `prometheus_client` Python-Paket
- Prometheus Server (optional, für persistente Metriken)
- Grafana (optional, für Dashboards)
- Redis (für Rate Limiting)

## 3. Installation

```bash
# Prometheus Client installieren
pip install prometheus_client

# Backend neu starten
sudo systemctl restart ailinux-backend.service

# Metriken testen
curl http://localhost:9100/metrics
```

## 4. Konfiguration

Umgebungsvariablen in `.env`:

| Variable | Beschreibung | Default |
|----------|--------------|---------|
| `METRICS_ENABLED` | Metriken aktivieren | `true` |
| `METRICS_PATH` | Metriken-Endpoint | `/metrics` |
| `AUDIT_LOG_DIR` | Audit-Log Verzeichnis | `logs/audit` |
| `AUDIT_RETENTION_DAYS` | Log-Aufbewahrung | `30` |
| `AUDIT_MAX_SIZE_MB` | Max. Log-Größe | `100` |

## 5. Metriken-Übersicht

| Metrik | Typ | Labels | Beschreibung |
|--------|-----|--------|--------------|
| `ailinux_request_count` | Counter | endpoint, method, status | HTTP Requests gesamt |
| `ailinux_request_latency_seconds` | Histogram | endpoint | Request-Latenz |
| `ailinux_llm_calls_total` | Counter | model, provider, status | LLM API Aufrufe |
| `ailinux_llm_latency_seconds` | Histogram | model, provider | LLM Latenz |
| `ailinux_llm_tokens_total` | Counter | model, provider, type | Token-Verbrauch |
| `ailinux_active_connections` | Gauge | - | Aktive Verbindungen |
| `ailinux_memory_entries_total` | Gauge | - | TriForce Memory Einträge |
| `ailinux_circuit_breaker_state` | Gauge | llm_id | CB Status (0/1/2) |

## 6. Grafana-Setup

1. **Datenquelle hinzufügen**
   - Configuration → Data Sources → Add
   - Typ: Prometheus
   - URL: `http://localhost:9090`

2. **Dashboard importieren**
   - Dashboards → Import
   - JSON-Datei: `grafana/tristar-dashboard.json`
   - Oder Dashboard-ID verwenden

3. **Alerts konfigurieren** (optional)
   - Alerting → Alert Rules → New
   - Beispiel: `ailinux_circuit_breaker_state > 0` für CB-Alarm

## 7. Alerting (Beispiele)

### Prometheus Alert Rules (`prometheus/alerts.yml`)

```yaml
groups:
- name: tristar
  rules:
  # Hohe Error-Rate
  - alert: HighErrorRate
    expr: |
      sum(rate(ailinux_request_count{status=~"5.."}[5m]))
      / sum(rate(ailinux_request_count[5m])) > 0.05
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "Error Rate über 5%"

  # Circuit Breaker offen
  - alert: CircuitBreakerOpen
    expr: ailinux_circuit_breaker_state == 1
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Circuit Breaker {{ $labels.llm_id }} ist OPEN"

  # Hohe LLM-Latenz
  - alert: HighLLMLatency
    expr: |
      histogram_quantile(0.95,
        sum(rate(ailinux_llm_latency_seconds_bucket[5m])) by (le, model)
      ) > 30
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "LLM {{ $labels.model }} P95-Latenz > 30s"

  # Wenig Memory verfügbar
  - alert: LowMemoryEntries
    expr: ailinux_memory_entries_total < 10
    for: 10m
    labels:
      severity: info
    annotations:
      summary: "Wenige Memory-Einträge im System"
```

## 8. SIEM-Export

Audit-Logs für SIEM-Systeme exportieren:

```python
from app.utils.audit_enhanced import enhanced_audit_logger

# Export der letzten 7 Tage
await enhanced_audit_logger.export_for_siem(
    output_path="export/audit_export.jsonl",
    compress=True,
    since=datetime.now() - timedelta(days=7)
)
```

Output-Format (JSON-Lines):
```json
{"timestamp":"2025-12-04T20:00:00Z","trace_id":"abc123","action":"llm_call","resource":"/v1/chat","log_level":"INFO",...}
```

## 9. Nützliche Queries

```promql
# Request Rate pro Sekunde
rate(ailinux_request_count[1m])

# LLM Calls nach Provider (letzte Stunde)
sum(increase(ailinux_llm_calls_total[1h])) by (provider)

# Durchschnittliche Latenz
avg(rate(ailinux_request_latency_seconds_sum[5m]) / rate(ailinux_request_latency_seconds_count[5m]))

# Token-Verbrauch pro Minute
sum(rate(ailinux_llm_tokens_total[1m])) by (type)
```

---

**Generiert von:** GPT-OSS 20B, Codestral, Gemini Flash, Mistral Large
**Review:** Claude Opus 4.5
**Version:** 2.60
