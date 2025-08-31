import { toggleFullscreen, toggleSidebar } from './uiInteractions.js';

export function setupShortcutKeys(app) {
    const commandInput = document.getElementById('commandInput');
    const fileInput = document.getElementById('fileInput');
    const uploadForm = document.getElementById('uploadForm');
    const fullscreenBtn = document.getElementById('fullscreenBtn');  
    const savePromptBtn = document.getElementById('savePromptBtn');
    const promptLibraryBtn = document.getElementById('promptLibraryBtn');
    const cellSelectorDisplay = document.getElementById('cellSelectorDisplay');
    const updateSchemaBtn = document.getElementById('updateSchemaBtn');
    const transformSchemaBtn = document.getElementById('transformSchemaBtn');
    const splitViewBtn = document.getElementById('splitViewBtn');
    const uploadCommandsBtn = document.getElementById('uploadCommandsBtn');
    const commandFileInput = document.getElementById('commandFileInput');
    

    if (commandInput) {
        commandInput.addEventListener('focus', () => {
            promptHistoryActive = false;
            resetPromptHistory();
        });
    }

    document.addEventListener('keydown', function(e) {
        const isCommandInputActive = document.activeElement === commandInput;
        const isCellSelectorActive = document.activeElement === cellSelectorDisplay;

        if (e.altKey && e.shiftKey && (e.key === 'x' || e.key === 'X')) {
            e.preventDefault();
            cellSelectorDisplay.focus();
            cellSelectorDisplay.select();
            return;
        }

        if (e.altKey && e.shiftKey && (e.key === 'u' || e.key === 'U')) {
            e.preventDefault();
            fileInput.click();
            return;
        }
        if (e.altKey && !e.shiftKey && (e.key === 'u' || e.key === 'U')) {
            e.preventDefault();
            if (fileInput.files.length > 0) uploadForm.requestSubmit();
            else fileInput.click();
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
        if (e.altKey && !e.shiftKey && (e.key === 'd' || e.key === 'D')) {
            e.preventDefault();
            if(app.downloadCurrentSpreadsheet) app.downloadCurrentSpreadsheet();
            return;
        }
        if (e.altKey && e.shiftKey && (e.key === 'm' || e.key === 'M')) {
            e.preventDefault();
            toggleFullscreen();
            return;
        }
        if (e.altKey && !e.shiftKey && (e.key === 'm' || e.key === 'M')) {
            e.preventDefault();
            toggleSidebar();
            return;
        }
        if (e.key === 'Enter' && isCommandInputActive && !e.shiftKey && !e.ctrlKey && !e.altKey) {
            e.preventDefault();
            if(app.processCurrentCommand) app.processCurrentCommand();
            return;
        }

        if (e.key === 'Escape' && isCommandInputActive) {
            e.preventDefault();
            commandInput.blur();
            commandInput.classList.add('highlight-escape');
            setTimeout(() => commandInput.classList.remove('highlight-escape'), 600);
            return;
        }

        if (e.altKey && e.shiftKey && isCommandInputActive && (e.key === 's' || e.key === 'S')) {
            e.preventDefault();
            if (savePromptBtn) savePromptBtn.click();
            return;
        }
        if (e.altKey && e.shiftKey && (e.key === 'p' || e.key === 'P')) {
            e.preventDefault();
            if (promptLibraryBtn) promptLibraryBtn.click();
            return;
        }
        if (e.altKey && !e.shiftKey && (e.key === 'i' || e.key === 'I')) {
            e.preventDefault();
            if (commandInput) commandInput.focus();
            return;
        }
        
        if (e.altKey && !e.shiftKey && (e.key === 'g' || e.key === 'G')) {
            e.preventDefault();
            if (app.openMappingManagement) app.openMappingManagement();
            return;
        }
        
        if (e.altKey && !e.shiftKey && !isCommandInputActive && !isCellSelectorActive && (e.key === 'a' || e.key === 'A')) {
            e.preventDefault();
            if (app.openAnalytics) app.openAnalytics();
            return;
        }
        
        if (e.key === 'Escape' && isCellSelectorActive) {
            e.preventDefault();
            cellSelectorDisplay.blur();
            cellSelectorDisplay.classList.add('highlight-escape');
            setTimeout(() => cellSelectorDisplay.classList.remove('highlight-escape'), 600);
            return;
        }
        if (e.altKey && !isCommandInputActive && (e.key === 'f' || e.key === 'F')) {
            e.preventDefault();
            if (fullscreenBtn) fullscreenBtn.click();
            return;       
        }
        if (e.altKey && e.shiftKey && (e.key === 's' || e.key === 'S')) {
            e.preventDefault();
            if (splitViewBtn && !splitViewBtn.disabled) splitViewBtn.click();
            return;
        }
        if (e.altKey && e.shiftKey && (e.key === 'u' || e.key === 'U')) {
            e.preventDefault();
            if (updateSchemaBtn && !updateSchemaBtn.disabled) updateSchemaBtn.click();
            return;
        }
        if (e.altKey && e.shiftKey && (e.key === 't' || e.key === 'T')) {
            e.preventDefault();
            if (transformSchemaBtn && !transformSchemaBtn.disabled) transformSchemaBtn.click();
            return;
        }
        if (e.altKey && !e.shiftKey && (e.key === 'c' || e.key === 'C')) {
            e.preventDefault();
            if (uploadCommandsBtn) commandFileInput.click();
            return;
        }
    });
}

let promptHistoryIndex = null;
let promptHistoryCache = [];
let promptHistoryActive = false;

export async function getCurrentSessionPrompts(e){
    if (!e.altKey) return;

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
}

function getCurrentSessionId() {
    return window.currentSessionId !== undefined ? window.currentSessionId : null;
}

export async function handlePromptHistoryNavigation(e) {
    const commandInput = document.getElementById('commandInput');
    const currentSessionId = getCurrentSessionId();
    if (document.activeElement !== commandInput) return;
    if (!currentSessionId) return;

    if (!e.altKey) return;
    if (e.key !== 'ArrowUp' && e.key !== 'ArrowDown') return;

    e.preventDefault();

    if (promptHistoryIndex === null) {
        promptHistoryIndex = -1;
    }

    if (e.key === 'ArrowUp') {
        promptHistoryIndex++;
    } else if (e.key === 'ArrowDown') {
        promptHistoryIndex--;
        if (promptHistoryIndex < 0) promptHistoryIndex = 0;
    }

    if (promptHistoryCache[promptHistoryIndex] !== undefined) {
        commandInput.value = promptHistoryCache[promptHistoryIndex] || '';
    } else {
        const prompt = await fetchPromptFromHistory(promptHistoryIndex);
        if (prompt !== null) {
            promptHistoryCache[promptHistoryIndex] = prompt;
            commandInput.value = prompt;
        } else {
            if (e.key === 'ArrowUp') {
                promptHistoryIndex--;
            } else if (e.key === 'ArrowDown' && promptHistoryIndex > 0) {
                promptHistoryIndex--;
            }
        }
    }
}

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

export function resetPromptHistory() {
    promptHistoryIndex = null;
    promptHistoryCache = [];
}

export function showShortcutInfoIfSpreadsheetVisible() {
    const spreadsheetContainer = document.getElementById('spreadsheetContainer');
    const shortcutInfo = document.getElementById('shortcutInfo');
    if (spreadsheetContainer && shortcutInfo) {
        if (spreadsheetContainer.style.display !== 'none') {
            shortcutInfo.style.display = 'block';
        } else {
            shortcutInfo.style.display = 'none';
        }
    }
}

const observer = new MutationObserver(showShortcutInfoIfSpreadsheetVisible);
const spreadsheetContainer = document.getElementById('spreadsheetContainer');
if (spreadsheetContainer) {
    observer.observe(spreadsheetContainer, { attributes: true, attributeFilter: ['style'] });
}

document.addEventListener('DOMContentLoaded', showShortcutInfoIfSpreadsheetVisible);
