// TriForce Setup Wizard v4.1 - JavaScript
// Alle Services und Configs parametrisiert
let config = {};

// Service -> Variable Prefix Mapping (ERWEITERT)
const serviceFilters = {
  wordpress: ['WP_', 'WORDPRESS_'],
  flarum: ['FLARUM_'],
  searxng: ['SEARXNG_'],
  mailserver: ['MAIL_', 'MAILSERVER_'],
  repository: ['REPO_', 'NGINX_'],
  api: ['GEMINI_', 'OPENAI_', 'MISTRAL_', 'GROQ_', 'CEREBRAS_', 'HUGGINGFACE_', 'OPENROUTER_', 'CLOUDFLARE_', 'MCP_', 'OLLAMA_', 'ANTHROPIC_'],
  php: ['PHP_'],
  mysql: ['MYSQL_'],
  ssl: ['SSL_', 'LETSENCRYPT_'],
  triforce: ['TRIFORCE_', 'TRISTAR_', 'TZ']
};

// Tab Navigation
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(tab.dataset.tab).classList.add('active');
    
    // Lade Service-Config wenn noch leer
    const configEl = document.getElementById(tab.dataset.tab + '-config');
    if (configEl && configEl.children.length === 0) {
      renderServiceConfig(tab.dataset.tab);
    }
  });
});

// Toast Notification
function toast(msg, type = 'info') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show ' + type;
  setTimeout(() => t.classList.remove('show'), 3000);
}

// Load Config
async function loadConfig() {
  try {
    const res = await fetch('/api/config');
    const data = await res.json();
    if (data.config) {
      config = data.config;
      document.getElementById('config-path').textContent = data.path;
      document.getElementById('var-count').textContent = Object.keys(config).length;
      renderAllConfigs();
      updateEnvStats();
      toast('Config geladen (' + Object.keys(config).length + ' Variablen)', 'success');
    }
  } catch (e) {
    toast('Fehler beim Laden: ' + e.message, 'error');
  }
}

// Render Config for each Service Tab
function renderAllConfigs() {
  for (const service of Object.keys(serviceFilters)) {
    renderServiceConfig(service);
  }
}

