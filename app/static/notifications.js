/**
 * Notification System Module
 * A reusable notification system for showing success, error, info, and warning messages
 */

const Notifications = {
    // Configuration
    config: {
        position: 'top-right', // top-right, top-left, bottom-right, bottom-left
        autoHide: true,
        autoHideDelay: 5000, // 5 seconds
        maxNotifications: 5
    },

    // Initialize the notification system
    init: function(customConfig = {}) {
        // Merge custom config with defaults
        this.config = { ...this.config, ...customConfig };
        
        // Add CSS styles if not already present
        this.addStyles();
        
        // Create container if it doesn't exist
        this.createContainer();
    },

    // Add required CSS styles
    addStyles: function() {
        if (document.querySelector('#notification-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'notification-styles';
        style.textContent = `
            .notification-container {
                position: fixed;
                z-index: 9999;
                pointer-events: none;
                max-width: 400px;
            }
            
            .notification-container.top-right {
                top: 20px;
                right: 20px;
            }
            
            .notification-container.top-left {
                top: 20px;
                left: 20px;
            }
            
            .notification-container.bottom-right {
                bottom: 20px;
                right: 20px;
            }
            
            .notification-container.bottom-left {
                bottom: 20px;
                left: 20px;
            }
            
            .notification-item {
                pointer-events: auto;
                margin-bottom: 10px;
                min-width: 300px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                border-radius: 6px;
                overflow: hidden;
            }
            
            .notification-item.notification-enter {
                animation: notificationSlideIn 0.3s ease-out;
            }
            
            .notification-item.notification-exit {
                animation: notificationSlideOut 0.3s ease-in;
            }
            
            @keyframes notificationSlideIn {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            
            @keyframes notificationSlideOut {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(100%);
                    opacity: 0;
                }
            }
            
            .notification-item .alert {
                margin: 0;
                border: none;
                border-radius: 6px;
            }
            
            .notification-progress {
                height: 3px;
                background: rgba(255,255,255,0.3);
                position: absolute;
                bottom: 0;
                left: 0;
                right: 0;
                border-radius: 0 0 6px 6px;
            }
            
            .notification-progress-bar {
                height: 100%;
                background: rgba(255,255,255,0.8);
                transition: width linear;
                border-radius: 0 0 6px 6px;
            }
        `;
        document.head.appendChild(style);
    },

    // Create notification container
    createContainer: function() {
        let container = document.querySelector('.notification-container');
        if (!container) {
            container = document.createElement('div');
            container.className = `notification-container ${this.config.position}`;
            document.body.appendChild(container);
        }
        return container;
    },

    // Show notification
    show: function(message, type = 'info', options = {}) {
        const config = { ...this.config, ...options };
        const container = this.createContainer();
        
        // Limit number of notifications
        const existingNotifications = container.querySelectorAll('.notification-item');
        if (existingNotifications.length >= this.config.maxNotifications) {
            existingNotifications[0].remove();
        }
        
        // Create notification element
        const notification = this.createElement(message, type, config);
        
        // Add to container with animation
        notification.classList.add('notification-enter');
        container.appendChild(notification);
        
        // Auto-hide if enabled
        if (config.autoHide) {
            this.scheduleRemoval(notification, config.autoHideDelay);
        }
        
        return notification;
    },

    // Create notification element
    createElement: function(message, type, config) {
        const notification = document.createElement('div');
        notification.className = 'notification-item';
        
        const typeConfig = this.getTypeConfig(type);
        
        notification.innerHTML = `
            <div class="alert alert-${typeConfig.bootstrapClass} alert-dismissible" role="alert">
                <i class="fas fa-${typeConfig.icon}"></i>
                ${message}
                <button type="button" class="btn-close" aria-label="Close"></button>
            </div>
            ${config.autoHide ? '<div class="notification-progress"><div class="notification-progress-bar"></div></div>' : ''}
        `;
        
        // Add close button handler
        const closeBtn = notification.querySelector('.btn-close');
        closeBtn.addEventListener('click', () => this.remove(notification));
        
        return notification;
    },

    // Get type configuration
    getTypeConfig: function(type) {
        const configs = {
            success: { bootstrapClass: 'success', icon: 'check-circle' },
            error: { bootstrapClass: 'danger', icon: 'exclamation-triangle' },
            warning: { bootstrapClass: 'warning', icon: 'exclamation-circle' },
            info: { bootstrapClass: 'info', icon: 'info-circle' }
        };
        return configs[type] || configs.info;
    },

    // Schedule notification removal
    scheduleRemoval: function(notification, delay) {
        const progressBar = notification.querySelector('.notification-progress-bar');
        
        if (progressBar) {
            // Animate progress bar
            progressBar.style.width = '100%';
            progressBar.style.transitionDuration = `${delay}ms`;
            
            // Start countdown
            setTimeout(() => {
                progressBar.style.width = '0%';
            }, 10);
        }
        
        // Remove after delay
        setTimeout(() => {
            if (notification.parentNode) {
                this.remove(notification);
            }
        }, delay);
    },

    // Remove notification with animation
    remove: function(notification) {
        notification.classList.add('notification-exit');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 300);
    },

    // Convenience methods
    success: function(message, options = {}) {
        return this.show(message, 'success', options);
    },

    error: function(message, options = {}) {
        return this.show(message, 'error', options);
    },

    warning: function(message, options = {}) {
        return this.show(message, 'warning', options);
    },

    info: function(message, options = {}) {
        return this.show(message, 'info', options);
    },

    // Clear all notifications
    clear: function() {
        const container = document.querySelector('.notification-container');
        if (container) {
            container.innerHTML = '';
        }
    }
};

// Auto-initialize when loaded
document.addEventListener('DOMContentLoaded', () => {
    Notifications.init();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Notifications;
} else {
    window.Notifications = Notifications;
}
