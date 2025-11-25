/**
 * Scroll-to-Top Button Functionality
 * Shows a button when user scrolls down, clicking scrolls back to top
 */
(function() {
    'use strict';

    const scrollTopBtn = document.getElementById('scroll-top');
    const scrollThreshold = 300; // Show button after scrolling 300px

    if (!scrollTopBtn) return;

    // Check scroll position and toggle button visibility
    function toggleScrollButton() {
        if (window.scrollY > scrollThreshold) {
            scrollTopBtn.classList.add('visible');
        } else {
            scrollTopBtn.classList.remove('visible');
        }
    }

    // Scroll to top when button is clicked
    function scrollToTop() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    }

    // Event listeners
    window.addEventListener('scroll', toggleScrollButton, { passive: true });
    scrollTopBtn.addEventListener('click', scrollToTop);

    // Initial check in case page loads scrolled
    toggleScrollButton();
})();