function renderServiceConfig(service) {
  const container = document.getElementById(service + '-config');
  if (!container) return;
  
  const prefixes = serviceFilters[service] || [];
  container.innerHTML = '';
  
  const filtered = Object.entries(config).filter(([key]) => 
    prefixes.some(p => key.startsWith(p))
  ).sort((a, b) => a[0].localeCompare(b[0]));
  
  for (const [key, value] of filtered) {
    const isPassword = key.includes('PASSWORD') || key.includes('SECRET') || key.includes('KEY') || key.includes('TOKEN');
    const isBoolean = value === 'true' || value === 'false' || value === 'on' || value === 'off';
    const isNumber = /^\d+(\.\d+)?$/.test(value);
    
    let inputHtml;
    if (isBoolean) {
      inputHtml = `<select id="cfg-${key}" data-key="${key}" onchange="saveVar('${key}', this.value)">
        <option value="true" ${value === 'true' ? 'selected' : ''}>true</option>
        <option value="false" ${value === 'false' ? 'selected' : ''}>false</option>
        <option value="on" ${value === 'on' ? 'selected' : ''}>on</option>
        <option value="off" ${value === 'off' ? 'selected' : ''}>off</option>
      </select>`;
    } else {
      inputHtml = `<input type="${isPassword ? 'password' : 'text'}" 
           id="cfg-${key}" 
           value="${escapeHtml(value)}" 
           data-key="${key}"
           onchange="saveVar('${key}', this.value)">`;
    }
    
    container.innerHTML += `
      <div class="config-item">
        <label>${key}</label>
        ${inputHtml}
      </div>`;
  }
  
  if (filtered.length === 0) {
    container.innerHTML = '<p style="color:var(--text-muted)">Keine Variablen für diesen Service gefunden.</p>';
  }
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// Save single Variable
async function saveVar(key, value) {
  try {
    const res = await fetch('/api/config', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({updates: {[key]: value}})
    });
    const data = await res.json();
    if (data.success) {
      config[key] = value;
      toast(`✓ ${key} gespeichert`, 'success');
    }
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

// Update env Stats
function updateEnvStats() {
  const stats = document.getElementById('env-stats');
  const categories = {};
  for (const key of Object.keys(config)) {
    const prefix = key.split('_')[0];
    categories[prefix] = (categories[prefix] || 0) + 1;
  }
  const sorted = Object.entries(categories).sort((a,b) => b[1] - a[1]).slice(0, 15);
  stats.innerHTML = `<strong>Top Kategorien:</strong><br>` +
    sorted.map(([k, v]) => `${k}: ${v}`).join(' | ') + 
    `<br><br><strong>Gesamt: ${Object.keys(config).length} Variablen</strong>`;
}

// Check Service Status
async function checkStatus() {
  const services = ['docker', 'redis', 'ollama', 'wordpress', 'flarum', 'searxng'];
  for (const svc of services) {
    const el = document.getElementById(svc + '-status');
    if (!el) continue;
    try {
      const res = await fetch('/api/status/' + svc);
      const data = await res.json();
      el.textContent = data.status;
      el.className = 'status ' + data.status;
    } catch {
      el.textContent = 'error';
      el.className = 'status stopped';
    }
  }
}

// Docker Service Controls
async function startService(name) {
  toast(`Starte ${name}...`);
  try {
    const res = await fetch('/api/docker/' + name + '/start', {method: 'POST'});
    const data = await res.json();
    toast(data.message || 'Gestartet', data.success ? 'success' : 'error');
    setTimeout(checkStatus, 2000);
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

async function stopService(name) {
  toast(`Stoppe ${name}...`);
  try {
    const res = await fetch('/api/docker/' + name + '/stop', {method: 'POST'});
    const data = await res.json();
    toast(data.message || 'Gestoppt', data.success ? 'success' : 'error');
    setTimeout(checkStatus, 2000);
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

async function restartService(name) {
  await stopService(name);
  setTimeout(() => startService(name), 2000);
}

// Generate Configs from Templates
async function generateConfigs() {
  toast('Generiere Configs...');
  try {
    const res = await fetch('/api/generate-configs', {method: 'POST'});
    const data = await res.json();
    toast(data.message || 'Configs generiert', data.success ? 'success' : 'error');
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

// Load Logs
async function loadLogs() {
  const level = document.getElementById('log-level').value;
  try {
    const res = await fetch('/api/logs?level=' + level);
    const data = await res.json();
    const output = document.getElementById('log-output');
    if (data.logs && data.logs.length > 0) {
      output.textContent = data.logs.map(l => 
        `${l.timestamp} [${l.level}] ${l.source}: ${l.message}`
      ).join('\n');
    } else {
      output.textContent = 'Keine Logs vorhanden.';
    }
  } catch (e) {
    document.getElementById('log-output').textContent = 'Fehler: ' + e.message;
  }
}

async function clearLogs() {
  if (!confirm('Logs wirklich löschen?')) return;
  try {
    await fetch('/api/logs/clear', {method: 'POST'});
    toast('Logs gelöscht', 'success');
    loadLogs();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

// Search Config
function searchConfig() {
  const query = document.getElementById('config-search').value.toLowerCase();
  document.querySelectorAll('.config-item').forEach(item => {
    const label = item.querySelector('label').textContent.toLowerCase();
    item.style.display = label.includes(query) ? 'block' : 'none';
  });
}

// Init
document.addEventListener('DOMContentLoaded', () => {
  loadConfig();
  checkStatus();
  setInterval(checkStatus, 30000);
});

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// SETTINGS IMPORT / EXPORT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

let importData = null;

// Export Settings als JSON
async function exportSettings() {
  try {
    const response = await fetch('/api/settings/export');
    const data = await response.json();
    
    if (data.success) {
      // Download als Datei
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `triforce-settings-${new Date().toISOString().slice(0,10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      showToast(`✅ ${data.total_variables} Variablen exportiert!`, 'success');
    } else {
      showToast('❌ Export fehlgeschlagen', 'error');
    }
  } catch (error) {
    console.error('Export error:', error);
    showToast('❌ Export Fehler: ' + error.message, 'error');
  }
}

// Handle Import File Selection
function handleImportFile(event) {
  const file = event.target.files[0];
  if (!file) return;
  
  const reader = new FileReader();
  reader.onload = function(e) {
    try {
      importData = JSON.parse(e.target.result);
      
      // Zeige Vorschau
      const preview = document.getElementById('import-preview');
      const stats = document.getElementById('preview-stats');
      const content = document.getElementById('preview-content');
      
      const varCount = importData.settings ? Object.keys(importData.settings).length : 0;
      stats.innerHTML = `<p>📊 <strong>${varCount}</strong> Variablen in der Datei</p>
                         <p>📅 Exportiert: ${importData.exported_at || 'Unbekannt'}</p>`;
      content.textContent = JSON.stringify(importData.settings || importData, null, 2).slice(0, 2000) + '...';
      
      preview.style.display = 'block';
      document.getElementById('import-btn').disabled = false;
      
      showToast(`📂 Datei geladen: ${varCount} Variablen`, 'info');
    } catch (error) {
      showToast('❌ Ungültige JSON-Datei', 'error');
      importData = null;
    }
  };
  reader.readAsText(file);
}

// Import Settings
async function importSettings() {
  if (!importData) {
    showToast('⚠️ Keine Datei ausgewählt', 'warning');
    return;
  }
  
  if (!confirm('⚠️ Settings importieren?\n\nDies überschreibt bestehende Werte.\nEin Backup wird automatisch erstellt.')) {
    return;
  }
  
  try {
    const response = await fetch('/api/settings/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ settings: importData.settings || importData })
    });
    
    const result = await response.json();
    
    if (result.success) {
      showToast(`✅ ${result.imported} Variablen importiert!`, 'success');
      // Reload nach 2 Sekunden
      setTimeout(() => location.reload(), 2000);
    } else {
      showToast('❌ Import fehlgeschlagen', 'error');
    }
  } catch (error) {
    console.error('Import error:', error);
    showToast('❌ Import Fehler: ' + error.message, 'error');
  }
}

// Secrets neu generieren
async function regenerateSecrets() {
  if (!confirm('🔐 Alle Secrets neu generieren?\n\n⚠️ ACHTUNG: Dies ändert alle Passwörter!\nDocker-Container müssen neu erstellt werden.')) {
    return;
  }
  
  try {
    const response = await fetch('/api/settings/regenerate-secrets', { method: 'POST' });
    const result = await response.json();
    
    if (result.success) {
      showToast(`✅ ${result.regenerated} Secrets neu generiert!`, 'success');
      setTimeout(() => location.reload(), 2000);
    } else {
      showToast('❌ Generierung fehlgeschlagen', 'error');
    }
  } catch (error) {
    showToast('❌ Fehler: ' + error.message, 'error');
  }
}

// Lade Config-Stats für Settings Tab
async function loadConfigStats() {
  try {
    const response = await fetch('/api/settings/export');
    const data = await response.json();
    
    if (data.success) {
      const stats = document.getElementById('current-config-stats');
      if (stats) {
        stats.innerHTML = `
          <p>📊 <strong>${data.total_variables}</strong> Variablen konfiguriert</p>
          <p>📅 Letzte Änderung: ${data.exported_at}</p>
          <p>📁 Pfad: config/triforce.env</p>
        `;
      }
    }
  } catch (error) {
    console.error('Config stats error:', error);
  }
}

// Init beim Tab-Wechsel
document.addEventListener('DOMContentLoaded', function() {
  // Settings Tab initialisieren wenn aktiv
  const settingsTab = document.querySelector('[data-tab="settings"]');
  if (settingsTab) {
    settingsTab.addEventListener('click', loadConfigStats);
  }
});

