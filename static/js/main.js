import { initParticleBackground, cleanUpParticles } from './particleEffects.js';
import { toggleSidebar, toggleFullscreen, updateStatus, resetApplicationUI, updateUndoRedoButtons} 
from './uiInteractions.js';
import { handleFileUpload as apiHandleFileUpload, processCommand as apiProcessCommand, undoModification as apiUndoModification, redoModification as apiRedoModification, downloadSpreadsheet as apiDownloadSpreadsheet }
from './apiService.js';
import { renderSpreadsheet, loadSpreadsheetData as fetchSpreadsheetData } from './spreadsheetHandler.js';
import { setupShortcutKeys,handlePromptHistoryNavigation,resetPromptHistory } from './shortcuts.js';

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

    // Add window unload handler to clean up particles
    window.addEventListener('beforeunload', cleanUpParticles);
});

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
    }
}

async function redoLastModification() {
    const result = await apiRedoModification(currentSessionId);
    if (result) {
        currentData = result;
        renderSpreadsheet(currentData);
        updateUndoRedoButtons(currentData.can_undo, currentData.can_redo);
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
}

// Export for prompts.js to access current prompt
export function getCurrentPromptText() {
    return commandInput.value;
}
export function setCurrentPromptText(text) {
    commandInput.value = text;
}
