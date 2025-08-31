import { initCellTagger, scanAndHighlightTags } from './cell-tagger.js';
import { initCellSelector, clearCellSelector } from './cell-selector.js';
import { showAlert, showConfirm, showErrorModal } from './modalUtils.js';
import { initParticleBackground, cleanUpParticles } from './particleEffects.js';
import { setupShortcutKeys,getCurrentSessionPrompts,resetPromptHistory } from './shortcuts.js';
import { toggleSidebar, toggleFullscreen, updateStatus, resetApplicationUI, updateUndoRedoButtons, showMainInterface, updateSessionInfo 
} from './uiInteractions.js';
import { renderSpreadsheet, loadSpreadsheetData as fetchSpreadsheetData, performTableUndo, performTableRedo, toggleSplitView, generateActionPlanLog, isSplitViewEnabled, renderSheetTabs, switchSheet 
} from './spreadsheetHandler.js';
import { handleFileUpload as apiHandleFileUpload, processCommand as apiProcessCommand, undoModification as apiUndoModification, redoModification as apiRedoModification, downloadSpreadsheet as apiDownloadSpreadsheet, generateAndExecuteAlgorithm as apiGenerateAndExecuteAlgorithm, createMapping as apiCreateMapping, getAllMappings as apiGetAllMappings, deleteMapping as apiDeleteMapping, updateMapping as apiUpdateMapping 
} from './apiService.js';

window.actionsSection = window.actionsSection || { style: {} };

let currentSessionId = null;
let currentData = null;
window.hotInstance = null;

const uploadForm = document.getElementById('uploadForm');
const fileInput = document.getElementById('fileInput');
const commandInput = document.getElementById('commandInput');
const processBtn = document.getElementById('processBtn');
const undoBtn = document.getElementById('undoBtn');
const redoBtn = document.getElementById('redoBtn');
const downloadBtn = document.getElementById('downloadBtn');
const cacheBtn = document.getElementById('cacheBtn');
const fullscreenBtn = document.getElementById('fullscreenBtn');
const sidebarToggleBtn = document.getElementById('sidebarToggleBtn');
const splitViewBtn = document.getElementById('splitViewBtn');
const updateSchemaBtn = document.getElementById('updateSchemaBtn');
const transformSchemaBtn = document.getElementById('transformSchemaBtn');
const uploadCommandsBtn = document.getElementById('uploadCommandsBtn');
const manageMappingsBtn = document.getElementById('manageMappingsBtn');
const analyticsBtn = document.getElementById('analyticsBtn');
const generateActionPlanBtn = document.getElementById('generateActionPlanBtn');
const commandFileInput = document.getElementById('commandFileInput');

document.addEventListener('DOMContentLoaded', function() {
    window.isBatchCommandMode = false;
    
    window.actionsSection = window.actionsSection || { style: {} };
    
    if (typeof actionsSection !== 'undefined' && !actionsSection) {
        actionsSection = { style: {} };
    }
    
    uploadForm.addEventListener('submit', onFileUpload);
    processBtn.addEventListener('click', processCurrentCommand);
    undoBtn.addEventListener('click', undoLastModification);
    redoBtn.addEventListener('click', redoLastModification);
    downloadBtn.addEventListener('click', downloadCurrentSpreadsheet);
    cacheBtn.addEventListener('click', openCacheManagement);
    
    fullscreenBtn.addEventListener('click', toggleFullscreen);
    sidebarToggleBtn.addEventListener('click', toggleSidebar);
    splitViewBtn.addEventListener('click', toggleSplitView);
    
    updateSchemaBtn.addEventListener('click', updateSchema);
    transformSchemaBtn.addEventListener('click', transformToSchema);
    
    uploadCommandsBtn.addEventListener('click', () => commandFileInput.click());
    commandFileInput.addEventListener('change', uploadCommandFile);
    
    manageMappingsBtn.addEventListener('click', openMappingManagement);
    
    analyticsBtn.addEventListener('click', openAnalytics);

    fileInput.addEventListener('change', function() {
        const label = document.querySelector('.file-input-label span');
        if (this.files.length > 0) {
            label.textContent = this.files[0].name;
        } else {
            label.textContent = 'Choose File';
        }
    });

    updateStatus('Ready', 'waiting');
    if ('requestIdleCallback' in window) {
        requestIdleCallback(() => initParticleBackground(), { timeout: 1500 });
    } else {
        setTimeout(() => initParticleBackground(), 0);
    }
    initCellSelector();
    initCellTagger(commandInput);
    
    commandInput.addEventListener('keyup', function(e) {
        getCurrentSessionPrompts(e);
    });

    setupShortcutKeys({
        processCurrentCommand,
        undoLastModification,
        redoLastModification,
        downloadCurrentSpreadsheet,
        openMappingManagement,
        openAnalytics
    });

    commandInput.addEventListener('input', function() {
    });

    initSessionLifecycle();

    window.addEventListener('beforeunload', () => {
        try {
            endSessionLifecycle();
        } catch (e) { /* ignore */ }
        cleanUpParticles();
    }, { capture: false });
});

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

function initializeSpreadsheet(data, container) {
    const columnCount = data.length > 0 ? data[0].length : 0;
    
    const colHeaders = generateExcelColHeaders(columnCount);
    
    if (!hot) {
        hot = new Handsontable(container, {
            data: data,
            rowHeaders: true,
            colHeaders: colHeaders,
            licenseKey: 'non-commercial-and-evaluation'
        });
    } else {
        hot.updateSettings({
            data: data,
            colHeaders: colHeaders
        });
    }
}

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
        
        if (fileInput.files && fileInput.files.length > 0) {
            window.currentSpreadsheetFilename = fileInput.files[0].name;
        }
        
        if (result.has_mapping && result.mapped_commands && result.mapped_commands.length > 0) {
            const shouldExecute = await showConfirm(
                `This spreadsheet has ${result.command_count} mapped commands that can be automatically executed.\n\n` +
                `Do you want to execute these commands now?`,
                'Execute Mapped Commands',
                {
                    confirmText: 'Execute',
                    confirmClass: 'btn-primary'
                }
            );
            
            if (shouldExecute) {
                updateStatus('Executing mapped commands...', 'processing');
                await processCommandsSequentially(result.mapped_commands);
            }
        }
        
        const initialData = await fetchSpreadsheetData(currentSessionId);
        if (initialData) {
            currentData = initialData;
            if (initialData.sheets && Array.isArray(initialData.sheets)) {
                renderSpreadsheet({
                    sheets: initialData.sheets,
                    activeSheetIndex: 0
                });
            } else {
                renderSpreadsheet(currentData);
            }
            updateUndoRedoButtons(currentData.can_undo, currentData.can_redo);           
        }
    }
}

