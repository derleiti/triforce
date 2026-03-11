/**
 * Nova AI Admin v6.3.0
 * REST-API-basiertes Admin Dashboard für AILinux.me
 * Nutzt /wp-json/nova-ai/v1/admin/* Endpoints
 */
(function () {
'use strict';

const C = window.novaAdminConfig || {
    restUrl: '/wp-json/nova-ai/v1',
    nonce: '',
    apiEndpoint: '',  // Fallback: gesetzt via wp_localize_script (novaAdminConfig)
    version: '6.3.0'
};

const rest = (path, opts = {}) => fetch(C.restUrl + path, {
    headers: { 'X-WP-Nonce': C.nonce, 'Content-Type': 'application/json', ...opts.headers },
    ...opts
}).then(r => r.json().catch(() => ({ error: 'invalid json', status: r.status })));

const post = (path, body) => rest(path, { method: 'POST', body: JSON.stringify(body) });

// ── DOM helpers ──────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const el = (tag, props = {}, inner = '') => {
    const e = document.createElement(tag);
    Object.assign(e, props);
    if (inner) e.innerHTML = inner;
    return e;
};
function setHTML(id, html) { const e = $(id); if (e) e.innerHTML = html; }
function setText(id, t) { const e = $(id); if (e) e.textContent = t; }
function showMsg(id, txt, type = 'info') {
    const e = $(id);
    if (!e) return;
    e.innerHTML = `<div class="notice notice-${type}" style="display:inline-block;padding:4px 12px;margin:0">${txt}</div>`;
}

// ── Copy buttons ─────────────────────────────────────────────────────────────
function initCopy() {
    document.querySelectorAll('.nova-copy,[data-copy]').forEach(btn => {
        btn.addEventListener('click', () => {
            const t = btn.dataset.copy || btn.textContent;
            navigator.clipboard.writeText(t).then(() => {
                const orig = btn.innerHTML;
                btn.innerHTML = '✅';
                setTimeout(() => btn.innerHTML = orig, 1500);
            });
        });
    });
}

// ── Dashboard tab ────────────────────────────────────────────────────────────
async function loadDashboard() {
    // Status
    try {
        const d = await rest('/admin/status');
        const ok = d.ok || d.status === 'ok' || d.status === 'healthy';
        setHTML('stat-status', ok ? '✅' : '⚠️');
        setText('stat-status-text', ok ? 'Online' : 'Degraded');
        if (d.model_count) setText('stat-models', d.model_count);
    } catch { setHTML('stat-status', '❌'); }

    // Agents count
    try {
        const ag = await rest('/admin/agents');
        const agents = ag.cli_agents || ag.agents || ag.data || [];
        const running = Array.isArray(agents) ? agents.filter(a => a.status === 'running' || a.running).length : '?';
        setText('stat-agents', running);
    } catch {}

    // Log
    loadLog();
}

async function loadLog() {
    try {
        const d = await rest('/admin/logs?category=all&limit=80');
        const logs = d.logs || d.entries || d.data || [];
        if (!Array.isArray(logs) || !logs.length) {
            setHTML('admin-log', '<span style="opacity:.5">Keine Logs verfügbar</span>');
            return;
        }
        const html = logs.map(l => {
            const lvl = (l.level || 'info').toLowerCase();
            const color = lvl === 'error' ? '#f85149' : lvl === 'warning' ? '#e3b341' : '#3fb950';
            return `<div style="color:${color};border-bottom:1px solid #333;padding:2px 0">` +
                `<span style="opacity:.5">${l.timestamp || l.time || ''}</span> ` +
                `<b>[${(l.category || l.module || '').toUpperCase()}]</b> ${escHtml(String(l.message || l.msg || JSON.stringify(l)))}` +
                `</div>`;
        }).join('');
        setHTML('admin-log', html);
        const el = $('admin-log'); if (el) el.scrollTop = el.scrollHeight;
    } catch (e) {
        setHTML('admin-log', `<span style="color:#f85149">Fehler: ${e.message}</span>`);
    }
}

// ── System tab ───────────────────────────────────────────────────────────────
async function loadSystem() {
    // Backend
    try {
        const d = await rest('/admin/status');
        const ok = d.ok || d.status === 'ok' || d.status === 'healthy';
        setHTML('sys-backend', statusBadge(ok, ok ? `OK — ${d.model_count || ''} Modelle` : 'Degraded'));
    } catch (e) { setHTML('sys-backend', statusBadge(false, e.message)); }

    // MCP
    try {
        const d = await rest('/admin/mcp/tools');
        const count = (d.tools || d.data || []).length;
        setHTML('sys-mcp', statusBadge(true, `${count} Tools verfügbar`));
    } catch { setHTML('sys-mcp', statusBadge(false, 'nicht erreichbar')); }

    // Ollama — BUG-FIX 2026-03-11: /health does not return services.ollama.
    // Use health ok + model_count as Ollama proxy (all models served via Ollama).
    try {
        const d = await rest('/health');
        const ok = d.ok || d.status === 'ok' || d.status === 'healthy';
        const mc = d.model_count || null;
        setHTML('sys-ollama', statusBadge(ok, ok
            ? (mc ? `${mc} Modelle verfügbar` : 'Online')
            : 'offline'));
    } catch { setHTML('sys-ollama', statusBadge(false, 'keine Daten')); }

    // Vault
    try {
        const d = await rest('/admin/vault/keys');
        const apiKeys = d.api_keys || {};
        const keyCount = Object.keys(apiKeys).filter(k => apiKeys[k] && String(apiKeys[k]).length > 3 && !['ollama_base_url','ollama_bearer_token','ollama_bearer_auth_enabled'].includes(k)).length;
        setHTML('sys-vault', statusBadge(keyCount > 0, `${keyCount} Keys gespeichert`));
    } catch { setHTML('sys-vault', statusBadge(false, 'nicht erreichbar')); }

    // Models table
    await loadModelsTable();
}

async function loadModelsTable() {
    setHTML('models-table', '⏳ Lade…');
    try {
        const d = await rest('/models');
        const models = d.models || [];
        setText('model-count', models.length + ' Modelle');

        // Populate provider filter
        const pf = $('provider-filter');
        if (pf && !pf.dataset.loaded) {
            const providers = [...new Set(models.map(m => m.provider).filter(Boolean))].sort();
            providers.forEach(p => {
                const o = document.createElement('option');
                o.value = p; o.textContent = p;
                pf.appendChild(o);
            });
            pf.dataset.loaded = '1';
            pf.addEventListener('change', () => filterModels(models));
        }
        $('model-filter')?.addEventListener('input', () => filterModels(models));
        filterModels(models);
    } catch (e) {
        setHTML('models-table', `<span style="color:#f85149">Fehler: ${escHtml(e.message)}</span>`);
    }
}

function filterModels(models) {
    const q = ($('model-filter')?.value || '').toLowerCase();
    const prov = $('provider-filter')?.value || '';
    const filtered = models.filter(m =>
        (!q || (m.id + m.name + m.provider).toLowerCase().includes(q)) &&
        (!prov || m.provider === prov)
    );
    const rows = filtered.map(m => `<tr>
        <td>${escHtml(m.id)}</td>
        <td>${escHtml(m.name)}</td>
        <td><span class="badge">${escHtml(m.provider)}</span></td>
        <td>${m.categories?.join(', ') || '—'}</td>
    </tr>`).join('');
    setHTML('models-table', `<table class="widefat striped" style="font-size:12px">
        <thead><tr><th>ID</th><th>Name</th><th>Provider</th><th>Kategorien</th></tr></thead>
        <tbody>${rows || '<tr><td colspan="4">Keine Treffer</td></tr>'}</tbody>
    </table>`);
}

// ── Agents tab ───────────────────────────────────────────────────────────────
async function loadAgents() {
    setHTML('agents-grid', '⏳ Lade Agents…');
    try {
        const d = await rest('/admin/agents');
        const agents = d.cli_agents || d.agents || d.data || [];
        if (!agents.length) { setHTML('agents-grid', 'Keine Agents gefunden.'); return; }
        const cards = agents.map(a => {
            const running = a.status === 'running' || a.running || a.active;
            return `<div class="card" style="padding:16px">
                <h4 style="margin:0 0 8px">${escHtml(a.name || a.id || a.agent_id)}</h4>
                <div>${statusBadge(running, running ? 'running' : (a.status || 'stopped'))}</div>
                <div style="font-size:12px;opacity:.7;margin-top:6px">PID: ${a.pid || '—'} | Uptime: ${a.uptime || '—'}</div>
                <div style="margin-top:10px;display:flex;gap:6px">
                    <button class="button button-small" onclick="novaAgentAction('${escHtml(a.id||a.agent_id||'')}','start')">▶ Start</button>
                    <button class="button button-small" onclick="novaAgentAction('${escHtml(a.id||a.agent_id||'')}','stop')">⏹ Stop</button>
                    <button class="button button-small" onclick="novaAgentAction('${escHtml(a.id||a.agent_id||'')}','restart')">🔄</button>
                </div>
            </div>`;
        }).join('');
        setHTML('agents-grid', cards);
    } catch (e) {
        setHTML('agents-grid', `<span style="color:#f85149">Fehler: ${escHtml(e.message)}</span>`);
    }
}

window.novaAgentAction = async (agentId, action) => {
    if (!agentId) return;
    try {
        const d = await post(`/admin/agents/${agentId}/${action}`, {});
        // BUG-FIX 2026-03-11: operator precedence — d.message||d.ok was parsed as (d.message||d.ok)?...
        alert(d.ok ? (d.message || `${action} OK`) : (d.message || JSON.stringify(d)));
        await loadAgents();
    } catch (e) { alert('Fehler: ' + e.message); }
};

// ── MCP tab ───────────────────────────────────────────────────────────────────
async function loadMcpTools() {
    setHTML('mcp-tools-list', '⏳');
    try {
        const d = await rest('/admin/mcp/tools');
        const tools = d.tools || d.data || [];
        setHTML('mcp-tools-list', tools.map(t => `
            <div class="mcp-tool" style="border-bottom:1px solid #ddd;padding:8px 0;cursor:pointer"
                 onclick="document.getElementById('mcp-call-tool').value='${escHtml(t.name||t.tool||'')}';document.getElementById('mcp-call-args').value=JSON.stringify(t.args||{},null,2)">
                <strong>${escHtml(t.name || t.tool)}</strong>
                <div style="font-size:12px;opacity:.7">${escHtml(t.description || '')}</div>
            </div>`).join('') || 'Keine Tools verfügbar');
        // Filter
        $('mcp-tool-filter')?.addEventListener('input', function () {
            document.querySelectorAll('.mcp-tool').forEach(el => {
                el.style.display = el.textContent.toLowerCase().includes(this.value.toLowerCase()) ? '' : 'none';
            });
        });
    } catch (e) {
        setHTML('mcp-tools-list', `<span style="color:#f85149">${escHtml(e.message)}</span>`);
    }
}

async function callMcpTool() {
    const tool = $('mcp-call-tool')?.value?.trim();
    const argsRaw = $('mcp-call-args')?.value?.trim() || '{}';
    if (!tool) { setHTML('mcp-call-result', '❌ Tool-Name fehlt'); return; }
    let args;
    try { args = JSON.parse(argsRaw); } catch { setHTML('mcp-call-result', '❌ Ungültiges JSON in Args'); return; }
    setHTML('mcp-call-result', '⏳ Läuft…');
    try {
        const d = await post('/admin/mcp/call', { tool, args });
        // BUG-FIX 2026-03-11: d.result can be an object → must stringify before escHtml
        const raw = d.result;
        const display = raw !== undefined
          ? (typeof raw === 'string' ? raw : JSON.stringify(raw, null, 2))
          : JSON.stringify(d, null, 2);
        setHTML('mcp-call-result', escHtml(display));
    } catch (e) {
        setHTML('mcp-call-result', `❌ ${escHtml(e.message)}`);
    }
}

// ── Crawler tab ───────────────────────────────────────────────────────────────
async function loadCrawler() {
    setHTML('crawler-config', '⏳');
    try {
        const d = await rest('/admin/crawler');
        const cfg = d.config || d.data || d;
        if (typeof cfg !== 'object') {
            setHTML('crawler-config', `<code>${escHtml(JSON.stringify(cfg))}</code>`);
            return;
        }
        setHTML('crawler-config', '');
        const form = $('crawler-form');
        if (form) form.style.display = '';
        const table = $('crawler-table');
        if (!table) return;
        table.innerHTML = Object.entries(cfg).map(([k, v]) =>
            `<tr><th><label for="crawl-${escHtml(k)}">${escHtml(k)}</label></th>
            <td><input type="text" id="crawl-${escHtml(k)}" name="${escHtml(k)}" class="regular-text" value="${escHtml(String(v))}"></td></tr>`
        ).join('');
    } catch (e) {
        setHTML('crawler-config', `<span style="color:#f85149">Fehler: ${escHtml(e.message)} — Backend-Endpoint /v1/crawler/config nötig</span>`);
    }
}

async function saveCrawler() {
    const table = $('crawler-table');
    if (!table) return;
    const data = {};
    table.querySelectorAll('input[name]').forEach(inp => { data[inp.name] = inp.value; });
    try {
        const d = await post('/admin/crawler', data);
        alert((d.config || d.updated || d.ok) ? '✅ Konfiguration gespeichert' : JSON.stringify(d));
    } catch (e) { alert('Fehler: ' + e.message); }
}

async function loadCrawlerStatus() {
    try {
        const d = await rest('/admin/status');
        const crawl = d.services?.crawler || d.crawler || {};
        setHTML('crawler-status', `<pre style="font-size:12px">${escHtml(JSON.stringify(crawl, null, 2))}</pre>`);
    } catch { setHTML('crawler-status', '—'); }
}

// ── Vault tab ─────────────────────────────────────────────────────────────────
async function loadVaultKeys() {
    setHTML('vault-keys', '⏳');
    try {
        const d = await rest('/admin/vault/keys');
        // Backend gibt d.api_keys als Objekt zurück
        const apiKeys = d.api_keys || {};
        const keys = Object.keys(apiKeys).filter(k => !['ollama_base_url','ollama_bearer_token','ollama_bearer_auth_enabled'].includes(k));
        if (!keys.length) { setHTML('vault-keys', '<em>Keine Keys gespeichert</em>'); return; }
        setHTML('vault-keys', '<ul>' + keys.map(k => {
            const val = String(apiKeys[k] || '');
            const masked = val.length > 6 ? val.slice(0,4) + '****' + val.slice(-4) : (val ? '****' : '(leer)');
            return `<li><code>${escHtml(k)}</code>: <span style="opacity:.6">${escHtml(masked)}</span></li>`;
        }).join('') + '</ul>');
    } catch (e) {
        setHTML('vault-keys', `<span style="color:#f85149">Fehler: ${escHtml(e.message)}</span>`);
    }
}

async function setVaultKey() {
    const key = $('vault-key-name')?.value?.trim();
    const value = $('vault-key-value')?.value?.trim();
    if (!key || !value) { showMsg('vault-msg', '❌ Key und Value erforderlich', 'error'); return; }
    try {
        const d = await post('/admin/vault/set', { key, value });
        const vok = d.success || d.ok;
        showMsg('vault-msg', vok ? '✅ Key gespeichert' : JSON.stringify(d), vok ? 'success' : 'error');
        if (vok) { $('vault-key-name').value = ''; $('vault-key-value').value = ''; await loadVaultKeys(); }
    } catch (e) { showMsg('vault-msg', '❌ ' + e.message, 'error'); }
}

// ── Utils ─────────────────────────────────────────────────────────────────────
function statusBadge(ok, text) {
    const color = ok ? '#3fb950' : '#f85149';
    const icon  = ok ? '✅' : '❌';
    return `<span style="color:${color}">${icon} ${escHtml(String(text))}</span>`;
}
function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── Wire buttons after DOM ready ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initCopy();

    // Detect active tab from URL
    const tab = new URLSearchParams(location.search).get('tab') || 'dashboard';

    // Dashboard
    if (tab === 'dashboard') {
        loadDashboard();
        $('btn-refresh-all')?.addEventListener('click', loadDashboard);
        $('btn-refresh-log')?.addEventListener('click', loadLog);
        $('btn-test-api')?.addEventListener('click', async () => {
            try {
                const d = await rest('/health');
                alert((d.status === 'healthy' || d.ok) ? '✅ API OK — ' + JSON.stringify(d) : '⚠️ ' + JSON.stringify(d));
            } catch (e) { alert('❌ ' + e.message); }
        });
        $('btn-view-models')?.addEventListener('click', async () => {
            window.location.href = '?page=nova-ai&tab=system';
        });
    }

    // System
    if (tab === 'system') {
        loadSystem();
        $('btn-system-refresh')?.addEventListener('click', loadSystem);
    }

    // Agents
    if (tab === 'agents') {
        loadAgents();
        $('btn-agents-refresh')?.addEventListener('click', loadAgents);
        $('btn-agents-bootstrap')?.addEventListener('click', async () => {
            try {
                const d = await post('/admin/bootstrap', {});
                const count = d.success_count || Object.keys(d.agents || {}).length;
                const errors = d.errors ? Object.keys(d.errors).length : 0;
                alert(`🚀 Bootstrap: ${count} Agents initialisiert${errors ? ', ' + errors + ' Fehler' : ''}`);
                await loadAgents();
            } catch (e) { alert('❌ ' + e.message); }
        });
    }

    // MCP
    if (tab === 'mcp') {
        loadMcpTools();
        $('btn-mcp-refresh')?.addEventListener('click', loadMcpTools);
        $('btn-mcp-call')?.addEventListener('click', callMcpTool);
    }

    // Crawler
    if (tab === 'crawler') {
        loadCrawler();
        $('btn-crawler-save')?.addEventListener('click', saveCrawler);
        $('btn-crawler-refresh')?.addEventListener('click', loadCrawlerStatus);
    }

    // Vault
    if (tab === 'vault') {
        loadVaultKeys();
        $('btn-vault-set')?.addEventListener('click', setVaultKey);
    }
});

})();
