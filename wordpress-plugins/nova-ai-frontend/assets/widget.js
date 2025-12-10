(function () {
  const config = window.NovaAIWidgetConfig || {};
  if (!config.fabEnabled) {
    return;
  }

  const API_BASE = (config.apiBase && config.apiBase.replace(/\/$/, '')) || 'https://api.ailinux.me';
  const CLIENT_HEADER = 'nova-ai-frontend/1.0';
  const PREFERRED_CHAT_MODEL = 'gpt-oss:latest';
  const STORAGE_KEY = 'novaai_fab_pos';
  const MIN_PADDING = 16;
  const ADMIN_BAR_OFFSET = config.isAdminBar ? 72 : MIN_PADDING;
  const FULLSCREEN_URL = config.fullscreenUrl || config.siteUrl || window.location.href;

  // Initialize API client with retry logic
  const apiClient = window.NovaAPIClient ? new window.NovaAPIClient(API_BASE, CLIENT_HEADER) : null;

  const disableMeta = document.querySelector('meta[name="novaai-fab"][content="off"]');
  if (disableMeta || document.body.classList.contains('novaai-fab-off')) {
    return;
  }

  const mount = document.getElementById('nova-ai-fab-root');
  if (!mount) {
    return;
  }

  const wrapper = document.createElement('div');
  wrapper.className = 'novaai-fab-wrapper';
  mount.appendChild(wrapper);

  const fab = document.createElement('button');
  fab.type = 'button';
  fab.className = 'novaai-fab-button';
  fab.setAttribute('aria-label', 'Open Nova AI');
  fab.innerHTML = '<span>N</span>';

  const panel = createPanel();
  const form = panel.querySelector('form');
  const transcript = panel.querySelector('.novaai-mini-transcript');
  
  // Copy button handler
  transcript.addEventListener('click', (e) => {
    if (e.target.classList.contains('novaai-copy-btn')) {
      const code = e.target.dataset.code;
      if (code) {
        navigator.clipboard.writeText(code).then(() => {
          const original = e.target.textContent;
          e.target.textContent = 'Copied!';
          setTimeout(() => e.target.textContent = original, 2000);
        }).catch(err => console.error('Failed to copy:', err));
      }
    }
  });

  const select = panel.querySelector('.novaai-mini-select');
  const textarea = panel.querySelector('.novaai-mini-textarea');
  const sendButton = panel.querySelector('.novaai-mini-send');
  const expandButton = panel.querySelector('.novaai-mini-expand');
  const closeButton = panel.querySelector('.novaai-widget-close');

  wrapper.appendChild(fab);
  wrapper.appendChild(panel);

  let modelsLoaded = false;
  let lock = false;
  let dragging = false;
  let pointerId = null;
  let offsetX = 0;
  let offsetY = 0;
  let lastFocus = null;
  const decoder = new TextDecoder();
  const widgetState = {
    models: [],
    messages: [],
  };
  const globalWidget = window.NovaAIWidget || (window.NovaAIWidget = {});
  const PANEL_WIDTH = 340;

  function updatePanelAnchor(save = false) {
    const rect = wrapper.getBoundingClientRect();
    const computedFab = getComputedStyle(fab);
    const fabSize = parseFloat(computedFab.width) || 60;
    const desiredSpace = PANEL_WIDTH + MIN_PADDING;
    let left = rect.left;
    let spaceRight = window.innerWidth - (left + fabSize);
    if (spaceRight < desiredSpace) {
      left = Math.max(MIN_PADDING, window.innerWidth - (fabSize + desiredSpace));
      wrapper.style.left = `${left}px`;
      spaceRight = window.innerWidth - (left + fabSize);
    }
    const availableWidth = Math.max(220, window.innerWidth - (left + fabSize + MIN_PADDING));
    panel.style.width = `${Math.min(PANEL_WIDTH, availableWidth)}px`;
    panel.classList.add('align-right');
    if (save) {
      savePosition({ x: left, y: parseFloat(wrapper.style.top) || rect.top });
    }
  }

  function defaultPosition() {
    return {
      x: window.innerWidth - (MIN_PADDING + 80),
      y: Math.max(window.innerHeight - (config.isAdminBar ? 140 : 120), ADMIN_BAR_OFFSET),
    };
  }

  function clampPosition(pos) {
    const maxX = Math.max(MIN_PADDING, window.innerWidth - 80);
    const maxY = Math.max(ADMIN_BAR_OFFSET, window.innerHeight - 80);
    return {
      x: Math.min(Math.max(pos.x, MIN_PADDING), maxX),
      y: Math.min(Math.max(pos.y, ADMIN_BAR_OFFSET), maxY),
    };
  }

  function applyPosition(pos) {
    const next = clampPosition(pos || loadPosition() || defaultPosition());
    wrapper.style.left = `${next.x}px`;
    wrapper.style.top = `${next.y}px`;
  }

  function loadPosition() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (!stored) return null;
      const parsed = JSON.parse(stored);
      if (typeof parsed.x === 'number' && typeof parsed.y === 'number') {
        return parsed;
      }
    } catch (error) {
      console.warn('[NovaAI] Unable to restore FAB position', error);
    }
    return null;
  }

  function savePosition(pos) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(clampPosition(pos)));
    } catch (error) {
      console.warn('[NovaAI] Unable to store FAB position', error);
    }
  }

  function openPanel() {
    if (panel.classList.contains('open')) {
      return;
    }
    lastFocus = document.activeElement;
    panel.classList.add('open');
    panel.setAttribute('aria-hidden', 'false');
    document.body.classList.add('novaai-mini-panel-open');
    updatePanelAnchor(true);
    ensureModels();
    setTimeout(() => {
      textarea.focus();
    }, 80);
  }

  function closePanel() {
    panel.classList.remove('open');
    panel.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('novaai-mini-panel-open');
    if (lastFocus && typeof lastFocus.focus === 'function') {
      lastFocus.focus();
    } else {
      fab.focus();
    }
  }

  async function ensureModels() {
    if (modelsLoaded) {
      return;
    }
    modelsLoaded = true;
    try {
      // Use API client with retry logic if available, fallback to fetch
      let data;
      if (apiClient) {
        const response = await apiClient.get('/v1/v1/models', { timeout: 10000 });
        data = await response.json();
        if (!response.ok) {
          throw data;
        }
      } else {
        const response = await fetch(`${API_BASE}/v1/models`, {
          headers: {
            'Accept': 'application/json',
            'X-AILinux-Client': CLIENT_HEADER,
          },
        });
        data = await response.json();
        if (!response.ok) {
          throw data;
        }
      }
      widgetState.models = Array.isArray(data.data)
        ? data.data.filter((model) => Array.isArray(model.capabilities) && model.capabilities.includes('chat'))
        : [];
      populateSelect();
    } catch (error) {
      modelsLoaded = false;
      displaySystemMessage('Unable to load models.', 'error');
    }
  }

  function populateSelect() {
    select.innerHTML = '';
    if (!widgetState.models.length) {
      const option = document.createElement('option');
      option.textContent = 'No models available';
      option.disabled = true;
      option.selected = true;
      select.appendChild(option);
      select.disabled = true;
      return;
    }
    select.disabled = false;
    let preferredApplied = false;
    widgetState.models.forEach((model, index) => {
      const option = document.createElement('option');
      option.value = model.id;
      option.textContent = model.id;
      if (model.id === PREFERRED_CHAT_MODEL) {
        option.selected = true;
        preferredApplied = true;
      } else if (!preferredApplied && index === 0) {
        option.selected = true;
      }
      select.appendChild(option);
    });
    if (!preferredApplied && select.options.length > 0) {
      select.options[0].selected = true;
    }
  }

  function displaySystemMessage(message, type) {
    const bubble = document.createElement('div');
    bubble.className = `novaai-mini-bubble ${type || 'assistant'}`;
    bubble.textContent = message;
    transcript.appendChild(bubble);
    transcript.scrollTop = transcript.scrollHeight;
  }

  async function handleSend(event) {
    event.preventDefault();
    if (lock || !select.value) {
      return;
    }
    const text = textarea.value.trim();
    if (!text) {
      return;
    }

    if (widgetState.messages.length === 0) {
      widgetState.messages.push({
        role: 'system',
        content: 'Du bist Nova AI. Antworte hilfreich und präzise. Formatiere Code IMMER in Markdown-Codeblöcken (```language ... ```), damit die Kopierfunktion funktioniert. Nutze Standard-Markdown für Textformatierung. Vermeide unnötige Sonderzeichen.'
      });
    }

    widgetState.messages.push({ role: 'user', content: text });
    appendMiniBubble('user', text);
    textarea.value = '';

    const aiBubble = appendMiniBubble('assistant', '');
    aiBubble.classList.add('streaming');

    lock = true;
    sendButton.disabled = true;

    try {
      await streamMiniChat(select.value, widgetState.messages, aiBubble);
      transcript.scrollTop = transcript.scrollHeight;
    } catch (error) {
      aiBubble.textContent = 'Error: ' + parseError(error);
      aiBubble.classList.add('error');
    } finally {
      aiBubble.classList.remove('streaming');
      lock = false;
      sendButton.disabled = false;
    }
  }

  async function streamMiniChat(modelId, messages, bubble) {
    // Use API client for streaming if available, fallback to fetch
    let response;
    if (apiClient) {
      response = await apiClient.postStream('/v1/v1/chat', {
        model: modelId,
        messages,
        stream: true,
      }, { timeout: 120000 });
    } else {
      response = await fetch(`${API_BASE}/v1/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/plain',
          'X-AILinux-Client': CLIENT_HEADER,
        },
        body: JSON.stringify({
          model: modelId,
          messages,
          stream: true,
        }),
      });
    }

    if (!response.ok || !response.body) {
      throw await safeJson(response);
    }

    const reader = response.body.getReader();
    bubble.textContent = '';
    let fullText = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }
      const chunk = decoder.decode(value, { stream: true });
      fullText += chunk;
      bubble.textContent = fullText;
    }
    bubble.innerHTML = formatMessage(fullText);

    widgetState.messages.push({ role: 'assistant', content: fullText });
  }

  function formatMessage(text) {
    if (!text) return '';
    const parts = text.split(/(```[\w-]*\n[\s\S]*?```)/g);
    return parts.map(part => {
      const match = part.match(/^```([\w-]*)\n([\s\S]*?)```$/);
      if (match) {
        const lang = match[1] || 'text';
        const code = match[2];
        const escapedCode = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        const safeCode = code.replace(/"/g, '&quot;');
        return `<div class="novaai-code-block">
                  <div class="novaai-code-header">
                    <span class="novaai-code-lang">${lang}</span>
                    <button type="button" class="novaai-copy-btn" data-code="${safeCode}">Copy</button>
                  </div>
                  <pre class="novaai-code-content"><code class="language-${lang}">${escapedCode}</code></pre>
                </div>`;
      }
      return part.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }).join('');
  }

  function appendMiniBubble(role, text) {
    const bubble = document.createElement('div');
    bubble.className = `novaai-mini-bubble ${role}`;
    bubble.textContent = text;
    transcript.appendChild(bubble);
    transcript.scrollTop = transcript.scrollHeight;
    return bubble;
  }

  function parseError(error) {
    if (!error) return 'Unknown error';
    if (typeof error === 'string') return error;
    if (error.error && error.error.message) return error.error.message;
    if (error.message) return error.message;
    return 'Unknown error';
  }

  async function safeJson(response) {
    try {
      return await response.json();
    } catch (error) {
      return { message: response.statusText || 'Error' };
    }
  }

  function handlePointerDown(event) {
    if (event.button !== 0) {
      return;
    }
    dragging = true;
    pointerId = event.pointerId;
    fab.setPointerCapture(pointerId);
    fab.classList.add('dragging');
    const rect = wrapper.getBoundingClientRect();
    offsetX = event.clientX - rect.left;
    offsetY = event.clientY - rect.top;
  }

  function handlePointerMove(event) {
    if (!dragging || event.pointerId !== pointerId) {
      return;
    }
    const pos = clampPosition({
      x: event.clientX - offsetX,
      y: event.clientY - offsetY,
    });
    wrapper.style.left = `${pos.x}px`;
    wrapper.style.top = `${pos.y}px`;
    updatePanelAnchor();
  }

  function handlePointerUp(event) {
    if (!dragging || event.pointerId !== pointerId) {
      return;
    }
    dragging = false;
    fab.classList.remove('dragging');
    fab.releasePointerCapture(pointerId);
    pointerId = null;
    const current = {
      x: parseFloat(wrapper.style.left) || 0,
      y: parseFloat(wrapper.style.top) || 0,
    };
    savePosition(current);
    updatePanelAnchor(true);
  }

  function handleResize() {
    applyPosition({
      x: parseFloat(wrapper.style.left) || 0,
      y: parseFloat(wrapper.style.top) || 0,
    });
    updatePanelAnchor(true);
  }

  function handleKeydown(event) {
    if (!panel.classList.contains('open')) {
      return;
    }
    if (event.key === 'Escape') {
      event.preventDefault();
      closePanel();
      return;
    }
    if (event.key !== 'Tab') {
      return;
    }

    const focusables = panel.querySelectorAll('button, [href], select, textarea');
    if (!focusables.length) {
      return;
    }
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  fab.addEventListener('click', (event) => {
    if (dragging) {
      return;
    }
    event.preventDefault();
    if (panel.classList.contains('open')) {
      closePanel();
    } else {
      openPanel();
    }
  });

  fab.addEventListener('pointerdown', handlePointerDown);
  fab.addEventListener('pointermove', handlePointerMove);
  fab.addEventListener('pointerup', handlePointerUp);
  fab.addEventListener('pointercancel', handlePointerUp);

  closeButton.addEventListener('click', closePanel);
  textarea.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      if (typeof form.requestSubmit === 'function') {
        form.requestSubmit();
      } else {
        form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
      }
    }
  });
  form.addEventListener('submit', handleSend);
  expandButton.addEventListener('click', () => {
    window.location.href = FULLSCREEN_URL;
  });

  document.addEventListener('keydown', handleKeydown);
  window.addEventListener('resize', handleResize);

  applyPosition();
  updatePanelAnchor(true);

  globalWidget.open = function () {
    openPanel();
  };

  globalWidget.openWithPrompt = function (prompt) {
    openPanel();
    if (typeof prompt === 'string') {
      const trimmed = prompt.trim();
      if (trimmed) {
        textarea.value = trimmed;
        setTimeout(() => {
          textarea.focus();
        }, 60);
      }
    }
  };

  globalWidget.close = function () {
    closePanel();
  };

  function createPanel() {
    const panel = document.createElement('div');
    panel.className = 'novaai-widget-panel';
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-modal', 'true');
    panel.setAttribute('aria-hidden', 'true');

    panel.innerHTML = `
      <div class="novaai-widget-header">
        <div class="novaai-widget-title">NovaAI Chat</div>
        <button type="button" class="novaai-widget-close" aria-label="Close chat">×</button>
      </div>
      <div class="novaai-mini-transcript" aria-live="polite"></div>
      <form class="novaai-mini-input">
        <select class="novaai-mini-select" required></select>
        <textarea class="novaai-mini-textarea" placeholder="Ask Nova AI anywhere on the page" required></textarea>
        <div class="novaai-mini-actions">
          <button type="submit" class="novaai-mini-send">Send</button>
          <button type="button" class="novaai-mini-expand">Open full screen</button>
        </div>
      </form>
    `;
    return panel;
  }
})();
