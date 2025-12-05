document.documentElement.classList.remove('no-js');
(() => {
  const storageKey = 'ailinux-nova-color-mode';
  const html = document.documentElement;

  const getSystemPreference = () => (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');

  const getSavedPreference = () => {
    try {
      return localStorage.getItem(storageKey);
    } catch (error) {
      return null;
    }
  };

  const applyTheme = (theme) => {
    const resolved = theme || getSystemPreference();
    html.setAttribute('data-theme', resolved);
    const bodyEl = document.body;
    if (bodyEl) {
      bodyEl.dataset.theme = resolved;
    }
  };

  const saveTheme = (theme) => {
    try {
      localStorage.setItem(storageKey, theme);
    } catch (error) {
      /* storage disabled */
    }
  };

  const initToggle = () => {
    const toggle = document.querySelector('.mode-toggle');
    if (!toggle) return;

    const syncState = () => {
      const current = html.getAttribute('data-theme') || 'dark';
      toggle.setAttribute('aria-pressed', current === 'light' ? 'true' : 'false');
    };

    syncState();

    toggle.addEventListener('click', () => {
      const now = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      applyTheme(now);
      saveTheme(now);
      syncState();
    });
  };

  const init = () => {
    const saved = getSavedPreference();
    applyTheme(saved);

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => {
        applyTheme(saved);
        initToggle();
      }, { once: true });
    } else {
      initToggle();
    }

    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = () => {
      if (!getSavedPreference()) {
        applyTheme(null);
      }
    };

    if (media.addEventListener) {
      media.addEventListener('change', handleChange);
    } else if (media.addListener) {
      media.addListener(handleChange);
    }
  };

  init();
})();