// Text Size Toggle Functionality for Fr. Conor Meditations
(function() {
  const STORAGE_KEY = 'text-size-preference';

  // Get text size preference
  function getTextSizePreference() {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'large') {
      return 'large';
    }
    return 'normal';
  }

  // Apply text size
  function applyTextSize(size) {
    if (size === 'large') {
      document.documentElement.setAttribute('data-text-size', 'large');
    } else {
      document.documentElement.removeAttribute('data-text-size');
    }
    updateButtons(size);
  }

  // Update button active states
  function updateButtons(size) {
    const normalBtn = document.getElementById('text-size-normal');
    const largeBtn = document.getElementById('text-size-large');

    if (!normalBtn || !largeBtn) return;

    if (size === 'large') {
      normalBtn.classList.remove('active');
      largeBtn.classList.add('active');
    } else {
      normalBtn.classList.add('active');
      largeBtn.classList.remove('active');
    }
  }

  // Set text size
  function setTextSize(size) {
    localStorage.setItem(STORAGE_KEY, size);
    applyTextSize(size);

    // Announce to screen readers
    const message = size === 'large' ? 'Large text enabled' : 'Normal text size';
    announceToScreenReader(message);
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
    const size = getTextSizePreference();
    applyTextSize(size);

    // Add click listeners
    const normalBtn = document.getElementById('text-size-normal');
    const largeBtn = document.getElementById('text-size-large');

    if (normalBtn) {
      normalBtn.addEventListener('click', function() {
        setTextSize('normal');
      });
    }

    if (largeBtn) {
      largeBtn.addEventListener('click', function() {
        setTextSize('large');
      });
    }
  });
})();
