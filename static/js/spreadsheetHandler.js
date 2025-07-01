import { showLoading, hideLoading, showError, showAlgorithmLoading } from './uiInteractions.js';
import { updateUndoRedoButtons, updateStatus } from './uiInteractions.js';
import { updateCellSelector, clearCellSelector } from './cell-selector.js';

const spreadsheetDataContainer = document.getElementById('spreadsheetData');
const sheetTabContainer = document.getElementById('sheetTabContainer'); // New: sheet tab bar
let workbookSheets = []; // [{name, data}]
let currentSheetIndex = 0;
let pendingChanges = []; // Store changes to batch submit
let isProcessingChanges = false; // Prevent overlapping change submissions

// Add these variables to track split view state
let isSplitViewActive = false;
let editableHotInstance = null;

export function renderSpreadsheet(data) { // data is currentData from main.js
    if (!data) return;

    // Detect workbook (multiple sheets)
    if (data.sheets && Array.isArray(data.sheets) && data.sheets.length > 0) {
        workbookSheets = data.sheets;
        // Default to first sheet if not set
        if (typeof data.activeSheetIndex === 'number') {
            currentSheetIndex = data.activeSheetIndex;
        } else {
            currentSheetIndex = 0;
        }
        renderSheetTabs(workbookSheets, currentSheetIndex);
        renderSingleSheet(workbookSheets[currentSheetIndex]);
    } else {
        // Single sheet fallback
        workbookSheets = [{ name: data.metadata?.sheetName || 'Sheet1', data: data.data }];
        currentSheetIndex = 0;
        renderSheetTabs(workbookSheets, 0);
        renderSingleSheet(workbookSheets[0]);
    }
}

/**
 * Render a single sheet (sheetObj: {name, data})
 */
