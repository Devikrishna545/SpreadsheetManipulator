import { showLoading, hideLoading, showError, updateStatus, showMainInterface, updateSessionInfo } from './uiInteractions.js';
import { resetApplicationState } from './main.js'; // Assuming main.js will export this

export async function handleFileUpload(event, fileInput) {
    event.preventDefault();
    
    const file = fileInput.files[0];
    if (!file) {
        showError('Please select a file to upload.');
        return null;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    updateStatus('Uploading...', 'processing');
    showLoading('Uploading spreadsheet...');
    
    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to upload file');
        }
        
        const data = await response.json();
        updateSessionInfo(file.name, 'Active');
        showMainInterface();
        updateStatus('Ready', 'active');
        return data; // Return { sessionId, ... }
    } catch (error) {
        updateStatus('Error', 'error');
        showError(error.message);
        return null;
    } finally {
        hideLoading();
    }
}

export async function processCommand(sessionId, command) {
    if (!command) {
        showError('Please enter a command.');
        return null;
    }
    if (!sessionId) {
        showError('No active session. Please upload a spreadsheet first.');
        return null;
    }
    
    updateStatus('Processing...', 'processing');
    showLoading('Processing your command...');
    
    try {
        const response = await fetch('/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sessionId, command })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to process command');
        }
        
        const data = await response.json();
        updateStatus('Command Executed', 'active');        
        setTimeout(() => updateStatus('Ready', 'active'), 3000);
        return data;
    } catch (error) {
        updateStatus('Error', 'error');
        showError(error.message);
        return null;
    } finally {
        hideLoading();
    }
}

export async function undoModification(sessionId) {
    if (!sessionId) return null;
    showLoading('Undoing last modification...');
    try {
        const response = await fetch(`/undo/${sessionId}`, { method: 'POST' });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Failed to undo modification');
        return data;
    } catch (error) {
        showError(error.message);
        return null;
    } finally {
        hideLoading();
    }
}

export async function redoModification(sessionId) {
    if (!sessionId) return null;
    showLoading('Redoing modification...');
    try {
        const response = await fetch(`/redo/${sessionId}`, { method: 'POST' });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Failed to redo modification');
        return data;
    } catch (error) {
        showError(error.message);
        return null;
    } finally {
        hideLoading();
    }
}

export function downloadSpreadsheet(sessionId) {
    if (!sessionId) return;
    updateStatus('Downloading...', 'processing');
    window.location.href = `/download/${sessionId}`;
    
    setTimeout(() => {
        if (confirm('Your session has been completed. The spreadsheet and all related data have been cleaned up. Click OK to return to the start page.')) {
            // Refresh the page after user confirms
            window.location.reload();
        } else {
            // Still reset the application state even if they cancel
            resetApplicationState();
        }
    }, 2000);
}
