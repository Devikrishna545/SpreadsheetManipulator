import { initParticleBackground, cleanUpParticles } from './particleEffects.js';
import { 
    toggleSidebar, toggleFullscreen, updateStatus, resetApplicationUI, 
    updateUndoRedoButtons, showMainInterface, updateSessionInfo 
} from './uiInteractions.js';
import { handleFileUpload as apiHandleFileUpload, processCommand as apiProcessCommand, undoModification as apiUndoModification, redoModification as apiRedoModification, downloadSpreadsheet as apiDownloadSpreadsheet, generateAndExecuteAlgorithm as apiGenerateAndExecuteAlgorithm }
from './apiService.js';
import { renderSpreadsheet, loadSpreadsheetData as fetchSpreadsheetData, performTableUndo, performTableRedo, toggleSplitView, generateActionPlanLog, isSplitViewEnabled } from './spreadsheetHandler.js';
import { setupShortcutKeys,getCurrentSessionPrompts,resetPromptHistory } from './shortcuts.js';
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
const uploadCommandsBtn = document.getElementById('uploadCommandsBtn'); // Add this for upload commands button
const generateActionPlanBtn = document.getElementById('generateActionPlanBtn');
const commandFileInput = document.getElementById('commandFileInput'); // Add this for command file input

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
    
    // Add event listener for uploading command files
    uploadCommandsBtn.addEventListener('click', () => commandFileInput.click());
    commandFileInput.addEventListener('change', uploadCommandFile);

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
    
  commandInput.addEventListener('keyup', function(e) {
      getCurrentSessionPrompts(e);
     });   

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

// Manual Schema Update - captures schema from right spreadsheet
function updateSchema() {
    // Check if split view is active
    if (!isSplitViewEnabled()) {
        updateStatus('Split view required for schema functions', 'error');
        setTimeout(() => updateStatus('Ready', 'waiting'), 3000);
        return;
    }
    
    // Show loading state
    updateStatus('Capturing schema structure...', 'processing');
    
    // Get data from the right spreadsheet
    const rightData = getRightSpreadsheetData();
    
    if (!rightData) {
        updateStatus('Right spreadsheet data not available', 'error');
        setTimeout(() => updateStatus('Ready', 'waiting'), 3000);
        return;
    }
    
    // Send to backend for schema capture
    fetch('/update_schema', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            sessionId: currentSessionId,
            rightSpreadsheetData: rightData,
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
            console.log('Schema captured:', data.schema);
            updateStatus(`Schema captured: ${Object.keys(data.schema.column_patterns).length} column patterns found`, 'success');
            setTimeout(() => updateStatus('Ready', 'waiting'), 3000);
        } else {
            throw new Error(data.error || 'Unknown error occurred');
        }
    })
    .catch(error => {
        console.error('Error capturing schema:', error);
        updateStatus(`Error capturing schema: ${error.message}`, 'error');
        setTimeout(() => updateStatus('Ready', 'waiting'), 3000);
    });
}

// Manual Schema Transformation - applies right spreadsheet structure to left spreadsheet
async function transformToSchema() {
    // Check if split view is active
    if (!isSplitViewEnabled()) {
        updateStatus('Split view must be active to use schema functions', 'error');
        setTimeout(() => updateStatus('Ready', 'waiting'), 3000);
        return;
    }
    
    // Get data from the right spreadsheet
    const rightData = getRightSpreadsheetData();
    
    if (!rightData) {
        updateStatus('Right spreadsheet data not available', 'error');
        setTimeout(() => updateStatus('Ready', 'waiting'), 3000);
        return;
    }
    
    // Show confirmation modal using the same modal as action plan
    const rowCount = currentData?.data?.length || 0;
    const transformationPlan = `This will transform the entire left spreadsheet (${rowCount} rows) to match the structure shown in the right spreadsheet.

The transformation will:
- Apply the column structure from the right spreadsheet
- Detect patterns (constants, sequences, dates, cycles) from the right spreadsheet
- Transform all ${rowCount} rows according to these patterns

This action cannot be undone easily.`;
    
    showActionPlanModal(transformationPlan, rowCount, () => {
        executeSchemaTransformation(rightData);
    });
}

