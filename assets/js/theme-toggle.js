// Theme Toggle Functionality for Fr. Conor Meditations
(function() {
  const STORAGE_KEY = 'theme-preference';

  // Get theme preference
  function getThemePreference() {
    // Check localStorage first
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return stored;
    }

    // Fallback to system preference
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }

    return 'light';
  }

  // Apply theme
  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    updateIcon(theme);

    // Announce to screen readers
    const message = theme === 'dark' ? 'Dark mode enabled' : 'Light mode enabled';
    announceToScreenReader(message);
  }

  // Update icon
  function updateIcon(theme) {
    const icon = document.getElementById('theme-icon');
    if (!icon) return;

    const sun = icon.querySelector('.sun');
    const moon = icon.querySelector('.moon');

    if (theme === 'dark') {
      if (sun) sun.style.display = 'block';
      if (moon) moon.style.display = 'none';
    } else {
      if (sun) sun.style.display = 'none';
      if (moon) moon.style.display = 'block';
    }
  }

  // Toggle theme
  function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';

    localStorage.setItem(STORAGE_KEY, newTheme);
    applyTheme(newTheme);
  }

  // Screen reader announcement
  function announceToScreenReader(message) {
    const announcement = document.createElement('div');
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', 'polite');
    announcement.classList.add('sr-only');
    announcement.textContent = message;
    document.body.appendChild(announcement);

    setTimeout(() => {
      document.body.removeChild(announcement);
    }, 1000);
  }

  // Initialize on DOM load
  document.addEventListener('DOMContentLoaded', function() {
    const theme = getThemePreference();
    applyTheme(theme);

    // Add click listener
    const toggleButton = document.getElementById('theme-toggle');
    if (toggleButton) {
      toggleButton.addEventListener('click', toggleTheme);
    }

    // Listen for system theme changes
    if (window.matchMedia) {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        // Only update if user hasn't set a preference
        if (!localStorage.getItem(STORAGE_KEY)) {
          applyTheme(e.matches ? 'dark' : 'light');
        }
      });
    }
  });
})();
