import { initParticleBackground, cleanUpParticles } from './particleEffects.js';
import { 
    toggleSidebar, toggleFullscreen, updateStatus, resetApplicationUI, 
    updateUndoRedoButtons, showMainInterface, updateSessionInfo 
} from './uiInteractions.js';
import { handleFileUpload as apiHandleFileUpload, processCommand as apiProcessCommand, undoModification as apiUndoModification, redoModification as apiRedoModification, downloadSpreadsheet as apiDownloadSpreadsheet, createMapping as apiCreateMapping, getAllMappings as apiGetAllMappings, deleteMapping as apiDeleteMapping, updateMapping as apiUpdateMapping }
from './apiService.js';
import { renderSpreadsheet, loadSpreadsheetData as fetchSpreadsheetData, performTableUndo, performTableRedo, toggleSplitView, isSplitViewEnabled, renderSheetTabs, switchSheet } from './spreadsheetHandler.js';
import { setupShortcutKeys,getCurrentSessionPrompts,resetPromptHistory } from './shortcuts.js';
import { initCellSelector, clearCellSelector } from './cell-selector.js';
import { initCellTagger, scanAndHighlightTags } from './cell-tagger.js';
import { showAlert, showConfirm, showErrorModal } from './modalUtils.js';

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
const uploadCommandsBtn = document.getElementById('uploadCommandsBtn'); // Add this for upload commands button
const manageMappingsBtn = document.getElementById('manageMappingsBtn'); // Add this for manage mappings button
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
    
    // Add event listener for uploading command files
    uploadCommandsBtn.addEventListener('click', () => commandFileInput.click());
    commandFileInput.addEventListener('change', uploadCommandFile);
    
    // Add event listener for manage mappings button
    manageMappingsBtn.addEventListener('click', openMappingManagement);

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
        downloadCurrentSpreadsheet,
        openMappingManagement
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
        
        // Store the uploaded filename globally
        if (fileInput.files && fileInput.files.length > 0) {
            window.currentSpreadsheetFilename = fileInput.files[0].name;
        }
        
        // Check if there's a mapping for this spreadsheet
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
        
        // Initial data load after upload
        const initialData = await fetchSpreadsheetData(currentSessionId);
        if (initialData) {
            currentData = initialData;
            // If backend returns sheets, pass as workbook
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
    // Highlight any tagged cells one final time before sending - this is where selections should happen
    scanAndHighlightTags();
    
    try {
        const result = await apiProcessCommand(currentSessionId, commandText);
        if (result) {
            currentData = result;
            renderSpreadsheet(currentData);
            updateUndoRedoButtons(currentData.can_undo, currentData.can_redo);
            commandInput.value = '';
            resetPromptHistory(); // Reset prompt history navigation state        
        }
    } catch (error) {
        // Re-throw script execution failures so they can be caught by sequential processing
        if (error.message === 'SCRIPT_EXECUTION_FAILED') {
            throw error;
        }
        // For other errors, they're already handled by apiService.js
        console.error('Error in processCurrentCommand:', error);
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

// PLACEHOLDER: updateLeftSpreadsheet function - functionality removed  
// This function previously updated the left spreadsheet with transformed schema data
// New implementation will use different update mechanisms

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
            allSuccess = false;
            
            // Check if this is a script execution failure - if so, stop processing
            if (error.message === 'SCRIPT_EXECUTION_FAILED') {
                console.log('Script execution failed - stopping command processing');
                updateStatus(`Stopped at command ${i+1}/${commands.length} due to execution failure`, 'error');
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
    
    // Return true if all commands executed successfully
    return allSuccess;
}

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

// ===== MAPPING MANAGEMENT FUNCTIONS =====

// Open the mapping management modal
async function openMappingManagement() {
    const modal = new bootstrap.Modal(document.getElementById('mappingManagementModal'));
    modal.show();
    
    // Load mappings when modal opens
    await loadMappings();
    
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
    refreshBtn.addEventListener('click', loadMappings);
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
        
        // Update statistics
        updateMappingStats(data.stats);
        
        // Update mappings table
        updateMappingsTable(data.mappings);
        
        updateStatus('Ready', 'active');
    } catch (error) {
        showErrorModal(`Error loading mappings: ${error.message}`);
        updateStatus('Error', 'error');
    }
}

// Update mapping statistics display
function updateMappingStats(stats) {
    document.getElementById('activeMappingsCount').textContent = stats.active_mappings || 0;
    document.getElementById('totalCommandsCount').textContent = stats.total_commands || 0;
    document.getElementById('totalUsesCount').textContent = stats.total_uses || 0;
    document.getElementById('lastUpdatedDate').textContent = 
        stats.last_updated ? new Date(stats.last_updated).toLocaleDateString() : 'Never';
}

// Update mappings table
function updateMappingsTable(mappings) {
    const tbody = document.getElementById('mappingsTableBody');
    const noMappingsMsg = document.getElementById('noMappingsMessage');
    const table = tbody.closest('table');
    
    // Clear existing rows
    tbody.innerHTML = '';
    
    if (!mappings || mappings.length === 0) {
        table.style.display = 'none';
        noMappingsMsg.style.display = 'block';
        return;
    }
    
    table.style.display = 'table';
    noMappingsMsg.style.display = 'none';
    
    mappings.forEach(mapping => {
        const row = createMappingRow(mapping);
        tbody.appendChild(row);
    });
}

// Create a table row for a mapping
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
            <button class="btn btn-sm btn-outline-warning me-1" onclick="editMapping('${mapping.mapping_id}')" title="Edit">
                <i class="fas fa-edit"></i>
            </button>
            <button class="btn btn-sm btn-outline-danger" onclick="deleteMapping('${mapping.mapping_id}')" title="Delete">
                <i class="fas fa-trash"></i>
            </button>
        </td>
    `;
    
    return row;
}

// Open create mapping modal
function openCreateMappingModal() {
    const createModal = new bootstrap.Modal(document.getElementById('createMappingModal'));
    createModal.show();
    
    // Reset form
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
        
        // Create a simple modal to show commands
        const commandsText = mapping.commands.join('\n');
        
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content bg-dark text-light">
                    <div class="modal-header border-secondary">
                        <h5 class="modal-title">Commands for ${mapping.spreadsheet_filename}</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <textarea class="form-control bg-dark text-light border-secondary" rows="15" readonly>${commandsText}</textarea>
                    </div>
                    <div class="modal-footer border-secondary">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
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

// Edit mapping (placeholder for future implementation)
function editMapping(mappingId) {
    showErrorModal('Edit functionality coming soon!');
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

// Expose the onSheetTabClick function to the global scope for tab clicks
window.onSheetTabClick = onSheetTabClick;
