// DOM Elements
const sidebar = document.getElementById('sidebar');
const sidebarToggleBtn = document.getElementById('sidebarToggleBtn');
const spreadsheetContainer = document.getElementById('spreadsheetContainer');
const commandContainer = document.getElementById('commandContainer');
const sessionInfo = document.getElementById('sessionInfo');
const statusBadge = document.getElementById('statusBadge');
const loadingContainer = document.getElementById('loadingContainer');
const loadingMessage = document.getElementById('loadingMessage');

// Bootstrap Modal initialization
let errorModal;
let errorModalBody;
try {
    const errorModalElement = document.getElementById('errorModal');
    if (window.bootstrap && errorModalElement) {
        errorModal = new bootstrap.Modal(errorModalElement);
        errorModalBody = document.getElementById('errorModalBody');
    }
} catch (e) {
    console.warn('Bootstrap Modal initialization failed:', e);
}

const uploadForm = document.getElementById('uploadForm');
const fileNameDisplay = document.getElementById('fileName');
const sessionStatusDisplay = document.getElementById('sessionStatus');
const fullscreenBtn = document.getElementById('fullscreenBtn');

// Handsontable render scheduler
let _pendingHotRender = false;
function scheduleHotRender() {
    if (_pendingHotRender) return;
    _pendingHotRender = true;
    requestAnimationFrame(() => {
        _pendingHotRender = false;
        if (window.hotInstance) {
            window.hotInstance.render();
        }
        if (window.editableHotInstance) {
            window.editableHotInstance.render();
        }
    });
}

// Command container observer
let _commandContainerObserver;
let _commandInputMinHeightSet = false;

export function toggleSidebar() {
    sidebar.classList.toggle('collapsed');
    const icon = sidebarToggleBtn.querySelector('i');
    if (sidebar.classList.contains('collapsed')) {
        icon.classList.remove('fa-bars');
        icon.classList.add('fa-arrow-right');
        sidebarToggleBtn.title = "Expand Sidebar";
    } else {
        icon.classList.remove('fa-arrow-right');
        icon.classList.add('fa-bars');
        sidebarToggleBtn.title = "Collapse Sidebar";
    }
    
    if (window.hotInstance && spreadsheetContainer.style.display !== 'none') {
        setTimeout(() => {
            window.hotInstance.render();
        }, 350);
    }
}

export function toggleFullscreen() {
    const spreadsheetCard = spreadsheetContainer.querySelector('.spreadsheet-card');
    const icon = fullscreenBtn.querySelector('i');
    
    if (spreadsheetCard.classList.contains('fullscreen')) {
        spreadsheetCard.classList.remove('fullscreen');
        icon.classList.remove('fa-compress');
        icon.classList.add('fa-expand');
        fullscreenBtn.title = 'Enter Fullscreen';
    } else {
        spreadsheetCard.classList.add('fullscreen');
        icon.classList.remove('fa-expand');
        icon.classList.add('fa-compress');
        fullscreenBtn.title = 'Exit Fullscreen';
    }
    
    if (window.hotInstance) {
        setTimeout(() => {
            window.hotInstance.render();
        }, 100);
    }
    
    if (window.editableHotInstance) {
        setTimeout(() => {
            window.editableHotInstance.render();
        }, 100);
    }
}

export function updateStatus(message, type = 'active') {
    statusBadge.textContent = message;
    statusBadge.className = `status-badge status-${type}`;
}

export function showLoading(message = 'Loading...') {
    loadingMessage.textContent = message;
    loadingContainer.style.display = 'flex';
}

export function showAlgorithmLoading(message = 'Generating algorithm...') {
    loadingMessage.textContent = message;
    loadingContainer.style.display = 'flex';
}

export function hideLoading() {
    loadingContainer.style.display = 'none';
}

export function showError(message) {
    if (errorModal && errorModalBody) {
        errorModalBody.textContent = message;
        errorModal.show();
    } else {
        console.error('UI Error:', message);
    }
}

export function showMainInterface() {
    spreadsheetContainer.style.display = 'block';
    commandContainer.style.display = 'block';
    sessionInfo.style.display = 'block';
    
    const shortcutInfo = document.getElementById('shortcutInfo');
    if (shortcutInfo) {
        shortcutInfo.style.display = 'block';
    }
    
    setTimeout(() => {
        if (!_commandInputMinHeightSet) {
            const commandInputEl = document.getElementById('commandInput');
            if (commandInputEl) {
                const initialHeightPx = commandInputEl.offsetHeight;
                if (initialHeightPx > 0) {
                    commandInputEl.style.minHeight = initialHeightPx + 'px';
                    _commandInputMinHeightSet = true;
                }
            }
        }

        const applyCommandHeight = () => {
            const commandSectionHeight = commandContainer.offsetHeight;
            const bufferHeight = 5;
            document.documentElement.style.setProperty('--command-section-height', `${commandSectionHeight + bufferHeight}px`);
            scheduleHotRender();
        };
        applyCommandHeight();

        if (window.ResizeObserver && !_commandContainerObserver) {
            _commandContainerObserver = new ResizeObserver(() => {
                applyCommandHeight();
            });
            _commandContainerObserver.observe(commandContainer);
        }
    }, 0);
}

export function resetApplicationUI() {
    spreadsheetContainer.style.display = 'none';
    commandContainer.style.display = 'none';
    sessionInfo.style.display = 'none';
    
    uploadForm.reset();
    document.querySelector('.file-input-label span').textContent = 'Choose File';
    fileNameDisplay.textContent = '-';
    sessionStatusDisplay.textContent = 'Inactive';
    
    updateStatus('Ready', 'waiting');
}

export function updateUndoRedoButtons(canUndo, canRedo) {
    const undoBtn = document.getElementById('undoBtn');
    const redoBtn = document.getElementById('redoBtn');
    if (undoBtn) undoBtn.disabled = !canUndo;
    if (redoBtn) redoBtn.disabled = !canRedo;
}

export function updateSessionInfo(uploadedFileName, statusText = 'Active') {
    if(fileNameDisplay) fileNameDisplay.textContent = uploadedFileName;
    if(sessionStatusDisplay) sessionStatusDisplay.textContent = statusText;
}
