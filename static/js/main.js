import { initParticleBackground, cleanUpParticles } from './particleEffects.js';
import { 
    toggleSidebar, toggleFullscreen, updateStatus, resetApplicationUI, 
    updateUndoRedoButtons, showMainInterface, updateSessionInfo 
} from './uiInteractions.js';
import { handleFileUpload as apiHandleFileUpload, processCommand as apiProcessCommand, undoModification as apiUndoModification, redoModification as apiRedoModification, downloadSpreadsheet as apiDownloadSpreadsheet }
from './apiService.js';
import { renderSpreadsheet, loadSpreadsheetData as fetchSpreadsheetData, performTableUndo, performTableRedo, toggleSplitView } from './spreadsheetHandler.js';
import { setupShortcutKeys,handlePromptHistoryNavigation,resetPromptHistory } from './shortcuts.js';
import { initCellSelector, clearCellSelector } from './cell-selector.js';
import { initCellTagger, scanAndHighlightTags } from './cell-tagger.js';

// Global state specific to main.js orchestration
let currentSessionId = null;
let currentData = null; // This will hold the entire data object { sessionId, data, headers, can_undo, can_redo, modified_cells }
window.hotInstance = null; // Make Handsontable instance globally accessible for modules if needed

// DOM Elements that main.js directly interacts with for event setup or passing to modules
const uploadForm = document.getElementById('uploadForm');
const fileInput = document.getElementById('fileInput');
const commandInput = document.getElementById('commandInput');
const processBtn = document.getElementById('processBtn');
const undoBtn = document.getElementById('undoBtn');
const redoBtn = document.getElementById('redoBtn');
const downloadBtn = document.getElementById('downloadBtn');
const fullscreenBtn = document.getElementById('fullscreenBtn'); // Already in uiInteractions but listener here
const sidebarToggleBtn = document.getElementById('sidebarToggleBtn'); // Same as fullscreenBtn
const splitViewBtn = document.getElementById('splitViewBtn'); // Add this line
const updateSchemaBtn = document.getElementById('updateSchemaBtn'); // Add this for schema button
const transformSchemaBtn = document.getElementById('transformSchemaBtn'); // Add this for transform button

document.addEventListener('DOMContentLoaded', function() {
    // Initialize UI elements and listeners
    uploadForm.addEventListener('submit', onFileUpload);
    processBtn.addEventListener('click', processCurrentCommand);
    undoBtn.addEventListener('click', undoLastModification);
    redoBtn.addEventListener('click', redoLastModification);
    downloadBtn.addEventListener('click', downloadCurrentSpreadsheet);
    
    // Listeners handled by uiInteractions.js if DOM elements are passed or queried there
    // For simplicity, keeping core interaction listeners here if they trigger app logic flow
    fullscreenBtn.addEventListener('click', toggleFullscreen); // toggleFullscreen is from uiInteractions
    sidebarToggleBtn.addEventListener('click', toggleSidebar); // toggleSidebar is from uiInteractions
    splitViewBtn.addEventListener('click', toggleSplitView); // Add this line for split view button
    
    // Add event listeners for schema management buttons
    updateSchemaBtn.addEventListener('click', updateSchema);
    transformSchemaBtn.addEventListener('click', transformToSchema);

    fileInput.addEventListener('change', function() {
        const label = document.querySelector('.file-input-label span');
        if (this.files.length > 0) {
            label.textContent = this.files[0].name;
        } else {
            label.textContent = 'Choose File';
        }
    });

    updateStatus('Ready', 'waiting');
    initParticleBackground(); 
    initCellSelector(); // Initialize cell selector
    initCellTagger(commandInput); // Initialize cell tagger with command input element
    
    // Move these lines to ensure commandInput is available and listeners are attached after DOM is ready
    commandInput.addEventListener('keydown', function(e) {
        // Only trigger for ArrowUp/ArrowDown to avoid interfering with other shortcuts
        if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
            handlePromptHistoryNavigation(e);
        }
    });
    commandInput.addEventListener('focus', resetPromptHistory);

    // Pass an 'app' object or specific methods to shortcuts
    setupShortcutKeys({
        processCurrentCommand,
        undoLastModification,
        redoLastModification,
        downloadCurrentSpreadsheet
        // uploadForm.requestSubmit and fileInput.click are handled directly in shortcuts.js
    });

    // Remove the automatic tag scanning during typing - only scan when explicitly needed
    // We'll keep the delayed scanning but only for preview, not actual selection
    commandInput.addEventListener('input', function() {
        // We'll keep this empty for now - scanning will only happen on Enter or command submission
    });

    // Add window unload handler to clean up particles
    window.addEventListener('beforeunload', cleanUpParticles);
});

