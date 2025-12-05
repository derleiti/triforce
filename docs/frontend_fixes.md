# Frontend API Integration Fixes

## Identifizierte Probleme

1. **Keine Timeout-Behandlung** bei fetch()-Requests
2. **Keine Retry-Logic** bei Netzwerkfehlern
3. **Unzureichende Fehlerbehandlung** bei API-Errors
4. **Fehlende Offline-Erkennung**
5. **Keine Verbindungsprüfung** vor Requests

## Lösungen

### 1. Robuster Fetch-Wrapper

**Neue Datei: `nova-ai-frontend/assets/api-client.js`**

```javascript
/**
 * Robuster API-Client mit Retry-Logic und Fehlerbehandlung
 */
(function (window) {
  const DEFAULT_TIMEOUT = 30000; // 30 Sekunden
  const MAX_RETRIES = 3;
  const RETRY_DELAY = 1000; // 1 Sekunde

  /**
   * Timeout-Wrapper für fetch()
   */
  function fetchWithTimeout(url, options = {}, timeout = DEFAULT_TIMEOUT) {
    return Promise.race([
      fetch(url, options),
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error('Request timeout')), timeout)
      )
    ]);
  }

  /**
   * Exponential Backoff Delay
   */
  function getRetryDelay(attempt) {
    return RETRY_DELAY * Math.pow(2, attempt);
  }

  /**
   * Prüft ob Fehler retry-fähig ist
   */
  function isRetryableError(error, response) {
    // Netzwerkfehler
    if (error.message === 'Request timeout' || error.message === 'Failed to fetch') {
      return true;
    }

    // HTTP Status-Codes
    if (response) {
      const status = response.status;
      return status === 408 || status === 429 || status >= 500;
    }

    return false;
  }

  /**
   * Robuster Fetch mit Retry-Logic
   */
  async function robustFetch(url, options = {}, config = {}) {
    const timeout = config.timeout || DEFAULT_TIMEOUT;
    const maxRetries = config.maxRetries || MAX_RETRIES;
    const onRetry = config.onRetry || (() => {});

    let lastError;
    let lastResponse;

    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        // Offline-Check
        if (!navigator.onLine) {
          throw new Error('No internet connection');
        }

        const response = await fetchWithTimeout(url, options, timeout);

        // Bei Erfolg direkt zurückgeben
        if (response.ok) {
          return response;
        }

        lastResponse = response;

        // Prüfen ob Retry sinnvoll ist
        if (!isRetryableError(null, response)) {
          return response; // Nicht retry-fähig, direkt zurückgeben
        }

        // Retry bei retryable errors
        if (attempt < maxRetries - 1) {
          const delay = getRetryDelay(attempt);
          console.warn(
            `API request failed (status ${response.status}), retrying in ${delay}ms... (attempt ${attempt + 1}/${maxRetries})`
          );
          onRetry(attempt + 1, delay);
          await new Promise(resolve => setTimeout(resolve, delay));
          continue;
        }

        return response;

      } catch (error) {
        lastError = error;

        // Prüfen ob Retry sinnvoll ist
        if (!isRetryableError(error, null)) {
          throw error; // Nicht retry-fähig, direkt werfen
        }

        // Retry bei retryable errors
        if (attempt < maxRetries - 1) {
          const delay = getRetryDelay(attempt);
          console.warn(
            `API request failed (${error.message}), retrying in ${delay}ms... (attempt ${attempt + 1}/${maxRetries})`
          );
          onRetry(attempt + 1, delay);
          await new Promise(resolve => setTimeout(resolve, delay));
          continue;
        }

        throw error;
      }
    }

    // Alle Versuche fehlgeschlagen
    if (lastResponse) {
      return lastResponse;
    }
    throw lastError || new Error('All retry attempts failed');
  }

  /**
   * API-Client Klasse
   */
  class NovaAPIClient {
    constructor(baseURL, clientHeader) {
      this.baseURL = baseURL.replace(/\/$/, '');
      this.clientHeader = clientHeader;
    }

    /**
     * GET-Request
     */
    async get(endpoint, config = {}) {
      const url = `${this.baseURL}${endpoint}`;
      const options = {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'X-AILinux-Client': this.clientHeader,
          ...config.headers,
        },
      };

      return robustFetch(url, options, config);
    }

    /**
     * POST-Request
     */
    async post(endpoint, data, config = {}) {
      const url = `${this.baseURL}${endpoint}`;
      const options = {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'X-AILinux-Client': this.clientHeader,
          ...config.headers,
        },
        body: JSON.stringify(data),
      };

      return robustFetch(url, options, config);
    }

    /**
     * POST mit Streaming-Response
     */
    async postStream(endpoint, data, config = {}) {
      const url = `${this.baseURL}${endpoint}`;
      const options = {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/plain',
          'X-AILinux-Client': this.clientHeader,
          ...config.headers,
        },
        body: JSON.stringify(data),
      };

      // Streaming hat keine Retries (würde state kaputt machen)
      return fetchWithTimeout(url, options, config.timeout || DEFAULT_TIMEOUT);
    }
  }

  // Export
  window.NovaAPIClient = NovaAPIClient;
  window.robustFetch = robustFetch;

})(window);
```

### 2. Integration in app.js

