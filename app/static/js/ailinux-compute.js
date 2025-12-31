/**
 * AILinux Hybrid Compute Client
 * ==============================
 *
 * Client-seitige GPU-Beschleunigung mit WebGPU/WebGL.
 * Verteilt Rechenarbeit zwischen Server und Client.
 *
 * Verwendung:
 *   const compute = new AILinuxCompute('https://api.ailinux.me');
 *   await compute.init();
 *
 *   // Embeddings (lokal mit WebGPU)
 *   const embeddings = await compute.embed(['Hello', 'World']);
 *
 *   // LLM (Server)
 *   const response = await compute.generate('Explain quantum physics');
 */

class AILinuxCompute {
    constructor(apiBase = '') {
        this.apiBase = apiBase || window.location.origin;
        this.sessionId = null;
        this.capabilities = null;
        this.availableModels = [];
        this.loadedPipelines = {};
        this.transformers = null;
        this.initialized = false;
    }

    /**
     * Initialisiert den Compute-Client
     */
    async init() {
        if (this.initialized) return this;

        // GPU-Fähigkeiten erkennen
        this.capabilities = await this._detectCapabilities();
        console.log('[AILinux Compute] Capabilities:', this.capabilities);

        // Bei Server registrieren
        const registration = await this._registerWithServer();
        this.sessionId = registration.session_id;
        this.availableModels = registration.available_models || [];

        // Transformers.js laden wenn WebGPU/WASM verfügbar
        if (this.capabilities.capability !== 'JS_ONLY') {
            await this._loadTransformers();
        }

        this.initialized = true;
        console.log('[AILinux Compute] Initialized with', this.availableModels.length, 'client models');

        return this;
    }

    /**
     * Erkennt Client GPU-Fähigkeiten
     */
    async _detectCapabilities() {
        const info = {
            capability: 'JS_ONLY',
            gpu_vendor: '',
            gpu_name: '',
            max_buffer_size: 0,
            max_texture_size: 0,
            supports_f16: false,
            supports_storage_buffers: false,
            estimated_tflops: 0,
        };

        // WebGPU Check
        if ('gpu' in navigator) {
            try {
                const adapter = await navigator.gpu.requestAdapter();
                if (adapter) {
                    const device = await adapter.requestDevice();
                    const adapterInfo = await adapter.requestAdapterInfo();

                    info.capability = 'WEBGPU';
                    info.gpu_vendor = adapterInfo.vendor || '';
                    info.gpu_name = adapterInfo.device || adapterInfo.description || '';
                    info.max_buffer_size = device.limits.maxBufferSize || 0;
                    info.max_texture_size = device.limits.maxTextureDimension2D || 0;
                    info.supports_storage_buffers = device.limits.maxStorageBuffersPerShaderStage > 0;

                    // F16 Support Check
                    info.supports_f16 = adapter.features.has('shader-f16');

                    // Geschätzte TFLOPS (sehr grob)
                    if (info.gpu_name.toLowerCase().includes('nvidia')) {
                        info.estimated_tflops = 10; // Placeholder
                    } else if (info.gpu_name.toLowerCase().includes('amd')) {
                        info.estimated_tflops = 8;
                    } else {
                        info.estimated_tflops = 2;
                    }

                    return info;
                }
            } catch (e) {
                console.warn('[AILinux Compute] WebGPU not available:', e);
            }
        }

        // WebGL2 Check
        const canvas = document.createElement('canvas');
        const gl2 = canvas.getContext('webgl2');
        if (gl2) {
            info.capability = 'WEBGL2';
            const debugInfo = gl2.getExtension('WEBGL_debug_renderer_info');
            if (debugInfo) {
                info.gpu_vendor = gl2.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
                info.gpu_name = gl2.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
            }
            info.max_texture_size = gl2.getParameter(gl2.MAX_TEXTURE_SIZE);
            return info;
        }

        // WebGL1 Check
        const gl1 = canvas.getContext('webgl');
        if (gl1) {
            info.capability = 'WEBGL';
            info.max_texture_size = gl1.getParameter(gl1.MAX_TEXTURE_SIZE);
            return info;
        }

        // WASM SIMD Check
        try {
            const simdSupported = WebAssembly.validate(new Uint8Array([
                0, 97, 115, 109, 1, 0, 0, 0, 1, 5, 1, 96, 0, 1, 123, 3,
                2, 1, 0, 10, 10, 1, 8, 0, 65, 0, 253, 15, 253, 98, 11
            ]));
            if (simdSupported) {
                info.capability = 'WASM_SIMD';
                return info;
            }
        } catch (e) {}

        // Basic WASM
        if (typeof WebAssembly === 'object') {
            info.capability = 'WASM';
        }

        return info;
    }