async function processCurrentCommand() {
    const commandText = commandInput.value.trim();
    scanAndHighlightTags();
    
    window.isBatchCommandMode = false;
    console.log('🔧 Processing single AI command - batch mode set to:', window.isBatchCommandMode);
    
    try {
        const result = await apiProcessCommand(currentSessionId, commandText);
        if (result) {
            currentData = result;
            renderSpreadsheet(currentData);
            updateUndoRedoButtons(currentData.can_undo, currentData.can_redo);
            commandInput.value = '';
            resetPromptHistory();
        }
    } catch (error) {
        if (error.message === 'SCRIPT_EXECUTION_FAILED') {
            throw error;
        }
        console.error('Error in processCurrentCommand:', error);
    }
}

async function processBatchCommand(commandText) {
    scanAndHighlightTags();
    
    console.log('🔧 Processing batch command - batch mode maintained at:', window.isBatchCommandMode);
    
    try {
        const result = await apiProcessCommand(currentSessionId, commandText);
        if (result) {
            currentData = result;
            renderSpreadsheet(currentData);
            updateUndoRedoButtons(currentData.can_undo, currentData.can_redo);
        }
        return result;
    } catch (error) {
        if (error.message === 'SCRIPT_EXECUTION_FAILED') {
            throw error;
        }
        console.error('Error in processBatchCommand:', error);
        throw error;
    }
}

async function undoLastModification() {
    const result = await apiUndoModification(currentSessionId);
    if (result) {
        currentData = result;
        renderSpreadsheet(currentData);
        updateUndoRedoButtons(currentData.can_undo, currentData.can_redo);
        
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
        
        const rightContainer = document.getElementById('rightSpreadsheet');
        if (rightContainer && rightContainer.hotInstance && currentData.rightViewData) {
            rightContainer.hotInstance.loadData(currentData.rightViewData.data);
            rightContainer.hotInstance.render();
        }
    }
}

function downloadCurrentSpreadsheet() {
    apiDownloadSpreadsheet(currentSessionId);
}

export function resetApplicationState() {
    currentSessionId = null;
    window.currentSessionId = null;
    currentData = null;
    if (window.hotInstance) {
        window.hotInstance.destroy();
        window.hotInstance = null;
    }
    resetApplicationUI();
    resetPromptHistory();
    clearCellSelector();
    
    const splitContainer = document.querySelector('.split-view-container');
    if (splitContainer) {
        const parent = splitContainer.parentNode;
        const spreadsheetDataContainer = document.getElementById('spreadsheetData');
        
        if (spreadsheetDataContainer && spreadsheetDataContainer.parentNode !== parent) {
            while (splitContainer.firstChild) {
                splitContainer.removeChild(splitContainer.firstChild);
            }
            parent.removeChild(splitContainer);
            parent.appendChild(spreadsheetDataContainer);
        }
        
        const splitViewBtn = document.getElementById('splitViewBtn');
        if (splitViewBtn) {
            splitViewBtn.innerHTML = '<i class="fas fa-columns"></i>';
            splitViewBtn.title = 'Split View';
        }
    }
}

let heartbeatTimer = null;

async function initSessionLifecycle() {
    try {
        const res = await fetch('/api/session/start', {
            method: 'POST'
        });
        if (!res.ok) return;
        const data = await res.json();
        window.currentSessionId = data.sessionId;
        currentSessionId = data.sessionId;
        updateSessionInfo && updateSessionInfo(currentSessionId);

        fetch('/', {
            method: 'GET',
            headers: { 'X-Session-Id': window.currentSessionId },
            cache: 'no-store',
            keepalive: true
        }).catch(() => {});

        heartbeatTimer = setInterval(() => {
            if (!window.currentSessionId) return;
            navigator.sendBeacon('/api/session/heartbeat', new Blob([
                JSON.stringify({ sessionId: window.currentSessionId })
            ], { type: 'application/json' }));
        }, 25000);
    } catch (e) {
        console.warn('Session start failed', e);
    }
}

function endSessionLifecycle() {
    if (heartbeatTimer) {
        clearInterval(heartbeatTimer);
        heartbeatTimer = null;
    }
    if (window.currentSessionId) {
        navigator.sendBeacon('/api/session/end', new Blob([
            JSON.stringify({ sessionId: window.currentSessionId })
        ], { type: 'application/json' }));
    }
}

export function getCurrentPromptText() {
    return commandInput.value;
}
export function setCurrentPromptText(text) {
    commandInput.value = text;
}

