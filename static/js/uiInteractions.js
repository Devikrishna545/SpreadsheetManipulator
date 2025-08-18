// DOM Elements that are primarily controlled here
const sidebar = document.getElementById('sidebar');
const sidebarToggleBtn = document.getElementById('sidebarToggleBtn');
const spreadsheetContainer = document.getElementById('spreadsheetContainer');
const commandContainer = document.getElementById('commandContainer');
const sessionInfo = document.getElementById('sessionInfo');
const statusBadge = document.getElementById('statusBadge');
const loadingContainer = document.getElementById('loadingContainer');
const loadingMessage = document.getElementById('loadingMessage');

// Add safety check for Bootstrap
let errorModal;
let errorModalBody;
try {
    // Only initialize if Bootstrap is available and the element exists
    const errorModalElement = document.getElementById('errorModal');
    if (window.bootstrap && errorModalElement) {
        errorModal = new bootstrap.Modal(errorModalElement);
        errorModalBody = document.getElementById('errorModalBody');
    }
} catch (e) {
    console.warn('Bootstrap Modal initialization failed:', e);
}

const uploadForm = document.getElementById('uploadForm');
const fileNameDisplay = document.getElementById('fileName'); // Renamed to avoid conflict
const sessionStatusDisplay = document.getElementById('sessionStatus'); // Renamed
const fullscreenBtn = document.getElementById('fullscreenBtn');

// Throttled Handsontable re-render scheduler
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

// Observe command container resize to keep layout in sync without lag
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
    // Refresh handsontable if visible (hotInstance needs to be passed or accessed globally/via import if moved)
    // For now, assuming hotInstance is accessible or this part is handled where hotInstance is defined
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
    
    // Check for both main instance and editable instance
    if (window.hotInstance) {
        setTimeout(() => {
            window.hotInstance.render();
        }, 100);
    }
    
    // Also update the editable instance if it exists
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
        // Fallback if modal isn't available - just log to console
        console.error('UI Error:', message);
    }
}

export function showMainInterface() {
    spreadsheetContainer.style.display = 'block';
    commandContainer.style.display = 'block';
    sessionInfo.style.display = 'block';
    
    // Show shortcut info when spreadsheet is visible
    const shortcutInfo = document.getElementById('shortcutInfo');
    if (shortcutInfo) {
        shortcutInfo.style.display = 'block';
    }
    
    // Calculate and set the command section height for spreadsheet sizing, and watch for live changes
    setTimeout(() => {
        // Lock the command input's minimum height to its initial rendered height
        if (!_commandInputMinHeightSet) {
            const commandInputEl = document.getElementById('commandInput');
            if (commandInputEl) {
                const initialHeightPx = commandInputEl.offsetHeight; // includes padding/border; fine for a visual floor
                if (initialHeightPx > 0) {
                    commandInputEl.style.minHeight = initialHeightPx + 'px';
                    _commandInputMinHeightSet = true;
                }
            }
        }

        const applyCommandHeight = () => {
            const commandSectionHeight = commandContainer.offsetHeight;
            const bufferHeight = 5; // ensure no scroll jitter
            document.documentElement.style.setProperty('--command-section-height', `${commandSectionHeight + bufferHeight}px`);
            scheduleHotRender();
        };
        applyCommandHeight();

        // Start observing for live height changes (e.g., user resizes textarea)
        if (window.ResizeObserver && !_commandContainerObserver) {
            _commandContainerObserver = new ResizeObserver(() => {
                applyCommandHeight();
            });
            _commandContainerObserver.observe(commandContainer);
        }
    }, 0); // run on next tick after DOM shows
}

export function resetApplicationUI() { // Renamed to avoid conflict if resetApplication logic is split
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
