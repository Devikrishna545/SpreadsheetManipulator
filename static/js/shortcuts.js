import { toggleFullscreen, toggleSidebar } from './uiInteractions.js';
// We'll need to import action handlers or pass them if they remain in main.js
// For now, assume they are callable globally or passed via main.js setup

export function setupShortcutKeys(app) { // app object to access methods like app.processCommand()
    const commandInput = document.getElementById('commandInput');
    const fileInput = document.getElementById('fileInput');
    const uploadForm = document.getElementById('uploadForm');

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
    });
}
