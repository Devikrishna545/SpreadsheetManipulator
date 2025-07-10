/**
 * Modal Utilities Module
 * Provides modern modal-based replacements for alert() and confirm()
 */

/**
 * Show an alert modal instead of browser alert()
 * @param {string} message - The message to display
 * @param {string} title - Optional title for the modal
 * @param {string} type - Optional type for styling ('info', 'warning', 'error', 'success')
 * @returns {Promise} Promise that resolves when modal is closed
 */
export function showAlert(message, title = 'Information', type = 'info') {
    return new Promise((resolve) => {
        const modal = document.getElementById('alertModal');
        const modalTitle = document.getElementById('alertModalLabel');
        const modalBody = document.getElementById('alertModalBody');
        const modalIcon = modalTitle.querySelector('i');
        
        if (!modal) {
            console.error('Alert modal not found:', message);
            resolve();
            return;
        }
        
        // Set title and message
        modalTitle.innerHTML = `<i class="fas ${getIconForType(type)} me-2 text-${getColorForType(type)}"></i>${title}`;
        modalBody.textContent = message;
        
        // Show the modal
        const bootstrapModal = new bootstrap.Modal(modal);
        
        // Handle modal close
        const handleClose = () => {
            modal.removeEventListener('hidden.bs.modal', handleClose);
            resolve();
        };
        
        modal.addEventListener('hidden.bs.modal', handleClose);
        bootstrapModal.show();
    });
}

/**
 * Show a confirmation modal instead of browser confirm()
 * @param {string} message - The message to display
 * @param {string} title - Optional title for the modal
 * @param {Object} options - Optional configuration
 * @param {string} options.confirmText - Text for confirm button (default: 'Confirm')
 * @param {string} options.cancelText - Text for cancel button (default: 'Cancel')
 * @param {string} options.confirmClass - CSS class for confirm button (default: 'btn-primary')
 * @returns {Promise<boolean>} Promise that resolves to true if confirmed, false if cancelled
 */
export function showConfirm(message, title = 'Confirmation', options = {}) {
    return new Promise((resolve) => {
        const modal = document.getElementById('confirmModal');
        const modalTitle = document.getElementById('confirmModalLabel');
        const modalBody = document.getElementById('confirmModalBody');
        const confirmBtn = document.getElementById('confirmModalConfirmBtn');
        const cancelBtn = document.getElementById('confirmModalCancelBtn');
        
        if (!modal) {
            console.error('Confirm modal not found:', message);
            resolve(false);
            return;
        }
        
        // Set default options
        const config = {
            confirmText: 'Confirm',
            cancelText: 'Cancel',
            confirmClass: 'btn-primary',
            ...options
        };
        
        // Set title and message
        modalTitle.innerHTML = `<i class="fas fa-question-circle me-2 text-info"></i>${title}`;
        modalBody.textContent = message;
        
        // Set button texts and styles
        confirmBtn.textContent = config.confirmText;
        cancelBtn.textContent = config.cancelText;
        confirmBtn.className = `btn ${config.confirmClass}`;
        
        // Show the modal
        const bootstrapModal = new bootstrap.Modal(modal);
        
        // Handle button clicks
        const handleConfirm = () => {
            cleanup();
            bootstrapModal.hide();
            resolve(true);
        };
        
        const handleCancel = () => {
            cleanup();
            bootstrapModal.hide();
            resolve(false);
        };
        
        const handleModalClose = () => {
            cleanup();
            resolve(false);
        };
        
        const cleanup = () => {
            confirmBtn.removeEventListener('click', handleConfirm);
            cancelBtn.removeEventListener('click', handleCancel);
            modal.removeEventListener('hidden.bs.modal', handleModalClose);
        };
        
        // Add event listeners
        confirmBtn.addEventListener('click', handleConfirm);
        cancelBtn.addEventListener('click', handleCancel);
        modal.addEventListener('hidden.bs.modal', handleModalClose);
        
        bootstrapModal.show();
    });
}

/**
 * Show an error modal
 * @param {string} message - The error message to display
 * @param {string} title - Optional title for the modal
 */
export function showErrorModal(message, title = 'Error') {
    const modal = document.getElementById('errorModal');
    const modalTitle = document.getElementById('errorModalLabel');
    const modalBody = document.getElementById('errorModalBody');
    
    if (!modal) {
        console.error('Error modal not found:', `Error: ${message}`);
        return;
    }
    
    // Set title and message
    modalTitle.innerHTML = `<i class="fas fa-exclamation-triangle me-2 text-warning"></i>${title}`;
    modalBody.textContent = message;
    
    // Show the modal
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
}

/**
 * Get appropriate icon for alert type
 * @param {string} type - The alert type
 * @returns {string} Font Awesome icon class
 */
function getIconForType(type) {
    switch (type) {
        case 'error':
            return 'fa-exclamation-triangle';
        case 'warning':
            return 'fa-exclamation-triangle';
        case 'success':
            return 'fa-check-circle';
        case 'info':
        default:
            return 'fa-info-circle';
    }
}

/**
 * Get appropriate color for alert type
 * @param {string} type - The alert type
 * @returns {string} Bootstrap color class
 */
function getColorForType(type) {
    switch (type) {
        case 'error':
            return 'danger';
        case 'warning':
            return 'warning';
        case 'success':
            return 'success';
        case 'info':
        default:
            return 'primary';
    }
}

/**
 * Replace the global alert function with modal version
 * Call this to override the browser's alert globally
 */
export function replaceGlobalAlert() {
    window.alert = showAlert;
}

/**
 * Replace the global confirm function with modal version
 * Call this to override the browser's confirm globally
 */
export function replaceGlobalConfirm() {
    window.confirm = showConfirm;
}
