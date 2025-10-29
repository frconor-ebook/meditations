// Copy link to clipboard functionality
function copyLinkToClipboard(event) {
    event.preventDefault();
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
        }
    } catch (err) {
        console.error('Copy failed:', err);
    }

    document.body.removeChild(textArea);
}

// Show notification that link was copied
function showCopyNotification() {
    const notification = document.getElementById('copy-notification');
    if (notification) {
        notification.classList.add('show');

        // Hide notification after 2 seconds
        setTimeout(() => {
            notification.classList.remove('show');
        }, 2000);
    }
}