function updateSchema() {
    if (!isSplitViewEnabled()) {
        updateStatus('Split view required for schema functions', 'error');
        setTimeout(() => updateStatus('Ready', 'waiting'), 3000);
        return;
    }
    
    updateStatus('Capturing schema structure...', 'processing');
    
    const rightData = getRightSpreadsheetData();
    
    if (!rightData) {
        updateStatus('Right spreadsheet data not available', 'error');
        setTimeout(() => updateStatus('Ready', 'waiting'), 3000);
        return;
    }
        fetch('/update_schema', {
        method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(window.currentSessionId ? { 'X-Session-Id': window.currentSessionId } : {})
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

async function transformToSchema() {
    if (!isSplitViewEnabled()) {
        updateStatus('Split view must be active to use schema functions', 'error');
        setTimeout(() => updateStatus('Ready', 'waiting'), 3000);
        return;
    }
    
    const rightData = getRightSpreadsheetData();
    
    if (!rightData) {
        updateStatus('Right spreadsheet data not available', 'error');
        setTimeout(() => updateStatus('Ready', 'waiting'), 3000);
        return;
    }
    
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
            const response = await fetch('/update_schema', {
            method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(window.currentSessionId ? { 'X-Session-Id': window.currentSessionId } : {})
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
            headers: { ...(window.currentSessionId ? { 'X-Session-Id': window.currentSessionId } : {}) },
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to upload command file');
        }
        
        const result = await response.json();
        
        if (result.commands && result.commands.length > 0) {
            updateStatus('Processing commands...', 'processing');
            
            // Store the command file info for mapping creation
            const commandFileInfo = {
                filename: result.filename,
                commands: result.commands
            };
            
            const success = await processCommandsSequentially(result.commands);
            
            // Commands executed successfully - ask if user wants to create a mapping
            if (success) {
                updateStatus('All commands executed successfully!', 'success');
                setTimeout(() => updateStatus('Ready', 'active'), 3000);
                
                // Ask user if they want to create a mapping
                const shouldCreateMapping = await showConfirm(
                    'All commands were executed successfully!\n\n' +
                    'Would you like to create a mapping between this spreadsheet and the command file?\n\n' +
                    'This will allow the commands to be automatically executed when this spreadsheet is uploaded in the future.',
                    'Create Mapping?',
                    {
                        confirmText: 'Create Mapping',
                        cancelText: 'Not Now',
                        confirmClass: 'btn-success'
                    }
                );
                
                if (shouldCreateMapping) {
                    await createMappingFromUpload(commandFileInfo);
                }
            } else {
                updateStatus('Some commands failed to execute', 'warning');
                setTimeout(() => updateStatus('Ready', 'active'), 3000);
            }
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

// Create mapping from uploaded command file
async function createMappingFromUpload(commandFileInfo) {
    try {
        const currentSpreadsheetName = getCurrentSpreadsheetName();
        if (!currentSpreadsheetName) {
            showErrorModal('Unable to determine current spreadsheet name');
            return;
        }
        
        updateStatus('Creating mapping...', 'processing');
        
        // Check for existing mappings for this spreadsheet
        const checkResponse = await fetch(`/check_mapping/${encodeURIComponent(currentSpreadsheetName)}`);
        if (checkResponse.ok) {
            const checkData = await checkResponse.json();
            if (checkData.conflicts && checkData.conflicts.length > 0) {
                const conflictCount = checkData.conflicts.length;
                const shouldContinue = await showConfirm(
                    `Warning: This spreadsheet already has ${conflictCount} existing mapping(s).\n\n` +
                    `Creating a new mapping will result in multiple mappings for the same spreadsheet.\n\n` +
                    `Do you want to continue?`,
                    'Mapping Conflict',
                    {
                        confirmText: 'Continue',
                        cancelText: 'Cancel',
                        confirmClass: 'btn-warning'
                    }
                );
                
                if (!shouldContinue) {
                    updateStatus('Mapping creation cancelled', 'warning');
                    setTimeout(() => updateStatus('Ready', 'active'), 2000);
                    return;
                }
            }
        }
        
        // Create the mapping
        const response = await apiCreateMapping(
            currentSpreadsheetName,
            commandFileInfo.filename,
            commandFileInfo.commands
        );
        
        if (response && response.success) {
            updateStatus('Mapping created successfully!', 'success');
            setTimeout(() => updateStatus('Ready', 'active'), 3000);
        } else {
            const errorMsg = response && response.error ? response.error : 'Failed to create mapping';
            throw new Error(errorMsg);
        }
        
    } catch (error) {
        console.error('Error creating mapping:', error);
        showErrorModal(`Failed to create mapping: ${error.message}`);
        updateStatus('Error', 'error');
    }
}

// Function to process commands one by one
async function processCommandsSequentially(commands) {
    let successCount = 0;
    let failCount = 0;
    let allSuccess = true;
    
    // Set batch command mode flag to enable scroll animation
    window.isBatchCommandMode = true;
    console.log('🔧 Starting batch command processing - batch mode set to:', window.isBatchCommandMode);
    
    for (let i = 0; i < commands.length; i++) {
        const command = commands[i].trim();
        if (!command) continue;
        
        updateStatus(`Processing command ${i+1}/${commands.length}...`, 'processing');
        
        // Set the command in the input field
        commandInput.value = command;
        
        try {
            // Wait a moment for UI to update
            await new Promise(resolve => setTimeout(resolve, 300));
            
            // Process the command using the batch-specific function
            await processBatchCommand(command);
            successCount++;
            
            // Wait between commands to allow for visual feedback
            await new Promise(resolve => setTimeout(resolve, 1000));
        } catch (error) {
            console.error('Error processing command:', error);
            failCount++;
            allSuccess = false;
            
            // Check if this is a script execution failure - if so, stop processing
            if (error.message === 'SCRIPT_EXECUTION_FAILED') {
                console.log('Script execution failed - stopping command processing');
                updateStatus(`Stopped at command ${i+1}/${commands.length} due to execution failure`, 'error');
                // Clear batch command mode flag
                window.isBatchCommandMode = false;
                return false; // Return false to indicate failure
            }
            
            // For other errors, continue with next command
            await new Promise(resolve => setTimeout(resolve, 500));
        }
    }
    
    // Show final status
    updateStatus(`Completed ${successCount}/${commands.length} commands`, 
                 failCount === 0 ? 'success' : 'warning');
    
    // Reset after a delay
    setTimeout(() => updateStatus('Ready', 'active'), 3000);
    
    // Clear batch command mode flag
    window.isBatchCommandMode = false;
    
    // Return true if all commands executed successfully
    return allSuccess;
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

// Add sheet tab rendering and switching
document.addEventListener('DOMContentLoaded', function() {
    const sheetTabContainer = document.getElementById('sheetTabContainer');
    
    // Initial render - assuming currentData.sheets is available
    if (currentData && currentData.sheets) {
        renderSheetTabs(currentData.sheets, sheetTabContainer, currentData.activeSheetIndex);
    }
});

// Handle sheet tab click
function onSheetTabClick(sheetIndex) {
    if (currentData && currentData.sheets && currentData.sheets.length > sheetIndex) {
        // Switch to the selected sheet
        switchSheet(currentData.sheets[sheetIndex]);
        
        // Update the active sheet index
        currentData.activeSheetIndex = sheetIndex;
        
        // Re-render the sheet tabs to reflect the active state
        const sheetTabContainer = document.getElementById('sheetTabContainer');
        renderSheetTabs(currentData.sheets, sheetTabContainer, sheetIndex);
    }
}

async function openAnalytics() {
  console.log('🚀 Opening Analytics Modal...');
  try {
    const analyticsModal = new bootstrap.Modal(document.getElementById('analyticsModal'));
    analyticsModal.show();

    const ensureChartLibs = () => new Promise((resolve, reject) => {
      const addScript = (src, flagKey) => new Promise((res, rej) => {
        if (window[flagKey]) return res();
        const s = document.createElement('script');
        s.src = src; s.async = true;
        s.onload = () => { window[flagKey] = true; res(); };
        s.onerror = () => rej(new Error('Failed to load ' + src));
        document.head.appendChild(s);
      });
      const tasks = [];
      if (!window.Chart) tasks.push(addScript('https://cdn.jsdelivr.net/npm/chart.js', '_chartJsLoaded'));
      if (!window._chartDateAdapterLoaded) tasks.push(addScript('https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns/dist/chartjs-adapter-date-fns.bundle.min.js', '_chartDateAdapterLoaded'));
      Promise.all(tasks).then(resolve).catch(reject);
    });

    await ensureChartLibs();

    const { initializeTokenDashboard, cleanupTokenDashboard } = await import('./tokenDashboard.js');
    await initializeTokenDashboard();

    const modalEl = document.getElementById('analyticsModal');
    const cleanupOnce = () => {
      modalEl.removeEventListener('hidden.bs.modal', cleanupOnce);
      try { cleanupTokenDashboard(); } catch (_) {}
    };
    modalEl.addEventListener('hidden.bs.modal', cleanupOnce);

    console.log('✅ Analytics Modal opened successfully');
  } catch (error) {
    console.error('❌ Error opening analytics modal:', error);
    showErrorModal('Error', 'Failed to open analytics dashboard. Please try again.');
  }
}

// ===== MAPPING MANAGEMENT FUNCTIONS =====

// Open the mapping management modal
async function openMappingManagement() {
  const modal = new bootstrap.Modal(document.getElementById('mappingManagementModal'));
  modal.show();

  // Load mappings when modal opens
  await loadMappings();

  // Ensure Chart.js libraries are available before initializing dashboard
  try {
    const ensureChartLibs = () => new Promise((resolve, reject) => {
      const addScript = (src, flagKey) => new Promise((res, rej) => {
        if (window[flagKey]) return res();
        const s = document.createElement('script');
        s.src = src; s.async = true;
        s.onload = () => { window[flagKey] = true; res(); };
        s.onerror = () => rej(new Error('Failed to load ' + src));
        document.head.appendChild(s);
      });
      const tasks = [];
      if (!window.Chart) tasks.push(addScript('https://cdn.jsdelivr.net/npm/chart.js', '_chartJsLoaded'));
      if (!window._chartDateAdapterLoaded) tasks.push(addScript('https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns/dist/chartjs-adapter-date-fns.bundle.min.js', '_chartDateAdapterLoaded'));
      Promise.all(tasks).then(resolve).catch(reject);
    });

    await ensureChartLibs();

    const { initializeTokenDashboard } = await import('./tokenDashboard.js');
    await initializeTokenDashboard();
  } catch (error) {
    console.error('Error initializing token dashboard:', error);
  }

  // Add event listeners for mapping management
  setupMappingEventListeners();
}

// Setup event listeners for mapping management
function setupMappingEventListeners() {
    const refreshBtn = document.getElementById('refreshMappingsBtn');
    const createNewBtn = document.getElementById('createNewMappingBtn');
    const commandFileInput = document.getElementById('mappingCommandFile');
    const saveMappingBtn = document.getElementById('saveMappingBtn');
    const spreadsheetNameInput = document.getElementById('mappingSpreadsheetName');
    
    // Remove existing listeners to prevent duplicates
    refreshBtn.removeEventListener('click', loadMappings);
    createNewBtn.removeEventListener('click', openCreateMappingModal);
    commandFileInput.removeEventListener('change', previewCommandFile);
    saveMappingBtn.removeEventListener('click', createNewMapping);
    spreadsheetNameInput.removeEventListener('input', validateMappingForm);
    
    // Add fresh listeners
    refreshBtn.addEventListener('click', async () => {
        const originalContent = refreshBtn.innerHTML;
        
        // Show loading state
        refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refreshing...';
        refreshBtn.disabled = true;
        
        try {
            await loadMappings();
        } finally {
            // Restore button state
            refreshBtn.innerHTML = originalContent;
            refreshBtn.disabled = false;
        }
    });
    createNewBtn.addEventListener('click', openCreateMappingModal);
    commandFileInput.addEventListener('change', previewCommandFile);
    saveMappingBtn.addEventListener('click', createNewMapping);
    spreadsheetNameInput.addEventListener('input', validateMappingForm);
}

// Load and display all mappings
async function loadMappings() {
    try {
        updateStatus('Loading mappings...', 'processing');
        
        const response = await fetch('/mappings');
        if (!response.ok) {
            throw new Error('Failed to load mappings');
        }
        
        const data = await response.json();
        
        updateMappingStats(data.stats);
        updateMappingsTable(data.mappings);
        
        updateStatus('Ready', 'active');
    } catch (error) {
        showErrorModal(`Error loading mappings: ${error.message}`);
        updateStatus('Error', 'error');
    }
}

function updateMappingStats(stats) {
    document.getElementById('activeMappingsCount').textContent = stats.active_mappings || 0;
    document.getElementById('totalCommandsCount').textContent = stats.total_commands || 0;
    document.getElementById('totalUsesCount').textContent = stats.total_uses || 0;
    document.getElementById('lastUpdatedDate').textContent = 
        stats.last_updated ? new Date(stats.last_updated).toLocaleDateString() : 'Never';
}

function updateMappingsTable(mappings) {
    const tbody = document.getElementById('mappingsTableBody');
    const noMappingsMsg = document.getElementById('noMappingsMessage');
    const table = tbody.closest('table');
    tbody.innerHTML = '';
    
    if (!mappings || mappings.length === 0) {
        table.style.display = 'none';
        noMappingsMsg.style.display = 'block';
        return;
    }
    tbody.innerHTML = '';
    
    table.style.display = 'table';
    noMappingsMsg.style.display = 'none';
    
    mappings.forEach(mapping => {
        const row = createMappingRow(mapping);
        tbody.appendChild(row);
    });
}

function createMappingRow(mapping) {
    const row = document.createElement('tr');
    
    const createdDate = mapping.created_at ? new Date(mapping.created_at).toLocaleDateString() : 'Unknown';
    const lastUsedDate = mapping.last_used ? new Date(mapping.last_used).toLocaleDateString() : 'Never';
    
    row.innerHTML = `
        <td>
            <span class="fw-bold">${mapping.spreadsheet_filename}</span>
            <br>
            <small class="text-muted">${mapping.spreadsheet_hash}</small>
        </td>
        <td>${mapping.command_filename}</td>
        <td>
            <span class="badge bg-primary">${mapping.command_count}</span>
            <button class="btn btn-sm btn-outline-info ms-2" onclick="viewMappingCommands('${mapping.mapping_id}')" title="View Commands">
                <i class="fas fa-eye"></i>
            </button>
        </td>
        <td>
            <span class="badge bg-success">${mapping.use_count}</span>
        </td>
        <td>
            <small>${createdDate}</small>
        </td>
        <td>
            <small>${lastUsedDate}</small>
        </td>
        <td>
            <button class="btn btn-sm btn-outline-warning me-1" onclick="console.log('Edit button clicked for:', '${mapping.mapping_id}'); editMapping('${mapping.mapping_id}')" title="Edit">
                <i class="fas fa-edit"></i>
            </button>
            <button class="btn btn-sm btn-outline-danger" onclick="console.log('Delete button clicked for:', '${mapping.mapping_id}'); deleteMapping('${mapping.mapping_id}')" title="Delete">
                <i class="fas fa-trash"></i>
            </button>
        </td>
    `;
    
    return row;
}

function openCreateMappingModal() {
    const createModal = new bootstrap.Modal(document.getElementById('createMappingModal'));
    createModal.show();
    
    document.getElementById('createMappingForm').reset();
    document.getElementById('mappingCommands').value = '';
    document.getElementById('saveMappingBtn').disabled = true;
    
    // Pre-fill spreadsheet name if available
    const currentSpreadsheetName = getCurrentSpreadsheetName();
    if (currentSpreadsheetName) {
        document.getElementById('mappingSpreadsheetName').value = currentSpreadsheetName;
    }
    
    // Re-validate form
    validateMappingForm();
}

// Preview command file content
async function previewCommandFile(event) {
    const file = event.target.files[0];
    const commandsTextarea = document.getElementById('mappingCommands');
    
    if (!file) {
        commandsTextarea.value = '';
        validateMappingForm();
        return;
    }
    
    try {
        const text = await file.text();
        const commands = text.split('\n').filter(line => line.trim());
        
        commandsTextarea.value = commands.join('\n');
        validateMappingForm();
        
    } catch (error) {
        showErrorModal(`Error reading file: ${error.message}`);
        commandsTextarea.value = '';
        validateMappingForm();
    }
}

// Validate mapping form and enable/disable save button
function validateMappingForm() {
    const spreadsheetName = document.getElementById('mappingSpreadsheetName').value.trim();
    const commandFile = document.getElementById('mappingCommandFile').files[0];
    const commands = document.getElementById('mappingCommands').value.trim();
    const saveBtn = document.getElementById('saveMappingBtn');
    
    // Enable save button if all required fields are filled
    saveBtn.disabled = !(spreadsheetName && commandFile && commands);
}

// Create new mapping
async function createNewMapping() {
    const spreadsheetName = document.getElementById('mappingSpreadsheetName').value.trim();
    const commandFile = document.getElementById('mappingCommandFile').files[0];
    const commandsText = document.getElementById('mappingCommands').value.trim();
    const commands = commandsText.split('\n').filter(line => line.trim());
    
    if (!spreadsheetName || !commandFile || commands.length === 0) {
        showErrorModal('Please provide all required information.');
        return;
    }
    
    try {
        updateStatus('Checking for conflicts...', 'processing');
        
        // Check for existing mappings for this spreadsheet
        const checkResponse = await fetch(`/check_mapping/${encodeURIComponent(spreadsheetName)}`);
        if (checkResponse.ok) {
            const checkData = await checkResponse.json();
            if (checkData.conflicts && checkData.conflicts.length > 0) {
                const conflictCount = checkData.conflicts.length;
                const shouldContinue = await showConfirm(
                    `Warning: This spreadsheet already has ${conflictCount} existing mapping(s).\n\n` +
                    `Creating a new mapping will result in multiple mappings for the same spreadsheet.\n\n` +
                    `Do you want to continue?`,
                    'Mapping Conflict Warning',
                    {
                        confirmText: 'Continue',
                        cancelText: 'Not Now',
                        confirmClass: 'btn-warning'
                    }
                );
                
                if (!shouldContinue) {
                    updateStatus('Mapping creation cancelled', 'warning');
                    setTimeout(() => updateStatus('Ready', 'active'), 2000);
                    return;
                }
            }
        }
        
        updateStatus('Creating mapping...', 'processing');
        
        const result = await apiCreateMapping(spreadsheetName, commandFile.name, commands);
        
        if (result && result.success) {
            // Close create modal
            const createModal = bootstrap.Modal.getInstance(document.getElementById('createMappingModal'));
            createModal.hide();
            
            // Refresh mappings
            await loadMappings();
            
            updateStatus('Mapping created successfully', 'active');
            setTimeout(() => updateStatus('Ready', 'active'), 2000);
        }
    } catch (error) {
        showErrorModal(`Error creating mapping: ${error.message}`);
        updateStatus('Error', 'error');
    }
}

// View mapping commands
async function viewMappingCommands(mappingId) {
    try {
        const response = await fetch(`/mapping/${mappingId}`);
        if (!response.ok) {
            throw new Error('Failed to load mapping details');
        }
        
        const data = await response.json();
        const mapping = data.mapping;
        
    // Create a modal to show commands with line numbers
    const numberedCommands = mapping.commands.map((command, index) => {
        return `<div class="command-line">${command}</div>`;
    }).join('');
    
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'viewCommandsModal';
    modal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header border-secondary">
                    <h5 class="modal-title">
                        <i class="fas fa-list me-2"></i>Commands for ${mapping.spreadsheet_filename}
                    </h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="commands-display">
                        <div class="commands-text">${numberedCommands}</div>
                    </div>
                </div>
                <div class="modal-footer border-secondary">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                        <i class="fas fa-times me-2"></i>Close
                    </button>
                </div>
            </div>
        </div>
    `;        document.body.appendChild(modal);
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
        
        // Remove modal after it's hidden
        modal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(modal);
        });
        
    } catch (error) {
        showErrorModal(`Error loading mapping commands: ${error.message}`);
    }
}

// Edit mapping - Show edit modal with mapping details
async function editMapping(mappingId) {
    try {
        console.log('🔧 Opening edit modal for mapping:', mappingId);
        
        // Fetch mapping details from the backend
        const response = await fetch(`/mapping/${mappingId}`);
        if (!response.ok) {
            throw new Error(`Failed to fetch mapping: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        const mapping = data.mapping || data; // Handle both response formats
        console.log('📋 Mapping details loaded:', mapping);
        
        // Populate the edit form
        document.getElementById('editMappingId').value = mapping.mapping_id;
        document.getElementById('editMappingSpreadsheetName').value = mapping.spreadsheet_filename;
        
        // Create numbered command lines for the contenteditable div (same as view modal)
        const editCommandsDiv = document.getElementById('editMappingCommands');
        const numberedCommands = mapping.commands.map((command, index) => {
            return `<div class="command-line">${command}</div>`;
        }).join('');
        editCommandsDiv.innerHTML = numberedCommands;
        
        // Setup contenteditable handlers
        setupEditCommandsHandlers();
        
        // Format and display metadata
        const createdDate = new Date(mapping.created_at).toLocaleString();
        document.getElementById('editMappingCreatedAt').textContent = createdDate;
        document.getElementById('editMappingUseCount').textContent = mapping.use_count || 0;
        
        // Show the edit modal with higher z-index and proper configuration
        const editModalElement = document.getElementById('editMappingModal');
        const editModal = new bootstrap.Modal(editModalElement, {
            backdrop: true,
            keyboard: true,
            focus: true
        });
        
        // Add event listeners to handle modal stacking
        editModalElement.addEventListener('shown.bs.modal', function() {
            // Ensure this modal is on top
            editModalElement.style.zIndex = '1100';
            
            // Find any other open modals and ensure they're below this one
            const openModals = document.querySelectorAll('.modal.show');
            openModals.forEach(modal => {
                if (modal !== editModalElement && modal.id === 'mappingManagementModal') {
                    modal.style.zIndex = '1055';
                }
            });
        });
        
        editModal.show();
        
        // Setup the update button event listener
        setupEditMappingEventListeners(mappingId);
        
        console.log('✅ Edit modal shown successfully');
        
    } catch (error) {
        console.error('❌ Error loading mapping for edit:', error);
        showErrorModal('Failed to load mapping details. Please try again.');
    }
}

// Setup event listeners for the edit mapping modal
function setupEditMappingEventListeners(mappingId) {
    const updateBtn = document.getElementById('updateMappingBtn');
    
    // Remove any existing event listeners to prevent duplicates
    const newUpdateBtn = updateBtn.cloneNode(true);
    updateBtn.parentNode.replaceChild(newUpdateBtn, updateBtn);
    
    // Add the update event listener
    newUpdateBtn.addEventListener('click', async () => {
        await updateMapping(mappingId);
    });
}

// Update mapping with new commands
async function updateMapping(mappingId) {
    try {
        const updateBtn = document.getElementById('updateMappingBtn');
        const originalContent = updateBtn.innerHTML;
        
        // Show loading state
        updateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Updating...';
        updateBtn.disabled = true;
        
        // Get the updated commands from contenteditable div
        const editCommandsDiv = document.getElementById('editMappingCommands');
        const commandLines = editCommandsDiv.querySelectorAll('.command-line');
        const commands = Array.from(commandLines).map(line => line.textContent.trim()).filter(cmd => cmd.length > 0);
        
        if (commands.length === 0) {
            showErrorModal('Commands cannot be empty. Please enter at least one command.');
            return;
        }
        
        // Use the API service to update the mapping
        const result = await apiUpdateMapping(mappingId, {
            commands: commands,
            command_count: commands.length
        });
        
        if (!result) {
            throw new Error('Failed to update mapping');
        }
        
        console.log('✅ Mapping updated successfully:', result);
        
        // Close the edit modal
        const editModal = bootstrap.Modal.getInstance(document.getElementById('editMappingModal'));
        editModal.hide();
        
        // Refresh the mappings list
        await loadMappings();
        
        // Show success message
        updateStatus('Mapping updated successfully!', 'success');
        setTimeout(() => updateStatus('Ready', 'active'), 3000);
        
    } catch (error) {
        console.error('❌ Error updating mapping:', error);
        showErrorModal('Failed to update mapping. Please try again.');
    } finally {
        // Always restore button state
        const updateBtn = document.getElementById('updateMappingBtn');
        if (updateBtn) {
            updateBtn.innerHTML = '<i class="fas fa-save"></i> Update Mapping';
            updateBtn.disabled = false;
        }
    }
}

// Delete mapping
async function deleteMapping(mappingId) {
    const confirmed = await showConfirm(
        'Are you sure you want to delete this mapping? This action cannot be undone.',
        'Delete Mapping',
        {
            confirmText: 'Delete',
            confirmClass: 'btn-danger'
        }
    );
    
    if (!confirmed) return;
    
    try {
        updateStatus('Deleting mapping...', 'processing');
        
        const result = await apiDeleteMapping(mappingId);
        
        if (result && result.success) {
            await loadMappings();
            updateStatus('Mapping deleted successfully', 'active');
            setTimeout(() => updateStatus('Ready', 'active'), 2000);
        }
    } catch (error) {
        showErrorModal(`Error deleting mapping: ${error.message}`);
        updateStatus('Error', 'error');
    }
}

// Create mapping for current session (existing function, keep it)
async function createMappingForCurrentSession(commandFileInfo) {
    try {
        updateStatus('Creating mapping...', 'processing');
        
        // Get current spreadsheet filename from session
        const currentSpreadsheetName = getCurrentSpreadsheetName();
        
        if (!currentSpreadsheetName) {
            showErrorModal('Unable to determine current spreadsheet name for mapping.');
            return;
        }
        
        const result = await apiCreateMapping(
            currentSpreadsheetName,
            commandFileInfo.filename,
            commandFileInfo.commands
        );
        
        if (result && result.success) {
            updateStatus('Mapping created successfully', 'active');
            setTimeout(() => updateStatus('Ready', 'active'), 2000);
        }
    } catch (error) {
        showErrorModal(`Error creating mapping: ${error.message}`);
        updateStatus('Error', 'error');
    }
}

// Setup handlers for contenteditable edit commands
function setupEditCommandsHandlers() {
    const editCommandsDiv = document.getElementById('editMappingCommands');
    
    // Handle Enter key to create new command lines
    editCommandsDiv.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            
            // Create a new command line div
            const newLine = document.createElement('div');
            newLine.className = 'command-line';
            newLine.innerHTML = '';
            
            // Insert the new line after the current selection
            const selection = window.getSelection();
            if (selection.rangeCount > 0) {
                const range = selection.getRangeAt(0);
                const currentLine = range.commonAncestorContainer.nodeType === Node.TEXT_NODE ? 
                    range.commonAncestorContainer.parentElement : range.commonAncestorContainer;
                
                if (currentLine.classList && currentLine.classList.contains('command-line')) {
                    currentLine.parentNode.insertBefore(newLine, currentLine.nextSibling);
                } else {
                    editCommandsDiv.appendChild(newLine);
                }
                
                // Focus on the new line
                newLine.focus();
                const newRange = document.createRange();
                newRange.selectNodeContents(newLine);
                newRange.collapse(true);
                selection.removeAllRanges();
                selection.addRange(newRange);
            }
        }
    });
    
    // Handle paste to maintain line structure
    editCommandsDiv.addEventListener('paste', function(e) {
        e.preventDefault();
        
        const pastedText = (e.clipboardData || window.clipboardData).getData('text');
        const lines = pastedText.split('\n').filter(line => line.trim());
        
        // Clear existing content if empty
        if (editCommandsDiv.textContent.trim() === '') {
            editCommandsDiv.innerHTML = '';
        }
        
        // Add each line as a command-line div
        lines.forEach(line => {
            const newLine = document.createElement('div');
            newLine.className = 'command-line';
            newLine.textContent = line.trim();
            editCommandsDiv.appendChild(newLine);
        });
    });
}

// Helper function to get current spreadsheet name
function getCurrentSpreadsheetName() {
    // First try to get from the global variable set during upload
    if (window.currentSpreadsheetFilename) {
        return window.currentSpreadsheetFilename;
    }
    
    // Fallback: try to get from currentData metadata
    if (currentData && currentData.metadata && currentData.metadata.filename) {
        return currentData.metadata.filename;
    }
    
    return null;
}

// Make functions available globally for onclick handlers
window.viewMappingCommands = viewMappingCommands;
window.editMapping = editMapping;
window.deleteMapping = deleteMapping;
window.openAnalytics = openAnalytics;

// Expose the onSheetTabClick function to the global scope for tab clicks
window.onSheetTabClick = onSheetTabClick;

function openCacheManagement() {
    const modal = new bootstrap.Modal(document.getElementById('cacheModal'));
    modal.show();
    
    setupCacheModalListeners();
}

function setupCacheModalListeners() {
    const buttonsConfig = [
        { id: 'deleteUploadsBtn', handler: deleteUploads },
        { id: 'deleteDownloadsBtn', handler: deleteDownloads },
        { id: 'deleteJsonBtn', handler: deleteJsonData },
        { id: 'deletePromptsBtn', handler: deletePrompts },
        { id: 'deleteScriptBtn', handler: deleteScripts },
        { id: 'deleteMappingsBtn', handler: deleteMappings },
        { id: 'allClearBtn', handler: performAllClear }
    ];
    
    buttonsConfig.forEach(config => {
        const button = document.getElementById(config.id);
        if (button) {
            // Remove existing listener if any
            button.removeEventListener('click', config.handler);
            // Add new listener
            button.addEventListener('click', config.handler);
        }
    });
}

/**
 * Delete all uploaded spreadsheet files
 */
async function deleteUploads() {
    const confirmed = await showConfirm(
        'Are you sure you want to clear all imported files? This action cannot be undone.',
        'Clear Imported Files',
        {
            confirmText: 'Confirm',
            confirmClass: 'btn-danger'
        }
    );
    
    if (confirmed) {
        const cacheModal = bootstrap.Modal.getInstance(document.getElementById('cacheModal'));
        if (cacheModal) {
            cacheModal.hide();
        }
        
        try {
            const response = await fetch('/cache/clear/uploads', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                await showAlert('Imported files have been cleared successfully.', 'Success', 'success');
            } else {
                throw new Error('Failed to delete uploads');
            }
        } catch (error) {
            console.error('Error deleting uploads:', error);
            await showAlert('Failed to clear imported files. Please try again.', 'Error', 'error');
        }
    }
}

async function deleteDownloads() {
    const confirmed = await showConfirm(
        'Are you sure you want to clear all exported files? This action cannot be undone.',
        'Clear Exported Files',
        {
            confirmText: 'Confirm',
            confirmClass: 'btn-danger'
        }
    );
    
    if (confirmed) {
        const cacheModal = bootstrap.Modal.getInstance(document.getElementById('cacheModal'));
        if (cacheModal) {
            cacheModal.hide();
        }
        
        try {
            const response = await fetch('/cache/clear/downloads', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                await showAlert('Exported files have been cleared successfully.', 'Success', 'success');
            } else {
                throw new Error('Failed to delete downloads');
            }
        } catch (error) {
            console.error('Error deleting downloads:', error);
            await showAlert('Failed to clear exported files. Please try again.', 'Error', 'error');
        }
    }
}

/**
 * Delete all JSON configuration files
 */
async function deleteJsonData() {
    const confirmed = await showConfirm(
        'Are you sure you want to reset all saved settings? This action cannot be undone.',
        'Clear Settings',
        {
            confirmText: 'Confirm',
            confirmClass: 'btn-danger'
        }
    );
    
    if (confirmed) {
        // Close the cache management modal
        const cacheModal = bootstrap.Modal.getInstance(document.getElementById('cacheModal'));
        if (cacheModal) {
            cacheModal.hide();
        }
        
        try {
            const response = await fetch('/cache/clear/json', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                await showAlert('Settings have been reset successfully.', 'Success', 'success');
            } else {
                throw new Error('Failed to delete JSON data');
            }
        } catch (error) {
            console.error('Error deleting JSON data:', error);
            await showAlert('Failed to reset settings. Please try again.', 'Error', 'error');
        }
    }
}

/**
 * Delete prompt history files (except prompts.txt) and clear prompts.txt content
 */
async function deletePrompts() {
    const confirmed = await showConfirm(
        'Are you sure you want to clear all saved history? This action cannot be undone.',
        'Clear History',
        {
            confirmText: 'Confirm',
            confirmClass: 'btn-danger'
        }
    );
    
    if (confirmed) {
        // Close the cache management modal
        const cacheModal = bootstrap.Modal.getInstance(document.getElementById('cacheModal'));
        if (cacheModal) {
            cacheModal.hide();
        }
        
        try {
            const response = await fetch('/cache/clear/prompts', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                await showAlert('History has been cleared successfully.', 'Success', 'success');
            } else {
                throw new Error('Failed to delete prompts');
            }
        } catch (error) {
            console.error('Error deleting prompts:', error);
            await showAlert('Failed to clear history. Please try again.', 'Error', 'error');
        }
    }
}

/**
 * Delete all generated Python scripts
 */
async function deleteScripts() {
    const confirmed = await showConfirm(
        'Are you sure you want to clear all saved automation rules? This action cannot be undone.',
        'Clear Automation',
        {
            confirmText: 'Confirm',
            confirmClass: 'btn-danger'
        }
    );
    
    if (confirmed) {
        // Close the cache management modal
        const cacheModal = bootstrap.Modal.getInstance(document.getElementById('cacheModal'));
        if (cacheModal) {
            cacheModal.hide();
        }
        
        try {
            const response = await fetch('/cache/clear/scripts', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                await showAlert('Automation rules have been cleared successfully.', 'Success', 'success');
            } else {
                throw new Error('Failed to delete scripts');
            }
        } catch (error) {
            console.error('Error deleting scripts:', error);
            await showAlert('Failed to clear automation rules. Please try again.', 'Error', 'error');
        }
    }
}

/**
 * Delete all mapping configuration files
 */
async function deleteMappings() {
    const confirmed = await showConfirm(
        'Are you sure you want to clear all saved connections? This action cannot be undone.',
        'Clear Connections',
        {
            confirmText: 'Confirm',
            confirmClass: 'btn-danger'
        }
    );
    
    if (confirmed) {
        // Close the cache management modal
        const cacheModal = bootstrap.Modal.getInstance(document.getElementById('cacheModal'));
        if (cacheModal) {
            cacheModal.hide();
        }
        
        try {
            const response = await fetch('/cache/clear/mappings', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                await showAlert('Connections have been cleared successfully.', 'Success', 'success');
            } else {
                throw new Error('Failed to delete mappings');
            }
        } catch (error) {
            console.error('Error deleting mappings:', error);
            await showAlert('Failed to clear mappings. Please try again.', 'Error', 'error');
        }
    }
}

/**
 * Perform all cache clearing operations
 */
async function performAllClear() {
    const confirmed = await showConfirm(
        'Are you sure you want to RESET THE ENTIRE WORKSPACE? This will clear all temporary files, settings, history, automation, and connections. This action cannot be undone.',
        'Reset Workspace - Irreversible Action',
        {
            confirmText: 'Confirm',
            confirmClass: 'btn-danger'
        }
    );
    
    if (confirmed) {
        // Close the cache management modal
        const cacheModal = bootstrap.Modal.getInstance(document.getElementById('cacheModal'));
        if (cacheModal) {
            cacheModal.hide();
        }
        
        try {
            const response = await fetch('/cache/clear/all', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                await showAlert('Workspace has been reset successfully. All temporary data has been cleared.', 'Workspace Reset Complete', 'success');
                // Reset the application UI state
                resetApplicationUI();
            } else {
                throw new Error('Failed to perform all clear');
            }
        } catch (error) {
            console.error('Error performing all clear:', error);
            await showAlert('Failed to reset workspace. Please try again.', 'Error', 'error');
        }
    }
}

// Make cache management functions available globally
window.openCacheManagement = openCacheManagement;
