(function (wp) {
  if (!wp || !wp.customize) {
    return;
  }

  const body = document.body;
  const root = document.documentElement;

  wp.customize('ailinux_nova_dark_accent', (value) => {
    value.bind((newValue) => {
      body.classList.remove('accent-blue', 'accent-green');
      body.classList.add(newValue);
    });
  });

  wp.customize('ailinux_nova_dark_hero_layout', (value) => {
    value.bind((newValue) => {
      body.classList.remove('hero-layout-grid', 'hero-layout-list');
      body.classList.add(`hero-layout-${newValue}`);
    });
  });

  wp.customize('ailinux_nova_dark_card_density', (value) => {
    value.bind((newValue) => {
      body.classList.remove('card-density-airy', 'card-density-compact');
      body.classList.add(`card-density-${newValue}`);
    });
  });

  // Dark Mode Colors
  const darkColors = {
    'ailinux_nova_dark_color_bg_0_dark': '--bg-0',
    'ailinux_nova_dark_color_bg_1_dark': '--bg-1',
    'ailinux_nova_dark_color_bg_2_dark': '--bg-2',
    'ailinux_nova_dark_color_text_dark': '--text',
    'ailinux_nova_dark_color_muted_dark': '--muted',
  };

  Object.entries(darkColors).forEach(([settingId, varName]) => {
    wp.customize(settingId, (value) => {
      value.bind((newValue) => {
        root.style.setProperty(varName, newValue);
      });
    });
  });

  // Light Mode Colors
  const lightColors = {
    'ailinux_nova_dark_color_bg_0_light': '--bg-0',
    'ailinux_nova_dark_color_bg_1_light': '--bg-1',
    'ailinux_nova_dark_color_bg_2_light': '--bg-2',
    'ailinux_nova_dark_color_text_light': '--text',
    'ailinux_nova_dark_color_muted_light': '--muted',
  };

  Object.entries(lightColors).forEach(([settingId, varName]) => {
    wp.customize(settingId, (value) => {
      value.bind((newValue) => {
        document.querySelector('html[data-theme="light"]').style.setProperty(varName, newValue);
      });
    });
  });

  // Typography
  wp.customize('ailinux_nova_dark_font_sans', (value) => {
    value.bind((newValue) => {
      root.style.setProperty('--font-sans', `'${newValue}', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`);
    });
  });

  wp.customize('ailinux_nova_dark_font_mono', (value) => {
    value.bind((newValue) => {
      root.style.setProperty('--font-mono', `'${newValue}', 'Fira Code', ui-monospace, SFMono-Regular, monospace`);
    });
  });

})(window.wp || {});
