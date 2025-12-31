/**
 * AILinux Distributed Compute Worker
 * ===================================
 *
 * Ermöglicht Websites, die GPU/CPU ihrer Besucher für verteilte
 * Berechnungen zu nutzen. Besucher können optional Credits sammeln.
 *
 * Verwendung:
 *   <script src="https://api.ailinux.me/static/js/ailinux-worker.js"></script>
 *   <script>
 *     const worker = new AILinuxWorker({
 *       apiBase: 'https://api.ailinux.me',
 *       autoStart: true,
 *       showBadge: true,
 *       onCreditsEarned: (credits) => console.log('Earned:', credits)
 *     });
 *   </script>
 */

class AILinuxWorker {
    constructor(options = {}) {
        this.apiBase = options.apiBase || window.location.origin;
        this.wsUrl = this.apiBase.replace('https://', 'wss://').replace('http://', 'ws://');

        // Optionen
        this.autoStart = options.autoStart !== false;
        this.showBadge = options.showBadge !== false;
        this.maxConcurrentTasks = options.maxConcurrentTasks || 1;
        this.idleOnly = options.idleOnly !== false;  // Nur bei Inaktivität arbeiten

        // Callbacks
        this.onConnect = options.onConnect || (() => {});
        this.onDisconnect = options.onDisconnect || (() => {});
        this.onTaskReceived = options.onTaskReceived || (() => {});
        this.onTaskCompleted = options.onTaskCompleted || (() => {});
        this.onCreditsEarned = options.onCreditsEarned || (() => {});
        this.onError = options.onError || ((e) => console.error('[AILinux Worker]', e));

        // State
        this.sessionId = null;
        this.ws = null;
        this.isConnected = false;
        this.isPaused = false;
        this.capabilities = null;
        this.pipelines = {};
        this.transformers = null;
        this.credits = 0;
        this.tasksCompleted = 0;

        // Heartbeat
        this.heartbeatInterval = null;

        // UI Badge
        this.badge = null;

        if (this.autoStart) {
            this.start();
        }
    }

    /**
     * Startet den Worker
     */
    async start() {
        if (this.isConnected) return;

        try {
            // GPU-Fähigkeiten erkennen
            this.capabilities = await this._detectCapabilities();
            console.log('[AILinux Worker] Capabilities:', this.capabilities);

            // Transformers.js laden
            if (this.capabilities.capability !== 'JS_ONLY') {
                await this._loadTransformers();
            }

            // WebSocket verbinden
            await this._connect();

            // Badge anzeigen
            if (this.showBadge) {
                this._createBadge();
            }

        } catch (e) {
            this.onError(e);
        }
    }

    /**
     * Stoppt den Worker
     */
    stop() {
        this.isPaused = true;

        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
        }

        if (this.ws) {
            this.ws.close();
        }

        if (this.badge) {
            this.badge.remove();
        }