function renderSingleSheet(sheetObj) {
    if (!sheetObj || !sheetObj.data) return;

    if (window.hotInstance) {
        window.hotInstance.destroy();
    }

    const columnCount = sheetObj.data[0] ? sheetObj.data[0].length : 0;
    const alphabeticHeaders = generateExcelColHeaders(columnCount);

    const settings = {
        data: sheetObj.data,
        rowHeaders: true,
        colHeaders: alphabeticHeaders,
        licenseKey: 'non-commercial-and-evaluation',
        stretchH: 'all',
        readOnly: true,
        contextMenu: true,
        manualColumnResize: true,
        manualRowResize: true,
        className: 'htDark',
        outsideClickDeselects: false,
        multiSelect: true,
        fillHandle: true,
        afterRender: function() {
            this.rootElement.classList.add('handsontable-dark');
        },
        afterSelection: function(r, c, r2, c2, preventScrolling, selectionLayerLevel) {
            updateCellSelector(this.getSelected());
        },
        afterDeselect: function() {
            const currentSelection = this.getSelected();
            if (!currentSelection || currentSelection.length === 0) {
                clearCellSelector();
            }
        },
        afterInit: function() {
            this.selectCell(0, 0);
        },
        afterChange: function(changes, source) {
            if (source === 'loadData') return;
            if (!changes) return;
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
                pendingChanges.push(changeData);
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

    if (sheetObj.modified_cells && sheetObj.modified_cells.length > 0) {
        highlightModifiedCells(sheetObj.modified_cells);
    }
}

/**
 * Render sheet tabs at the bottom left.
 * @param {Array} sheets - Array of {name, data}
 * @param {number} activeIndex
 */
export function renderSheetTabs(sheets, activeIndex) {
    if (!sheetTabContainer) return;
    sheetTabContainer.innerHTML = '';
    sheets.forEach((sheet, idx) => {
        const tab = document.createElement('button');
        tab.className = 'sheet-tab-btn btn btn-sm btn-outline-light' + (idx === activeIndex ? ' active' : '');
        tab.textContent = sheet.name || `Sheet${idx + 1}`;
        tab.style.marginRight = '4px';
        tab.style.borderRadius = '6px 6px 0 0';
        tab.style.padding = '2px 12px';
        tab.style.fontWeight = idx === activeIndex ? 'bold' : 'normal';
        tab.onclick = () => switchSheet(idx);
        sheetTabContainer.appendChild(tab);
    });
}

/**
 * Switch to a different sheet in the workbook.
 * @param {number} sheetIndex
 */
export function switchSheet(sheetIndex) {
    if (sheetIndex === currentSheetIndex || !workbookSheets[sheetIndex]) return;
    currentSheetIndex = sheetIndex;
    renderSheetTabs(workbookSheets, currentSheetIndex);
    renderSingleSheet(workbookSheets[currentSheetIndex]);
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
        
        // Instead of blankData, clone the original spreadsheet data
        // const currentData = window.hotInstance.getData();
        // const clonedData = clone2DArray(currentData);

        // Use blank data for the right spreadsheet as before
        const leftData = window.hotInstance.getData();
        const rowCount = leftData.length;
        const colCount = leftData[0] ? leftData[0].length : 0;
        const blankData = Array.from({ length: rowCount }, () => Array(colCount).fill(''));

        // Create settings for the editable spreadsheet
        const editableSettings = {
            data: blankData,
            rowHeaders: true,
            colHeaders: generateExcelColHeaders(colCount),
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

// Helper to deep clone a 2D array
function clone2DArray(arr) {
    return arr.map(row => Array.isArray(row) ? [...row] : []);
}

// Compare two 2D arrays and generate a simple English log of cell changes
export function generateActionPlanLog(leftData, rightData) {
    let actions = [];
    const rowCount = Math.max(leftData.length, rightData.length);
    const colCount = Math.max(
        leftData[0] ? leftData[0].length : 0,
        rightData[0] ? rightData[0].length : 0
    );
    
    // Track patterns of changes
    let columnChanges = {};
    let rowPatterns = [];
    
    for (let i = 0; i < rowCount; i++) {
        const rightRow = rightData[i] || [];
        if (rightRow.some(cell => cell !== null && cell !== undefined && cell !== '')) {
            const leftRow = leftData[i] || [];
            let rowChanges = [];
            
            for (let j = 0; j < colCount; j++) {
                const leftCell = leftRow[j] ?? '';
                const rightCell = rightRow[j] ?? '';
                if (leftCell !== rightCell) {
                    const colLetter = String.fromCharCode(65 + j);
                    const change = `Cell ${colLetter}${i + 1}: "${leftCell}" → "${rightCell}"`;
                    actions.push(change);
                    rowChanges.push({col: j, from: leftCell, to: rightCell});
                    
                    // Track column-level patterns
                    if (!columnChanges[j]) columnChanges[j] = [];
                    columnChanges[j].push({row: i, from: leftCell, to: rightCell});
                }
            }
            
            if (rowChanges.length > 0) {
                rowPatterns.push({row: i, changes: rowChanges});
            }
        }
    }
    
    // Add pattern analysis to the action plan
    if (actions.length > 0) {
        let patternSummary = "\n\nPattern Analysis:";
        
        // Analyze column patterns
        for (let colIndex in columnChanges) {
            const colLetter = String.fromCharCode(65 + parseInt(colIndex));
            const changes = columnChanges[colIndex];
            if (changes.length > 1) {
                patternSummary += `\nColumn ${colLetter}: ${changes.length} changes detected`;
                
                // Check for common transformation patterns
                const allEmpty = changes.every(c => c.to === '');
                const allSame = changes.every(c => c.to === changes[0].to);
                
                if (allEmpty) {
                    patternSummary += " (clearing column)";
                } else if (allSame) {
                    patternSummary += ` (setting all to "${changes[0].to}")`;
                }
            }
        }
        
        return actions.join('\n') + patternSummary;
    }
    
    return 'No changes detected.';
}

// Add getter for split view state
export function isSplitViewEnabled() {
    return isSplitViewActive;
}

// Add getter for the editable instance
export function getEditableInstance() {
    return editableHotInstance;
}
