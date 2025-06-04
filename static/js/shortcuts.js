import { toggleFullscreen, toggleSidebar } from './uiInteractions.js';
// We'll need to import action handlers or pass them if they remain in main.js
// For now, assume they are callable globally or passed via main.js setup

export function setupShortcutKeys(app) { // app object to access methods like app.processCommand()
    const commandInput = document.getElementById('commandInput');
    const fileInput = document.getElementById('fileInput');
    const uploadForm = document.getElementById('uploadForm');
    const cellSelectorDisplay = document.getElementById('cellSelectorDisplay');

    document.addEventListener('keydown', function(e) {
        const isCommandInputActive = document.activeElement === commandInput;
        const isCellSelectorActive = document.activeElement === cellSelectorDisplay;

        // CTRL+SHIFT+X to focus the cell selector
        if (e.ctrlKey && e.shiftKey && (e.key === 'x' || e.key === 'X')) {
            e.preventDefault();
            cellSelectorDisplay.focus();
            cellSelectorDisplay.select();
            return;
        }

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
            if (!isCommandInputActive && !isCellSelectorActive) {
                e.preventDefault();
                if(app.undoLastModification) app.undoLastModification();
            }
            return;
        }
        if (e.ctrlKey && !e.shiftKey && (e.key === 'y' || e.key === 'Y')) {
            if (!isCommandInputActive && !isCellSelectorActive) {
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
        
        // Escape: Remove focus from cellSelectorDisplay and highlight it
        if (e.key === 'Escape' && isCellSelectorActive) {
            e.preventDefault();
            cellSelectorDisplay.blur();
            cellSelectorDisplay.classList.add('highlight-escape');
            setTimeout(() => cellSelectorDisplay.classList.remove('highlight-escape'), 600);
            return;
        }
    });
}
// Prompt history navigation state
let promptHistoryIndex = null;
let promptHistoryCache = [];
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
    const commandInput = document.getElementById('commandInput');
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
