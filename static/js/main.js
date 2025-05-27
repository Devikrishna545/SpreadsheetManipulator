/**
 * Spreadsheet Auto-Editor
 * Main JavaScript file handling UI interactions and API calls
 */

// Global variables
let hotInstance = null; // Handsontable instance
let currentSessionId = null; // Current session ID
let currentData = null; // Current spreadsheet data

// DOM Elements
const uploadForm = document.getElementById('uploadForm');
const fileInput = document.getElementById('fileInput');
const spreadsheetContainer = document.getElementById('spreadsheetContainer');
const commandContainer = document.getElementById('commandContainer');
const loadingContainer = document.getElementById('loadingContainer');
const loadingMessage = document.getElementById('loadingMessage');
const spreadsheetData = document.getElementById('spreadsheetData');
const commandInput = document.getElementById('commandInput');
const processBtn = document.getElementById('processBtn');
const undoBtn = document.getElementById('undoBtn');
const redoBtn = document.getElementById('redoBtn');
const downloadBtn = document.getElementById('downloadBtn');
const actionsSection = document.getElementById('actionsSection');
const sessionInfo = document.getElementById('sessionInfo');
const statusBadge = document.getElementById('statusBadge');
const fileName = document.getElementById('fileName');
const sessionStatus = document.getElementById('sessionStatus');
const fullscreenBtn = document.getElementById('fullscreenBtn');

// Error modal elements
const errorModal = new bootstrap.Modal(document.getElementById('errorModal'));
const errorModalBody = document.getElementById('errorModalBody');

// Prompt history navigation state
let promptHistoryIndex = null;
let promptHistoryCache = [];

/**
 * Initialize the application
 */
document.addEventListener('DOMContentLoaded', function() {
    // Set up event listeners
    uploadForm.addEventListener('submit', handleFileUpload);
    processBtn.addEventListener('click', processCommand);
    undoBtn.addEventListener('click', undoModification);
    redoBtn.addEventListener('click', redoModification);
    downloadBtn.addEventListener('click', downloadSpreadsheet);
    fullscreenBtn.addEventListener('click', toggleFullscreen);
    
    // File input change event for better UX
    fileInput.addEventListener('change', function() {
        const label = document.querySelector('.file-input-label span');
        if (this.files.length > 0) {
            label.textContent = this.files[0].name;
        } else {
            label.textContent = 'Choose File';
        }
    });

    commandInput.addEventListener('keydown', handlePromptHistoryNavigation);
    commandInput.addEventListener('focus', resetPromptHistory);

    // Initialize status
    updateStatus('Ready', 'waiting');
    setupShortcutKeys();
});

/**
 * Setup global keyboard shortcuts for the application
 */
function setupShortcutKeys() {
    document.addEventListener('keydown', function(e) {
        // Helper to check if focus is inside the command input
        const isCommandInputActive = document.activeElement === commandInput;

        // Ctrl+Shift+U: Focus/select file input
        if (e.ctrlKey && e.shiftKey && (e.key === 'u' || e.key === 'U')) {
            e.preventDefault();
            fileInput.click();
            return;
        }

        // Ctrl+U: Upload file (submit form)
        if (e.ctrlKey && !e.shiftKey && (e.key === 'u' || e.key === 'U')) {
            e.preventDefault();
            uploadForm.requestSubmit();
            return;
        }

        // Ctrl+Z: Undo (only if not in command input)
        if (e.ctrlKey && !e.shiftKey && (e.key === 'z' || e.key === 'Z')) {
            if (!isCommandInputActive) {
                e.preventDefault();
                undoModification();
            }
            return;
        }

        // Ctrl+Y: Redo (only if not in command input)
        if (e.ctrlKey && !e.shiftKey && (e.key === 'y' || e.key === 'Y')) {
            if (!isCommandInputActive) {
                e.preventDefault();
                redoModification();
            }
            return;
        }

        // Ctrl+D: Download
        if (e.ctrlKey && !e.shiftKey && (e.key === 'd' || e.key === 'D')) {
            e.preventDefault();
            downloadSpreadsheet();
            return;
        }

        // Ctrl+M: Toggle maximize/minimize spreadsheet
        if (e.ctrlKey && !e.shiftKey && (e.key === 'm' || e.key === 'M')) {
            e.preventDefault();
            toggleFullscreen();
            return;
        }

        // Enter: Process command if inside command input
        if (e.key === 'Enter' && isCommandInputActive && !e.shiftKey && !e.ctrlKey && !e.altKey) {
            e.preventDefault();
            processCommand();
            return;
        }
    });
}

/**
 * Update application status
 * @param {string} message - Status message
 * @param {string} type - Status type (active, waiting, processing, error)
 */
function updateStatus(message, type = 'active') {
    statusBadge.textContent = message;
    statusBadge.className = `status-badge status-${type}`;
}

/**
 * Handle file upload
 * @param {Event} event - Form submit event
 */
