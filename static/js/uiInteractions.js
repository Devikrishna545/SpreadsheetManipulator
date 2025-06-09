// DOM Elements that are primarily controlled here
const sidebar = document.getElementById('sidebar');
const sidebarToggleBtn = document.getElementById('sidebarToggleBtn');
const spreadsheetContainer = document.getElementById('spreadsheetContainer');
const commandContainer = document.getElementById('commandContainer');
const actionsSection = document.getElementById('actionsSection');
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

export function hideLoading() {
    loadingContainer.style.display = 'none';
}

export function showError(message) {
    if (errorModal && errorModalBody) {
        errorModalBody.textContent = message;
        errorModal.show();
    } else {
        // Fallback if modal isn't available
        console.error('UI Error:', message);
        alert(message);
    }
}

export function showMainInterface() {
    spreadsheetContainer.style.display = 'block';
    commandContainer.style.display = 'block';
    actionsSection.style.display = 'block';
    sessionInfo.style.display = 'block';
    
    // Calculate and set the command section height for spreadsheet sizing
    setTimeout(() => {
        const commandSectionHeight = commandContainer.offsetHeight;
        // Add a small buffer to ensure no scrolling
        const bufferHeight = 5;
        document.documentElement.style.setProperty('--command-section-height', `${commandSectionHeight + bufferHeight}px`);
        
        // Calculate total content height and ensure it fits
        const navbarHeight = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--navbar-height'));
        const totalContentHeight = commandSectionHeight + navbarHeight + spreadsheetContainer.offsetHeight;
        
        // If total content would cause scrolling, reduce spreadsheet height
        if (totalContentHeight > window.innerHeight) {
            const adjustment = totalContentHeight - window.innerHeight + 10; // 10px buffer
            const currentSpreadsheetHeight = spreadsheetContainer.querySelector('.spreadsheet-card').offsetHeight;
            const newSpreadsheetHeight = currentSpreadsheetHeight - adjustment;
            
            // Set a custom property for this specific spreadsheet
            document.documentElement.style.setProperty('--custom-spreadsheet-height', `${newSpreadsheetHeight}px`);
            spreadsheetContainer.querySelector('.spreadsheet-card').style.height = `var(--custom-spreadsheet-height)`;
        }
        
        // If we have a Handsontable instance, refresh it to fit the new size
        if (window.hotInstance) {
            window.hotInstance.render();
        }
    }, 50); // Small delay to ensure DOM is fully rendered
}

export function resetApplicationUI() { // Renamed to avoid conflict if resetApplication logic is split
    spreadsheetContainer.style.display = 'none';
    commandContainer.style.display = 'none';
    actionsSection.style.display = 'none';
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
