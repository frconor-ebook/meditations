// Copy link to clipboard functionality
function copyLinkToClipboard() {
    const currentUrl = window.location.href;

    // Try modern clipboard API first
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(currentUrl)
            .then(() => {
                showCopyNotification();
            })
            .catch(err => {
                // Fallback if clipboard API fails
                fallbackCopyToClipboard(currentUrl);
            });
    } else {
        // Fallback for older browsers
        fallbackCopyToClipboard(currentUrl);
    }
}

// Fallback copy method for older browsers
function fallbackCopyToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
        const successful = document.execCommand('copy');
        if (successful) {
            showCopyNotification();
        } else {
            console.error('Copy command failed');
            alert('Failed to copy link. Please copy manually: ' + text);
        }
    } catch (err) {
        console.error('Copy failed:', err);
        alert('Failed to copy link. Please copy manually: ' + text);
    }

    document.body.removeChild(textArea);
}

// Show notification that link was copied
function showCopyNotification() {
    // Find all copy notifications on the page (top and bottom)
    const notifications = document.querySelectorAll('#copy-notification');
    const copyButtons = document.querySelectorAll('.copy-link');

    // Show notifications
    notifications.forEach(notification => {
        notification.classList.remove('hidden');
    });

    // Change button appearance
    copyButtons.forEach(button => {
        button.classList.add('copied');
        const buttonText = button.querySelector('.copy-text');
        const originalText = buttonText.textContent;
        buttonText.textContent = 'Copied!';

        // Reset after 3 seconds
        setTimeout(() => {
            buttonText.textContent = originalText;
            button.classList.remove('copied');
        }, 3000);
    });

    // Hide notifications after 3 seconds
    setTimeout(() => {
        notifications.forEach(notification => {
            notification.classList.add('hidden');
        });
    }, 3000);
}