async function handleFileUpload(event) {
    event.preventDefault();
    
    const file = fileInput.files[0];
    if (!file) {
        showError('Please select a file to upload.');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    updateStatus('Uploading...', 'processing');
    showLoading('Uploading spreadsheet...');
    
    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to upload file');
        }
        
        // Store session ID
        currentSessionId = data.sessionId;
        
        // Update UI
        fileName.textContent = file.name;
        sessionStatus.textContent = 'Active';
        
        // Load spreadsheet data
        await loadSpreadsheetData();
        
        // Show relevant sections
        showMainInterface();
        updateStatus('Ready', 'active');
    } catch (error) {
        updateStatus('Error', 'error');
        showError(error.message);
    } finally {
        hideLoading();
    }
}

/**
 * Show main interface sections
 */
function showMainInterface() {
    spreadsheetContainer.style.display = 'block';
    commandContainer.style.display = 'block';
    actionsSection.style.display = 'block';
    sessionInfo.style.display = 'block';
}

/**
 * Load spreadsheet data from the server
 */
async function loadSpreadsheetData() {
    if (!currentSessionId) return;
    
    showLoading('Loading spreadsheet data...');
    
    try {
        const response = await fetch(`/view/${currentSessionId}`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to load spreadsheet data');
        }
        
        currentData = data;
        renderSpreadsheet();
        updateUndoRedoButtons();
    } catch (error) {
        showError(error.message);
    } finally {
        hideLoading();
    }
}

/**
 * Render spreadsheet using Handsontable
 */
function renderSpreadsheet() {
    if (!currentData || !currentData.data) return;
    
    if (hotInstance) {
        hotInstance.destroy();
    }
    
    const settings = {
        data: currentData.data,
        rowHeaders: true,
        colHeaders: currentData.headers,
        licenseKey: 'non-commercial-and-evaluation',
        stretchH: 'all',
        readOnly: true,
        contextMenu: false,
        manualColumnResize: true,
        manualRowResize: true,
        className: 'htDark',
        // Enhanced styling for dark theme
        afterRender: function() {
            // Apply dark theme classes
            this.rootElement.classList.add('handsontable-dark');
        }
    };
    
    hotInstance = new Handsontable(spreadsheetData, settings);
    
    // Highlight modified cells if available
    if (currentData.modified_cells && currentData.modified_cells.length > 0) {
        highlightModifiedCells(currentData.modified_cells);
    }
}

/**
 * Highlight cells that were modified in the last operation
 * @param {Array} modifiedCells - Array of cell coordinates [row, col]
 */
function highlightModifiedCells(modifiedCells) {
    for (const [row, col] of modifiedCells) {
        const td = hotInstance.getCell(row, col);
        if (td) {
            td.classList.add('modified');
            
            // Remove highlight after 2 seconds
            setTimeout(() => {
                td.classList.remove('modified');
            }, 2000);
        }
    }
}

/**
 * Process command through the LLM
 */
async function processCommand() {
    const command = commandInput.value.trim();
    if (!command) {
        showError('Please enter a command.');
        return;
    }
    
    if (!currentSessionId) {
        showError('No active session. Please upload a spreadsheet first.');
        return;
    }
    
    updateStatus('Processing...', 'processing');
    showLoading('Processing your command...');
    
    try {
        const response = await fetch('/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                sessionId: currentSessionId,
                command: command
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to process command');
        }
        
        // Update spreadsheet with new data
        currentData = data;
        renderSpreadsheet();
        updateUndoRedoButtons();
        
        // Clear command input
        commandInput.value = '';
        resetPromptHistory();
        updateStatus('Command Executed', 'active');
        
        // Reset status after 3 seconds
        setTimeout(() => updateStatus('Ready', 'active'), 3000);
    } catch (error) {
        updateStatus('Error', 'error');
        showError(error.message);
    } finally {
        hideLoading();
    }
}

/**
 * Undo last modification
 */
async function undoModification() {
    if (!currentSessionId) return;
    
    showLoading('Undoing last modification...');
    
    try {
        const response = await fetch(`/undo/${currentSessionId}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to undo modification');
        }
        
        // Update spreadsheet with previous data
        currentData = data;
        renderSpreadsheet();
        updateUndoRedoButtons();
    } catch (error) {
        showError(error.message);
    } finally {
        hideLoading();
    }
}

/**
 * Redo previously undone modification
 */
async function redoModification() {
    if (!currentSessionId) return;
    
    showLoading('Redoing modification...');
    
    try {
        const response = await fetch(`/redo/${currentSessionId}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to redo modification');
        }
        
        // Update spreadsheet with next data
        currentData = data;
        renderSpreadsheet();
        updateUndoRedoButtons();
    } catch (error) {
        showError(error.message);
    } finally {
        hideLoading();
    }
}

/**
 * Download the modified spreadsheet
 */