// Add this function to generate Excel-style column headers
function generateExcelColHeaders(count) {
    const headers = [];
    
    for (let i = 0; i < count; i++) {
        let header = '';
        let colNum = i;
        
        while (colNum >= 0) {
            const remainder = colNum % 26;
            header = String.fromCharCode(65 + remainder) + header;
            colNum = Math.floor(colNum / 26) - 1;
        }
        
        headers.push(header);
    }
    
    return headers;
}

// When initializing or updating the spreadsheet, modify the configuration to use Excel-style headers
function initializeSpreadsheet(data, container) {
    // Get the column count from the data
    const columnCount = data.length > 0 ? data[0].length : 0;
    
    // Generate Excel-style column headers (A, B, C, ...)
    const colHeaders = generateExcelColHeaders(columnCount);
    
    // Create or update the Handsontable instance
    if (!hot) {
        hot = new Handsontable(container, {
            data: data,
            rowHeaders: true,
            colHeaders: colHeaders,
            // ...other configuration options
            licenseKey: 'non-commercial-and-evaluation'
        });
    } else {
        hot.updateSettings({
            data: data,
            colHeaders: colHeaders
        });
    }
}

// When updating the spreadsheet data, make sure to update the column headers too
function updateSpreadsheetData(data) {
    if (hot) {
        const columnCount = data.length > 0 ? data[0].length : 0;
        const colHeaders = generateExcelColHeaders(columnCount);
        
        hot.updateSettings({
            data: data,
            colHeaders: colHeaders
        });
    }
}

async function onFileUpload(event) {
    const result = await apiHandleFileUpload(event, fileInput);
    if (result && result.sessionId) {
        currentSessionId = result.sessionId;
        window.currentSessionId = currentSessionId;
        // Initial data load after upload
        const initialData = await fetchSpreadsheetData(currentSessionId);
        if (initialData) {
            currentData = initialData;
            renderSpreadsheet(currentData);
            updateUndoRedoButtons(currentData.can_undo, currentData.can_redo);
        }
    }
}

async function processCurrentCommand() {
    const commandText = commandInput.value.trim();
    // Highlight any tagged cells one final time before sending - this is where selections should happen
    scanAndHighlightTags();
    
    const result = await apiProcessCommand(currentSessionId, commandText);
    if (result) {
        currentData = result;
        renderSpreadsheet(currentData);
        updateUndoRedoButtons(currentData.can_undo, currentData.can_redo);
        commandInput.value = '';
        resetPromptHistory(); // Reset prompt history navigation state        
    }
}

async function undoLastModification() {
    const result = await apiUndoModification(currentSessionId);
    if (result) {
        currentData = result;
        renderSpreadsheet(currentData);
        updateUndoRedoButtons(currentData.can_undo, currentData.can_redo);
        
        // Update both spreadsheets if in split view
        const rightContainer = document.getElementById('rightSpreadsheet');
        if (rightContainer && rightContainer.hotInstance && currentData.rightViewData) {
            rightContainer.hotInstance.loadData(currentData.rightViewData.data);
            rightContainer.hotInstance.render();
        }
    }
}

