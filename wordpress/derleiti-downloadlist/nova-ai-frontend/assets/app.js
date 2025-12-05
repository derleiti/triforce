(function () {
  const config = window.NovaAIConfig || {};
  const API_BASE = (config.apiBase && config.apiBase.replace(/\/$/, '')) || 'https://api.ailinux.me:9000';
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

  const PREFERRED_CHAT_MODEL = 'gpt-oss:latest';

  const decoder = new TextDecoder();

  function createLayout() {
    root.innerHTML = `
      <div class="nova-shell">
        <div class="nova-header">
          <div class="nova-title">Nova AI</div>
          <div class="nova-subtitle">Chat · Vision · Image Generation</div>
        </div>
        <nav class="nova-tabs" role="tablist">
          <button class="active" data-tab="chat" role="tab" aria-selected="true">Chat</button>
          <button data-tab="vision" role="tab" aria-selected="false">Vision</button>
          <button data-tab="image" role="tab" aria-selected="false">Image</button>
        </nav>
        <section class="nova-panel active" data-panel="chat" role="tabpanel">
          <div class="chat-transcript" id="nova-chat-transcript" aria-live="polite"></div>
          <form class="form chat-form" id="nova-chat-form">
            <div class="form-row">
              <label for="nova-chat-model">Model</label>
              <select id="nova-chat-model" required></select>
            </div>
            <div class="form-row slider-row">
              <label for="nova-chat-temp">Temperature <span id="nova-chat-temp-value">0.70</span></label>
              <input type="range" min="0" max="1" step="0.05" value="0.7" id="nova-chat-temp" />
            </div>
            <div class="form-row">
              <label for="nova-chat-input">Message</label>
              <textarea id="nova-chat-input" rows="3" placeholder="Ask Nova AI anything..." required></textarea>
            </div>
            <div class="form-actions">
              <button type="submit" class="btn primary">Send</button>
              <button type="button" class="btn" id="nova-chat-reset">Reset</button>
            </div>
          </form>
        </section>
        <section class="nova-panel" data-panel="vision" role="tabpanel" aria-hidden="true">
          <form class="form" id="nova-vision-form">
            <div class="form-row">
              <label for="nova-vision-model">Model</label>
              <select id="nova-vision-model" required></select>
            </div>
            <div class="form-row">
              <label for="nova-vision-image">Image URL</label>
              <input type="url" id="nova-vision-image" placeholder="https://..." />
            </div>
            <div class="form-row">
              <label for="nova-vision-upload">Upload image</label>
              <input type="file" id="nova-vision-upload" accept="image/*" />
              <p class="field-hint">Uploads are processed securely and deleted within 2 minutes.</p>
              <p class="field-note" id="nova-vision-upload-info" aria-live="polite"></p>
            </div>
            <div class="form-row">
              <label for="nova-vision-prompt">Description</label>
              <textarea id="nova-vision-prompt" rows="3" placeholder="Describe what Nova should analyze" required></textarea>
            </div>
            <div class="form-actions">
              <button type="submit" class="btn primary">Analyze</button>
            </div>
          </form>
          <div class="vision-result" id="nova-vision-result" aria-live="polite"></div>
        </section>
        <section class="nova-panel" data-panel="image" role="tabpanel" aria-hidden="true">
          <form class="form" id="nova-image-form">
            <div class="form-row">
              <label for="nova-image-model">Model</label>
              <select id="nova-image-model" required></select>
            </div>
            <div class="form-row">
              <label for="nova-image-prompt">Prompt</label>
              <textarea id="nova-image-prompt" rows="3" placeholder="Describe the image you want" required></textarea>
            </div>
            <div class="form-row">
              <label for="nova-image-negative">Negative prompt</label>
              <textarea id="nova-image-negative" rows="2" placeholder="Optional"></textarea>
            </div>
            <div class="form-grid">
              <div>
                <label for="nova-image-width">Width</label>
                <input type="number" id="nova-image-width" min="64" max="2048" step="64" value="512" required />
              </div>
              <div>
                <label for="nova-image-height">Height</label>
                <input type="number" id="nova-image-height" min="64" max="2048" step="64" value="512" required />
              </div>
              <div>
                <label for="nova-image-steps">Steps</label>
                <input type="number" id="nova-image-steps" min="1" max="150" value="30" required />
              </div>
              <div>
                <label for="nova-image-seed">Seed</label>
                <input type="number" id="nova-image-seed" value="-1" required />
              </div>
            </div>
            <div class="form-actions">
              <button type="submit" class="btn primary">Generate image</button>
            </div>
          </form>
          <div class="image-result" id="nova-image-result" aria-live="polite"></div>
        </section>
      </div>
    `;
  }

  function bindTabs() {
    const tabs = Array.from(root.querySelectorAll('.nova-tabs button'));
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
      state.chatModels = state.models.filter((model) => Array.isArray(model.capabilities) && model.capabilities.includes('chat'));
      state.visionModels = state.models.filter((model) => Array.isArray(model.capabilities) && model.capabilities.includes('vision'));
      state.imageModels = state.models.filter((model) => Array.isArray(model.capabilities) && model.capabilities.includes('image_gen'));
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
    const imageSelect = root.querySelector('#nova-image-model');

    fillSelect(chatSelect, state.chatModels, PREFERRED_CHAT_MODEL);
    fillSelect(visionSelect, state.visionModels);
    fillSelect(imageSelect, state.imageModels);
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
            bubble.innerHTML += `<br>Found ${data.results.length} results. <a href="${API_BASE}/v1/crawler/results?job_id=${jobId}" target="_blank">View results</a>`;
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

      const response = await apiClient.postStream('/v1/chat/completions', {
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

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const payload = {
        model: form.querySelector('#nova-image-model').value,
        prompt: form.querySelector('#nova-image-prompt').value,
        negative_prompt: form.querySelector('#nova-image-negative').value,
        width: parseInt(form.querySelector('#nova-image-width').value, 10),
        height: parseInt(form.querySelector('#nova-image-height').value, 10),
        steps: parseInt(form.querySelector('#nova-image-steps').value, 10),
        seed: parseInt(form.querySelector('#nova-image-seed').value, 10),
      };

      result.innerHTML = '<div class="loader">Generating image...</div>';

      try {
        const response = await apiClient.post('/v1/images/generate', payload);
        const data = await response.json();
        if (!response.ok) {
          throw data;
        }
        renderImages(result, Array.isArray(data.images) ? data.images : []);
      } catch (error) {
        result.innerHTML = `<div class="error">Error: ${parseError(error)}</div>`;
      }
    });
  }

  function renderImages(container, images) {
    if (!images.length) {
      container.innerHTML = '<div class="error">No images received.</div>';
      return;
    }
    const grid = document.createElement('div');
    grid.className = 'image-grid';
    images.forEach((img, index) => {
      const figure = document.createElement('figure');
      figure.className = 'image-card';
      const image = document.createElement('img');
      image.alt = `Generated image ${index + 1}`;
      image.src = img.startsWith('data:') ? img : `data:image/png;base64,${img}`;
      figure.appendChild(image);
      const downloadButton = document.createElement('button');
      downloadButton.type = 'button';
      downloadButton.className = 'btn secondary download-link';
      downloadButton.textContent = 'Download';
      downloadButton.addEventListener('click', () => {
        const link = document.createElement('a');
        link.href = image.src;
        link.download = `nova-image-${index + 1}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      });
      figure.appendChild(downloadButton);
      grid.appendChild(figure);
    });
    container.innerHTML = '';
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
