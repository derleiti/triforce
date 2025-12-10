const AilinuxNovaApp = (() => {
  const SELECTORS = {
    header: '[data-header]',
    navContainer: '.site-nav',
    navList: '.site-nav > ul',
    observe: '[data-observe]',
    readingTarget: '[data-words]',
    toc: '[data-toc]'
  };

  const STATE = {
    lastScrollY: 0,
    ticking: false,
    prefersReducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches
  };

  const WPM = 200;

  const computeReadingTime = (element) => {
    const words = parseInt(element.getAttribute('data-words'), 10) || 0;
    const placeholder = element.querySelector('[data-reading]');

    if (!placeholder) {
      return;
    }

    const minutes = Math.max(1, Math.round(words / WPM));
    placeholder.textContent = `${minutes} min Lesezeit`;
  };

  const updateReadingTimers = () => {
    document.querySelectorAll(SELECTORS.readingTarget).forEach(computeReadingTime);
  };

  const initIntersectionObserver = () => {
    if (STATE.prefersReducedMotion || !('IntersectionObserver' in window)) {
      document.querySelectorAll(SELECTORS.observe).forEach((element) => {
        element.classList.add('is-visible');
      });
      return;
    }

    const observer = new IntersectionObserver((entries, obs) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          obs.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.15,
      rootMargin: '0px 0px -10% 0px'
    });

    document.querySelectorAll(SELECTORS.observe).forEach((element) => observer.observe(element));
  };

  const updateHeaderOffset = () => {
    const header = document.querySelector(SELECTORS.header);
    if (!header) {
      return;
    }
    document.documentElement.style.setProperty('--hdr', `${header.offsetHeight}px`);
  };

  const updateHeaderState = (currentY) => {
    const header = STATE.headerEl;
    if (!header) {
      return;
    }

    const isScrollingDown = currentY >= STATE.lastScrollY;

    if (currentY > 24 && isScrollingDown) {
      header.classList.add('is-scrolled');
    } else if (currentY <= 24 || !isScrollingDown) {
      header.classList.remove('is-scrolled');
    }
  };

  const onScroll = () => {
    if (STATE.ticking) return;

    STATE.ticking = true;
    window.requestAnimationFrame(() => {
      const currentY = window.scrollY || window.pageYOffset;
      updateHeaderState(currentY);
      STATE.lastScrollY = currentY;
      STATE.ticking = false;
    });
  };

  const initHeader = () => {
    STATE.headerEl = document.querySelector(SELECTORS.header);

    if (!STATE.headerEl) {
      return;
    }

    updateHeaderOffset();
    updateHeaderState(window.scrollY || window.pageYOffset || 0);
    window.removeEventListener('scroll', onScroll);
    window.addEventListener('scroll', onScroll, { passive: true });
  };

  const highlightActiveLink = () => {
    const currentPath = window.location.pathname.replace(/\/$/, '') || '/';
    const links = document.querySelectorAll('.main-menu a, .nav-more .more-menu a');
    links.forEach((link) => {
      const linkPath = link.pathname.replace(/\/$/, '') || '/';
      if (linkPath === currentPath) {
        link.classList.add('is-active');
      } else {
        link.classList.remove('is-active');
      }
    });
  };

  const initNavOverflow = () => {
    const nav = document.querySelector(SELECTORS.navContainer);
    const list = document.querySelector(SELECTORS.navList);

    if (!nav || !list) {
      return;
    }

    // Don't initialize overflow menu on mobile (viewport < 768px)
    // Mobile uses the dedicated mobile menu instead
    const isMobile = () => window.innerWidth < 768;
    if (isMobile()) {
      return;
    }

    if (!nav.__overflowState) {
      const moreItem = document.createElement('li');
      moreItem.className = 'nav-more';
      moreItem.innerHTML = '<button type="button" aria-haspopup="true" aria-expanded="false">Mehr ▼</button><div class="more-menu" aria-hidden="true" role="menu"></div>';
      list.appendChild(moreItem);

      const moreButton = moreItem.querySelector('button');
      const moreMenu = moreItem.querySelector('.more-menu');
      const originals = Array.from(list.querySelectorAll(':scope > li')).filter((li) => li !== moreItem);

      const closeMore = () => {
        moreItem.classList.remove('is-open');
        moreButton.setAttribute('aria-expanded', 'false');
        moreMenu.setAttribute('aria-hidden', 'true');
      };

      moreButton.addEventListener('click', (event) => {
        event.preventDefault();
        const expanded = moreItem.classList.toggle('is-open');
        moreButton.setAttribute('aria-expanded', String(expanded));
        moreMenu.setAttribute('aria-hidden', String(!expanded));
      });

      document.addEventListener('click', (event) => {
        if (!moreItem.contains(event.target)) {
          closeMore();
        }
      });

      document.addEventListener('keyup', (event) => {
        if (event.key === 'Escape') {
          closeMore();
        }
      });

      nav.__overflowState = {
        moreItem,
        moreButton,
        moreMenu,
        originals,
        layoutBound: false
      };
    }

    const state = nav.__overflowState;
    const { moreItem, moreButton, moreMenu, originals } = state;

    const resetMenu = () => {
      originals.forEach((li) => {
        if (!list.contains(li)) {
          list.insertBefore(li, moreItem);
        }
      });
      moreMenu.innerHTML = '';
      moreItem.style.display = 'none';
      moreItem.classList.remove('is-open');
      moreButton.setAttribute('aria-expanded', 'false');
      moreMenu.setAttribute('aria-hidden', 'true');
    };

    const countRows = () => {
      const anchors = originals
        .filter((li) => list.contains(li))
        .map((li) => li.querySelector('a'))
        .filter((anchor) => anchor && anchor.offsetParent);
      if (!anchors.length) {
        return 0;
      }
      const tops = new Set(anchors.map((anchor) => Math.round(anchor.getBoundingClientRect().top)));
      return tops.size;
    };

    const moveLastItem = () => {
      const available = originals.filter((li) => list.contains(li));
      const candidate = available[available.length - 1];
      if (!candidate) {
        return false;
      }

      const anchor = candidate.querySelector('a');
      const anchorClone = anchor ? anchor.cloneNode(true) : null;

      list.removeChild(candidate);

      if (anchorClone) {
        anchorClone.classList.add('more-menu-link');
        anchorClone.setAttribute('role', 'menuitem');
        anchorClone.addEventListener('click', () => {
          closeMore();
        });
        const wrapper = document.createElement('div');
        wrapper.className = 'more-menu__item';
        wrapper.appendChild(anchorClone);
        moreMenu.prepend(wrapper);
      }

      return true;
    };

    const relayout = () => {
      resetMenu();
      highlightActiveLink();

      const MAX_ROWS = 2;
      let safety = originals.length;
      let rows = countRows();

      while ((rows > MAX_ROWS || nav.scrollHeight - nav.clientHeight > 4) && safety > 0) {
        if (!moveLastItem()) {
          break;
        }
        safety -= 1;
        rows = countRows();
      }

      if (moreMenu.childElementCount > 0) {
        moreItem.style.display = 'inline-flex';
        moreMenu.setAttribute('aria-hidden', 'true');
      }
    };

    if (!state.layoutBound) {
      const handleResize = () => window.requestAnimationFrame(relayout);
      state.layoutBound = true;
      window.addEventListener('resize', handleResize);
      window.addEventListener('load', relayout);
    }

    relayout();
    highlightActiveLink();
  };

  const initNav = () => {
    initNavOverflow();
    highlightActiveLink();
  };

  const smoothScrollAnchors = () => {
    const links = document.querySelectorAll("a[href^='#']");

    links.forEach((link) => {
      if (link.dataset.smoothBound === 'true') {
        return;
      }

      link.dataset.smoothBound = 'true';

      link.addEventListener('click', (event) => {
        const targetId = link.getAttribute('href');
        if (!targetId || targetId === '#') {
          return;
        }

        if (link.pathname.replace(/\/$/, '') !== window.location.pathname.replace(/\/$/, '')) {
          return;
        }

        const targetElement = document.querySelector(targetId);
        if (!targetElement) {
          return;
        }

        event.preventDefault();
        targetElement.scrollIntoView({
          behavior: STATE.prefersReducedMotion ? 'auto' : 'smooth',
          block: 'start'
        });

        if (!targetElement.hasAttribute('tabindex')) {
          targetElement.setAttribute('tabindex', '-1');
        }

        targetElement.focus({ preventScroll: true });
      });
    });
  };

  const disableSwupOnSpecialPages = () => {
    document.querySelectorAll('a[href*="/forum"], a[href*="/topics"], a.bbp-topic-permalink, a[href*="datenschutz"], a[href*="privacy"]')
      .forEach(a => a.setAttribute('data-no-swup', ''));
  };

  const buildTOC = () => {
    const toc = document.querySelector(SELECTORS.toc);
    if (!toc) return;

    const headings = document.querySelectorAll('.single-post__content h2, .single-post__content h3');
    if (!headings.length) {
      return;
    }

    const list = toc.querySelector('.post-toc__list');
    if (!list) return;

    toc.removeAttribute('hidden');
    list.innerHTML = '';

    headings.forEach((heading, index) => {
      if (!heading.id) {
        heading.id = `section-${index + 1}`;
      }

      const item = document.createElement('li');
      const link = document.createElement('a');
      link.href = `#${heading.id}`;
      link.textContent = heading.textContent;
      link.setAttribute('data-scroll', '');

      if (heading.tagName.toLowerCase() === 'h3') {
        item.classList.add('is-sub');
      }

      item.appendChild(link);
      list.appendChild(item);
    });
  };

  const observeAnchors = () => {
    if (!('IntersectionObserver' in window)) return;

    const headings = document.querySelectorAll('.single-post__content h2[id], .single-post__content h3[id]');
    const tocLinks = document.querySelectorAll('.post-toc__list a');

    if (!headings.length || !tocLinks.length) {
      return;
    }

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          tocLinks.forEach((link) => {
            link.classList.toggle('is-active', link.hash === `#${entry.target.id}`);
          });
        }
      });
    }, {
      threshold: 0.3,
      rootMargin: '0px 0px -50% 0px'
    });

    headings.forEach((heading) => observer.observe(heading));
  };

  const initScrollRestoration = () => {
    if ('scrollRestoration' in history) {
      history.scrollRestoration = 'manual';
    }
  };

  // Focus trap utility for modal accessibility
  const createFocusTrap = (element) => {
    const focusableSelectors = 'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

    const getFocusableElements = () => {
      return Array.from(element.querySelectorAll(focusableSelectors));
    };

    const handleTabKey = (e) => {
      const focusableElements = getFocusableElements();
      if (!focusableElements.length) return;

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (e.shiftKey && document.activeElement === firstElement) {
        e.preventDefault();
        lastElement.focus();
      } else if (!e.shiftKey && document.activeElement === lastElement) {
        e.preventDefault();
        firstElement.focus();
      }
    };

    const activate = () => {
      element.addEventListener('keydown', (e) => {
        if (e.key === 'Tab') {
          handleTabKey(e);
        }
      });

      // Focus first focusable element
      const focusableElements = getFocusableElements();
      if (focusableElements.length) {
        setTimeout(() => focusableElements[0].focus(), 100);
      }
    };

    return { activate };
  };

  const setupAiDiscuss = () => {
    const button = document.getElementById('ai-discuss-btn');
    const panel = document.getElementById('ai-discuss-panel');
    const sendButton = document.getElementById('ai-send');
    const input = document.getElementById('ai-input');
    const output = document.getElementById('ai-output');
    const close = panel ? panel.querySelector('.ai-close') : null;
    const modelSelect = document.getElementById('ai-model-select');
    const modelSelectWrapper = document.querySelector('.ai-model-select-wrapper');

    if (!button || !panel || !sendButton || !input || !output) {
      console.warn('[DiscussAI] Required elements not found');
      return;
    }

    // Get API configuration with fallbacks
    const getApiConfig = () => {
      const base = (window.NOVA_API && window.NOVA_API.BASE) || 'https://api.ailinux.me';
      const chatEndpoint = (window.NOVA_API && window.NOVA_API.CHAT_ENDPOINT) || '/v1/chat/completions';
      const modelsEndpoint = (window.NOVA_API && window.NOVA_API.MODELS_ENDPOINT) || '/v1/models';
      const healthEndpoint = (window.NOVA_API && window.NOVA_API.HEALTH_ENDPOINT) || '/health';
      const defaultModel = (window.NOVA_API && window.NOVA_API.DEFAULT_MODEL) || 'llama4:latest';

      const normalizedBase = base.replace(/\/+$/, '');

      return {
        chatUrl: `${normalizedBase}${chatEndpoint.startsWith('/') ? chatEndpoint : `/${chatEndpoint}`}`,
        modelsUrl: `${normalizedBase}${modelsEndpoint.startsWith('/') ? modelsEndpoint : `/${modelsEndpoint}`}`,
        healthUrl: `${normalizedBase}${healthEndpoint.startsWith('/') ? healthEndpoint : `/${healthEndpoint}`}`,
        defaultModel: defaultModel,
        base: normalizedBase
      };
    };

    const config = getApiConfig();
    let abortController = null;
    let selectedModel = config.defaultModel;
    let focusTrap = createFocusTrap(panel);

    // Health check to toggle availability
    const markUnavailable = (why = 'AI nicht erreichbar') => {
      button.disabled = true;
      button.title = why;
      button.classList.add('is-disabled');
    };
    const healthCheck = async () => {
      try {
        const res = await fetch(config.healthUrl, { method: 'GET' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
      } catch (e) {
        markUnavailable(e.message);
      }
    };
    healthCheck();

    console.log('[DiscussAI] Initialized with config:', {
      chatUrl: config.chatUrl,
      modelsUrl: config.modelsUrl,
      defaultModel: config.defaultModel
    });

    // Load available models
    const loadModels = async () => {
      try {
        const response = await fetch(config.modelsUrl, {
          method: 'GET',
          headers: { 'Accept': 'application/json' }
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        const models = data.data || data.models || [];

        if (models.length > 0 && modelSelect && modelSelectWrapper) {
          modelSelect.innerHTML = '';
          models.forEach((model) => {
            const option = document.createElement('option');
            option.value = model.id || model.name || model;
            option.textContent = model.id || model.name || model;
            if (option.value === config.defaultModel) {
              option.selected = true;
            }
            modelSelect.appendChild(option);
          });

          modelSelectWrapper.style.display = 'block';
          console.log('[DiscussAI] Loaded', models.length, 'models');
        } else {
          console.log('[DiscussAI] No models returned or model list is empty, using default');
        }
      } catch (error) {
        console.warn('[DiscussAI] Failed to load models:', error.message);
        // Silently fail - will use default model
      }
    };


    const updateContextPrompt = () => {
      // Use data attributes from button if available
      if (button.dataset.novaaiDiscussTitle || button.dataset.novaaiDiscussExcerpt) {
        const title = button.dataset.novaaiDiscussTitle || '';
        const excerpt = button.dataset.novaaiDiscussExcerpt || '';
        if (title || excerpt) {
          input.value = `Diskutiere: "${title}"${excerpt ? ' - ' + excerpt : ''}`;
          return;
        }
      }

      // Fallback to AIContext if available
      if (typeof AIContext !== 'undefined' && AIContext.contextPrompt) {
        input.value = AIContext.contextPrompt;
      } else {
        input.value = '';
      }
    };

    const openPanel = () => {
      updateHeaderOffset();
      panel.classList.add('open');
      panel.setAttribute('aria-hidden', 'false');
      button.setAttribute('aria-expanded', 'true');
      document.body.classList.add('ai-panel-open');

      // Update context for current page
      updateContextPrompt();

      // Load models on first open
      if (modelSelect && modelSelect.options.length <= 1) {
        loadModels();
      }

      // Activate focus trap
      focusTrap.activate();
    };

    const closePanel = () => {
      panel.classList.remove('open');
      panel.setAttribute('aria-hidden', 'true');
      button.setAttribute('aria-expanded', 'false');
      document.body.classList.remove('ai-panel-open');
      if (abortController) {
        abortController.abort();
      }
      button.focus(); // Return focus to trigger button
    };

    const getSelectionText = () => {
      const selection = window.getSelection ? window.getSelection().toString().trim() : '';
      return selection || '';
    };

    const getPostContext = () => {
      const title = document.querySelector('article h1, article h2, h1, h2')?.textContent?.trim() || document.title;
      const body = document.querySelector('.single-post__content, .entry-content, article')?.innerText || '';
      const excerpt = body.replace(/\s+/g, ' ').trim().slice(0, 1100);
      return `${title}\n\n${excerpt}`;
    };

    const getMetaInfo = () => {
      const categories = Array.from(document.querySelectorAll('.single-post__badge a, .post-tags a'))
        .map((el) => el.textContent.trim())
        .filter(Boolean);
      const parts = [
        `URL: ${window.location.href}`,
        `Sprache: ${document.documentElement.lang || 'de'}`,
        categories.length ? `Kategorien: ${categories.join(', ')}` : ''
      ].filter(Boolean);
      return parts.join('\n');
    };

    const setLoading = (loading) => {
      sendButton.disabled = loading;
      sendButton.textContent = loading ? 'Sende...' : 'Senden';
      if (loading) {
        output.textContent = 'Verbinde und lade Antwort...';
        output.style.color = 'var(--muted)';
      } else {
        output.style.color = '';
      }
    };

    const createErrorMessage = (error) => {
      // Check for CORS/Network errors
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        return 'CORS oder Mixed-Content blockiert – API muss über HTTPS erreichbar und für diese Domain freigegeben sein.';
      }

      if (error.name === 'AbortError') {
        return 'Anfrage abgebrochen - bitte erneut versuchen.';
      }

      if (error.status === 404) {
        return `Endpoint nicht gefunden (404) - Bitte NOVA_API.CHAT_ENDPOINT prüfen. Aktuell: ${config.chatUrl}`;
      }

      if (error.status === 401 || error.status === 403) {
        return 'Nicht autorisiert - API-Zugang prüfen.';
      }

      if (error.status === 429) {
        return 'Zu viele Anfragen (429) - bitte kurz warten und erneut versuchen.';
      }

      if (error.status && error.status >= 500) {
        return `Serverfehler (${error.status}) - bitte später erneut versuchen.`;
      }

      return error.message || 'Keine Antwort vom AI-Service.';
    };

    const safeJson = async (res) => {
      const text = await res.text();
      try { return JSON.parse(text); } catch { return { raw: text }; }
    };

    const fetchChat = async (payload, attempt = 1) => {
      const MAX_ATTEMPTS = 2; // Changed from 3 to 2 as per requirements
      abortController = new AbortController();
      const timeoutId = window.setTimeout(() => abortController.abort(), 90000); // 90 seconds timeout

      try {
        console.log('[DiscussAI] Request attempt', attempt, 'to', config.chatUrl);

        const response = await fetch(config.chatUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: JSON.stringify(payload),
          signal: abortController.signal
        });

        if (!response.ok) {
          // Retry only on 429, 500, 502, 503, 504 and not on 4xx
          if ([429, 500, 502, 503, 504].includes(response.status) && attempt <= MAX_ATTEMPTS) {
            const delay = Math.pow(2, attempt) * 500; // Exponential backoff
            console.log('[DiscussAI] Retrying after', delay, 'ms');
            await new Promise((resolve) => setTimeout(resolve, delay));
            return fetchChat(payload, attempt + 1);
          }

          const data = await safeJson(response);
          const msg = (data && (data.error?.message || data.message)) || `HTTP ${response.status}`;
          const error = new Error(msg);
          error.status = response.status;
          throw error;
        }

        return await safeJson(response);
      } catch (error) {
        console.error('[DiscussAI] Fetch error:', error);
        throw error;
      } finally {
        window.clearTimeout(timeoutId);
        abortController = null;
      }
    };

    const renderResponse = (data) => {
      // Support both OpenAI format and simple {text: "..."} format
      const message = data?.choices?.[0]?.message?.content || data?.text || '';
      output.textContent = message || 'Keine Antwort erhalten.';
      output.style.color = '';
    };

    const discuss = async () => {
      const userPrompt = input.value.trim();
      const selection = getSelectionText();
      const context = selection || getPostContext();

      if (!userPrompt && !selection) {
        input.focus();
        return;
      }

      if (!config.chatUrl) {
        output.textContent = 'Keine API-Konfiguration gefunden (NOVA_API).';
        console.error('[DiscussAI] No API configuration found');
        return;
      }

      // Ensure HTTPS
      if (!config.chatUrl.startsWith('https://')) {
        output.textContent = '⚠ Warnung: API verwendet kein HTTPS. Mixed-Content könnte blockiert werden.';
        output.style.color = 'var(--warning-color, #f59e0b)';
        return;
      }

      if (abortController) {
        abortController.abort();
      }

      // Get selected model
      if (modelSelect && modelSelect.value) {
        selectedModel = modelSelect.value;
      }

      const payload = {
        model: selectedModel,
        stream: false, // Keep stream:false for simplicity
        messages: [
          {
            role: 'system',
            content: 'You are AILinux site assistant. Provide helpful, concise answers in German.'
          },
          {
            role: 'user',
            content: `${userPrompt || 'Bitte analysieren:'}\n\n---\nKontext:\n${context}\n\n${getMetaInfo()}`
          }
        ]
      };

      console.log('[DiscussAI] Sending request with model:', selectedModel);
      setLoading(true);

      try {
        const data = await fetchChat(payload);
        renderResponse(data);
        console.log('[DiscussAI] Response received successfully');
      } catch (error) {
        const errorMsg = createErrorMessage(error);
        output.textContent = `AI nicht erreichbar: ${errorMsg}`;
        output.style.color = 'var(--error-color, #ef4444)';
        console.error('[DiscussAI] Error:', errorMsg);
      } finally {
        setLoading(false);
      }
    };

    // Event listeners - bound once on initialization
    button.addEventListener('click', () => {
      if (panel.classList.contains('open')) {
        closePanel();
      } else {
        openPanel();
      }
    });

    if (close) {
      close.addEventListener('click', closePanel);
    }

    panel.addEventListener('click', (event) => {
      if (event.target === panel) {
        closePanel();
      }
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && panel.classList.contains('open')) {
        closePanel();
      }
    });

    sendButton.addEventListener('click', discuss);

    input.addEventListener('keydown', (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
        discuss();
      }
    });

    if (modelSelect) {
      modelSelect.addEventListener('change', (event) => {
        selectedModel = event.target.value;
        console.log('[DiscussAI] Model changed to:', selectedModel);
      });
    }
  };

  let aiDiscussInitialized = false;

  const init = () => {
    document.documentElement.classList.remove('no-js');

    const panel = document.getElementById('ai-discuss-panel');
    if (panel) {
      panel.classList.remove('open');
      panel.setAttribute('aria-hidden', 'true');

      // Clear output on page change
      const output = document.getElementById('ai-output');
      if (output) {
        output.textContent = '';
        output.style.color = '';
      }
    }
    document.body.classList.remove('ai-panel-open');

    updateHeaderOffset();
    window.removeEventListener('resize', updateHeaderOffset);
    window.addEventListener('resize', updateHeaderOffset, { passive: true });
    window.addEventListener('load', updateHeaderOffset, { once: true });

    initScrollRestoration();
    initHeader();
    initNav();
    updateReadingTimers();
    initIntersectionObserver();
    buildTOC();
    observeAnchors();
    smoothScrollAnchors();
    disableSwupOnSpecialPages();

    // Only initialize AI discuss once (button is outside #swup container)
    if (!aiDiscussInitialized) {
      setupAiDiscuss();
      aiDiscussInitialized = true;
    }
  };

  return { init };
})();

const AilinuxNovaTransitions = (() => {
  let swupInstance = null;
  let reinitRaf = null;

  const initSwup = () => {
    if (!window.Swup || swupInstance) {
      return;
    }

    swupInstance = new window.Swup({
      containers: ['#swup'],
      animateHistoryBrowsing: true,
      linkSelector: [
        `a[href^="/"]:not([data-no-swup]):not([target])`,
        `a[href^="${window.location.origin}"]:not([data-no-swup]):not([target])`
      ].join(', '),
      animationSelector: '[class*="transition-"]'
    });

    swupInstance.hooks.on('page:view', () => {
      if (reinitRaf) cancelAnimationFrame(reinitRaf);
      reinitRaf = requestAnimationFrame(() => AilinuxNovaApp.init());
    });
  };

  return { initSwup };
})();

document.addEventListener('DOMContentLoaded', () => {
  AilinuxNovaApp.init();
  AilinuxNovaTransitions.initSwup();
});
