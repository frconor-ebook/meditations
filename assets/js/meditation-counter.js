// Meditation Counter - Tracks reading progress
(function() {
  const STORAGE_KEY = 'meditations-read';
  const READ_DELAY_MS = 10000; // 10 seconds before counting as read

  // Get list of read meditations from localStorage
  function getReadList() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch (e) {
      return [];
    }
  }

  // Save read list to localStorage
  function saveReadList(list) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
    } catch (e) {
      console.warn('Could not save reading progress');
    }
  }

  // Check if meditation was already read
  function isAlreadyRead(slug) {
    const list = getReadList();
    return list.some(item => item.slug === slug);
  }

  // Mark meditation as read
  function markAsRead(slug, title) {
    if (isAlreadyRead(slug)) return;

    const list = getReadList();
    list.push({
      slug: slug,
      title: title,
      readAt: new Date().toISOString()
    });
    saveReadList(list);
    updateBadgeCount();
    announceToScreenReader(`"${title}" added to your reading list`);
  }

  // Update the badge count display
  function updateBadgeCount() {
    const countElement = document.getElementById('counter-number');
    if (countElement) {
      const count = getReadList().length;
      countElement.textContent = count;
    }
  }

  // Check if current page is a meditation (homily) page
  function isHomily() {
    return window.location.pathname.includes('/homilies/');
  }

  // Get meditation slug from URL
  function getSlugFromUrl() {
    const path = window.location.pathname;
    const match = path.match(/\/homilies\/([^\/]+)/);
    return match ? match[1].replace(/\/$/, '') : null;
  }

  // Get meditation title from page
  function getTitleFromPage() {
    const h1 = document.querySelector('article h1');
    return h1 ? h1.textContent.trim() : null;
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
      if (announcement.parentNode) {
        document.body.removeChild(announcement);
      }
    }, 1000);
  }

  // Render the reading list modal
  function renderModal() {
    const list = getReadList();
    const baseurl = document.body.dataset.baseurl || '';

    // Sort by most recent first
    list.sort((a, b) => new Date(b.readAt) - new Date(a.readAt));

    let listHTML = '';
    if (list.length === 0) {
      listHTML = '<p class="modal-empty">No meditations read yet. Start reading to track your progress!</p>';
    } else {
      listHTML = '<ul class="reading-list">';
      list.forEach(item => {
        const date = new Date(item.readAt).toLocaleDateString();
        listHTML += `
          <li>
            <a href="${baseurl}/homilies/${item.slug}/">${item.title}</a>
            <span class="read-date">${date}</span>
          </li>
        `;
      });
      listHTML += '</ul>';
      listHTML += '<div class="modal-footer"><button id="clear-history" class="clear-history-btn">Clear History</button></div>';
    }

    const modal = document.getElementById('reading-list-modal');
    const modalContent = document.getElementById('reading-list-content');
    if (modal && modalContent) {
      modalContent.innerHTML = listHTML;
      modal.classList.add('active');
      modal.setAttribute('aria-hidden', 'false');
      document.body.style.overflow = 'hidden';

      // Attach clear history button handler
      const clearBtn = document.getElementById('clear-history');
      if (clearBtn) {
        clearBtn.addEventListener('click', clearHistory);
      }

      // Focus the close button for accessibility
      const closeBtn = document.getElementById('modal-close');
      if (closeBtn) closeBtn.focus();
    }
  }

  // Close the modal
  function closeModal() {
    const modal = document.getElementById('reading-list-modal');
    if (modal) {
      modal.classList.remove('active');
      modal.setAttribute('aria-hidden', 'true');
      document.body.style.overflow = '';

      // Return focus to badge
      const badge = document.getElementById('counter-badge');
      if (badge) badge.focus();
    }
  }

  // Clear all reading history
  function clearHistory() {
    if (confirm('Are you sure you want to clear your reading history? This cannot be undone.')) {
      localStorage.removeItem(STORAGE_KEY);
      updateBadgeCount();
      renderModal(); // Re-render to show empty state
      announceToScreenReader('Reading history cleared');
    }
  }

  // Initialize on DOM load
  document.addEventListener('DOMContentLoaded', function() {
    // Update badge count on every page
    updateBadgeCount();

    // Track reading on homily pages
    if (isHomily()) {
      const slug = getSlugFromUrl();
      const title = getTitleFromPage();

      if (slug && title && !isAlreadyRead(slug)) {
        // Start timer - mark as read after 10 seconds
        setTimeout(() => {
          markAsRead(slug, title);
        }, READ_DELAY_MS);
      }
    }

    // Badge click handler - open modal
    const badge = document.getElementById('counter-badge');
    if (badge) {
      badge.addEventListener('click', renderModal);
    }

    // Modal close handlers
    const closeBtn = document.getElementById('modal-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', closeModal);
    }

    const modalOverlay = document.getElementById('reading-list-modal');
    if (modalOverlay) {
      modalOverlay.addEventListener('click', function(e) {
        if (e.target === modalOverlay) {
          closeModal();
        }
      });
    }

    // Close modal on Escape key
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        closeModal();
      }
    });
  });
})();
