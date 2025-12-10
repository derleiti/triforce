(() => {
  const toggleButton = document.getElementById('mobile-menu-toggle');
  const mobileNavPanel = document.getElementById('mobile-nav-panel');
  const mobileNavOverlay = document.getElementById('mobile-nav-overlay');

  if (!toggleButton || !mobileNavPanel || !mobileNavOverlay) {
    return;
  }

  const toggleMenu = () => {
    const isOpen = mobileNavPanel.classList.contains('is-open');
    mobileNavPanel.classList.toggle('is-open');
    mobileNavOverlay.classList.toggle('is-open');
    toggleButton.classList.toggle('is-active');
    toggleButton.setAttribute('aria-expanded', !isOpen);

    // Verhindere Body-Scroll wenn Menü offen ist
    document.body.style.overflow = isOpen ? '' : 'hidden';
  };

  toggleButton.addEventListener('click', toggleMenu);
  mobileNavOverlay.addEventListener('click', toggleMenu);

  const menuItemsWithChildren = mobileNavPanel.querySelectorAll('.menu-item-has-children > a');

  menuItemsWithChildren.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const parent = item.parentElement;
      parent.classList.toggle('is-open');
    });
  });

  // Schließe Menü bei Escape-Taste
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && mobileNavPanel.classList.contains('is-open')) {
      toggleMenu();
    }
  });
})();
