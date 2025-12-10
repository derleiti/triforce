(function () {
  const config = window.NovaAIDiscussConfig || {};
  const API_BASE = (config.apiBase && config.apiBase.replace(/\/$/, '')) || 'https://api.ailinux.me';
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
    
    transcript.addEventListener('click', (e) => {
      if (e.target.classList.contains('novaai-discuss-copy-btn')) {
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

    textarea.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        // Trigger form submission handler directly
        handleSubmit(event);
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
    const basePrompt = [
      'Du bist ein Analyse-Assistent für Artikel. Den Artikeltext erhältst du automatisch vom Frontend; '
        + 'der Nutzer muss ihn nicht erneut senden.',
      'Du beantwortest Nutzerfragen auf Basis des automatisch übergebenen Artikels, deines Grundwissens '
        + 'und der Projektstruktur.',
      'Frontend: ~/wordpress/html/wp-content/. Backend: ~/ailinux-ai-server-backend.',
      'Regeln:',
      '1. Verwende immer den automatisch übergebenen Artikeltext; fordere ihn nie an.',
      '2. Wiederhole oder paraphrasiere den Artikel nur auf ausdrückliche Aufforderung '
        + '(z. B. „Fasse zusammen“, „Wichtigste Punkte“, „Erkläre das im Detail“).',
      '3. Zitiere nur kurze relevante Stellen, wenn es hilft.',
      '4. Wenn der Artikel eine Frage nicht beantwortet, nutze Grundwissen und kennzeichne es klar mit: '
        + '„Im Artikel steht dazu nichts, aber allgemein gilt …“.',
      '5. Antworte präzise, ruhig und strukturiert, damit Backend und Frontend die Antwort problemlos '
        + 'verarbeiten können.',
      '6. Vermeide generische Einleitungen oder Wiederholungen früherer Antworten.',
      '7. Beantworte nur das, was der Nutzer verlangt – nicht mehr, nicht weniger.',
      '8. Analysen, Prognosen oder Meinungen sind erlaubt, wenn sie auf Artikel + Grundwissen basieren.',
      '9. Wiederholungen und Zusammenfassungen nur, wenn der Nutzer sie verlangt.',
      '10. Erfinde keine Details, die weder im Artikel noch im verlässlichen Allgemeinwissen stehen.',
      '11. Wenn Informationen fehlen oder unklar sind, sage dies klar und eindeutig.',
      '12. Formatiere deine Antworten sauber und lesbar.',
      '13. Nutze für Code-Beispiele IMMER Markdown-Codeblöcke (```language ... ```), damit sie korrekt angezeigt werden und die Kopierfunktion funktioniert.',
      '14. Vermeide übermäßige Sonderzeichen oder komplexe Formatierungen, die nicht Standard-Markdown sind.',
    ].join('\\n');

    const articleContext = [
      'Artikelkontext:',
      `- Titel: "${context.title}"`,
      context.url ? `- URL: ${context.url}` : '- URL: (nicht verfügbar)',
      context.excerpt ? `- Kurzfassung: ${context.excerpt}` : '- Kurzfassung: (nicht verfügbar)',
      '- Wiederhole oder zitiere den Artikel nur bei ausdrücklicher Nachfrage.',
    ].join('\\n');

    return `${basePrompt}\\n\\n${articleContext}\\nAntworte knapp und halte dich an die Regeln.`;
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
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 60000); // 60s timeout

    try {
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
        signal: controller.signal,
      });

      clearTimeout(timeout);

      if (!response.ok || !response.body) {
        throw await safeJson(response);
      }

      bubble.classList.add('is-streaming');
      const reader = response.body.getReader();
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

      bubble.classList.remove('is-streaming');
    } catch (error) {
      clearTimeout(timeout);
      if (error.name === 'AbortError') {
        throw new Error('Request timeout after 60 seconds');
      }
      throw error;
    }
  }

  function formatMessage(text) {
    if (!text) return '';
    const parts = text.split(/(```[\w-]*[ \t]*\r?\n[\s\S]*?```)/g);
    return parts.map(part => {
      const match = part.match(/^```([\w-]*)[ \t]*\r?\n([\s\S]*?)```$/);
      if (match) {
        const lang = match[1] || 'text';
        const code = match[2];
        const escapedCode = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        const safeCode = code.replace(/"/g, '&quot;');
        return `<div class="novaai-discuss-code-block">
                  <div class="novaai-discuss-code-header">
                    <span class="novaai-discuss-code-lang">${lang}</span>
                    <button type="button" class="novaai-discuss-copy-btn" data-code="${safeCode}">Copy</button>
                  </div>
                  <pre class="novaai-discuss-code-content"><code class="language-${lang}">${escapedCode}</code></pre>
                </div>`;
      }
      return part.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }).join('');
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
