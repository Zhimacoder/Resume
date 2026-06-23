/**
 * Toast 提示组件
 * 替代原生 alert()，提供更友好的提示体验
 */

const Toast = (function() {
    const DEFAULT_DURATION = 3000;

    function ensureContainer() {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
        return container;
    }

    function show(message, type, duration) {
        const container = ensureContainer();
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;

        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ'
        };

        toast.innerHTML = `
            <span class="toast-icon">${icons[type] || icons.info}</span>
            <span class="toast-message"></span>
        `;
        toast.querySelector('.toast-message').textContent = message;

        container.appendChild(toast);

        requestAnimationFrame(() => {
            toast.classList.add('toast-show');
        });

        const dur = duration || DEFAULT_DURATION;
        if (dur > 0) {
            setTimeout(() => {
                removeToast(toast);
            }, dur);
        }

        return toast;
    }

    function removeToast(toast) {
        toast.classList.remove('toast-show');
        toast.classList.add('toast-hide');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }

    return {
        success: function(msg, dur) { return show(msg, 'success', dur); },
        error: function(msg, dur) { return show(msg, 'error', dur); },
        warning: function(msg, dur) { return show(msg, 'warning', dur); },
        info: function(msg, dur) { return show(msg, 'info', dur); }
    };
})();

window.Toast = Toast;