        this.isConnected = false;
    }

    /**
     * Pausiert/Resumiert den Worker
     */
    toggle() {
        this.isPaused = !this.isPaused;
        this._updateBadge();

        if (!this.isPaused) {
            this._sendMessage({ type: 'capability_update', supported_models: this._getSupportedModels() });
        }
    }

    /**
     * GPU-Fähigkeiten erkennen
     */
    async _detectCapabilities() {
        const info = {
            capability: 'JS_ONLY',
            gpu_vendor: '',
            gpu_name: '',
            estimated_tflops: 0,
        };

        // WebGPU
        if ('gpu' in navigator) {
            try {
                const adapter = await navigator.gpu.requestAdapter();
                if (adapter) {
                    const adapterInfo = await adapter.requestAdapterInfo();
                    info.capability = 'WEBGPU';
                    info.gpu_vendor = adapterInfo.vendor || '';
                    info.gpu_name = adapterInfo.device || adapterInfo.description || '';

                    // Grobe TFLOPS-Schätzung
                    const name = info.gpu_name.toLowerCase();
                    if (name.includes('rtx 40')) info.estimated_tflops = 40;
                    else if (name.includes('rtx 30')) info.estimated_tflops = 25;
                    else if (name.includes('rtx 20')) info.estimated_tflops = 12;
                    else if (name.includes('nvidia')) info.estimated_tflops = 10;
                    else if (name.includes('radeon')) info.estimated_tflops = 15;
                    else if (name.includes('intel')) info.estimated_tflops = 3;
                    else if (name.includes('apple')) info.estimated_tflops = 8;
                    else info.estimated_tflops = 2;

                    return info;
                }
            } catch (e) {
                console.warn('[AILinux Worker] WebGPU not available');
            }
        }

        // WebGL2
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl2');
        if (gl) {
            info.capability = 'WEBGL2';
            const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
            if (debugInfo) {
                info.gpu_vendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
                info.gpu_name = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
            }
            info.estimated_tflops = 1;
            return info;
        }

        // WASM SIMD
        try {
            const simd = WebAssembly.validate(new Uint8Array([
                0, 97, 115, 109, 1, 0, 0, 0, 1, 5, 1, 96, 0, 1, 123,
                3, 2, 1, 0, 10, 10, 1, 8, 0, 65, 0, 253, 15, 253, 98, 11
            ]));
            if (simd) {
                info.capability = 'WASM_SIMD';
                info.estimated_tflops = 0.5;
                return info;
            }
        } catch (e) {}

        if (typeof WebAssembly === 'object') {
            info.capability = 'WASM';
            info.estimated_tflops = 0.2;
        }

        return info;
    }

    /**
     * Transformers.js laden
     */
    async _loadTransformers() {
        if (window.transformers) {
            this.transformers = window.transformers;
            return;
        }

        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/@xenova/transformers@2.17.0';
            script.onload = () => {
                this.transformers = window.transformers;
                console.log('[AILinux Worker] Transformers.js loaded');
                resolve();
            };
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    /**
     * WebSocket verbinden
     */
    async _connect() {
        const wsUrl = `${this.wsUrl}/v1/distributed/worker?capability=${this.capabilities.capability}&gpu_name=${encodeURIComponent(this.capabilities.gpu_name)}&tflops=${this.capabilities.estimated_tflops}`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            // Registrierungsnachricht senden
            this._sendMessage({
                type: 'register',
                session_id: this.sessionId || '',
                supported_models: this._getSupportedModels(),
            });
        };

        this.ws.onmessage = async (event) => {
            try {
                const msg = JSON.parse(event.data);
                await this._handleMessage(msg);
            } catch (e) {
                this.onError(e);
            }
        };

        this.ws.onclose = () => {
            this.isConnected = false;
            this._updateBadge();
            this.onDisconnect();

            // Reconnect nach 5 Sekunden
            if (!this.isPaused) {
                setTimeout(() => this._connect(), 5000);
            }
        };

        this.ws.onerror = (e) => {
            this.onError(e);
        };
    }

    /**
     * Unterstützte Models
     */
    _getSupportedModels() {
        const models = [];

        if (this.capabilities.capability === 'WEBGPU') {
            models.push(
                'embedding_small',
                'embedding_multilingual',
                'sentiment',
                'summarize_small',
                'clip_embed',
                'whisper_tiny'
            );
        } else if (this.capabilities.capability === 'WEBGL2') {
            models.push('embedding_small', 'sentiment');
        } else if (this.capabilities.capability.startsWith('WASM')) {
            models.push('embedding_small');
        }

        return models;
    }

    /**
     * Nachricht senden
     */
    _sendMessage(msg) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(msg));
        }
    }

    /**
     * Nachricht verarbeiten
     */
    async _handleMessage(msg) {
        switch (msg.type) {
            case 'worker_registered':
                this.sessionId = msg.session_id;
                this.isConnected = true;
                this._startHeartbeat();
                this._updateBadge();
                this.onConnect();
                console.log('[AILinux Worker] Connected:', this.sessionId);
                break;

            case 'heartbeat_ack':
                // OK
                break;

            case 'task_assignment':
                if (!this.isPaused) {
                    await this._processTask(msg.task);
                }
                break;

            case 'cancel_task':
                // Task abbrechen (falls möglich)
                break;
        }
    }

    /**
     * Task verarbeiten
     */
    async _processTask(task) {
        this.onTaskReceived(task);
        const startTime = performance.now();

        try {
            let result;

            switch (task.task_type) {
                case 'embedding':
                case 'embedding_batch':
                    result = await this._runEmbedding(task.input_data, task.model_id);
                    break;

                case 'sentiment':
                case 'sentiment_batch':
                    result = await this._runSentiment(task.input_data);
                    break;

                case 'classification':
                    result = await this._runClassification(task.input_data);
                    break;

                case 'whisper_tiny':
                    result = await this._runWhisper(task.input_data, 'Xenova/whisper-tiny');
                    break;

                case 'clip_embed':
                    result = await this._runClip(task.input_data);
                    break;

                default:
                    throw new Error(`Unknown task type: ${task.task_type}`);
            }

            const computeTime = (performance.now() - startTime) / 1000;

            // Ergebnis melden
            this._sendMessage({
                type: 'task_result',
                task_id: task.task_id,
                success: true,
                result: result,
                compute_time: computeTime,
            });

            this.tasksCompleted++;
            this._updateBadge();
            this.onTaskCompleted(task, result);

        } catch (e) {
            this._sendMessage({
                type: 'task_result',
                task_id: task.task_id,
                success: false,
                error: e.message,
                compute_time: (performance.now() - startTime) / 1000,
            });

            this.onError(e);
        }
    }

    /**
     * Embedding berechnen
     */
    async _runEmbedding(texts, modelId) {
        const model = this._getModelName(modelId) || 'Xenova/all-MiniLM-L6-v2';
        const pipe = await this._getPipeline('feature-extraction', model);

        if (!Array.isArray(texts)) texts = [texts];

        const results = await pipe(texts, { pooling: 'mean', normalize: true });
        return results.tolist ? results.tolist() : Array.from(results.data);
    }

    /**
     * Sentiment-Analyse
     */
    async _runSentiment(texts) {
        const model = 'Xenova/distilbert-base-uncased-finetuned-sst-2-english';
        const pipe = await this._getPipeline('sentiment-analysis', model);

        if (!Array.isArray(texts)) texts = [texts];

        const results = await Promise.all(texts.map(t => pipe(t)));
        return results.map(r => r[0]);
    }

    /**
     * Text-Klassifizierung
     */
    async _runClassification(texts) {
        const model = 'Xenova/distilbert-base-uncased-finetuned-sst-2-english';
        const pipe = await this._getPipeline('text-classification', model);

        if (!Array.isArray(texts)) texts = [texts];

        return await Promise.all(texts.map(t => pipe(t)));
    }

    /**
     * Whisper Transcription
     */
    async _runWhisper(audioData, model) {
        const pipe = await this._getPipeline('automatic-speech-recognition', model);
        const result = await pipe(audioData);
        return result.text;
    }

    /**
     * CLIP Embedding
     */
    async _runClip(imageData) {
        const model = 'Xenova/clip-vit-base-patch32';
        const pipe = await this._getPipeline('image-feature-extraction', model);
        const result = await pipe(imageData);
        return result.tolist ? result.tolist() : Array.from(result.data);
    }

    /**
     * Pipeline holen/erstellen
     */
    async _getPipeline(task, model) {
        const key = `${task}:${model}`;
        if (!this.pipelines[key]) {
            console.log('[AILinux Worker] Loading:', key);
            this.pipelines[key] = await this.transformers.pipeline(task, model);
        }
        return this.pipelines[key];
    }

    /**
     * Model-ID zu HuggingFace Name
     */
    _getModelName(modelId) {
        const models = {
            'embedding_small': 'Xenova/all-MiniLM-L6-v2',
            'embedding_multilingual': 'Xenova/paraphrase-multilingual-MiniLM-L12-v2',
            'sentiment': 'Xenova/distilbert-base-uncased-finetuned-sst-2-english',
            'clip_embed': 'Xenova/clip-vit-base-patch32',
            'whisper_tiny': 'Xenova/whisper-tiny',
        };
        return models[modelId];
    }

    /**
     * Heartbeat starten
     */
    _startHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
        }

        this.heartbeatInterval = setInterval(() => {
            this._sendMessage({ type: 'heartbeat' });
        }, 30000);
    }

    /**
     * Badge erstellen
     */
    _createBadge() {
        if (this.badge) return;

        this.badge = document.createElement('div');
        this.badge.id = 'ailinux-worker-badge';
        this.badge.innerHTML = `
            <style>
                #ailinux-worker-badge {
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                    color: #fff;
                    padding: 12px 16px;
                    border-radius: 12px;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    font-size: 13px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                    z-index: 99999;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    min-width: 180px;
                }
                #ailinux-worker-badge:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 6px 25px rgba(0,0,0,0.4);
                }
                #ailinux-worker-badge .status {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    margin-bottom: 6px;
                }
                #ailinux-worker-badge .dot {
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    background: #4ade80;
                    animation: pulse 2s infinite;
                }
                #ailinux-worker-badge .dot.offline { background: #ef4444; animation: none; }
                #ailinux-worker-badge .dot.paused { background: #f59e0b; animation: none; }
                #ailinux-worker-badge .stats {
                    font-size: 11px;
                    opacity: 0.8;
                }
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }
            </style>
            <div class="status">
                <span class="dot"></span>
                <span class="label">AILinux Compute</span>
            </div>
            <div class="stats">
                <span class="tasks">0 tasks</span> •
                <span class="gpu">${this.capabilities?.gpu_name || 'Detecting...'}</span>
            </div>
        `;

        this.badge.onclick = () => this.toggle();
        document.body.appendChild(this.badge);
        this._updateBadge();
    }

    /**
     * Badge aktualisieren
     */
    _updateBadge() {
        if (!this.badge) return;

        const dot = this.badge.querySelector('.dot');
        const label = this.badge.querySelector('.label');
        const tasks = this.badge.querySelector('.tasks');

        dot.className = 'dot';
        if (!this.isConnected) {
            dot.classList.add('offline');
            label.textContent = 'Disconnected';
        } else if (this.isPaused) {
            dot.classList.add('paused');
            label.textContent = 'Paused';
        } else {
            label.textContent = 'Computing';
        }

        tasks.textContent = `${this.tasksCompleted} tasks`;
    }

    /**
     * Status abrufen
     */
    getStatus() {
        return {
            isConnected: this.isConnected,
            isPaused: this.isPaused,
            sessionId: this.sessionId,
            capabilities: this.capabilities,
            tasksCompleted: this.tasksCompleted,
            credits: this.credits,
        };
    }
}

// Global verfügbar machen
window.AILinuxWorker = AILinuxWorker;

// Export für ES6 Module
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AILinuxWorker };
}
