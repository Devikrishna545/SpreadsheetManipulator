import { showLoading, hideLoading, showError } from './uiInteractions.js';
import { updateUndoRedoButtons, updateStatus } from './uiInteractions.js';
import { updateCellSelector, clearCellSelector } from './cell-selector.js';

const spreadsheetDataContainer = document.getElementById('spreadsheetData');
let pendingChanges = []; // Store changes to batch submit
let isProcessingChanges = false; // Prevent overlapping change submissions

// Add these variables to track split view state
let isSplitViewActive = false;
let editableHotInstance = null;

export function renderSpreadsheet(data) { // data is currentData from main.js
    if (!data || !data.data) return;
    
    if (window.hotInstance) {
        window.hotInstance.destroy();
    }
    
    // Generate Excel-style column headers (A, B, C, ...)
    const columnCount = data.data[0] ? data.data[0].length : 0;
    const alphabeticHeaders = generateExcelColHeaders(columnCount);
    
    const settings = {
        data: data.data,
        rowHeaders: true,
        colHeaders: alphabeticHeaders, // Use alphabetic headers instead of data.headers
        licenseKey: 'non-commercial-and-evaluation',
        stretchH: 'all',
        readOnly: true, // Changed from false to true to make non-editable
        contextMenu: true, // Enable context menu for row/column operations
        manualColumnResize: true,
        manualRowResize: true,
        className: 'htDark',
        outsideClickDeselects: false, // Persist selection when clicking outside
        multiSelect: true, // Enable multiple selection of cell ranges
        fillHandle: true, // Enable the drag-down fill handle for data entry
        afterRender: function() {
            this.rootElement.classList.add('handsontable-dark');
        },
        afterSelection: function(r, c, r2, c2, preventScrolling, selectionLayerLevel) {
            // Update cell selector with all selected ranges
            // getSelected returns an array of [startRow, startCol, endRow, endCol] arrays
            updateCellSelector(this.getSelected());
        },
        afterDeselect: function() {
            // Clear cell selector only if there's truly no selection
            const currentSelection = this.getSelected();
            if (!currentSelection || currentSelection.length === 0) {
                clearCellSelector();
            }
        },
        afterInit: function() {
            // Initialize with first cell selected
            this.selectCell(0, 0);
        },
        // Track changes for undo/redo functionality
        afterChange: function(changes, source) {
            if (source === 'loadData') return; // Skip initial data load
            if (!changes) return;
            
            // Process changes for undo/redo
            if (source !== 'undo' && source !== 'redo') {
                const changeData = {
                    type: 'cell',
                    changes: changes.map(([row, prop, oldValue, newValue]) => ({
                        row, 
                        col: typeof prop === 'string' ? this.propToCol(prop) : prop,
                        oldValue, 
                        newValue
                    }))
                };
                
                // Add to pending changes queue
                pendingChanges.push(changeData);
                
                // Debounce to avoid too many API calls
                submitPendingChanges();
            }
        },
        afterCreateRow: function(index, amount, source) {
            if (source === 'loadData') return;
            if (source !== 'undo' && source !== 'redo') {
                pendingChanges.push({
                    type: 'row',
                    action: 'create',
                    index,
                    amount
                });
                submitPendingChanges();
            }
        },
        afterRemoveRow: function(index, amount, source) {
            if (source === 'loadData') return;
            if (source !== 'undo' && source !== 'redo') {
                pendingChanges.push({
                    type: 'row',
                    action: 'remove',
                    index,
                    amount
                });
                submitPendingChanges();
            }
        },
        afterCreateCol: function(index, amount, source) {
            if (source === 'loadData') return;
            if (source !== 'undo' && source !== 'redo') {
                pendingChanges.push({
                    type: 'col',
                    action: 'create',
                    index,
                    amount
                });
                submitPendingChanges();
            }
        },
        afterRemoveCol: function(index, amount, source) {
            if (source === 'loadData') return;
            if (source !== 'undo' && source !== 'redo') {
                pendingChanges.push({
                    type: 'col',
                    action: 'remove',
                    index,
                    amount
                });
                submitPendingChanges();
            }
        },
        // Add options to context menu
        contextMenu: {
            items: {
                'row_above': {name: 'Insert row above'},
                'row_below': {name: 'Insert row below'},
                'col_left': {name: 'Insert column left'},
                'col_right': {name: 'Insert column right'},
                'remove_row': {name: 'Remove row'},
                'remove_col': {name: 'Remove column'},
                'separator1': '---------',
                'undo': {name: 'Undo'},
                'redo': {name: 'Redo'}
            }
        }
    };
    
    window.hotInstance = new Handsontable(spreadsheetDataContainer, settings);
    
    if (data.modified_cells && data.modified_cells.length > 0) {
        highlightModifiedCells(data.modified_cells);
    }
}

