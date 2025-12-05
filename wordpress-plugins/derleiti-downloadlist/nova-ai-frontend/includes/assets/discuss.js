(function () {
  const config = window.NovaAIDiscussConfig || {};
  const API_BASE = (config.apiBase && config.apiBase.replace(/\/$/, '')) || 'https://api.ailinux.me:9000';
  const CLIENT_HEADER = 'nova-ai-frontend/1.0';
  const buttons = document.querySelectorAll('[data-novaai-discuss-button]');
  if (!buttons.length) {
    return;
  }

  let overlay;
  let modal;
  let closeButton;
  let modelSelect;
  let transcript;
  let textarea;
  let form;
  let resetButton;
  let contextTarget;
  let lastFocus = null;
  const decoder = new TextDecoder();
  const state = {
    modelsLoaded: false,
    loading: false,
    busy: false,
    context: null,
    history: [],
  };

  buttons.forEach((button) => {
    button.addEventListener('click', () => openModal(button));
  });

  function openModal(button) {
    ensureModal();
    const context = {
      title: button.getAttribute('data-novaai-discuss-title') || document.title,
      url: button.getAttribute('data-novaai-discuss-url') || window.location.href,
      excerpt: button.getAttribute('data-novaai-discuss-excerpt') || '',
    };

    lastFocus = document.activeElement;
    resetConversation(context);
    document.body.classList.add('novaai-discuss-open');
    overlay.classList.add('is-visible');
    modal.setAttribute('aria-hidden', 'false');
    loadModels();
    setTimeout(() => {
      textarea.focus({ preventScroll: true });
    }, 60);
    document.addEventListener('keydown', handleKeydown, true);
  }

  function closeModal() {
    if (!overlay) {
      return;
    }
    overlay.classList.remove('is-visible');
    modal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('novaai-discuss-open');
    document.removeEventListener('keydown', handleKeydown, true);
    if (lastFocus && typeof lastFocus.focus === 'function') {
      lastFocus.focus();
    }
  }

  function handleKeydown(event) {
    if (event.key === 'Escape') {
      event.stopPropagation();
      closeModal();
    }
  }

  function ensureModal() {
    if (overlay) {
      return;
    }

    overlay = document.createElement('div');
    overlay.className = 'novaai-discuss-overlay';
    overlay.innerHTML = `
      <div class="novaai-discuss-modal" role="dialog" aria-modal="true" aria-hidden="true" aria-labelledby="novaai-discuss-title">
        <button type="button" class="novaai-discuss-close" aria-label="Close Nova AI discussion"></button>
        <h2 id="novaai-discuss-title">Discuss this article with Nova AI</h2>
        <p class="novaai-discuss-context" id="novaai-discuss-context"></p>
        <div class="novaai-discuss-control">
          <label for="novaai-discuss-model">Choose a model</label>
          <select id="novaai-discuss-model" required></select>
        </div>
        <div class="novaai-discuss-transcript" id="novaai-discuss-transcript" aria-live="polite"></div>
        <form class="novaai-discuss-form" id="novaai-discuss-form">
          <label class="screen-reader-text" for="novaai-discuss-input">Ask Nova AI about the article</label>
          <textarea id="novaai-discuss-input" rows="3" placeholder="Ask a question about the article..." required></textarea>
          <div class="novaai-discuss-actions">
            <button type="submit" class="novaai-btn novaai-btn-primary">Send</button>
            <button type="button" class="novaai-btn" data-novaai-discuss-reset>New topic</button>
          </div>
        </form>
      </div>
    `;

    document.body.appendChild(overlay);

    modal = overlay.querySelector('.novaai-discuss-modal');
    closeButton = overlay.querySelector('.novaai-discuss-close');
    modelSelect = overlay.querySelector('#novaai-discuss-model');
    transcript = overlay.querySelector('#novaai-discuss-transcript');
    textarea = overlay.querySelector('#novaai-discuss-input');
    form = overlay.querySelector('#novaai-discuss-form');
    resetButton = overlay.querySelector('[data-novaai-discuss-reset]');
    contextTarget = overlay.querySelector('#novaai-discuss-context');

    overlay.addEventListener('click', (event) => {
      if (event.target === overlay) {
        closeModal();
      }
    });

    closeButton.addEventListener('click', closeModal);

    form.addEventListener('submit', handleSubmit);
    resetButton.addEventListener('click', () => {
      if (state.context) {
        resetConversation(state.context);
        textarea.focus({ preventScroll: true });
      }
    });
  }

  function resetConversation(context) {
    state.context = context;
    state.history = [
      {
        role: 'system',
        content: buildSystemPrompt(context),
      },
    ];
    if (contextTarget) {
      const summary = context.excerpt ? `Summary: ${context.excerpt}` : 'The full article is shared with Nova AI.';
      contextTarget.textContent = `${context.title} — ${summary}`;
    }
    if (transcript) {
      transcript.innerHTML = '';
      appendMessage('system', 'Nova AI is ready to discuss this article.');
    }
    if (textarea) {
      textarea.value = '';
      textarea.placeholder = `Ask a question about "${context.title}"...`;
    }
  }

  function buildSystemPrompt(context) {
    const parts = [
      'You are Nova AI, assisting a reader who wants to discuss a blog article.',
      `Article title: "${context.title}".`,
    ];
    if (context.url) {
      parts.push(`Article URL: ${context.url}.`);
    }
    if (context.excerpt) {
      parts.push(`Article summary: ${context.excerpt}.`);
    }
    parts.push('Answer in English, keep responses concise, and reference relevant sections from the article when helpful.');
    return parts.join(' ');
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (state.busy || !modelSelect || !modelSelect.value) {
      return;
    }
    const message = textarea.value.trim();
    if (!message) {
      return;
    }

    const history = state.history.slice();
    history.push({ role: 'user', content: message });

    appendMessage('user', message);
    textarea.value = '';
    textarea.focus({ preventScroll: true });
    const assistantBubble = appendMessage('assistant', '');
    state.busy = true;

    try {
      await streamChat(history, assistantBubble);
      state.history = history;
      scrollTranscript();
    } catch (error) {
      assistantBubble.textContent = 'Error: ' + parseError(error);
      assistantBubble.classList.add('is-error');
    } finally {
      state.busy = false;
    }
  }

  function scrollTranscript() {
    if (transcript) {
      transcript.scrollTop = transcript.scrollHeight;
    }
  }

  async function loadModels() {
    if (state.modelsLoaded || !modelSelect) {
      return;
    }
    state.modelsLoaded = true;
    setModelLoading(true);
    try {
      const response = await fetch(`${API_BASE}/v1/models`, {
        headers: {
          'Accept': 'application/json',
          'X-AILinux-Client': CLIENT_HEADER,
        },
      });
      const payload = await response.json();
      if (!response.ok) {
        throw payload;
      }
      const models = Array.isArray(payload.data)
        ? payload.data.filter((model) => Array.isArray(model.capabilities) && model.capabilities.includes('chat'))
        : [];
      populateModels(models);
    } catch (error) {
      state.modelsLoaded = false;
      populateModels([]);
      appendMessage('system', 'Unable to load models. Please try again later.');
      console.error('[NovaAI] Failed to load models', error);
    } finally {
      setModelLoading(false);
    }
  }

  function setModelLoading(loading) {
    state.loading = !!loading;
    if (modelSelect) {
      modelSelect.disabled = !!loading;
    }
  }

  function populateModels(models) {
    if (!modelSelect) {
      return;
    }
    modelSelect.innerHTML = '';
    if (!models.length) {
      const option = document.createElement('option');
      option.textContent = 'No models available';
      option.disabled = true;
      option.selected = true;
      modelSelect.appendChild(option);
      modelSelect.disabled = true;
      return;
    }
    modelSelect.disabled = false;
    models.forEach((model, index) => {
      const option = document.createElement('option');
      option.value = model.id;
      option.textContent = model.id;
      if (model.id === 'gpt-oss:latest' || index === 0) {
        option.selected = true;
      }
      modelSelect.appendChild(option);
    });
  }

  async function streamChat(messages, bubble) {
    const response = await fetch(`${API_BASE}/v1/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/plain',
        'X-AILinux-Client': CLIENT_HEADER,
      },
      body: JSON.stringify({
        model: modelSelect.value,
        messages,
        stream: true,
        temperature: 0.7,
      }),
    });

    if (!response.ok || !response.body) {
      throw await safeJson(response);
    }

    bubble.classList.add('is-streaming');
    const reader = response.body.getReader();

    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }
      const chunk = decoder.decode(value, { stream: true });
      bubble.textContent += chunk;
    }

    bubble.classList.remove('is-streaming');
  }

  function appendMessage(role, message) {
    if (!transcript) {
      return null;
    }
    const bubble = document.createElement('div');
    bubble.className = `novaai-discuss-bubble is-${role}`;
    bubble.textContent = message;
    transcript.appendChild(bubble);
    scrollTranscript();
    return bubble;
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
    } catch (error) {
      return { message: response.statusText || 'Unknown error' };
    }
  }
})();
