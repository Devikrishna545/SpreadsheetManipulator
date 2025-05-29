import { toggleFullscreen, toggleSidebar } from './uiInteractions.js';
// We'll need to import action handlers or pass them if they remain in main.js
// For now, assume they are callable globally or passed via main.js setup
const commandInput = document.getElementById('commandInput');
export function setupShortcutKeys(app) {    
    const fileInput = document.getElementById('fileInput');
    const uploadForm = document.getElementById('uploadForm');
    // Add prompt buttons for shortcuts
    const savePromptBtn = document.getElementById('savePromptBtn');
    const promptLibraryBtn = document.getElementById('promptLibraryBtn');

    document.addEventListener('keydown', function(e) {
        const isCommandInputActive = document.activeElement === commandInput;

        if (e.ctrlKey && e.shiftKey && (e.key === 'u' || e.key === 'U')) {
            e.preventDefault();
            fileInput.click();
            return;
        }
        if (e.ctrlKey && !e.shiftKey && (e.key === 'u' || e.key === 'U')) {
            e.preventDefault();
            if (fileInput.files.length > 0) uploadForm.requestSubmit(); // Only submit if file selected
            else fileInput.click(); // Open file dialog if no file selected
            return;
        }
        if (e.ctrlKey && !e.shiftKey && (e.key === 'z' || e.key === 'Z')) {
            if (!isCommandInputActive) {
                e.preventDefault();
                if(app.undoLastModification) app.undoLastModification();
            }
            return;
        }
        if (e.ctrlKey && !e.shiftKey && (e.key === 'y' || e.key === 'Y')) {
            if (!isCommandInputActive) {
                e.preventDefault();
                if(app.redoLastModification) app.redoLastModification();
            }
            return;
        }
        if (e.ctrlKey && !e.shiftKey && (e.key === 'd' || e.key === 'D')) {
            e.preventDefault();
            if(app.downloadCurrentSpreadsheet) app.downloadCurrentSpreadsheet();
            return;
        }
        if (e.ctrlKey && e.shiftKey && (e.key === 'm' || e.key === 'M')) {
            e.preventDefault();
            toggleFullscreen();
            return;
        }
        if (e.ctrlKey && !e.shiftKey && (e.key === 'm' || e.key === 'M')) {
            e.preventDefault();
            toggleSidebar();
            return;
        }
        if (e.key === 'Enter' && isCommandInputActive && !e.shiftKey && !e.ctrlKey && !e.altKey) {
            e.preventDefault();
            if(app.processCurrentCommand) app.processCurrentCommand();
            return;
        }

        // Escape: Remove focus from commandInput and highlight it
        if (e.key === 'Escape' && isCommandInputActive) {
            e.preventDefault();
            commandInput.blur();
            commandInput.classList.add('highlight-escape');
            setTimeout(() => commandInput.classList.remove('highlight-escape'), 600);
            return;
        }        
        // Ctrl+Shift+S: Save prompt
        if (e.ctrlKey && e.shiftKey && isCommandInputActive && (e.key === 's' || e.key === 'S')) {
            e.preventDefault();
            if (savePromptBtn) savePromptBtn.click();
            return;
        }
        // Ctrl+Shift+P: View prompts
        if (e.ctrlKey && e.shiftKey && (e.key === 'p' || e.key === 'P')) {
            e.preventDefault();
            if (promptLibraryBtn) promptLibraryBtn.click();
            return;
        }
        // Ctrl+I: Focus command input
        if (e.ctrlKey && !e.shiftKey && (e.key === 'i' || e.key === 'I')) {
            e.preventDefault();
            if (commandInput) commandInput.focus();
            return;
        }
    });
}

// Prompt history navigation state
let promptHistoryIndex = null;
let promptHistoryCache = [];
let promptHistoryActive = false;
export async function getCurrentSessionPrompts(e){
    // Only trigger for ArrowUp/ArrowDown to avoid interfering with other shortcuts
    if (!promptHistoryActive) {
        if (e.key === 'ArrowUp') {
            promptHistoryActive = true;
            handlePromptHistoryNavigation(e);
        }
    } else {
        if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
            handlePromptHistoryNavigation(e);
        }
    }  
       commandInput.addEventListener('focus', function() {
            promptHistoryActive = false;           
            resetPromptHistory();
        });
}

/**
 * Helper to always get the latest currentSessionId from main.js/global
 */
function getCurrentSessionId() {
    return window.currentSessionId !== undefined ? window.currentSessionId : null;
}

/**
 * Handle up/down arrow navigation in command input for prompt history
 */
export async function handlePromptHistoryNavigation(e) {    
    const currentSessionId = getCurrentSessionId();
    if (document.activeElement !== commandInput) return;
    if (!currentSessionId) return;

    // Only handle up/down arrows
    if (e.key !== 'ArrowUp' && e.key !== 'ArrowDown') return;

    e.preventDefault();

    // Initialize index if not set
    if (promptHistoryIndex === null) {
        promptHistoryIndex = -1; // Start at -1 to fetch the most recent prompt first
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
 * Fetch a prompt from history for the current session
 * @param {number} index - The index in the history (0 = most recent)
 * @returns {Promise<string|null>} - The prompt string or null if not found
 */
async function fetchPromptFromHistory(index) {
    const currentSessionId = getCurrentSessionId();
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
 * Reset prompt history navigation state
 */
export function resetPromptHistory() {
    promptHistoryIndex = null;
    promptHistoryCache = [];
}
// Show shortcut info when spreadsheet is uploaded/displayed
export function showShortcutInfoIfSpreadsheetVisible() {
    const spreadsheetContainer = document.getElementById('spreadsheetContainer');
    const shortcutInfo = document.getElementById('shortcutInfo');
    if (spreadsheetContainer && shortcutInfo) {
        if (spreadsheetContainer.style.display !== 'none') {
            shortcutInfo.style.display = '';
        } else {
            shortcutInfo.style.display = 'none';
        }
    }
}

// Hook into spreadsheet display logic
const observer = new MutationObserver(showShortcutInfoIfSpreadsheetVisible);
observer.observe(document.getElementById('spreadsheetContainer'), { attributes: true, attributeFilter: ['style'] });

// Also call once on load in case spreadsheet is already visible
document.addEventListener('DOMContentLoaded', showShortcutInfoIfSpreadsheetVisible);
    