async function redoLastModification() {
    const result = await apiRedoModification(currentSessionId);
    if (result) {
        currentData = result;
        renderSpreadsheet(currentData);
        updateUndoRedoButtons(currentData.can_redo, currentData.can_redo);
        
        // Update both spreadsheets if in split view
        const rightContainer = document.getElementById('rightSpreadsheet');
        if (rightContainer && rightContainer.hotInstance && currentData.rightViewData) {
            rightContainer.hotInstance.loadData(currentData.rightViewData.data);
            rightContainer.hotInstance.render();
        }
    }
}

function downloadCurrentSpreadsheet() {
    apiDownloadSpreadsheet(currentSessionId);
    // resetApplicationState will be called by apiDownloadSpreadsheet after timeout
}

// Centralized state reset
export function resetApplicationState() {
    currentSessionId = null;
    window.currentSessionId = null;
    currentData = null;
    if (window.hotInstance) {
        window.hotInstance.destroy();
        window.hotInstance = null;
    }
    resetApplicationUI(); // Resets the visual parts of the UI
    resetPromptHistory(); // Reset prompt history navigation state
    clearCellSelector(); // Clear cell selector
    
    // Clean up split view if active
    const splitContainer = document.querySelector('.split-view-container');
    if (splitContainer) {
        const parent = splitContainer.parentNode;
        const spreadsheetDataContainer = document.getElementById('spreadsheetData');
        
        // If spreadsheetData is inside the split container, move it back
        if (spreadsheetDataContainer && spreadsheetDataContainer.parentNode !== parent) {
            while (splitContainer.firstChild) {
                splitContainer.removeChild(splitContainer.firstChild);
            }
            parent.removeChild(splitContainer);
            parent.appendChild(spreadsheetDataContainer);
        }
        
        // Update button state
        const splitViewBtn = document.getElementById('splitViewBtn');
        if (splitViewBtn) {
            splitViewBtn.innerHTML = '<i class="fas fa-columns"></i>';
            splitViewBtn.title = 'Split View';
        }
    }
}

// Export for prompts.js to access current prompt
export function getCurrentPromptText() {
    return commandInput.value;
}
export function setCurrentPromptText(text) {
    commandInput.value = text;
}

// Update the schema functions to work with the revised data format
function updateSchema() {
    // Show loading state
    updateStatus('Updating schema...', 'processing');
    
    // Get data from the right spreadsheet
    const rightData = getRightSpreadsheetData();
    
    if (!rightData) {
        showErrorModal('Right spreadsheet not available. Please make sure split view is active.');
        updateStatus('Ready', 'waiting');
        return;
    }
    
    // Send to backend
    fetch('/update_schema', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            sessionId: currentSessionId,
            rightSpreadsheetData: rightData.structuredData,
            columnNames: rightData.columnNames,
            useFirstRowAsHeader: rightData.useFirstRowAsHeader,
            transformLeft: false
        }),
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Server responded with status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            console.log('Schema updated:', data.schema);
            updateStatus('Schema updated successfully', 'success');
            setTimeout(() => updateStatus('Ready', 'waiting'), 2000);
        } else {
            throw new Error(data.error || 'Unknown error occurred');
        }
    })
    .catch(error => {
        console.error('Error updating schema:', error);
        showErrorModal(`Error updating schema: ${error.message}`);
        updateStatus('Ready', 'waiting');
    });
}

