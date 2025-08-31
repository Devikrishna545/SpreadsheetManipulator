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
        
        modalTitle.innerHTML = `<i class="fas ${getIconForType(type)} me-2 text-${getColorForType(type)}"></i>${title}`;
        modalBody.textContent = message;
        
        const bootstrapModal = new bootstrap.Modal(modal);
        
        const handleClose = () => {
            modal.removeEventListener('hidden.bs.modal', handleClose);
            resolve();
        };
        
        modal.addEventListener('hidden.bs.modal', handleClose);
        bootstrapModal.show();
    });
}

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
        
        const config = {
            confirmText: 'Confirm',
            cancelText: 'Cancel',
            confirmClass: 'btn-primary',
            ...options
        };
        
        modalTitle.innerHTML = `<i class="fas fa-question-circle me-2 text-info"></i>${title}`;
        modalBody.textContent = message;
        
        let confirmIcon = '';
        if (config.confirmText.toLowerCase().includes('execute')) {
            confirmIcon = '<i class="fas fa-play me-2"></i>';
        } else if (config.confirmText.toLowerCase().includes('delete')) {
            confirmIcon = '<i class="fas fa-trash me-2"></i>';
        } else if (config.confirmText.toLowerCase().includes('save') || config.confirmText.toLowerCase().includes('create')) {
            confirmIcon = '<i class="fas fa-save me-2"></i>';
        } else if (config.confirmText.toLowerCase().includes('continue')) {
            confirmIcon = '<i class="fas fa-arrow-right me-2"></i>';
        } else {
            confirmIcon = '<i class="fas fa-check me-2"></i>';
        }
        
        confirmBtn.innerHTML = `${confirmIcon}${config.confirmText}`;
        cancelBtn.innerHTML = `<i class="fas fa-times me-2"></i>${config.cancelText}`;
        confirmBtn.className = `btn ${config.confirmClass}`;
        
        const bootstrapModal = new bootstrap.Modal(modal);
        
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
        
        confirmBtn.addEventListener('click', handleConfirm);
        cancelBtn.addEventListener('click', handleCancel);
        modal.addEventListener('hidden.bs.modal', handleModalClose);
        
        bootstrapModal.show();
    });
}

export function showErrorModal(message, title = 'Error') {
    const modal = document.getElementById('errorModal');
    const modalTitle = document.getElementById('errorModalLabel');
    const modalBody = document.getElementById('errorModalBody');
    
    if (!modal) {
        console.error('Error modal not found:', `Error: ${message}`);
        return;
    }
    
    modalTitle.innerHTML = `<i class="fas fa-exclamation-triangle me-2 text-warning"></i>${title}`;
    modalBody.textContent = message;
    
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
}

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

export function replaceGlobalAlert() {
    window.alert = showAlert;
}

export function replaceGlobalConfirm() {
    window.confirm = showConfirm;
}