// Separate function to execute the actual transformation
async function executeSchemaTransformation(rightData) {
    // Show loading state
    updateStatus('Transforming left spreadsheet to match schema...', 'processing');
    
    try {
        // Send to backend for transformation
        const response = await fetch('/update_schema', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                sessionId: currentSessionId,
                rightSpreadsheetData: rightData,
                transformLeft: true
            }),
        });
        
        if (!response.ok) {
            throw new Error(`Server responded with status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success !== false) {
            // Update the current data and render the left spreadsheet with the transformed data
            currentData = data;
            renderSpreadsheet(currentData);
            updateUndoRedoButtons(currentData.can_undo, currentData.can_redo);
            
            updateStatus('Schema transformation complete', 'success');
            setTimeout(() => updateStatus('Ready', 'waiting'), 2000);
        } else {
            throw new Error(data.error || 'Unknown error occurred');
        }
    } catch (error) {
        console.error('Error transforming spreadsheet:', error);
        updateStatus(`Error transforming spreadsheet: ${error.message}`, 'error');
        setTimeout(() => updateStatus('Ready', 'waiting'), 3000);
    }
}

// Function to get data from the right spreadsheet
function getRightSpreadsheetData() {
    // Check if we're in split view mode
    const rightContainer = document.getElementById('rightSpreadsheet');
    if (!rightContainer || !rightContainer.hotInstance) {
        return null;
    }
    
    const rightHotInstance = rightContainer.hotInstance;
    
    // Get data as 2D array (this is what the backend expects)
    const data = rightHotInstance.getData();
    
    // Filter out completely empty rows
    const filteredData = data.filter(row => 
        row.some(cell => cell !== null && cell !== undefined && cell !== '')
    );
    
    return filteredData.length > 0 ? filteredData : null;
}

// PLACEHOLDER: updateLeftSpreadsheet function - functionality removed  
// This function previously updated the left spreadsheet with transformed schema data
// New implementation will use different update mechanisms

// Helper function to show error modal
function showErrorModal(message) {
    const errorModal = new bootstrap.Modal(document.getElementById('errorModal'));
    document.getElementById('errorModalBody').textContent = message;
    errorModal.show();
}

// Helper function to show action plan confirmation modal
function showActionPlanModal(actionPlan, rowCount, onConfirm) {
    // Set the row count in the warning message
    document.getElementById('actionPlanRowCount').textContent = rowCount;
    
    // Set the action plan content
    document.getElementById('actionPlanContent').textContent = actionPlan;
    
    // Create modal instance
    const actionPlanModal = new bootstrap.Modal(document.getElementById('actionPlanModal'));
    
    // Handle proceed button click
    const proceedBtn = document.getElementById('actionPlanProceedBtn');
    
    // Remove any existing event listeners to prevent duplicates
    const newProceedBtn = proceedBtn.cloneNode(true);
    proceedBtn.parentNode.replaceChild(newProceedBtn, proceedBtn);
    
    // Add new event listener
    newProceedBtn.addEventListener('click', () => {
        actionPlanModal.hide();
        onConfirm();
    });
    
    // Show the modal
    actionPlanModal.show();
}

// Add this new function to handle command file uploads
async function uploadCommandFile(event) {
    if (!event.target.files || event.target.files.length === 0) {
        return;
    }
    
    const file = event.target.files[0];
    if (!file || !file.name.endsWith('.txt')) {
        showErrorModal('Please select a text (.txt) file.');
        return;
    }
    
    if (!currentSessionId) {
        showErrorModal('Please upload a spreadsheet first before running commands.');
        return;
    }
    
    updateStatus('Uploading commands...', 'processing');
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('sessionId', currentSessionId);
    
    try {
        const response = await fetch('/upload_commands', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to upload command file');
        }
        
        const result = await response.json();
        
        if (result.commands && result.commands.length > 0) {
            updateStatus('Processing commands...', 'processing');
            await processCommandsSequentially(result.commands);
        } else {
            updateStatus('No commands found in file', 'warning');
            setTimeout(() => updateStatus('Ready', 'active'), 2000);
        }
    } catch (error) {
        showErrorModal(error.message);
        updateStatus('Error', 'error');
    } finally {
        // Reset the file input so the same file can be selected again
        event.target.value = '';
    }
}

// Function to process commands one by one
async function processCommandsSequentially(commands) {
    let successCount = 0;
    let failCount = 0;
    
    for (let i = 0; i < commands.length; i++) {
        const command = commands[i].trim();
        if (!command) continue;
        
        updateStatus(`Processing command ${i+1}/${commands.length}...`, 'processing');
        
        // Set the command in the input field
        commandInput.value = command;
        
        try {
            // Wait a moment for UI to update
            await new Promise(resolve => setTimeout(resolve, 300));
            
            // Process the command
            await processCurrentCommand();
            successCount++;
            
            // Wait between commands to allow for visual feedback
            await new Promise(resolve => setTimeout(resolve, 1000));
        } catch (error) {
            console.error('Error processing command:', error);
            failCount++;
            
            // Continue with next command despite errors
            await new Promise(resolve => setTimeout(resolve, 500));
        }
    }
    
    // Show final status
    updateStatus(`Completed ${successCount}/${commands.length} commands`, 
                 failCount > 0 ? 'warning' : 'success');
    
    // Reset after a delay
    setTimeout(() => updateStatus('Ready', 'active'), 3000);
}

// Add event listener for the new "Generate Action Plan" button
generateActionPlanBtn.addEventListener('click', async function() {
    // Get left and right spreadsheet data
    const leftHot = window.hotInstance;
    const rightContainer = document.getElementById('rightSpreadsheet');
    const rightHot = rightContainer && rightContainer.hotInstance ? rightContainer.hotInstance : null;
    
    if (!leftHot || !rightHot) {
        showErrorModal('Both spreadsheets must be visible to generate an action plan. Please enable split view first.');
        return;
    }
    
    // IMPORTANT: Get full left dataset from currentData, not from the display
    // The display might be virtualized and not contain all rows
    const leftData = currentData && currentData.data ? currentData.data : leftHot.getData();
    const rightData = rightHot.getData();
    
    console.log(`Algorithm will process ${leftData.length} rows from left spreadsheet and ${rightData.length} rows from right spreadsheet`);
    
    // Generate the action plan
    const actionPlan = generateActionPlanLog(leftData, rightData);
    
    if (actionPlan === 'No changes detected.') {
        showErrorModal('No changes detected in the right spreadsheet. Please make some modifications first to show the system what changes you want applied to the entire left spreadsheet.');
        return;
    }
    
    // Show action plan modal for user confirmation
    showActionPlanModal(actionPlan, leftData.length, async () => {
        // User confirmed, proceed with algorithm generation
        try {
            const result = await apiGenerateAndExecuteAlgorithm(currentSessionId, actionPlan, leftData, rightData);
            
            if (result) {
                // Update the current data and render the spreadsheet with the new changes
                currentData = result;
                renderSpreadsheet(currentData);
                updateUndoRedoButtons(currentData.can_undo, currentData.can_redo);

                // Show success message
                updateStatus('Universal algorithm applied successfully', 'success');
                setTimeout(() => updateStatus('Ready', 'active'), 3000);
            }
        } catch (error) {
            console.error('Error generating algorithm:', error);
            showErrorModal(`Error generating algorithm: ${error.message}`);
        }
    });
});
