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
        
        // Pass modified_cells to the active sheet if available
        const activeSheet = workbookSheets[currentSheetIndex];
        if (data.modified_cells && data.modified_cells.length > 0) {
            activeSheet.modified_cells = data.modified_cells;
        }
        renderSingleSheet(activeSheet);
    } else {
        // Single sheet fallback - ensure modified_cells are passed through
        const singleSheet = { 
            name: data.metadata?.sheetName || 'Sheet1', 
            data: data.data,
            modified_cells: data.modified_cells || []
        };
        workbookSheets = [singleSheet];
        currentSheetIndex = 0;
        renderSheetTabs(workbookSheets, 0);
        renderSingleSheet(singleSheet);
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

    // Use all data without extracting headers - show headers as normal data row
    const fullData = sheetObj.data;
    
    console.log('🔧 Frontend data processing:');
    console.log('   - Full data rows:', fullData.length);
    console.log('   - First row (headers):', fullData.length > 0 ? fullData[0].slice(0, 5) : 'No data', '...');
    console.log('   - Second row:', fullData.length > 1 ? fullData[1].slice(0, 5) : 'No data', '...');

    // Generate Excel-style column letters for display (A, B, C, etc.)
    const columnCount = fullData.length > 0 ? fullData[0].length : 0;
    const alphabeticHeaders = generateExcelColHeaders(columnCount);

    // Use only Excel-style column headers (A, B, C)
    const settings = {
        data: fullData, // Use all data including the header row
        rowHeaders: true,
        colHeaders: alphabeticHeaders, // Just use Excel-style headers
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
                        row: row + 1, // Adjust for headers row that was removed from frontend display
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
                    index: index + 1, // Adjust for headers row
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
                    index: index + 1, // Adjust for headers row
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
        console.log(`Triggering highlighting for ${sheetObj.modified_cells.length} modified cells:`, sheetObj.modified_cells);
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

/**
 * Animate scrolling through modified cells for better UX
 * @param {Object} hotInstance - The Handsontable instance
 * @param {Array} cells - Array of [row, col] coordinates
 */
async function animateScrollThroughCells(hotInstance, cells) {
    if (!hotInstance || cells.length === 0) return;
    
    // Check if instance is destroyed before starting animation
    if (hotInstance.isDestroyed !== undefined && hotInstance.isDestroyed) {
        console.warn('Cannot animate scroll - Handsontable instance has been destroyed');
        return;
    }
    
    console.log(`📜 Starting scroll animation through ${cells.length} modified cells`);
    
    // Sort cells by row then column for logical scrolling order
    const sortedCells = [...cells].sort((a, b) => {
        if (a[0] !== b[0]) return a[0] - b[0]; // Sort by row first
        return a[1] - b[1]; // Then by column
    });
    
    // For large numbers of cells, group nearby cells and only scroll to representative ones
    let cellsToScrollTo = sortedCells;
    if (sortedCells.length > 10) {
        cellsToScrollTo = optimizeScrollPath(sortedCells);
        console.log(`📊 Optimized scroll path: ${sortedCells.length} → ${cellsToScrollTo.length} stops`);
    }
    
    // Calculate timing based on number of cells to scroll to
    const maxScrollTime = 2000; // Maximum time to spend scrolling (2 seconds)
    const minDelayPerCell = 120; // Minimum time per cell (120ms)
    const delayPerCell = Math.max(minDelayPerCell, Math.min(600, maxScrollTime / cellsToScrollTo.length));
    
    let previousFocusCell = null;
    
    for (let i = 0; i < cellsToScrollTo.length; i++) {
        const [row, col] = cellsToScrollTo[i];
        
        if (typeof row !== 'number' || typeof col !== 'number') continue;
        if (row < 0 || col < 0) continue;
        
        // Check if instance is still valid before each operation
        if (hotInstance.isDestroyed !== undefined && hotInstance.isDestroyed) {
            console.warn('Animation stopped - Handsontable instance was destroyed');
            break;
        }
        
        try {
            // Remove previous focus styling
            if (previousFocusCell) {
                const prevTd = hotInstance.getCell(previousFocusCell[0], previousFocusCell[1]);
                if (prevTd) {
                    prevTd.classList.remove('scroll-focus');
                }
            }
            
            // Scroll to the cell smoothly
            hotInstance.scrollViewportTo(row, col, true, true);
            
            // Add special focus styling for current cell
            const currentTd = hotInstance.getCell(row, col);
            if (currentTd) {
                currentTd.classList.add('scroll-focus');
            }
            
            // Briefly select the cell to draw extra attention
            hotInstance.selectCell(row, col, row, col, false);
            
            console.log(`📍 Scrolled to cell [${row}, ${col}] (${i + 1}/${cellsToScrollTo.length})`);
            
            previousFocusCell = [row, col];
            
            // Wait before moving to the next cell (except for the last one)
            if (i < cellsToScrollTo.length - 1) {
                await new Promise(resolve => setTimeout(resolve, delayPerCell));
            }
        } catch (error) {
            console.warn(`Could not scroll to cell [${row}, ${col}]:`, error);
        }
    }
    
    // Clean up the last focus styling
    setTimeout(() => {
        if (previousFocusCell) {
            try {
                // Check if instance is still valid before cleanup
                if (hotInstance && hotInstance.isDestroyed !== undefined && !hotInstance.isDestroyed) {
                    const lastTd = hotInstance.getCell(previousFocusCell[0], previousFocusCell[1]);
                    if (lastTd) {
                        lastTd.classList.remove('scroll-focus');
                    }
                }
            } catch (error) {
                // Ignore errors in cleanup
            }
        }
    }, 400);
    
    console.log(`✅ Completed scroll animation through all ${cellsToScrollTo.length} scroll stops`);
    
    // If there are multiple cells, show a brief overview at the end
    if (cellsToScrollTo.length > 1) {
        setTimeout(() => {
            try {
                // Check if instance is still valid before using it
                if (hotInstance && !hotInstance.isDestroyed && hotInstance.isDestroyed !== undefined) {
                    // Scroll to show the first few modified cells in view
                    const firstCell = cellsToScrollTo[0];
                    hotInstance.scrollViewportTo(firstCell[0], firstCell[1], true, true);
                    
                    // Clear selection after the animation
                    setTimeout(() => {
                        if (hotInstance && !hotInstance.isDestroyed && hotInstance.isDestroyed !== undefined) {
                            hotInstance.deselectCell();
                        }
                    }, 300);
                }
            } catch (error) {
                console.warn('Could not complete final scroll positioning:', error);
            }
        }, 200);
    } else if (cellsToScrollTo.length === 1) {
        // For single cell, just clear selection after a brief moment
        setTimeout(() => {
            try {
                if (hotInstance && !hotInstance.isDestroyed && hotInstance.isDestroyed !== undefined) {
                    hotInstance.deselectCell();
                }
            } catch (error) {
                // Ignore errors
            }
        }, 600);
    }
}

/**
 * Optimize scroll path for large numbers of modified cells
 * Groups nearby cells and selects representative cells to scroll to
 * @param {Array} sortedCells - Array of [row, col] coordinates sorted by position
 * @returns {Array} Optimized array of cells to scroll to
 */
function optimizeScrollPath(sortedCells) {
    if (sortedCells.length <= 10) return sortedCells;
    
    const optimized = [];
    const groupDistance = 5; // Group cells within 5 rows/columns
    
    for (let i = 0; i < sortedCells.length; i++) {
        const currentCell = sortedCells[i];
        
        // Always include the first cell
        if (i === 0) {
            optimized.push(currentCell);
            continue;
        }
        
        // Check if this cell is far enough from the last included cell
        const lastIncluded = optimized[optimized.length - 1];
        const rowDiff = Math.abs(currentCell[0] - lastIncluded[0]);
        const colDiff = Math.abs(currentCell[1] - lastIncluded[1]);
        
        // Include cell if it's far enough away or if it's the last cell
        if (rowDiff >= groupDistance || colDiff >= groupDistance || i === sortedCells.length - 1) {
            optimized.push(currentCell);
        }
    }
    
    return optimized;
}

function highlightModifiedCells(modifiedCells) {
    if (!modifiedCells || modifiedCells.length === 0) return;
    
    console.log(`🎨 Processing ${modifiedCells.length} modified cells:`, modifiedCells);
    
    // No need to adjust cell coordinates anymore since we're not removing header row
    const adjustedCells = modifiedCells;
    console.log(`🔧 Using original coordinates for frontend display:`, adjustedCells.slice(0, 5), '...');
    
    // Function to scroll through cells first, then apply highlighting
    const scrollThenHighlight = async (hotInstance, cells) => {
        if (!hotInstance) return;
        
        // Show status message for the entire modification process
        updateStatus('Applying Modifications', 'processing');
        
        // First, animate scrolling through the modified cells (without highlighting)
        if (cells.length > 0) {
            await animateScrollThroughCells(hotInstance, cells);
        }
        
        // After scrolling is complete, highlight all modified cells
        let highlightedCount = 0;
        for (const [row, col] of cells) {
            if (typeof row !== 'number' || typeof col !== 'number') continue;
            if (row < 0 || col < 0) continue;
            
            try {
                const td = hotInstance.getCell(row, col);
                if (td) {
                    td.classList.add('modified');
                    highlightedCount++;
                }
            } catch (error) {
                console.warn(`Could not highlight cell [${row}, ${col}]:`, error);
            }
        }
        
        console.log(`✨ Successfully highlighted ${highlightedCount} cells after scrolling`);
        
        // Update status when highlighting is applied and keep "Applying Modifications" for the duration
        updateStatus('Applying Modifications', 'processing');
        
        // Remove highlighting after 3 seconds (instead of 2)
        setTimeout(() => {
            let removedCount = 0;
            for (const [row, col] of cells) {
                if (typeof row !== 'number' || typeof col !== 'number') continue;
                if (row < 0 || col < 0) continue;
                
                try {
                    const td = hotInstance.getCell(row, col);
                    if (td) {
                        td.classList.remove('modified');
                        removedCount++;
                    }
                } catch (error) {
                    // Cell might be out of bounds, skip silently
                }
            }
            console.log(`🎨 Cell highlighting removed (${removedCount} cells)`);
            
            // Only update status to "Ready" after highlighting is completely removed
            updateStatus(`Applied ${highlightedCount} modifications`, 'success');
            setTimeout(() => updateStatus('Ready', 'active'), 1000);
        }, 3000);
    };
    
    // Apply scrolling then highlighting to the main spreadsheet (left side)
    if (window.hotInstance) {
        console.log('Applying scroll-then-highlight to main spreadsheet');
        scrollThenHighlight(window.hotInstance, adjustedCells);
    }
    
    // Also apply to the editable instance in split view if it exists
    if (window.editableHotInstance) {
        console.log('Applying scroll-then-highlight to editable spreadsheet (split view)');
        scrollThenHighlight(window.editableHotInstance, adjustedCells);
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

// Add getter for split view state
export function isSplitViewEnabled() {
    return isSplitViewActive;
}

// Add getter for the editable instance
export function getEditableInstance() {
    return editableHotInstance;
}

// Export highlighting function for use by other modules
export { highlightModifiedCells };

// Utility function to manually highlight specific cells
export function highlightCells(cells) {
    if (!cells || !Array.isArray(cells) || cells.length === 0) return;
    
    // Convert cells to the expected format [row, col] if needed
    const formattedCells = cells.map(cell => {
        if (Array.isArray(cell) && cell.length >= 2) {
            return [cell[0], cell[1]];
        } else if (typeof cell === 'object' && cell.row !== undefined && cell.col !== undefined) {
            return [cell.row, cell.col];
        }
        return null;
    }).filter(cell => cell !== null);
    
    if (formattedCells.length > 0) {
        highlightModifiedCells(formattedCells);
    }
}

// Make highlighting functions available globally for testing
if (typeof window !== 'undefined') {
    window.testHighlighting = function(row = 0, col = 0) {
        console.log(`Testing scroll-then-highlight on cell [${row}, ${col}]`);
        highlightCells([[row, col]]);
    };
    
    window.testMultipleHighlighting = function() {
        console.log('Testing scroll-then-highlight on multiple cells: [0,0], [1,1], [2,2]');
        highlightCells([[0, 0], [1, 1], [2, 2]]);
    };
    
    window.testManyHighlighting = function() {
        console.log('Testing scroll-then-highlight optimization with many cells');
        const manyCells = [];
        for (let i = 0; i < 25; i++) {
            manyCells.push([Math.floor(i / 5) * 3, (i % 5) * 2]);
        }
        highlightCells(manyCells);
    };
    
    window.testScatteredHighlighting = function() {
        console.log('Testing scroll-then-highlight with scattered cells across the spreadsheet');
        const scatteredCells = [[0, 0], [5, 3], [10, 1], [15, 4], [20, 2], [25, 5]];
        highlightCells(scatteredCells);
    };
}