// Function to submit pending changes to the server
function submitPendingChanges() {
    if (pendingChanges.length === 0 || isProcessingChanges) return;
    
    // Prevent multiple simultaneous submissions
    isProcessingChanges = true;
    
    // Get the current session ID from the window global
    const sessionId = window.currentSessionId;
    if (!sessionId) {
        pendingChanges = [];
        isProcessingChanges = false;
        return;
    }
    
    // Clone the changes array and clear the pending queue
    const changes = [...pendingChanges];
    pendingChanges = [];
    
    updateStatus('Saving changes...', 'processing');
    
    // Submit changes to the server
    fetch('/table_changes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sessionId, changes })
    })
    .then(response => {
        if (!response.ok) throw new Error('Failed to save changes');
        return response.json();
    })
    .then(data => {
        // --- Always re-render spreadsheet with latest data from backend ---
        renderSpreadsheet(data);
        updateUndoRedoButtons(data.can_undo, data.can_redo);
        updateStatus('Changes saved', 'active');
        setTimeout(() => updateStatus('Ready', 'active'), 2000);
    })
    .catch(error => {
        showError(`Error saving changes: ${error.message}`);
        updateStatus('Error', 'error');
    })
    .finally(() => {
        isProcessingChanges = false;
        // Check if more changes accumulated during processing
        if (pendingChanges.length > 0) {
            setTimeout(submitPendingChanges, 100);
        }
    });
}

// Add function to generate Excel-style column headers
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

function highlightModifiedCells(modifiedCells) {
    if (!window.hotInstance) return;
    for (const [row, col] of modifiedCells) {
        const td = window.hotInstance.getCell(row, col);
        if (td) {
            td.classList.add('modified');
            setTimeout(() => {
                td.classList.remove('modified');
            }, 2000);
        }
    }
}

export async function loadSpreadsheetData(sessionId) {
    if (!sessionId) return null;
    showLoading('Loading spreadsheet data...');
    try {
        const response = await fetch(`/view/${sessionId}`);
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Failed to load spreadsheet data');
        return data; 
    } catch (error) {
        showError(error.message);
        return null;
    } finally {
        hideLoading();
    }
}

// New function to manually trigger undo/redo in the table
export function performTableUndo() {
    if (window.hotInstance) {
        window.hotInstance.undo();
    }
}

export function performTableRedo() {
    if (window.hotInstance) {
        window.hotInstance.redo();
    }
}

/**
 * Toggle between normal and split view modes
 */
