import { showConfirm } from './modalUtils.js';
import { resetApplicationState } from './main.js';
import { showLoading, hideLoading, showError, updateStatus, showMainInterface, updateSessionInfo, showAlgorithmLoading } from './uiInteractions.js';

function sessionHeaders() {
    try {
        if (window && window.currentSessionId) {
            return { 'X-Session-Id': window.currentSessionId };
        }
    } catch {}
    return {};
}

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
            headers: { ...sessionHeaders() },
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
        return data;
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
            headers: { 'Content-Type': 'application/json', ...sessionHeaders() },
            body: JSON.stringify({ sessionId, command })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            
            if (response.status === 422 && errorData.detail?.error === 'SCRIPT_EXECUTION_FAILED') {
                throw new Error(`SCRIPT_EXECUTION_FAILED: ${errorData.detail.message}`);
            }
            
            throw new Error(errorData.detail || 'Failed to process command');
        }
        
        const data = await response.json();
        updateStatus('Command Executed', 'active');        
        setTimeout(() => updateStatus('Ready', 'active'), 3000);
        return data;
    } catch (error) {
        updateStatus('Error', 'error');
        
        if (error.message.startsWith('SCRIPT_EXECUTION_FAILED:')) {
            const userMessage = error.message.replace('SCRIPT_EXECUTION_FAILED: ', '');
            showError(userMessage);
            throw new Error('SCRIPT_EXECUTION_FAILED');
        } else {
            showError(error.message);
        }
        return null;
    } finally {
        hideLoading();
    }
}

export async function undoModification(sessionId) {
    if (!sessionId) return null;
    showLoading('Undoing last modification...');
    try {
        const response = await fetch(`/undo/${sessionId}`, { method: 'POST', headers: { ...sessionHeaders() } });
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
        const response = await fetch(`/redo/${sessionId}`, { method: 'POST', headers: { ...sessionHeaders() } });
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
    
    fetch(`/download/${sessionId}`, { headers: { ...sessionHeaders() } })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.detail || 'Failed to download file');
                });
            }
            return response.blob();
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            
            fetch(`/download/${sessionId}`, { method: 'HEAD', headers: { ...sessionHeaders() } })
                .then(headResp => {
                    let filename = 'spreadsheet.xlsx';
                    const disposition = headResp.headers.get('Content-Disposition');
                    if (disposition && disposition.indexOf('filename=') !== -1) {
                        filename = disposition.split('filename=')[1].replace(/["']/g, '');
                    }
                    a.href = url;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    setTimeout(async () => {
                        document.body.removeChild(a);
                        window.URL.revokeObjectURL(url);
                        
                        const shouldReload = await showConfirm(
                            'Your session has been completed. The spreadsheet and all related data have been cleaned up.',
                            'Session Complete',
                            {
                                confirmText: 'Return to Start',
                                cancelText: 'Stay Here',
                                confirmClass: 'btn-primary'
                            }
                        );
                        
                        if (shouldReload) {
                            window.location.reload();
                        } else {
                            resetApplicationState();
                        }
                    }, 30000);
                });
        })
        .catch(error => {
            updateStatus('Error', 'error');
            showError(error.message);
        });
}

export async function generateAndExecuteAlgorithm(sessionId, actionPlan, leftData, rightData) {
    if (!sessionId) {
        showError('No active session. Please upload a spreadsheet first.');
        return null;
    }
    
    updateStatus('Generating universal algorithm...', 'processing');
    showAlgorithmLoading('Analyzing action plan and generating universal algorithm...');
    
    try {
        const response = await fetch('/generate_algorithm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...sessionHeaders() },
            body: JSON.stringify({ 
                sessionId, 
                actionPlan,
                leftSpreadsheetData: leftData,
                rightSpreadsheetData: rightData
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to generate universal algorithm');
        }
        
        const data = await response.json();
        updateStatus('Universal algorithm executed successfully', 'success');        
        setTimeout(() => updateStatus('Ready', 'active'), 3000);
        return data;
    } catch (error) {
        updateStatus('Error', 'error');
        showError(`Algorithm generation failed: ${error.message}`);
        return null;
    } finally {
        hideLoading();
    }
}

// Mapping API functions
export async function createMapping(spreadsheetFilename, commandFilename, commands) {
    try {
        const response = await fetch('/create_mapping', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...sessionHeaders() },
            body: JSON.stringify({
                spreadsheet_filename: spreadsheetFilename,
                command_filename: commandFilename,
                commands: commands
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to create mapping');
        }
        
        return await response.json();
    } catch (error) {
        showError(`Error creating mapping: ${error.message}`);
        return { success: false, error: error.message };
    }
}

export async function getAllMappings() {
    try {
        const response = await fetch('/mappings', { headers: { ...sessionHeaders() } });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to get mappings');
        }
        
        return await response.json();
    } catch (error) {
        showError(`Error getting mappings: ${error.message}`);
        return null;
    }
}

export async function deleteMapping(mappingId) {
    try {
        const response = await fetch(`/mapping/${mappingId}`, {
            method: 'DELETE',
            headers: { ...sessionHeaders() }
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to delete mapping');
        }
        
        return await response.json();
    } catch (error) {
        showError(`Error deleting mapping: ${error.message}`);
        return null;
    }
}

export async function updateMapping(mappingId, updates) {
    try {
        const response = await fetch(`/mapping/${mappingId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', ...sessionHeaders() },
            body: JSON.stringify(updates)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to update mapping');
        }
        
        return await response.json();
    } catch (error) {
        showError(`Error updating mapping: ${error.message}`);
        return null;
    }
}
