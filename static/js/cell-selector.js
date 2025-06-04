/**
 * Cell Selector Module
 * Handles tracking and displaying selected cells in spreadsheet
 */
// Create a fallback error handler in case uiInteractions isn't loaded
function showError(message) {
    if (typeof window.showError === 'function') {
        window.showError(message);
    } else if (window.bootstrap && bootstrap.Modal) {
        // Try to use bootstrap directly if available
        let errorModal = document.getElementById('errorModal');
        if (!errorModal) {
            // Create an error modal if it doesn't exist
            errorModal = document.createElement('div');
            errorModal.id = 'errorModal';
            errorModal.className = 'modal fade';
            errorModal.innerHTML = `
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Error</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body" id="errorModalBody">${message}</div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(errorModal);
            new bootstrap.Modal(errorModal).show();
        } else {
            document.getElementById('errorModalBody').textContent = message;
            new bootstrap.Modal(errorModal).show();
        }
    } else {
        // Fallback to alert if bootstrap isn't available
        console.error('Cell Selector Error:', message);
        alert(message);
    }
}

let currentSelectionArray = null; // Stores the array from hotInstance.getSelected()
let isSelectionActive = false;

/**
 * Convert column index to Excel-style letter (0=A, 1=B, etc.)
 */
function getColumnLetter(colIndex) {
    let result = '';
    let index = colIndex;
    
    while (index >= 0) {
        result = String.fromCharCode(65 + (index % 26)) + result;
        index = Math.floor(index / 26) - 1;
    }
    
    return result;
}

/**
 * Convert Excel-style column letter (A, B, AA) to 0-indexed column number
 */
function parseColumnLetter(columnName) {
    let col = 0;
    if (!columnName) return -1; // Handle empty or null input
    columnName = columnName.toUpperCase();
    for (let i = 0; i < columnName.length; i++) {
        const charCode = columnName.charCodeAt(i);
        if (charCode < 65 || charCode > 90) return -1; // Invalid character
        col = col * 26 + (charCode - 64);
    }
    return col - 1; // Adjust to be 0-indexed
}

/**
 * Convert cell ID string (e.g., "A1") to {row, col}
 */
function parseCellId(cellIdStr) {
    if (!cellIdStr) return null;
    const match = cellIdStr.trim().match(/^([A-Z]+)([1-9][0-9]*)$/i); // Ensure row number starts from 1
    if (!match) return null;
    
    const colStr = match[1];
    const rowStr = match[2];
    
    const col = parseColumnLetter(colStr);
    const row = parseInt(rowStr, 10) - 1; // 1-indexed to 0-indexed
    
    if (isNaN(row) || row < 0 || col < 0) return null;
    return { row, col };
}

/**
 * Format cell selection for display
 * selectionArrays is an array of [startRow, startCol, endRow, endCol]
 */
function formatCellSelection(selectionArrays) {
    if (!selectionArrays || selectionArrays.length === 0 || !window.hotInstance || window.hotInstance.isDestroyed) {
        return '-';
    }

    const hot = window.hotInstance;
    if (!hot || hot.isDestroyed) return '-';
    const maxRows = hot.countRows();
    const maxCols = hot.countCols();

    if (maxRows === 0 || maxCols === 0) { // Table not fully initialized or empty
        // Fallback to simple formatting if table dimensions are unknown
        return selectionArrays.map(sel => {
            const [r, c, r2, c2] = sel;
            const startCell = `${getColumnLetter(c)}${r + 1}`;
            if (r === r2 && c === c2) return startCell;
            const endCell = `${getColumnLetter(c2)}${r2 + 1}`;
            return `${startCell}:${endCell}`;
        }).join(', ');
    }
    
    return selectionArrays.map(sel => {
        const [r, c, r2, c2] = sel;

        const isFullColumnSelection = (r === 0 && r2 === maxRows - 1);
        const isFullRowSelection = (c === 0 && c2 === maxCols - 1);

        if (isFullColumnSelection) {
            if (c === c2) return getColumnLetter(c); // Single full column "A"
            return `${getColumnLetter(c)}:${getColumnLetter(c2)}`; // Full column range "A:C"
        }
        if (isFullRowSelection) {
            if (r === r2) return `${r + 1}`; // Single full row "1"
            return `${r + 1}:${r2 + 1}`; // Full row range "1:3"
        }

        // Standard cell or cell range
        const startCell = `${getColumnLetter(c)}${r + 1}`;
        if (r === r2 && c === c2) { // Single cell
            return startCell;
        } else { // Range
            const endCell = `${getColumnLetter(c2)}${r2 + 1}`;
            return `${startCell}:${endCell}`;
        }
    }).join(', ');
}

/**
 * Update the cell selector display
 */
export function updateCellSelector(selection) { // selection is from hotInstance.getSelected()
    const displayInput = document.getElementById('cellSelectorDisplay');
    if (!displayInput) return;
    if (!window.hotInstance || window.hotInstance.isDestroyed) {
        displayInput.value = '-';
        return;
    }
    currentSelectionArray = selection; // Store the raw selection array
    isSelectionActive = (selection && selection.length > 0);
    const formattedSelection = formatCellSelection(selection);
    displayInput.value = formattedSelection; // Use .value for input field
    const selectorBar = document.getElementById('cellSelectorBar');
    if (selectorBar) {
        if (isSelectionActive) {
            selectorBar.classList.add('active');
        } else {
            selectorBar.classList.remove('active');
        }
    }
}

/**
 * Clear cell selector display
 */
export function clearCellSelector() {
    const displayInput = document.getElementById('cellSelectorDisplay');
    if (displayInput) {
        displayInput.value = ''; // Use .value for input field
        displayInput.placeholder = '-';
    }
    
    const selectorBar = document.getElementById('cellSelectorBar');
    if (selectorBar) {
        selectorBar.classList.remove('active');
    }
    
    currentSelectionArray = null;
    isSelectionActive = false;
}

/**
 * Get current selection
 */
export function getCurrentSelection() {
    return currentSelectionArray; // Return the stored raw selection
}

/**
 * Check if selection is active
 */
export function isSelectionActiveState() {
    return isSelectionActive;
}

/**
 * Initialize cell selector functionality
 */
export function initCellSelector() {
    const displayInput = document.getElementById('cellSelectorDisplay');
    clearCellSelector(); // Initialize display

    if (displayInput) {
        // Add standard change event listener
        displayInput.addEventListener('change', handleCellSelectorChange);
        
        // Add custom event for cell tagging that won't shift focus
        displayInput.addEventListener('cellTagChange', function(event) {
            const value = this.value.trim().toUpperCase();
            handleCellSelection(value, event.detail?.preventFocusShift);
        });

        // Enhanced key handling for the cell selector
        displayInput.addEventListener('keydown', function(event) {
            // If escape is pressed, blur the input and add highlight effect
            if (event.key === 'Escape') {
                event.preventDefault();
                this.blur();
                this.classList.add('highlight-escape');
                setTimeout(() => this.classList.remove('highlight-escape'), 600);
                
                // Focus back to the table if it exists
                if (window.hotInstance) {
                    const currentSel = window.hotInstance.getSelected();
                    if (currentSel && currentSel.length > 0) {
                        window.hotInstance.selectCell(currentSel[0][0], currentSel[0][1]);
                    } else {
                        window.hotInstance.selectCell(0, 0);
                    }
                }
                return;
            }
            
            // Prevent table navigation keys from propagating when input is focused
            event.stopPropagation();
        });
        
        // Handle focus to select all text for easy replacement
        displayInput.addEventListener('focus', function() {
            this.select();
        });
    }
    
    const selectorBar = document.getElementById('cellSelectorBar');
    if (selectorBar) {
        selectorBar.addEventListener('click', function(event) {
            // If click is on the input itself, let it be.
            if (event.target === displayInput) return;
            // Focus back to spreadsheet if it exists and not clicking on input
            if (window.hotInstance) {
                const currentSel = window.hotInstance.getSelected();
                if (currentSel && currentSel.length > 0) {
                    const [firstSelection] = currentSel;
                    window.hotInstance.selectCell(firstSelection[0], firstSelection[1]);
                } else {
                    window.hotInstance.selectCell(0,0); // Default focus
                }
                // Ensure Handsontable listens for keyboard events
                const activeEditor = window.hotInstance.getActiveEditor();
                if (activeEditor) activeEditor.focus();
                else if (window.hotInstance.rootElement.contains(document.activeElement)) {
                     // if focus is already within HOT, ensure its listeners are active
                     // This part is tricky as HOT manages its own focus.
                     // Often, just selecting a cell is enough.
                }
            }
        });
    }
}

/**
 * Handle cell selector value changes
 */
function handleCellSelectorChange(event) {
    const value = event.target.value.trim().toUpperCase();
    handleCellSelection(value, false); // Standard change doesn't prevent focus shift
}

/**
 * Process cell selection with option to prevent focus shift
 */
function handleCellSelection(value, preventFocusShift = false) {
    if (!value || !window.hotInstance) {
        if (value === '' && window.hotInstance) {
            window.hotInstance.deselectCell();
        } else {
            updateCellSelector(window.hotInstance ? window.hotInstance.getSelected() : null);
        }
        return;
    }

    const hot = window.hotInstance;
    if (!hot || hot.isDestroyed || hot.countRows() === 0 || hot.countCols() === 0) {
        showError("Spreadsheet is not loaded or is empty.");
        updateCellSelector(hot && !hot.isDestroyed ? hot.getSelected() : null);
        return;
    }
    const maxRows = hot.countRows();
    const maxCols = hot.countCols();
    const selectionsToMake = [];
    
    try {
        // Parse cell references (existing code)
        const parts = value.split(',').map(part => part.trim());
        if (parts.some(part => !part)) throw new Error("Empty cell or range in selection list.");

        for (const part of parts) {
            let matched = false;

            // 1. Cell Range: A1:C3
            let match = part.match(/^([A-Z]+)([1-9][0-9]*):([A-Z]+)([1-9][0-9]*)$/);
            if (match) {
                const startCoords = parseCellId(match[1] + match[2]);
                const endCoords = parseCellId(match[3] + match[4]);
                if (startCoords && endCoords) {
                    selectionsToMake.push([
                        Math.min(startCoords.row, endCoords.row),
                        Math.min(startCoords.col, endCoords.col),
                        Math.max(startCoords.row, endCoords.row),
                        Math.max(startCoords.col, endCoords.col)
                    ]);
                    matched = true;
                } else { throw new Error(`Invalid cell range format: ${part}`); }
            }

            // 2. Column Range: A:C
            if (!matched) {
                match = part.match(/^([A-Z]+):([A-Z]+)$/);
                if (match) {
                    const startCol = parseColumnLetter(match[1]);
                    const endCol = parseColumnLetter(match[2]);
                    if (startCol !== -1 && endCol !== -1) {
                        selectionsToMake.push([0, Math.min(startCol, endCol), maxRows - 1, Math.max(startCol, endCol)]);
                        matched = true;
                    } else { throw new Error(`Invalid column range format: ${part}`); }
                }
            }

            // 3. Row Range: 1:5
            if (!matched) {
                match = part.match(/^([1-9][0-9]*):([1-9][0-9]*)$/);
                if (match) {
                    const startRow = parseInt(match[1], 10) - 1;
                    const endRow = parseInt(match[2], 10) - 1;
                    if (startRow >= 0 && endRow >= 0) {
                        selectionsToMake.push([Math.min(startRow, endRow), 0, Math.max(startRow, endRow), maxCols - 1]);
                        matched = true;
                    } else { throw new Error(`Invalid row range format: ${part}`); }
                }
            }
            
            // 4. Single Cell: A1
            if (!matched) {
                const coords = parseCellId(part); // parseCellId handles ^([A-Z]+)([1-9][0-9]*)$
                if (coords) {
                    selectionsToMake.push([coords.row, coords.col, coords.row, coords.col]);
                    matched = true;
                }
            }

            // 5. Single Column: A
            if (!matched) {
                match = part.match(/^([A-Z]+)$/);
                if (match) {
                    const col = parseColumnLetter(match[1]);
                    if (col !== -1) {
                        selectionsToMake.push([0, col, maxRows - 1, col]);
                        matched = true;
                    } else { throw new Error(`Invalid column format: ${part}`); }
                }
            }

            // 6. Single Row: 1
            if (!matched) {
                match = part.match(/^([1-9][0-9]*)$/);
                if (match) {
                    const row = parseInt(match[1], 10) - 1;
                    if (row >= 0) {
                        selectionsToMake.push([row, 0, row, maxCols - 1]);
                        matched = true;
                    } else { throw new Error(`Invalid row format: ${part}`); }
                }
            }
            
            if (!matched) {
                throw new Error(`Invalid selection part: ${part}. Use formats like A1, A1:C3, A, A:C, 1, 1:3.`);
            }
        }

        if (selectionsToMake.length > 0) {
            // Validate selections against table bounds
            for (const sel of selectionsToMake) {
                if (sel[0] < 0 || sel[1] < 0 || sel[2] >= maxRows || sel[3] >= maxCols) {
                    throw new Error(`Selection out of bounds: ${formatCellSelection([sel])}`);
                }
            }
            
            // Select cells but don't focus if preventFocusShift is true
            if (preventFocusShift) {
                // Just highlight without focusing
                const originalActiveElement = document.activeElement;
                hot.selectCells(selectionsToMake);
                
                // Return focus to the original element if needed
                if (originalActiveElement && originalActiveElement !== document.activeElement) {
                    setTimeout(() => {
                        originalActiveElement.focus();
                    }, 10);
                }
            } else {
                // Standard selection with focus
                hot.selectCells(selectionsToMake);
            }
        } else if (value !== '-') {
             throw new Error(`Cannot parse selection: ${value}`);
        }
    } catch (e) {
        showError(e.message);
        updateCellSelector(hot.getSelected());
    }
}
