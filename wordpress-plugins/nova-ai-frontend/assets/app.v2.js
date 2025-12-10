(function () {
  const config = window.NovaAIConfig || {};
  const API_BASE = (config.apiBase && config.apiBase.replace(/\/$/, '')) || 'https://api.ailinux.me';
  const CLIENT_HEADER = 'nova-ai-frontend/1.0';
  const root = document.getElementById('nova-ai-root');
  if (!root) {
    return;
  }

  const apiClient = new NovaAPIClient(API_BASE, CLIENT_HEADER);

  // Online/Offline Status
  let isOnline = navigator.onLine;

  window.addEventListener('online', () => {
    isOnline = true;
    console.log('✅ Internetverbindung wiederhergestellt');
    showNotification('Internetverbindung wiederhergestellt', 'success');
  });

  window.addEventListener('offline', () => {
    isOnline = false;
    console.warn('⚠️ Internetverbindung verloren');
    showNotification('Keine Internetverbindung', 'warning');
  });

  function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `nova-notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
      notification.classList.add('fade-out');
      setTimeout(() => notification.remove(), 300);
    }, 3000);
  }

  const state = {
    models: [],
    chatModels: [],
    visionModels: [],
    imageModels: [],
    chatHistory: [],
  };

  const IMAGE_MODEL_PRESETS = [
    {
      matcher: (id) => /sd3(?:\.|_)?5.*turbo/.test(id),
      preset: { workflow: 'sd35', width: 1024, height: 1024, steps: 12, cfg: 4.5, label: 'SD 3.5 Turbo preset' },
    },
    {
      matcher: (id) => /sd3(?:\.|_)?5/.test(id),
      preset: { workflow: 'sd35', width: 1024, height: 1024, steps: 28, cfg: 6.5, label: 'SD 3.5 Large preset' },
    },
    {
      matcher: (id) => /(sdxl|xl)/.test(id),
      preset: { workflow: 'sdxl', width: 1024, height: 1024, steps: 30, cfg: 7.0, label: 'SDXL preset' },
    },
  ];

  const DEFAULT_IMAGE_PRESET = { workflow: 'sd15', width: 512, height: 512, steps: 30, cfg: 7.0, label: 'Standard SD 1.5' };

  function getImagePreset(modelId) {
    if (!modelId) {
      return { ...DEFAULT_IMAGE_PRESET };
    }
    const lowered = modelId.toLowerCase();
    const match = IMAGE_MODEL_PRESETS.find((entry) => entry.matcher(lowered));
    return match ? { ...DEFAULT_IMAGE_PRESET, ...match.preset } : { ...DEFAULT_IMAGE_PRESET };
  }

  function applyImagePreset(modelId) {
    const form = root.querySelector('#nova-image-form');
    if (!form) {
      return;
    }
    const preset = getImagePreset(modelId);
    form.dataset.workflowIntent = preset.workflow || 'auto';

    const widthInput = form.querySelector('#nova-image-width');
    const heightInput = form.querySelector('#nova-image-height');
    const stepsInput = form.querySelector('#nova-image-steps');
    const cfgSlider = form.querySelector('#nova-image-cfg');
    const cfgValue = form.querySelector('#nova-image-cfg-value');
    const presetInfo = form.querySelector('#nova-image-preset-info');

    if (widthInput) {
      widthInput.value = preset.width;
    }
    if (heightInput) {
      heightInput.value = preset.height;
    }
    if (stepsInput) {
      stepsInput.value = preset.steps;
    }
    if (cfgSlider) {
      cfgSlider.value = preset.cfg;
      if (cfgValue) {
        cfgValue.textContent = Number(preset.cfg).toFixed(1);
      }
    }
    if (presetInfo) {
      const infoBits = [
        preset.label,
        `${preset.width}×${preset.height}`,
        `Steps ${preset.steps}`,
        `CFG ${Number(preset.cfg).toFixed(1)}`,
      ].filter(Boolean);
      presetInfo.textContent = infoBits.join(' · ');
    }
  }

  const PREFERRED_CHAT_MODEL = 'gpt-oss:latest';

  const decoder = new TextDecoder();

  function createLayout() {
    root.innerHTML = `
      <div class="nova-shell">
        <div class="nova-header">
          <div class="nova-header-top">
            <div class="nova-title">Nova AI</div>
            <div class="nova-mode-switcher">
              <button class="mode-btn active" data-tab="chat" role="tab" aria-selected="true">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
                Chat
              </button>
              <button class="mode-btn" data-tab="vision" role="tab" aria-selected="false">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                Vision
              </button>
            </div>
          </div>
          <div class="nova-subtitle">Powered by AILinux Backend</div>
        </div>
        
        <section class="nova-panel active" data-panel="chat" role="tabpanel">
          <div class="chat-transcript" id="nova-chat-transcript" aria-live="polite">
            <div class="bubble system">Welcome to Nova AI. How can I help you today?</div>
          </div>
          <form class="form chat-form" id="nova-chat-form">
            <div class="controls-row">
              <div class="select-wrapper">
                <select id="nova-chat-model" required></select>
              </div>
              <div class="temp-wrapper">
                <label for="nova-chat-temp" title="Temperature">Temp: <span id="nova-chat-temp-value">0.7</span></label>
                <input type="range" min="0" max="1" step="0.05" value="0.7" id="nova-chat-temp" />
              </div>
            </div>
            <div class="input-area">
              <textarea id="nova-chat-input" rows="1" placeholder="Type a message..." required></textarea>
              <div class="form-actions">
                <button type="button" class="btn icon-btn" id="nova-chat-reset" title="Clear Chat">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"></path><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                </button>
                <button type="submit" class="btn primary send-btn">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
                </button>
              </div>
            </div>
          </form>
        </section>

        <section class="nova-panel" data-panel="vision" role="tabpanel" aria-hidden="true">
          <form class="form" id="nova-vision-form">
            <div class="controls-row">
               <div class="select-wrapper" style="flex-grow: 1;">
                <select id="nova-vision-model" required></select>
              </div>
            </div>
            <div class="vision-inputs">
              <div class="form-row">
                <input type="url" id="nova-vision-image" placeholder="https://example.com/image.jpg" />
              </div>
              <div class="file-drop-area">
                <input type="file" id="nova-vision-upload" accept="image/*" />
                <p class="field-note" id="nova-vision-upload-info">or upload an image</p>
              </div>
            </div>
            <div class="input-area">
              <textarea id="nova-vision-prompt" rows="2" placeholder="Ask something about the image..." required></textarea>
              <div class="form-actions">
                <button type="submit" class="btn primary">Analyze</button>
              </div>
            </div>
          </form>
          <div class="vision-result" id="nova-vision-result" aria-live="polite"></div>
        </section>
      </div>
    `;
  }

  function bindTabs() {
    const tabs = Array.from(root.querySelectorAll('.mode-btn'));
    const panels = Array.from(root.querySelectorAll('.nova-panel'));
    tabs.forEach((tab) => {
      tab.addEventListener('click', () => {
        const target = tab.dataset.tab;
        tabs.forEach((btn) => {
          const isActive = btn === tab;
          btn.classList.toggle('active', isActive);
          btn.setAttribute('aria-selected', String(isActive));
        });
        panels.forEach((panel) => {
          const active = panel.dataset.panel === target;
          panel.classList.toggle('active', active);
          panel.setAttribute('aria-hidden', String(!active));
        });
      });
    });
  }

  async function fetchModels() {
    setLoading(root, true);
    try {
      const response = await apiClient.get('/v1/models', {
        timeout: 10000,
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
      state.chatModels = state.models.filter((model) => Array.isArray(model.capabilities) && model.capabilities.includes('chat'));
      state.visionModels = state.models.filter((model) => Array.isArray(model.capabilities) && model.capabilities.includes('vision'));
      
      populateModelSelects();
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

  function populateModelSelects() {
    const chatSelect = root.querySelector('#nova-chat-model');
    const visionSelect = root.querySelector('#nova-vision-model');

    fillSelect(chatSelect, state.chatModels, PREFERRED_CHAT_MODEL);
    fillSelect(visionSelect, state.visionModels);
  }

  function fillSelect(select, models, preferred) {
    if (!select) {
      return;
    }
    select.innerHTML = '';
    if (!models || models.length === 0) {
      const option = document.createElement('option');
      option.textContent = 'No models found';
      option.disabled = true;
      option.selected = true;
      select.appendChild(option);
      select.disabled = true;
      return;
    }
    select.disabled = false;
    let preferredApplied = false;
    models.forEach((model, index) => {
      const option = document.createElement('option');
      option.value = model.id;
      option.textContent = model.id;
      if (preferred && model.id === preferred) {
        option.selected = true;
        preferredApplied = true;
      } else if (!preferred && index === 0) {
        option.selected = true;
      }
      select.appendChild(option);
    });
    if (preferred && !preferredApplied && select.options.length > 0) {
      select.options[0].selected = true;
    }
  }

  function bindChat() {
    const form = root.querySelector('#nova-chat-form');
    const transcript = root.querySelector('#nova-chat-transcript');
    const input = root.querySelector('#nova-chat-input');
    const select = root.querySelector('#nova-chat-model');
    const reset = root.querySelector('#nova-chat-reset');
    const temp = root.querySelector('#nova-chat-temp');
    const tempValue = root.querySelector('#nova-chat-temp-value');

    if (!form || !transcript || !input || !select || !temp || !tempValue) {
      return;
    }

    const analyzeButton = document.createElement('button');
    analyzeButton.type = 'button';
    analyzeButton.className = 'btn';
    analyzeButton.textContent = 'Analyze URL';
    analyzeButton.style.display = 'none';
    form.querySelector('.form-actions').prepend(analyzeButton);

    input.addEventListener('input', () => {
        try {
            const url = new URL(input.value.trim());
            analyzeButton.style.display = 'inline-block';
        } catch (e) {
            analyzeButton.style.display = 'none';
        }
    });

    analyzeButton.addEventListener('click', () => {
        const url = input.value.trim();
        handleCrawlCommand(`/crawl kw:analyse seeds:${url} depth:1 pages:10`);
        input.value = '';
        analyzeButton.style.display = 'none';
    });

    temp.addEventListener('input', () => {
      tempValue.textContent = parseFloat(temp.value).toFixed(2);
    });

    reset.addEventListener('click', () => {
      state.chatHistory = [];
      transcript.innerHTML = '';
    });

    // Event delegation for copy buttons
    transcript.addEventListener('click', (e) => {
      const btn = e.target.closest('.nova-app-copy-btn');
      if (btn) {
        const code = btn.dataset.code;
        if (code) {
          navigator.clipboard.writeText(code).then(() => {
            const original = btn.textContent;
            btn.textContent = 'Copied!';
            setTimeout(() => btn.textContent = original, 2000);
          }).catch(err => console.error('Failed to copy:', err));
        }
      }
    });

    input.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        if (typeof form.requestSubmit === 'function') {
          form.requestSubmit();
        } else {
          form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
        }
      }
    });

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (!select.value) {
        return;
      }
      const message = input.value.trim();
      if (!message) {
        return;
      }

      if (config.chatCrawlerToolsEnabled && message.startsWith('/crawl')) {
        handleCrawlCommand(message);
        input.value = '';
        return;
      }

      const history = state.chatHistory.slice();
      if (history.length === 0) {
        history.push({
          role: 'system',
          content: 'Du bist Nova AI. Antworte hilfreich und präzise. Formatiere Code IMMER in Markdown-Codeblöcken (```language ... ```), damit die Kopierfunktion funktioniert. Nutze Standard-Markdown für Textformatierung. Vermeide unnötige Sonderzeichen.'
        });
      }
      history.push({ role: 'user', content: message });

      appendMessage(transcript, 'user', message);
      input.value = '';
      input.focus();

      const aiBubble = appendMessage(transcript, 'assistant', '');

      try {
        await streamChat({
          model: select.value,
          messages: history,
          temperature: parseFloat(temp.value),
        }, aiBubble);
        state.chatHistory = history;
        transcript.scrollTop = transcript.scrollHeight;
      } catch (error) {
        aiBubble.textContent = 'Error: ' + parseError(error);
        aiBubble.classList.add('error');
      }
    });

    const sourcesButton = document.createElement('button');
    sourcesButton.type = 'button';
    sourcesButton.className = 'btn';
    sourcesButton.textContent = 'Sources';
    sourcesButton.id = 'nova-chat-sources';
    sourcesButton.style.display = config.chatCrawlerToolsEnabled ? 'inline-block' : 'none';
    form.querySelector('.form-actions').prepend(sourcesButton);

    sourcesButton.addEventListener('click', async () => {
      // Browser-compatible alternative to findLast
      const userMessages = state.chatHistory.filter(msg => msg.role === 'user');
      const lastUserMessage = userMessages.length > 0 ? userMessages[userMessages.length - 1] : null;
      if (!lastUserMessage) {
        alert('Please ask a question first.');
        return;
      }
      const query = lastUserMessage.content;
      const sourcesBubble = appendMessage(transcript, 'system', 'Searching for sources...');
      try {
        const results = await searchCrawler(query);
        if (results.length > 0) {
          sourcesBubble.innerHTML = '<strong>Sources:</strong><br>' + results.map(r => `&bull; <a href="${r.url}" target="_blank">${r.title}</a> (Score: ${r.score.toFixed(2)})`).join('<br>');
        } else {
          sourcesBubble.textContent = 'No relevant sources found.';
        }
      } catch (error) {
        sourcesBubble.textContent = 'Error searching for sources: ' + parseError(error);
        sourcesBubble.classList.add('error');
      }
    });
  }

  async function handleCrawlCommand(command) {
    const parts = command.split(' ').slice(1);
    const args = {};
    parts.forEach(part => {
      const [key, value] = part.split(':');
      if (key && value) {
        args[key] = value;
      }
    });

    const keywords = (args.kw || '').split(',').map(s => s.trim()).filter(Boolean);
    const seeds = (args.seeds || '').split(' ').map(s => s.trim()).filter(Boolean);
    const depth = parseInt(args.depth || '0', 10);
    const pages = parseInt(args.pages || '10', 10);
    const allowExternal = args.ext === 'true';

    if (keywords.length === 0 || seeds.length === 0) {
      appendMessage(root.querySelector('#nova-chat-transcript'), 'system', 'Usage: /crawl kw:<keywords> seeds:<urls> [depth:<0-5>] [pages:<1-200>] [ext:<true|false>]');
      return;
    }

    const jobBubble = appendMessage(root.querySelector('#nova-chat-transcript'), 'system', 'Starting crawl job...');
    try {
      const response = await apiClient.post('/v1/crawler/jobs', {
        keywords: keywords,
        seeds: seeds,
        max_depth: depth,
        max_pages: pages,
        allow_external: allowExternal,
      });
      const data = await response.json();
      if (!response.ok) {
        throw data;
      }
      jobBubble.textContent = `Crawl job ${data.id} started. Status: ${data.status}.`;
      pollCrawlJobStatus(data.id, jobBubble);
    } catch (error) {
      jobBubble.textContent = 'Error starting crawl job: ' + parseError(error);
      jobBubble.classList.add('error');
    }
  }

  async function pollCrawlJobStatus(jobId, bubble) {
    let status = 'queued';
    while (status === 'queued' || status === 'running') {
      await new Promise(resolve => setTimeout(resolve, 5000)); // Poll every 5 seconds
      try {
        const response = await apiClient.get(`/v1/crawler/jobs/${jobId}`);
        const data = await response.json();
        if (!response.ok) {
          throw data;
        }
        status = data.status;
        bubble.textContent = `Crawl job ${jobId} status: ${status}. Pages crawled: ${data.pages_crawled || 0}.`;
        if (status === 'completed') {
          if (data.results && data.results.length > 0) {
            bubble.innerHTML += `<br>Found ${data.results.length} results. <a href="${API_BASE}/crawler/results?job_id=${jobId}" target="_blank">View results</a>`;
          }
        } else if (status === 'failed') {
          bubble.textContent += ` Error: ${data.error || 'Unknown error'}`;
          bubble.classList.add('error');
        }
      } catch (error) {
        bubble.textContent = 'Error polling crawl job status: ' + parseError(error);
        bubble.classList.add('error');
        break;
      }
    }
  }

  async function searchCrawler(query, limit = 5, min_score = 0.35, freshness_days = 7) {
    const response = await apiClient.post('/v1/crawler/search', {
      query: query,
      limit: limit,
      min_score: min_score,
      freshness_days: freshness_days,
    });
    const data = await response.json();
    if (!response.ok) {
      throw data;
    }
    return data;
  }

  async function streamChat(payload, bubble) {
    try {
      // Offline-Check
      if (!isOnline) {
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

      if (response.status === 429) {
        const retryAfter = response.headers.get('Retry-After');
        const waitMessage = retryAfter ? `Please retry in ${retryAfter} seconds.` : 'Please try again in a moment.';
        bubble.textContent = `🚦 Rate limit reached. ${waitMessage}`;
        bubble.classList.add('warning');
        if (window.showNotification) {
          window.showNotification('Rate limit reached. Please wait a moment before retrying.', 'warning');
        }
        return;
      }

      if (!response.ok) {
        const error = await safeJson(response);

        // Enhanced error handling for 404 endpoint mismatch
        if (response.status === 404) {
          throw new Error(`Endpoint not found (404). Expected /chat endpoint. Check API configuration at: ${API_BASE}`);
        }

        throw new Error(error.error?.message || `HTTP ${response.status}: ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error('Keine Streaming-Antwort vom Server erhalten');
      }

      const reader = response.body.getReader();
      bubble.classList.add('streaming');
      let fullText = '';

      try {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          fullText += chunk;
          bubble.textContent = fullText;
        }
        // Final formatting
        bubble.innerHTML = formatMessage(fullText);
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
      } else if (error.message.includes('Endpoint not found') || error.message.includes('404')) {
        errorMsg = `⚠️ ${error.message}`;
        console.error('API Endpoint Mismatch:', error.message);
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

  function formatMessage(text) {
    if (!text) return '';
    // Simple Markdown code block parser
    // Splits by ```lang ... ```
    // Updated regex to be more robust with newlines and spaces
    const parts = text.split(/(```[\w-]*[ \t]*\r?\n[\s\S]*?```)/g);
    
    return parts.map(part => {
      // Check if it's a code block
      const match = part.match(/^```([\w-]*)[ \t]*\r?\n([\s\S]*?)```$/);
      if (match) {
        const lang = match[1] || 'text';
        const code = match[2];
        // Escape HTML for the display area
        const escapedCode = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        // Escape code for the data attribute (double quotes)
        const safeCode = code.replace(/"/g, '&quot;');
        
        return `<div class="nova-app-code-block">
                  <div class="nova-app-code-header">
                    <span class="nova-app-code-lang">${lang}</span>
                    <button type="button" class="nova-app-copy-btn" data-code="${safeCode}">Copy</button>
                  </div>
                  <pre class="nova-app-code-content"><code class="language-${lang}">${escapedCode}</code></pre>
                </div>`;
      }
      
      // Regular text: Escape HTML but preserve whitespace (handled by css pre-wrap)
      return part.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }).join('');
  }

  function appendMessage(container, role, message) {
    const wrapper = document.createElement('div');
    wrapper.className = `bubble ${role}`;
    wrapper.textContent = message;
    container.appendChild(wrapper);
    return wrapper;
  }

  function bindVision() {
    const form = root.querySelector('#nova-vision-form');
    const result = root.querySelector('#nova-vision-result');
    const urlInput = root.querySelector('#nova-vision-image');
    const fileInput = root.querySelector('#nova-vision-upload');
    const fileInfo = root.querySelector('#nova-vision-upload-info');
    if (!form || !result) {
      return;
    }

    if (fileInput && urlInput) {
      fileInput.addEventListener('change', () => {
        if (fileInput.files && fileInput.files.length > 0) {
          urlInput.disabled = true;
          urlInput.value = '';
          if (fileInfo) {
            const file = fileInput.files[0];
            const sizeKb = Math.round(file.size / 1024);
            fileInfo.textContent = `${file.name} (${sizeKb} KB)`;
          }
        } else {
          urlInput.disabled = false;
          if (fileInfo) {
            fileInfo.textContent = '';
          }
        }
      });
    }

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const model = form.querySelector('#nova-vision-model').value;
      const prompt = form.querySelector('#nova-vision-prompt').value;
      const file = fileInput ? fileInput.files[0] : null;
      const imageUrl = urlInput ? urlInput.value.trim() : '';
      result.textContent = 'Analyzing...';

      try {
        if (!file && !imageUrl) {
          throw { error: { message: 'Please provide an image URL or upload a file.' } };
        }
        if (file && file.size > 12 * 1024 * 1024) {
          throw { error: { message: 'The image exceeds 12 MB. Please choose a smaller file.' } };
        }
        let data;
        if (file) {
          const formData = new FormData();
          formData.append('model', model);
          formData.append('prompt', prompt);
          formData.append('image_file', file);
          const response = await apiClient.post('/v1/images/analyze/upload', formData, {
            headers: {
              'X-AILinux-Client': CLIENT_HEADER,
            },
            isFormData: true,
          });
          data = await response.json();
          if (!response.ok) {
            throw data;
          }
        } else {
          const response = await apiClient.post('/v1/images/analyze', { model, image_url: imageUrl, prompt });
          data = await response.json();
          if (!response.ok) {
            throw data;
          }
        }
        result.textContent = data.text || 'No response received.';
      } catch (error) {
        result.textContent = 'Error: ' + parseError(error);
      } finally {
        if (fileInput) {
          fileInput.value = '';
          if (urlInput) {
            urlInput.disabled = false;
          }
          if (fileInfo) {
            fileInfo.textContent = '';
          }
        }
      }
    });
  }

  function bindImageGen() {
    const form = root.querySelector('#nova-image-form');
    const result = root.querySelector('#nova-image-result');
    if (!form || !result) {
      return;
    }

    const modelSelect = form.querySelector('#nova-image-model');
    const cfgSlider = form.querySelector('#nova-image-cfg');
    const cfgValue = form.querySelector('#nova-image-cfg-value');

    const syncCfgDisplay = () => {
      if (cfgValue && cfgSlider) {
        cfgValue.textContent = Number(cfgSlider.value || 7).toFixed(1);
      }
    };

    if (cfgSlider) {
      cfgSlider.addEventListener('input', syncCfgDisplay);
      syncCfgDisplay();
    }

    if (modelSelect) {
      modelSelect.addEventListener('change', () => applyImagePreset(modelSelect.value));
    }

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const clampDimension = (raw) => {
        const value = Number.parseInt(raw, 10);
        if (!Number.isFinite(value)) {
          return 512;
        }
        let sanitized = Math.max(64, Math.min(2048, Math.round(value)));
        const remainder = sanitized % 64;
        if (remainder !== 0) {
          sanitized -= remainder;
          if (sanitized < 64) {
            sanitized = 64;
          }
        }
        return sanitized;
      };

      const widthInput = form.querySelector('#nova-image-width');
      const heightInput = form.querySelector('#nova-image-height');
      const stepsInput = form.querySelector('#nova-image-steps');
      const seedInput = form.querySelector('#nova-image-seed');

      const model = modelSelect ? modelSelect.value : '';
      const width = clampDimension(widthInput ? widthInput.value : 512);
      const height = clampDimension(heightInput ? heightInput.value : 512);
      const stepsRaw = Number.parseInt(stepsInput ? stepsInput.value : '30', 10);
      const steps = Number.isFinite(stepsRaw) ? Math.max(1, Math.min(100, stepsRaw)) : 30;
      const cfgRaw = cfgSlider ? Number.parseFloat(cfgSlider.value) : 7.0;
      const cfgScale = Number.isFinite(cfgRaw) ? Math.max(1, Math.min(30, cfgRaw)) : 7.0;
      const seedRaw = Number.parseInt(seedInput ? seedInput.value : '-1', 10);
      const seed = Number.isFinite(seedRaw) ? seedRaw : -1;

      if (widthInput) {
        widthInput.value = width;
      }
      if (heightInput) {
        heightInput.value = height;
      }
      if (stepsInput) {
        stepsInput.value = steps;
      }
      if (cfgSlider) {
        cfgSlider.value = cfgScale;
        syncCfgDisplay();
      }
      if (seedInput) {
        seedInput.value = seed;
      }

      const payload = {
        prompt: form.querySelector('#nova-image-prompt').value,
        negative_prompt: form.querySelector('#nova-image-negative').value,
        width,
        height,
        steps,
        cfg_scale: cfgScale,
        seed,
        model,
        workflow_type: form.dataset.workflowIntent || 'auto'
      };

      result.innerHTML = '<div class="loader">Generating image...</div>';

      try {
        const response = await apiClient.post('/v1/txt2img', payload);
        const data = await safeJson(response);
        if (!response.ok) {
          const errorMessage =
            (data && typeof data === 'object' && (data.error?.message || data.message)) ||
            response.statusText ||
            `HTTP ${response.status}`;
          throw { status: response.status, message: errorMessage };
        }

        // Handle new response format with images array containing objects with 'data' field
        const images = Array.isArray(data.images) ? data.images : [];
        renderImages(result, images, {
          workflowType: data.workflow_type,
          model: data.model || model,
          error: data.error,
        });
      } catch (error) {
        result.innerHTML = `<div class="error">Error: ${parseError(error)}</div>`;
      }
    });

    // Ensure defaults are applied once models are loaded
    if (modelSelect && modelSelect.value) {
      applyImagePreset(modelSelect.value);
    } else {
      applyImagePreset('');
    }
  }

  function renderImages(container, images, meta = {}) {
    if (!container) {
      return;
    }
    const normalized = (Array.isArray(images) ? images : []).map((img, index) => {
      if (!img) {
        return null;
      }
      if (typeof img === 'string') {
        return { data: img, filename: `nova-image-${index + 1}.png`, seed: null };
      }
      const data = img.data || '';
      return {
        data,
        filename: img.filename || `nova-image-${index + 1}.png`,
        seed: typeof img.seed === 'number' ? img.seed : null,
      };
    }).filter(Boolean);

    if (!normalized.length) {
      const message = meta && meta.error ? parseError(meta.error) : 'Image generation failed. This may be due to GPU memory constraints or model unavailability. Please try again or contact support if the issue persists.';
      container.innerHTML = `<div class="error">${message}</div>`;
      return;
    }
    container.innerHTML = '';

    if ((meta && meta.model) || (meta && meta.workflowType)) {
      const metaLine = document.createElement('p');
      metaLine.className = 'image-meta';
      const parts = [];
      if (meta.model) {
        parts.push(`Model: ${meta.model}`);
      }
      if (meta.workflowType) {
        parts.push(`Workflow: ${String(meta.workflowType).toUpperCase()}`);
      }
      metaLine.textContent = parts.join(' · ');
      container.appendChild(metaLine);
    }

    const grid = document.createElement('div');
    grid.className = 'image-grid';
    normalized.forEach((img, index) => {
      const figure = document.createElement('figure');
      figure.className = 'image-card';
      const image = document.createElement('img');
      image.alt = `Generated image ${index + 1}`;
      const source = typeof img.data === 'string' && img.data.startsWith('data:')
        ? img.data
        : `data:image/png;base64,${img.data}`;
      image.src = source;
      figure.appendChild(image);
      const downloadButton = document.createElement('button');
      downloadButton.type = 'button';
      downloadButton.className = 'btn secondary download-link';
      downloadButton.textContent = 'Download';
      downloadButton.addEventListener('click', () => {
        const link = document.createElement('a');
        link.href = image.src;
        link.download = img.filename || `nova-image-${index + 1}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      });
      figure.appendChild(downloadButton);
      if (img.seed !== null && img.seed !== undefined) {
        const caption = document.createElement('figcaption');
        caption.textContent = `Seed: ${img.seed}`;
        figure.appendChild(caption);
      }
      grid.appendChild(figure);
    });
    container.appendChild(grid);
  }

  function setLoading(target, loading) {
    target.classList.toggle('is-loading', !!loading);
  }

  function parseError(error) {
    if (!error) {
      return 'Unknown error';
    }
    if (typeof error === 'string') {
      return error;
    }
    if (error.error && error.error.message) {
      return error.error.message;
    }
    if (error.message) {
      return error.message;
    }
    return 'Unknown error';
  }

  async function safeJson(response) {
    try {
      return await response.json();
    } catch (e) {
      return { message: response.statusText || 'Unknown error' };
    }
  }

  function reportError(context, error) {
    console.error('[NovaAI]', context, error);
  }

  createLayout();
  bindTabs();
  bindChat();
  bindVision();
  bindImageGen();
  fetchModels();
})();
