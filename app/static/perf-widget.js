/**
 * AILinux Live Performance Widget v1.1
 * Shows real-time latency, model count, and provider breakdown
 */
(function() {
    'use strict';
    
    const CONFIG = {
        pollInterval: 5000,
        pingInterval: 30000,
        apiBase: '/api/perf'
    };

    const WIDGET_CSS = `
        #ailinux-perf-widget {
            position: fixed;
            bottom: 12px;
            right: 12px;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border: 1px solid #0f3460;
            border-radius: 8px;
            padding: 8px 12px;
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
            font-size: 11px;
            color: #e0e0e0;
            z-index: 99999;
            min-width: 180px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            transition: all 0.3s ease;
            cursor: pointer;
            user-select: none;
        }
        #ailinux-perf-widget:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0,0,0,0.4);
        }
        #ailinux-perf-widget.minimized { min-width: auto; padding: 6px 10px; }
        #ailinux-perf-widget.minimized .perf-details,
        #ailinux-perf-widget.minimized .perf-providers { display: none; }
        
        .perf-header {
            display: flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 4px;
        }
        .perf-status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #4ade80;
            animation: pulse 2s infinite;
        }
        .perf-status-dot.warning { background: #fbbf24; }
        .perf-status-dot.error { background: #f87171; animation: none; }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .perf-title {
            font-weight: 600;
            color: #60a5fa;
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .perf-version {
            font-size: 9px;
            color: #6b7280;
            margin-left: auto;
        }
        
        .perf-details {
            display: grid;
            grid-template-columns: auto auto;
            gap: 2px 8px;
            margin-top: 6px;
        }
        .perf-label { color: #9ca3af; font-size: 10px; }
        .perf-value { color: #f0f0f0; font-weight: 500; text-align: right; }
        .perf-value.good { color: #4ade80; }
        .perf-value.warn { color: #fbbf24; }
        .perf-value.bad { color: #f87171; }
        
        .perf-models {
            margin-top: 6px;
            padding-top: 6px;
            border-top: 1px solid #334155;
            font-size: 10px;
            color: #9ca3af;
        }
        .perf-models-count { color: #60a5fa; font-weight: 600; font-size: 14px; }
        
        .perf-providers {
            margin-top: 4px;
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
        }
        .perf-provider {
            background: #334155;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 9px;
        }
        .perf-provider-count { color: #60a5fa; }
    `;

    let isMinimized = false;
    let lastData = null;

    function createWidget() {
        const style = document.createElement('style');
        style.textContent = WIDGET_CSS;
        document.head.appendChild(style);

        const widget = document.createElement('div');
        widget.id = 'ailinux-perf-widget';
        widget.innerHTML = '<div class="perf-header"><div class="perf-status-dot" id="perf-dot"></div><span class="perf-title">AILinux</span><span class="perf-version">v1.1</span></div><div class="perf-details"><span class="perf-label">Backend:</span><span class="perf-value" id="perf-backend">--ms</span><span class="perf-label">Ollama:</span><span class="perf-value" id="perf-ollama">--ms</span><span class="perf-label">Request:</span><span class="perf-value" id="perf-request">--ms</span></div><div class="perf-models"><span class="perf-models-count" id="perf-model-count">0</span> Models</div><div class="perf-providers" id="perf-providers"></div>';
        
        widget.addEventListener('click', toggleMinimize);
        document.body.appendChild(widget);
    }

    function toggleMinimize() {
        const widget = document.getElementById('ailinux-perf-widget');
        isMinimized = !isMinimized;
        widget.classList.toggle('minimized', isMinimized);
    }

    async function fetchPerfData() {
        try {
            const start = performance.now();
            const resp = await fetch(CONFIG.apiBase + '/live', { cache: 'no-store' });
            const clientLatency = Math.round(performance.now() - start);
            if (!resp.ok) throw new Error('API error');
            const data = await resp.json();
            data.clientLatency = clientLatency;
            updateWidget(data);
            lastData = data;
        } catch (err) {
            updateWidgetError();
        }
    }

    function updateWidget(data) {
        const dot = document.getElementById('perf-dot');
        const backend = document.getElementById('perf-backend');
        const ollama = document.getElementById('perf-ollama');
        const request = document.getElementById('perf-request');
        const models = document.getElementById('perf-model-count');
        const providers = document.getElementById('perf-providers');

        dot.className = 'perf-status-dot';
        if (data.services.backend !== 'up' || data.services.ollama !== 'up') {
            dot.classList.add('warning');
        }

        backend.textContent = data.latency.backend ? data.latency.backend + 'ms' : 'DOWN';
        backend.className = 'perf-value ' + getLatencyClass(data.latency.backend);
        
        ollama.textContent = data.latency.ollama ? data.latency.ollama + 'ms' : 'DOWN';
        ollama.className = 'perf-value ' + getLatencyClass(data.latency.ollama);
        
        request.textContent = data.clientLatency + 'ms';
        request.className = 'perf-value ' + getLatencyClass(data.clientLatency, 100, 500);

        models.textContent = data.models.total || 0;

        const byProvider = data.models.by_provider || {};
        providers.innerHTML = Object.entries(byProvider)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 5)
            .map(([name, count]) => '<span class="perf-provider">' + name + ': <span class="perf-provider-count">' + count + '</span></span>')
            .join('');
    }

    function updateWidgetError() {
        document.getElementById('perf-dot').className = 'perf-status-dot error';
        ['perf-backend', 'perf-ollama', 'perf-request'].forEach(function(id) {
            var el = document.getElementById(id);
            el.textContent = 'ERR';
            el.className = 'perf-value bad';
        });
    }

    function getLatencyClass(ms, warnThresh, badThresh) {
        warnThresh = warnThresh || 50;
        badThresh = badThresh || 200;
        if (!ms) return 'bad';
        if (ms < warnThresh) return 'good';
        if (ms < badThresh) return 'warn';
        return 'bad';
    }

    async function ping() {
        try { await fetch(CONFIG.apiBase + '/ping', { cache: 'no-store' }); } catch (e) {}
    }

    function init() {
        if (document.getElementById('ailinux-perf-widget')) return;
        createWidget();
        fetchPerfData();
        setInterval(fetchPerfData, CONFIG.pollInterval);
        setInterval(ping, CONFIG.pingInterval);
        console.log('[AILinux] Performance Widget v1.1 initialized');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    window.AILinuxPerf = { refresh: fetchPerfData, toggle: toggleMinimize, getData: function() { return lastData; } };
})();