```javascript
// VORHER (Zeile 143-165):
async function fetchModels() {
  setLoading(root, true);
  try {
    const response = await fetch(`${API_BASE}/v1/models`, {
      headers: {
        'Accept': 'application/json',
        'X-AILinux-Client': CLIENT_HEADER,
      },
    });
    if (!response.ok) {
      throw await response.json();
    }
    const payload = await response.json();
    // ...
  } catch (error) {
    reportError('Unable to load models', error);
  }
}

// NACHHER:
const apiClient = new NovaAPIClient(API_BASE, CLIENT_HEADER);

async function fetchModels() {
  setLoading(root, true);
  try {
    const response = await apiClient.get('/v1/models', {
      timeout: 10000, // 10 Sekunden für Model-Liste
      onRetry: (attempt, delay) => {
        console.log(`Retrying models request (attempt ${attempt})...`);
      }
    });

    if (!response.ok) {
      const error = await response.json();
      throw error;
    }

    const payload = await response.json();
    state.models = Array.isArray(payload.data) ? payload.data : [];
    // ...
  } catch (error) {
    if (error.message === 'No internet connection') {
      reportError('Keine Internetverbindung', error);
    } else if (error.message === 'Request timeout') {
      reportError('Anfrage hat zu lange gedauert', error);
    } else {
      reportError('Modelle konnten nicht geladen werden', error);
    }
  } finally {
    setLoading(root, false);
  }
}
```

### 3. Streaming mit besserer Fehlerbehandlung

```javascript
// VORHER (Zeile 441-474):
async function streamChat(payload, bubble) {
  const response = await fetch(`${API_BASE}/v1/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/plain',
      'X-AILinux-Client': CLIENT_HEADER,
    },
    body: JSON.stringify({
      model: payload.model,
      messages: payload.messages,
      stream: true,
      temperature: payload.temperature,
    }),
  });

  if (!response.ok || !response.body) {
    throw await safeJson(response);
  }

  const reader = response.body.getReader();
  bubble.classList.add('streaming');

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value, { stream: true });
    bubble.textContent += chunk;
  }

  bubble.classList.remove('streaming');
}

// NACHHER:
async function streamChat(payload, bubble) {
  try {
    // Offline-Check
    if (!navigator.onLine) {
      throw new Error('Keine Internetverbindung. Bitte überprüfen Sie Ihre Netzwerkverbindung.');
    }

    const response = await apiClient.postStream('/v1/chat', {
      model: payload.model,
      messages: payload.messages,
      stream: true,
      temperature: payload.temperature,
    }, {
      timeout: 120000, // 2 Minuten für Chat-Streaming
    });

    if (!response.ok) {
      const error = await safeJson(response);
      throw new Error(error.error?.message || `HTTP ${response.status}: ${response.statusText}`);
    }

    if (!response.body) {
      throw new Error('Keine Streaming-Antwort vom Server erhalten');
    }

    const reader = response.body.getReader();
    bubble.classList.add('streaming');

    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        bubble.textContent += chunk;
      }
    } finally {
      // Immer aufräumen, auch bei Fehler
      reader.releaseLock();
      bubble.classList.remove('streaming');
    }

  } catch (error) {
    bubble.classList.remove('streaming');

    // Benutzerfreundliche Fehlermeldungen
    let errorMsg = 'Fehler beim Chat-Streaming';
    if (error.message === 'Request timeout') {
      errorMsg = 'Die Anfrage hat zu lange gedauert. Bitte versuchen Sie es erneut.';
    } else if (error.message.includes('Keine Internetverbindung')) {
      errorMsg = error.message;
    } else if (error.message.includes('HTTP')) {
      errorMsg = `Server-Fehler: ${error.message}`;
    }

    bubble.textContent = `❌ ${errorMsg}`;
    bubble.classList.add('error');
    throw error;
  }
}
```

### 4. Offline-Erkennung

```javascript
// Am Anfang von app.js hinzufügen:

// Online/Offline Status
let isOnline = navigator.onLine;

window.addEventListener('online', () => {
  isOnline = true;
  console.log('✅ Internetverbindung wiederhergestellt');
  // Optional: Banner anzeigen
  showNotification('Internetverbindung wiederhergestellt', 'success');
});

window.addEventListener('offline', () => {
  isOnline = false;
  console.warn('⚠️ Internetverbindung verloren');
  showNotification('Keine Internetverbindung', 'warning');
});

function showNotification(message, type = 'info') {
  // Einfaches Toast-Notification System
  const notification = document.createElement('div');
  notification.className = `nova-notification ${type}`;
  notification.textContent = message;
  document.body.appendChild(notification);

  setTimeout(() => {
    notification.classList.add('fade-out');
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}
```

## CSS für Notifications

```css
.nova-notification {
  position: fixed;
  top: 20px;
  right: 20px;
  padding: 12px 20px;
  background: #333;
  color: white;
  border-radius: 4px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.3);
  z-index: 10000;
  animation: slideIn 0.3s ease;
}

.nova-notification.success {
  background: #28a745;
}

.nova-notification.warning {
  background: #ffc107;
  color: #333;
}

.nova-notification.error {
  background: #dc3545;
}

.nova-notification.fade-out {
  opacity: 0;
  transition: opacity 0.3s ease;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.bubble.error {
  background-color: #fee;
  border-left: 4px solid #dc3545;
}
```

## Zusammenfassung der Verbesserungen

1. ✅ **Timeout-Handling**: 30s Default, konfigurierbar
2. ✅ **Retry-Logic**: 3 Versuche mit exponential backoff
3. ✅ **Offline-Erkennung**: Event-Listener für online/offline
4. ✅ **Bessere Fehler**: Benutzerfreundliche Fehlermeldungen
5. ✅ **Resource Cleanup**: Reader wird immer freigegeben
6. ✅ **Notifications**: Visuelles Feedback für Netzwerkstatus
