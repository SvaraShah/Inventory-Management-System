document.addEventListener('DOMContentLoaded', () => {
    // 1. Flash Messages Auto-hide
    const flashMessages = document.querySelectorAll('.flash-message');
    if (flashMessages.length > 0) {
        setTimeout(() => {
            flashMessages.forEach(msg => {
                msg.style.transform = 'translateX(100%)';
                msg.style.opacity = '0';
                setTimeout(() => { msg.remove(); }, 300);
            });
        }, 5000);
    }
});