async function transformToSchema() {
    // Show loading state
    updateStatus('Transforming data to match schema...', 'processing');
    
    // Get data from the right spreadsheet
    const rightData = getRightSpreadsheetData();
    
    if (!rightData) {
        showErrorModal('Right spreadsheet not available. Please make sure split view is active.');
        updateStatus('Ready', 'waiting');
        return;
    }
    
    // Send to backend with transformLeft=true
    fetch('/update_schema', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            sessionId: currentSessionId,
            rightSpreadsheetData: rightData.structuredData,
            columnNames: rightData.columnNames,
            useFirstRowAsHeader: rightData.useFirstRowAsHeader,
            transformLeft: true
        }),
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(errorData => {
                throw new Error(errorData.detail || `Server responded with status: ${response.status}`);
            });
        }
        return response.json();
    })
    .then(data => {
        // The backend returns the transformed spreadsheet view directly (with 'data', etc.)
        // So we just pass 'data' to updateLeftSpreadsheet
        if (data.success === false) {
            throw new Error(data.error || 'Unknown error occurred');
        }
        // Defensive: if data.transformedData exists, use it; else use data.data
        if (data.transformedData) {
            updateLeftSpreadsheet(data.transformedData);
        } else if (data.data) {
            updateLeftSpreadsheet({ data: data.data, headers: data.headers || null });
        } else {
            throw new Error('No transformed data returned from server.');
        }

        // Update the current data for undo/redo tracking
        currentData = data;
        updateUndoRedoButtons(currentData.can_undo, currentData.can_redo);

        updateStatus('Transformation complete', 'success');
        setTimeout(() => updateStatus('Ready', 'waiting'), 2000);
    })
    .catch(error => {
        console.error('Error transforming spreadsheet:', error);
        let errorMessage = error.message;
        if (errorMessage.includes('safety concerns')) {
            errorMessage = 'The AI model blocked the transformation due to content safety concerns. Please review your data and try again.';
        } else if (errorMessage.includes('No valid response')) {
            errorMessage = 'The AI model could not generate a valid transformation. Please try simplifying your schema or data structure.';
        }
        showErrorModal(`Error transforming spreadsheet: ${errorMessage}`);
        updateStatus('Ready', 'waiting');
    });
}

// Function to get data from the right spreadsheet
function getRightSpreadsheetData() {
    // Check if we're in split view mode
    const rightContainer = document.getElementById('rightSpreadsheet');
    if (!rightContainer || !rightContainer.hotInstance) {
        return null;
    }
    
    const rightHotInstance = rightContainer.hotInstance;
    
    // Get data and headers
    const data = rightHotInstance.getData();
    const headers = rightHotInstance.getColHeader();
    
    // Create a properly formatted structure for the backend
    // First row can be used as "real" column headers if needed
    const firstRow = data[0] || [];
    
    // Determine if first row contains proper headers or is just data
    const useFirstRowAsHeader = firstRow.some(cell => cell !== null && cell !== '');
    
    // If the first row has data, use it as column names, otherwise use the Excel headers
    const columnNames = useFirstRowAsHeader ? firstRow : headers;
    
    // Create an array of row objects, skipping the header row if we're using it as headers
    const startIndex = useFirstRowAsHeader ? 1 : 0;
    const formattedData = [];
    
    for (let i = startIndex; i < data.length; i++) {
        const rowObj = {};
        const row = data[i];
        
        // For each cell in the row, use the appropriate header as the key
        for (let j = 0; j < row.length; j++) {
            // Use the column name (or Excel-style header if no column names)
            const key = j < columnNames.length ? columnNames[j] : `Column${j+1}`;
            rowObj[key] = row[j];
        }
        
        formattedData.push(rowObj);
    }
    
    // Return both raw data and properly formatted data
    return {
        rawData: data,
        structuredData: formattedData,
        headers: headers,
        columnNames: columnNames,
        useFirstRowAsHeader: useFirstRowAsHeader
    };
}

// Function to update the left spreadsheet with transformed data
function updateLeftSpreadsheet(transformedData) {
    // Get the left spreadsheet instance
    const leftContainer = document.getElementById('spreadsheetData');
    if (!leftContainer || !window.hotInstance) {
        console.error('Left spreadsheet not available');
        return;
    }

    // Defensive: support both {data, headers} and just data array
    let data = Array.isArray(transformedData) ? transformedData : transformedData.data;
    let headers = transformedData.headers || null;

    // Update the spreadsheet with new data
    window.hotInstance.loadData(data);

    // If headers have changed, update them too
    if (headers) {
        window.hotInstance.updateSettings({
            colHeaders: headers
        });
    }

    // Refresh the view
    window.hotInstance.render();
}

// Helper function to show error modal
function showErrorModal(message) {
    const errorModal = new bootstrap.Modal(document.getElementById('errorModal'));
    document.getElementById('errorModalBody').textContent = message;
    errorModal.show();
}