export function toggleSplitView() {
    const spreadsheetDataContainer = document.getElementById('spreadsheetData');
    
    if (!window.hotInstance || !spreadsheetDataContainer) {
        showError("No spreadsheet is loaded.");
        return;
    }
    
    if (isSplitViewActive) {
        // Disable split view
        const splitContainer = document.querySelector('.split-view-container');
        if (splitContainer) {
            // Get the parent of the split container
            const parent = splitContainer.parentNode;
            
            // Remove the split container and its contents
            while (splitContainer.firstChild) {
                splitContainer.removeChild(splitContainer.firstChild);
            }
            parent.removeChild(splitContainer);
            
            // Re-add the original spreadsheet container
            parent.appendChild(spreadsheetDataContainer);
            
            // Destroy the editable instance if it exists
            if (editableHotInstance) {
                editableHotInstance.destroy();
                editableHotInstance = null;
            }
        }
        
        // Update button icon and status
        const splitViewBtn = document.getElementById('splitViewBtn');
        if (splitViewBtn) {
            splitViewBtn.innerHTML = '<i class="fas fa-columns"></i>';
            splitViewBtn.title = 'Split View';
        }
        
        isSplitViewActive = false;
        
        // Re-render the main spreadsheet
        window.hotInstance.render();
        updateStatus('Split view disabled', 'active');
        setTimeout(() => updateStatus('Ready', 'active'), 2000);
    } else {
        // Enable split view
        // Create split view container
        const splitContainer = document.createElement('div');
        splitContainer.className = 'split-view-container';
        
        // Create left pane (original spreadsheet)
        const leftPane = document.createElement('div');
        leftPane.className = 'split-view-pane original-pane';
        const leftLabel = document.createElement('div');
        leftLabel.className = 'pane-label';
        leftLabel.textContent = 'Original (Read-only)';
        leftPane.appendChild(leftLabel);
        
        // Create right pane (editable spreadsheet)
        const rightPane = document.createElement('div');
        rightPane.className = 'split-view-pane editable-pane';
        const rightLabel = document.createElement('div');
        rightLabel.className = 'pane-label';
        rightLabel.textContent = 'Editable';
        rightPane.appendChild(rightLabel);
        
        // Create the right pane content
        const rightContent = document.createElement('div');
        rightContent.id = 'rightSpreadsheet'; // Set correct id for right spreadsheet
        rightPane.appendChild(rightContent);
        
        // Add panes to the split container
        splitContainer.appendChild(leftPane);
        splitContainer.appendChild(rightPane);
        
        // Get the parent of the current spreadsheet container
        const parent = spreadsheetDataContainer.parentNode;
        
        // Remove the current spreadsheet container from DOM
        parent.removeChild(spreadsheetDataContainer);
        
        // Add the split container to the parent
        parent.appendChild(splitContainer);
        
        // Move the original spreadsheet container to the left pane
        leftPane.appendChild(spreadsheetDataContainer);
        
        // Create a new Handsontable instance for the right pane
        const currentData = window.hotInstance.getData();
        const columnCount = currentData[0] ? currentData[0].length : 0;
        const rowCount = currentData.length;
        
        // Create blank data with same dimensions
        const blankData = Array(rowCount).fill(0).map(() => Array(columnCount).fill(null));
        
        // Generate Excel-style column headers
        const alphabeticHeaders = generateExcelColHeaders(columnCount);
        
        // Create settings for the editable spreadsheet
        const editableSettings = {
            data: blankData,
            rowHeaders: true,
            colHeaders: alphabeticHeaders,
            licenseKey: 'non-commercial-and-evaluation',
            stretchH: 'all',
            readOnly: false, // Make this editable
            contextMenu: true,
            manualColumnResize: true,
            manualRowResize: true,
            className: 'htDark',
            afterRender: function() {
                this.rootElement.classList.add('handsontable-dark');
            }
        };
        
        // Create the editable Handsontable instance
        editableHotInstance = new Handsontable(
            rightContent,
            editableSettings
        );
        // Assign the instance to the DOM for main.js access
        rightContent.hotInstance = editableHotInstance;
        
        // Update button icon and status
        const splitViewBtn = document.getElementById('splitViewBtn');
        if (splitViewBtn) {
            splitViewBtn.innerHTML = '<i class="fas fa-compress-arrows-alt"></i>';
            splitViewBtn.title = 'Exit Split View';
        }
        
        isSplitViewActive = true;
        
        // Re-render both spreadsheets
        window.hotInstance.render();
        editableHotInstance.render();
        updateStatus('Split view enabled', 'active');
        setTimeout(() => updateStatus('Ready', 'active'), 2000);
    }
}

// Add getter for split view state
export function isSplitViewEnabled() {
    return isSplitViewActive;
}

// Add getter for the editable instance
export function getEditableInstance() {
    return editableHotInstance;
}
