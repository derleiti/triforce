/**
 * Robuster API-Client mit Retry-Logic und Fehlerbehandlung
 *
 * Features:
 * - Timeout-Behandlung für fetch()-Requests
 * - Retry-Logic mit exponential backoff
 * - Offline-Erkennung und Verbindungsprüfung
 * - Benutzerfreundliche Fehlermeldungen
 * - Resource Cleanup für Streaming
 * - Toast-Notifications für Netzwerkstatus
 */
(function (window) {
  console.log('api-client.js loaded and executing'); // Added for debugging
  // SD3.5 jobs at ≥1080p exceed 30s easily; allow up to 10 minutes per request
  const DEFAULT_TIMEOUT = 600000; // 10 Minuten
  const MAX_RETRIES = 3;
  const RETRY_DELAY = 1000; // 1 Sekunde

  /**
   * Timeout-Wrapper für fetch()
   * Wirft einen Timeout-Fehler wenn Request zu lange dauert
   *
   * @param {string} url - URL für den Request
   * @param {Object} options - fetch() Optionen
   * @param {number} timeout - Timeout in Millisekunden
   * @returns {Promise<Response>}
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
   * Berechnet die Wartezeit zwischen Retry-Versuchen
   *
   * @param {number} attempt - Aktueller Versuch (0-basiert)
   * @returns {number} Delay in Millisekunden
   */
  function getRetryDelay(attempt) {
    return RETRY_DELAY * Math.pow(2, attempt);
  }

  /**
   * Prüft ob Fehler retry-fähig ist
   * Netzwerkfehler und bestimmte HTTP-Status-Codes können wiederholt werden
   *
   * @param {Error} error - Der aufgetretene Fehler
   * @param {Response} response - Die HTTP-Response (falls vorhanden)
   * @returns {boolean} True wenn Retry sinnvoll ist
   */
  function isRetryableError(error, response) {
    // Netzwerkfehler sind immer retry-fähig
    if (error && (error.message === 'Request timeout' || error.message === 'Failed to fetch')) {
      return true;
    }

    // HTTP Status-Codes die retry-fähig sind
    if (response) {
      const status = response.status;
      // 408 Request Timeout, 429 Too Many Requests, 5xx Server Errors
      return status === 408 || status === 429 || status >= 500;
    }

    return false;
  }

  /**
   * Robuster Fetch mit Retry-Logic
   * Führt automatisch Retries bei Netzwerkfehlern und bestimmten HTTP-Errors durch
   *
   * @param {string} url - URL für den Request
   * @param {Object} options - fetch() Optionen
   * @param {Object} config - Konfiguration für Retry-Logic
   * @param {number} config.timeout - Timeout in Millisekunden
   * @param {number} config.maxRetries - Maximale Anzahl an Retries
   * @param {Function} config.onRetry - Callback bei Retry-Versuch
   * @returns {Promise<Response>}
   */
  async function robustFetch(url, options = {}, config = {}) {
    const timeout = config.timeout || DEFAULT_TIMEOUT;
    const maxRetries = config.maxRetries || MAX_RETRIES;
    const onRetry = config.onRetry || (() => {});

    let lastError;
    let lastResponse;

    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        // Offline-Check vor jedem Versuch
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
   * Bietet Methoden für GET, POST und Streaming-Requests
   */
  class NovaAPIClient {
    /**
     * @param {string} baseURL - Basis-URL der API
     * @param {string} clientHeader - Client-Identifikation für X-AILinux-Client Header
     */
    constructor(baseURL, clientHeader) {
      this.baseURL = baseURL.replace(/\/$/, '');
      this.clientHeader = clientHeader;
    }

    /**
     * GET-Request mit Retry-Logic
     *
     * @param {string} endpoint - API-Endpoint (z.B. '/v1/models')
     * @param {Object} config - Konfiguration
     * @param {number} config.timeout - Timeout in Millisekunden
     * @param {number} config.maxRetries - Maximale Anzahl an Retries
     * @param {Function} config.onRetry - Callback bei Retry-Versuch
     * @param {Object} config.headers - Zusätzliche HTTP-Headers
     * @returns {Promise<Response>}
     */
    async get(endpoint, config = {}) {
      const url = `${this.baseURL}${endpoint}`;
      const options = {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'X-AILinux-Client': this.clientHeader,
          ...(config.headers || {}),
        },
      };

      return robustFetch(url, options, config);
    }

    /**
     * POST-Request mit Retry-Logic
     *
     * @param {string} endpoint - API-Endpoint
     * @param {Object} data - Daten für Request-Body (wird als JSON gesendet)
     * @param {Object} config - Konfiguration (siehe get())
     * @returns {Promise<Response>}
     */
    async post(endpoint, data, config = {}) {
      const url = `${this.baseURL}${endpoint}`;
      let options = {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'X-AILinux-Client': this.clientHeader,
          ...(config.headers || {}),
        },
      };

      if (config.isFormData) {
        // For FormData, fetch automatically sets Content-Type: multipart/form-data
        // We should not set Content-Type header manually, as it will break the boundary string
        options.body = data;
      } else {
        options.headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify(data);
      }

      return robustFetch(url, options, config);
    }

    /**
     * POST mit Streaming-Response
     * WICHTIG: Streaming hat keine Retries, da dies den State kaputt machen würde
     *
     * @param {string} endpoint - API-Endpoint
     * @param {Object} data - Daten für Request-Body
     * @param {Object} config - Konfiguration
     * @param {number} config.timeout - Timeout in Millisekunden
     * @param {Object} config.headers - Zusätzliche HTTP-Headers
     * @returns {Promise<Response>}
     */
    async postStream(endpoint, data, config = {}) {
      const url = `${this.baseURL}${endpoint}`;
      const options = {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/plain',
          'X-AILinux-Client': this.clientHeader,
          ...(config.headers || {}),
        },
        body: JSON.stringify(data),
      };

      // Streaming hat keine Retries (würde state kaputt machen)
      return fetchWithTimeout(url, options, config.timeout || DEFAULT_TIMEOUT);
    }
  }

  /**
   * Online/Offline Status Management
   * Event-Listener für Netzwerkstatus-Änderungen
   */
  let isOnline = navigator.onLine;

  window.addEventListener('online', () => {
    isOnline = true;
    console.log('✅ Internetverbindung wiederhergestellt');
    if (window.showNotification) {
      window.showNotification('Internetverbindung wiederhergestellt', 'success');
    }
  });

  window.addEventListener('offline', () => {
    isOnline = false;
    console.warn('⚠️ Internetverbindung verloren');
    if (window.showNotification) {
      window.showNotification('Keine Internetverbindung', 'warning');
    }
  });

  /**
   * Toast-Notification System
   * Zeigt benutzerfreundliche Benachrichtigungen am oberen rechten Bildschirmrand
   *
   * @param {string} message - Nachricht zum Anzeigen
   * @param {string} type - Typ der Notification ('info', 'success', 'warning', 'error')
   */
  function showNotification(message, type = 'info') {
    // Einfaches Toast-Notification System
    const notification = document.createElement('div');
    notification.className = `nova-notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    // Auto-remove nach 3 Sekunden
    setTimeout(() => {
      notification.classList.add('fade-out');
      setTimeout(() => notification.remove(), 300);
    }, 3000);
  }

  // Export globaler Objekte und Funktionen
  window.NovaAPIClient = NovaAPIClient;
  window.robustFetch = robustFetch;
  window.showNotification = showNotification;
  window.isOnline = () => isOnline;
  console.log('NovaAPIClient exposed globally'); // Added for debugging

})(window);
