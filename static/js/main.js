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

// Error modal elements
const errorModal = new bootstrap.Modal(document.getElementById('errorModal'));
const errorModalBody = document.getElementById('errorModalBody');

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
});

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
        
        // Load spreadsheet data
        await loadSpreadsheetData();
        
        // Show spreadsheet and command containers
        spreadsheetContainer.style.display = 'block';
        commandContainer.style.display = 'block';
    } catch (error) {
        showError(error.message);
    } finally {
        hideLoading();
    }
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
        manualRowResize: true
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
    } catch (error) {
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
    
    spreadsheetContainer.style.display = 'none';
    commandContainer.style.display = 'none';
    uploadForm.reset();
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
    loadingContainer.style.display = 'block';
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
