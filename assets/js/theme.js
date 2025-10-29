// Theme toggle functionality
(function() {
    // Check for saved theme preference, default to light mode
    const savedTheme = localStorage.getItem('theme') || 'light';

    // Apply the theme on page load
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode');
    }

    // Update button text based on current theme
    function updateButtonText() {
        const themeBtn = document.getElementById('theme-toggle-btn');
        if (themeBtn) {
            if (document.body.classList.contains('dark-mode')) {
                themeBtn.textContent = 'Light Mode';
            } else {
                themeBtn.textContent = 'Dark Mode';
            }
        }
    }

    // Initialize button text when DOM is loaded
    document.addEventListener('DOMContentLoaded', function() {
        updateButtonText();
    });

    // Toggle theme function
    window.toggleTheme = function() {
        document.body.classList.toggle('dark-mode');

        // Save preference to localStorage
        if (document.body.classList.contains('dark-mode')) {
            localStorage.setItem('theme', 'dark');
        } else {
            localStorage.setItem('theme', 'light');
        }

        // Update button text
        updateButtonText();
    };
})();