    /**
     * Registriert bei Server
     */
    async _registerWithServer() {
        try {
            const response = await fetch(`${this.apiBase}/v1/compute/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.capabilities),
            });

            if (!response.ok) {
                throw new Error(`Registration failed: ${response.status}`);
            }

            return await response.json();
        } catch (e) {
            console.warn('[AILinux Compute] Server registration failed:', e);
            // Offline-Modus
            return {
                session_id: 'offline-' + Date.now(),
                available_models: [],
            };
        }
    }

    /**
     * Lädt Transformers.js für Client-seitige Inferenz
     */
    async _loadTransformers() {
        try {
            // Dynamischer Import
            if (!window.transformers) {
                // CDN-Version laden
                await this._loadScript(
                    'https://cdn.jsdelivr.net/npm/@xenova/transformers@2.17.0'
                );
            }

            this.transformers = window.transformers || await import('@xenova/transformers');

            // Backend konfigurieren
            if (this.capabilities.capability === 'WEBGPU') {
                this.transformers.env.backends.onnx.wasm.numThreads = navigator.hardwareConcurrency || 4;
                // WebGPU aktivieren wenn verfügbar
                if (this.transformers.env.backends.onnx.webgpu) {
                    this.transformers.env.backends.onnx.webgpu.enabled = true;
                }
            }

            console.log('[AILinux Compute] Transformers.js loaded');
        } catch (e) {
            console.warn('[AILinux Compute] Failed to load Transformers.js:', e);
        }
    }

    /**
     * Hilfsfunktion zum Laden von Scripts
     */
    _loadScript(src) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    /**
     * Holt oder erstellt eine Pipeline
     */
    async _getPipeline(task, model) {
        const key = `${task}:${model}`;
        if (!this.loadedPipelines[key]) {
            console.log('[AILinux Compute] Loading pipeline:', key);
            this.loadedPipelines[key] = await this.transformers.pipeline(task, model);
        }
        return this.loadedPipelines[key];
    }

    /**
     * Erstellt Embeddings (Client-seitig wenn möglich)
     */
    async embed(texts, options = {}) {
        if (!Array.isArray(texts)) texts = [texts];

        // Client-seitig wenn Transformers.js verfügbar
        if (this.transformers && this._hasModel('embedding_small')) {
            try {
                const model = options.model || 'Xenova/all-MiniLM-L6-v2';
                const pipe = await this._getPipeline('feature-extraction', model);

                const results = await pipe(texts, {
                    pooling: 'mean',
                    normalize: true,
                });

                return {
                    embeddings: results.tolist ? results.tolist() : Array.from(results.data),
                    location: 'client',
                    model: model,
                    backend: this.capabilities.capability,
                };
            } catch (e) {
                console.warn('[AILinux Compute] Client embedding failed, falling back to server:', e);
            }
        }

        // Fallback: Server
        return this._serverRequest('/v1/embeddings', {
            input: texts,
            model: options.model || 'text-embedding-ada-002',
        });
    }

    /**
     * Text-Generierung (immer Server-seitig)
     */
    async generate(prompt, options = {}) {
        return this._serverRequest('/v1/chat/completions', {
            model: options.model || 'gemini-2.0-flash',
            messages: [{ role: 'user', content: prompt }],
            max_tokens: options.max_tokens || 512,
            temperature: options.temperature || 0.7,
            stream: options.stream || false,
        });
    }

    /**
     * Sentiment-Analyse (Client wenn möglich)
     */
    async sentiment(texts, options = {}) {
        if (!Array.isArray(texts)) texts = [texts];

        if (this.transformers && this._hasModel('sentiment')) {
            try {
                const model = 'Xenova/distilbert-base-uncased-finetuned-sst-2-english';
                const pipe = await this._getPipeline('sentiment-analysis', model);

                const results = await Promise.all(texts.map(t => pipe(t)));

                return {
                    results: results.map(r => r[0]),
                    location: 'client',
                    model: model,
                };
            } catch (e) {
                console.warn('[AILinux Compute] Client sentiment failed:', e);
            }
        }

        // Fallback: Server
        return this._serverRequest('/v1/analyze/sentiment', { texts });
    }

    /**
     * Bild-Embeddings mit CLIP (Client wenn möglich)
     */
    async embedImage(imageData, options = {}) {
        if (this.transformers && this._hasModel('clip_embed')) {
            try {
                const model = 'Xenova/clip-vit-base-patch32';
                const pipe = await this._getPipeline('image-feature-extraction', model);

                const result = await pipe(imageData);

                return {
                    embedding: result.tolist ? result.tolist() : Array.from(result.data),
                    location: 'client',
                    model: model,
                };
            } catch (e) {
                console.warn('[AILinux Compute] Client CLIP failed:', e);
            }
        }

        // Fallback: Server
        return this._serverRequest('/v1/vision/embed', {
            image: imageData,
        });
    }

    /**
     * Speech-to-Text mit Whisper (Client für kleine Audio)
     */
    async transcribe(audioData, options = {}) {
        if (this.transformers && this._hasModel('whisper_tiny')) {
            try {
                const model = options.model || 'Xenova/whisper-tiny';
                const pipe = await this._getPipeline('automatic-speech-recognition', model);

                const result = await pipe(audioData, {
                    language: options.language || 'en',
                    task: 'transcribe',
                });

                return {
                    text: result.text,
                    location: 'client',
                    model: model,
                };
            } catch (e) {
                console.warn('[AILinux Compute] Client Whisper failed:', e);
            }
        }

        // Fallback: Server
        const formData = new FormData();
        formData.append('audio', audioData);
        formData.append('language', options.language || 'auto');

        return this._serverRequest('/v1/audio/transcribe', formData, {
            isFormData: true,
        });
    }

    /**
     * Server-Request mit Auth
     */
    async _serverRequest(endpoint, body, options = {}) {
        const headers = options.isFormData ? {} : {
            'Content-Type': 'application/json',
        };

        if (this.sessionId) {
            headers['X-Compute-Session'] = this.sessionId;
        }

        const response = await fetch(`${this.apiBase}${endpoint}`, {
            method: 'POST',
            headers,
            body: options.isFormData ? body : JSON.stringify(body),
        });

        if (!response.ok) {
            throw new Error(`Server request failed: ${response.status}`);
        }

        const result = await response.json();
        result.location = 'server';
        return result;
    }

    /**
     * Prüft ob Model client-seitig verfügbar
     */
    _hasModel(modelId) {
        return this.availableModels.some(m => m.id === modelId);
    }

    /**
     * Gibt Compute-Status zurück
     */
    getStatus() {
        return {
            initialized: this.initialized,
            sessionId: this.sessionId,
            capabilities: this.capabilities,
            availableModels: this.availableModels.map(m => m.id),
            loadedPipelines: Object.keys(this.loadedPipelines),
            transformersLoaded: !!this.transformers,
        };
    }
}

// Export für ES6 Module
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AILinuxCompute };
}

// Global verfügbar machen
window.AILinuxCompute = AILinuxCompute;