function downloadSpreadsheet() {
    if (!currentSessionId) return;
    
    updateStatus('Downloading...', 'processing');
    window.location.href = `/download/${currentSessionId}`;
    
    // Show message that the session will be cleaned up
    setTimeout(() => {
        alert('Your session has been completed. The spreadsheet and all related data have been cleaned up.');
        resetApplication();
    }, 2000);
}

/**
 * Reset the application state
 */
function resetApplication() {
    currentSessionId = null;
    currentData = null;
    
    if (hotInstance) {
        hotInstance.destroy();
        hotInstance = null;
    }
    
    // Reset UI
    spreadsheetContainer.style.display = 'none';
    commandContainer.style.display = 'none';
    actionsSection.style.display = 'none';
    sessionInfo.style.display = 'none';
    
    // Reset form and labels
    uploadForm.reset();
    document.querySelector('.file-input-label span').textContent = 'Choose File';
    fileName.textContent = '-';
    sessionStatus.textContent = 'Inactive';
    
    updateStatus('Ready', 'waiting');
    resetPromptHistory();
}

/**
 * Update the state of undo/redo buttons based on current data
 */
function updateUndoRedoButtons() {
    if (!currentData) return;
    
    undoBtn.disabled = !currentData.can_undo;
    redoBtn.disabled = !currentData.can_redo;
}

/**
 * Show loading spinner with custom message
 * @param {string} message - Loading message
 */
function showLoading(message = 'Loading...') {
    loadingMessage.textContent = message;
    loadingContainer.style.display = 'flex';
}

/**
 * Hide loading spinner
 */
function hideLoading() {
    loadingContainer.style.display = 'none';
}

/**
 * Show error message in modal
 * @param {string} message - Error message
 */
function showError(message) {
    errorModalBody.textContent = message;
    errorModal.show();
}

/**
 * Toggle fullscreen mode for the spreadsheet
 */
function toggleFullscreen() {
    const spreadsheetCard = spreadsheetContainer.querySelector('.spreadsheet-card');
    const icon = fullscreenBtn.querySelector('i');
    
    if (spreadsheetCard.classList.contains('fullscreen')) {
        // Exit fullscreen
        spreadsheetCard.classList.remove('fullscreen');
        icon.classList.remove('fa-compress');
        icon.classList.add('fa-expand');
        fullscreenBtn.title = 'Enter Fullscreen';
    } else {
        // Enter fullscreen
        spreadsheetCard.classList.add('fullscreen');
        icon.classList.remove('fa-expand');
        icon.classList.add('fa-compress');
        fullscreenBtn.title = 'Exit Fullscreen';
    }
    
    // Refresh handsontable after fullscreen toggle
    if (hotInstance) {
        setTimeout(() => {
            hotInstance.render();
        }, 100);
    }
}

// Prompt history navigation state


/**
 * Fetch a prompt from history for the current session
 * @param {number} index - The index in the history (0 = most recent)
 * @returns {Promise<string|null>} - The prompt string or null if not found
 */
async function fetchPromptFromHistory(index) {
    if (!currentSessionId) return null;
    try {
        const response = await fetch(`/prompt_history/${currentSessionId}?index=${index}`);
        if (!response.ok) return null;
        const data = await response.json();
        return data.prompt || null;
    } catch {
        return null;
    }
}

/**
 * Handle up/down arrow navigation in command input for prompt history
 */
async function handlePromptHistoryNavigation(e) {
    if (document.activeElement !== commandInput) return;
    if (!currentSessionId) return;

    // Only handle up/down arrows
    if (e.key !== 'ArrowUp' && e.key !== 'ArrowDown') return;

    e.preventDefault();

    // Initialize index if not set
    if (promptHistoryIndex === null) {
        promptHistoryIndex = 0;
    }

    // Adjust index based on key
    if (e.key === 'ArrowUp') {
        promptHistoryIndex++;
    } else if (e.key === 'ArrowDown') {
        promptHistoryIndex--;
        if (promptHistoryIndex < 0) promptHistoryIndex = 0;
    }

    // Fetch prompt from cache if available, else from backend
    if (promptHistoryCache[promptHistoryIndex] !== undefined) {
        commandInput.value = promptHistoryCache[promptHistoryIndex] || '';
    } else {
        const prompt = await fetchPromptFromHistory(promptHistoryIndex);
        if (prompt !== null) {
            promptHistoryCache[promptHistoryIndex] = prompt;
            commandInput.value = prompt;
        } else {
            // No more history in this direction
            if (e.key === 'ArrowUp') {
                promptHistoryIndex--;
            } else if (e.key === 'ArrowDown' && promptHistoryIndex > 0) {
                promptHistoryIndex--;
            }
        }
    }
}

/**
 * Reset prompt history navigation state
 */
function resetPromptHistory() {
    promptHistoryIndex = null;
    promptHistoryCache = [];
}
