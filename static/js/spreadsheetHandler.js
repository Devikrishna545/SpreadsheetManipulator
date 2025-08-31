import { updateUndoRedoButtons, updateStatus } from './uiInteractions.js';
import { updateCellSelector, clearCellSelector } from './cell-selector.js';
import { showLoading, hideLoading, showError } from './uiInteractions.js';

const spreadsheetDataContainer = document.getElementById('spreadsheetData');
const sheetTabContainer = document.getElementById('sheetTabContainer');
let workbookSheets = [];
let currentSheetIndex = 0;
let pendingChanges = [];
let isProcessingChanges = false;

let isSplitViewActive = false;
let editableHotInstance = null;

export function renderSpreadsheet(data) {
    if (!data) return;

    if (data.sheets && Array.isArray(data.sheets) && data.sheets.length > 0) {
        workbookSheets = data.sheets;
        if (typeof data.activeSheetIndex === 'number') {
            currentSheetIndex = data.activeSheetIndex;
        } else {
            currentSheetIndex = 0;
        }
        renderSheetTabs(workbookSheets, currentSheetIndex);
        
        const activeSheet = workbookSheets[currentSheetIndex];
        if (data.modified_cells && data.modified_cells.length > 0) {
            activeSheet.modified_cells = data.modified_cells;
        }
        renderSingleSheet(activeSheet);
    } else {
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

function renderSingleSheet(sheetObj) {
    if (!sheetObj || !sheetObj.data) return;

    if (window.hotInstance) {
        window.hotInstance.destroy();
    }

    const fullData = sheetObj.data;
    
    console.log('🔧 Frontend data processing:');
    console.log('   - Full data rows:', fullData.length);
    console.log('   - First row (headers):', fullData.length > 0 ? fullData[0].slice(0, 5) : 'No data', '...');
    console.log('   - Second row:', fullData.length > 1 ? fullData[1].slice(0, 5) : 'No data', '...');

    const columnCount = fullData.length > 0 ? fullData[0].length : 0;
    const alphabeticHeaders = generateExcelColHeaders(columnCount);

    const settings = {
        data: fullData,
        rowHeaders: true,
        colHeaders: alphabeticHeaders,
        licenseKey: 'non-commercial-and-evaluation',
        stretchH: 'all',
        readOnly: true,
        contextMenu: true,
        manualColumnResize: true,
        manualRowResize: true,
        className: 'htDark',
        autoRowSize: false,
        rowHeights: 28,
        wordWrap: false,
        outsideClickDeselects: false,
        multiSelect: true,
        fillHandle: true,
        afterRender: function() {
            this.rootElement.classList.add('handsontable-dark');
            scheduleHeaderRefresh(this);
        },
        afterSelection: function(r, c, r2, c2, preventScrolling, selectionLayerLevel) {
            updateCellSelector(this.getSelected());
            const selection = this.getSelected();
            if (selection && selection.length > 0) {
                highlightHeaders(this, selection);
            }
        },
        afterInit: function() {
            this.selectCell(0, 0);
            setTimeout(() => {
                const selection = this.getSelected();
                if (selection && selection.length > 0) {
                    highlightHeaders(this, selection);
                }
            }, 100);
        },
        afterScrollHorizontally: function() {
            scheduleHeaderRefresh(this);
        },
        afterScrollVertically: function() {
            scheduleHeaderRefresh(this);
        },
        afterDeselect: function() {
            const currentSelection = this.getSelected();
            if (!currentSelection || currentSelection.length === 0) {
                clearCellSelector();
                clearHeaderHighlights(this);
            }
        },
        afterGetColHeader: function(col, TH) {
            if (Array.isArray(this.__currentSelectionRanges) && isColSelected(this.__currentSelectionRanges, col)) {
                TH.classList.add('highlighted-header');
            } else {
                TH.classList.remove('highlighted-header');
            }
        },
        afterGetRowHeader: function(row, TH) {
            if (Array.isArray(this.__currentSelectionRanges) && isRowSelected(this.__currentSelectionRanges, row)) {
                TH.classList.add('highlighted-header');
            } else {
                TH.classList.remove('highlighted-header');
            }
        },
        afterCreateRow: function(index, amount, source) {
            if (source === 'loadData') return;
            if (source !== 'undo' && source !== 'redo') {
                pendingChanges.push({
                    type: 'row',
                    action: 'create',
                    index: index + 1,
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
                    index: index + 1,
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
        const showScrollAnimation = window.isBatchCommandMode || false;
        console.log('🎬 Animation decision - batch mode:', window.isBatchCommandMode, '| Show scroll animation:', showScrollAnimation);
        highlightModifiedCells(sheetObj.modified_cells, showScrollAnimation);
    }
}

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

export function switchSheet(sheetIndex) {
    if (sheetIndex === currentSheetIndex || !workbookSheets[sheetIndex]) return;
    currentSheetIndex = sheetIndex;
    renderSheetTabs(workbookSheets, currentSheetIndex);
    renderSingleSheet(workbookSheets[currentSheetIndex]);
}

function submitPendingChanges() {
    if (pendingChanges.length === 0 || isProcessingChanges) return;
    isProcessingChanges = true;
    const sessionId = window.currentSessionId;
    if (!sessionId) {
        pendingChanges = [];
        isProcessingChanges = false;
        return;
    }
    const changes = [...pendingChanges];
    pendingChanges = [];
    
    updateStatus('Saving changes...', 'processing');
    
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
        if (pendingChanges.length > 0) {
            setTimeout(submitPendingChanges, 100);
        }
    });
}

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

async function animateScrollThroughCells(hotInstance, cells) {
    if (!hotInstance || cells.length === 0) return;
    
    if (hotInstance.isDestroyed !== undefined && hotInstance.isDestroyed) {
        console.warn('Cannot animate scroll - Handsontable instance has been destroyed');
        return;
    }
    
    console.log(`📜 Starting scroll animation through ${cells.length} modified cells`);
    
    const sortedCells = [...cells].sort((a, b) => {
        if (a[0] !== b[0]) return a[0] - b[0];
        return a[1] - b[1];
    });
    
    let cellsToScrollTo = sortedCells;
    if (sortedCells.length > 10) {
        cellsToScrollTo = optimizeScrollPath(sortedCells);
        console.log(`📊 Optimized scroll path: ${sortedCells.length} → ${cellsToScrollTo.length} stops`);
    }
    
    const maxScrollTime = 2000;
    const minDelayPerCell = 120;
    const delayPerCell = Math.max(minDelayPerCell, Math.min(600, maxScrollTime / cellsToScrollTo.length));
    
    let previousFocusCell = null;
    
    for (let i = 0; i < cellsToScrollTo.length; i++) {
        const [row, col] = cellsToScrollTo[i];
        
        if (typeof row !== 'number' || typeof col !== 'number') continue;
        if (row < 0 || col < 0) continue;
        
        if (hotInstance.isDestroyed !== undefined && hotInstance.isDestroyed) {
            console.warn('Animation stopped - Handsontable instance was destroyed');
            break;
        }
        
        try {
            if (previousFocusCell) {
                const prevTd = hotInstance.getCell(previousFocusCell[0], previousFocusCell[1]);
                if (prevTd) {
                    prevTd.classList.remove('scroll-focus');
                }
            }
            
            hotInstance.scrollViewportTo(row, col, true, true);
            
            const currentTd = hotInstance.getCell(row, col);
            if (currentTd) {
                currentTd.classList.add('scroll-focus');
            }
            
            hotInstance.selectCell(row, col, row, col, false);
            
            console.log(`📍 Scrolled to cell [${row}, ${col}] (${i + 1}/${cellsToScrollTo.length})`);
            
            previousFocusCell = [row, col];
            
            if (i < cellsToScrollTo.length - 1) {
                await new Promise(resolve => setTimeout(resolve, delayPerCell));
            }
        } catch (error) {
            console.warn(`Could not scroll to cell [${row}, ${col}]:`, error);
        }
    }
    
    setTimeout(() => {
        if (previousFocusCell) {
            try {
                if (hotInstance && hotInstance.isDestroyed !== undefined && !hotInstance.isDestroyed) {
                    const lastTd = hotInstance.getCell(previousFocusCell[0], previousFocusCell[1]);
                    if (lastTd) {
                        lastTd.classList.remove('scroll-focus');
                    }
                }
            } catch (error) {
                // ignore
            }
        }
    }, 400);
    
    console.log(`✅ Completed scroll animation through all ${cellsToScrollTo.length} scroll stops`);
    
    if (cellsToScrollTo.length > 1) {
        setTimeout(() => {
            try {
                if (hotInstance && !hotInstance.isDestroyed && hotInstance.isDestroyed !== undefined) {
                    const firstCell = cellsToScrollTo[0];
                    hotInstance.scrollViewportTo(firstCell[0], firstCell[1], true, true);
                    
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
        setTimeout(() => {
            try {
                if (hotInstance && !hotInstance.isDestroyed && hotInstance.isDestroyed !== undefined) {
                    hotInstance.deselectCell();
                }
            } catch (error) {
                // ignore
            }
        }, 600);
    }
}

function optimizeScrollPath(sortedCells) {
    if (sortedCells.length <= 10) return sortedCells;
    
    const optimized = [];
    const groupDistance = 5;
    
    for (let i = 0; i < sortedCells.length; i++) {
        const currentCell = sortedCells[i];
        
        if (i === 0) {
            optimized.push(currentCell);
            continue;
        }
        
        const lastIncluded = optimized[optimized.length - 1];
        const rowDiff = Math.abs(currentCell[0] - lastIncluded[0]);
        const colDiff = Math.abs(currentCell[1] - lastIncluded[1]);
        
        if (rowDiff >= groupDistance || colDiff >= groupDistance || i === sortedCells.length - 1) {
            optimized.push(currentCell);
        }
    }
    
    return optimized;
}

function highlightModifiedCells(modifiedCells, showScrollAnimation = true) {
    if (!modifiedCells || modifiedCells.length === 0) return;
    
    console.log(`🎨 Processing ${modifiedCells.length} modified cells:`, modifiedCells);
    console.log('🎬 Scroll animation enabled:', showScrollAnimation);
    
    const adjustedCells = modifiedCells;
    console.log(`🔧 Using original coordinates for frontend display:`, adjustedCells.slice(0, 5), '...');
    
    const scrollThenHighlight = async (hotInstance, cells) => {
        if (!hotInstance) return;
        
        updateStatus('Applying Modifications', 'processing');
        
        if (showScrollAnimation && cells.length > 0) {
            await animateScrollThroughCells(hotInstance, cells);
        }
        
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
            
            console.log(`✨ Successfully highlighted ${highlightedCount} cells after scrolling`);        updateStatus('Applying Modifications', 'processing');
        
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
                    // out of bounds, skip
                }
            }
            console.log(`🎨 Cell highlighting removed (${removedCount} cells)`);
            
            updateStatus(`Applied ${highlightedCount} modifications`, 'success');
            setTimeout(() => updateStatus('Ready', 'active'), 1000);
        }, 3000);
    };
    
    if (window.hotInstance) {
        console.log('Applying scroll-then-highlight to main spreadsheet');
        scrollThenHighlight(window.hotInstance, adjustedCells);
    }
    
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

export function toggleSplitView() {
    if (!window.hotInstance || !spreadsheetDataContainer) {
        showError("No spreadsheet is loaded.");
        return;
    }
    
    if (isSplitViewActive) {
        const splitContainer = document.querySelector('.split-view-container');
        if (splitContainer) {
            const parent = splitContainer.parentNode;
            while (splitContainer.firstChild) {
                splitContainer.removeChild(splitContainer.firstChild);
            }
            parent.removeChild(splitContainer);
            parent.appendChild(spreadsheetDataContainer);
            if (editableHotInstance) {
                editableHotInstance.destroy();
                editableHotInstance = null;
                window.editableHotInstance = null;
            }
        }
        
        const splitViewBtn = document.getElementById('splitViewBtn');
        if (splitViewBtn) {
            splitViewBtn.innerHTML = '<i class="fas fa-columns"></i>';
            splitViewBtn.title = 'Split View';
        }
        
        isSplitViewActive = false;
        
        window.hotInstance.render();
        updateStatus('Split view disabled', 'active');
        setTimeout(() => updateStatus('Ready', 'active'), 2000);
    } else {
        const splitContainer = document.createElement('div');
        splitContainer.className = 'split-view-container';
        
        const leftPane = document.createElement('div');
        leftPane.className = 'split-view-pane original-pane';
        const leftLabel = document.createElement('div');
        leftLabel.className = 'pane-label';
        leftLabel.textContent = 'Original (Read-only)';
        leftPane.appendChild(leftLabel);
        
        const rightPane = document.createElement('div');
        rightPane.className = 'split-view-pane editable-pane';
        const rightLabel = document.createElement('div');
        rightLabel.className = 'pane-label';
        rightLabel.textContent = 'Editable';
        rightPane.appendChild(rightLabel);
        
        const rightContent = document.createElement('div');
        rightContent.id = 'rightSpreadsheet';
        rightPane.appendChild(rightContent);
        
        splitContainer.appendChild(leftPane);
        splitContainer.appendChild(rightPane);
        
        const parent = spreadsheetDataContainer.parentNode;
        parent.removeChild(spreadsheetDataContainer);
        parent.appendChild(splitContainer);
        leftPane.appendChild(spreadsheetDataContainer);

        const leftData = window.hotInstance.getData();
        const rowCount = leftData.length;
        const colCount = leftData[0] ? leftData[0].length : 0;
        const blankData = Array.from({ length: rowCount }, () => Array(colCount).fill(''));

        const editableSettings = {
            data: blankData,
            rowHeaders: true,
            colHeaders: generateExcelColHeaders(colCount),
            licenseKey: 'non-commercial-and-evaluation',
            stretchH: 'all',
            readOnly: false,
            contextMenu: true,
            manualColumnResize: true,
            manualRowResize: true,
            className: 'htDark',
            autoRowSize: false,
            rowHeights: 28,
            wordWrap: false,
            afterRender: function() {
                this.rootElement.classList.add('handsontable-dark');
                scheduleHeaderRefresh(this);
            },
            afterInit: function() {
                this.selectCell(0, 0);
                setTimeout(() => {
                    const selection = this.getSelected();
                    if (selection && selection.length > 0) {
                        highlightHeaders(this, selection);
                    }
                }, 100);
            },
            afterSelection: function(r, c, r2, c2, preventScrolling, selectionLayerLevel) {
                const selection = this.getSelected();
                if (selection && selection.length > 0) {
                    highlightHeaders(this, selection);
                }
            },
            afterDeselect: function() {
                const currentSelection = this.getSelected();
                if (!currentSelection || currentSelection.length === 0) {
                    clearHeaderHighlights(this);
                }
            },
            afterScrollHorizontally: function() {
                scheduleHeaderRefresh(this);
            },
            afterScrollVertically: function() {
                scheduleHeaderRefresh(this);
            },
            afterGetColHeader: function(col, TH) {
                if (Array.isArray(this.__currentSelectionRanges) && isColSelected(this.__currentSelectionRanges, col)) {
                    TH.classList.add('highlighted-header');
                } else {
                    TH.classList.remove('highlighted-header');
                }
            },
            afterGetRowHeader: function(row, TH) {
                if (Array.isArray(this.__currentSelectionRanges) && isRowSelected(this.__currentSelectionRanges, row)) {
                    TH.classList.add('highlighted-header');
                } else {
                    TH.classList.remove('highlighted-header');
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
        
        editableHotInstance = new Handsontable(
            rightContent,
            editableSettings
        );
        rightContent.hotInstance = editableHotInstance;
        window.editableHotInstance = editableHotInstance;

        const splitViewBtn = document.getElementById('splitViewBtn');
        if (splitViewBtn) {
            splitViewBtn.innerHTML = '<i class="fas fa-compress-arrows-alt"></i>';
            splitViewBtn.title = 'Exit Split View';
        }
        
        isSplitViewActive = true;
        
        window.hotInstance.render();
        editableHotInstance.render();
        updateStatus('Split view enabled', 'active');
        setTimeout(() => updateStatus('Ready', 'active'), 2000);
    }
}

export function generateActionPlanLog(leftData, rightData) {
    let actions = [];
    const rowCount = Math.max(leftData.length, rightData.length);
    const colCount = Math.max(
        leftData[0] ? leftData[0].length : 0,
        rightData[0] ? rightData[0].length : 0
    );
    
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
                    
                    if (!columnChanges[j]) columnChanges[j] = [];
                    columnChanges[j].push({row: i, from: leftCell, to: rightCell});
                }
            }
            
            if (rowChanges.length > 0) {
                rowPatterns.push({row: i, changes: rowChanges});
            }
        }
    }
    
    if (actions.length > 0) {
        let patternSummary = "\n\nPattern Analysis";
        
        for (let colIndex in columnChanges) {
            const colLetter = String.fromCharCode(65 + parseInt(colIndex));
            const changes = columnChanges[colIndex];
            if (changes.length > 1) {
                patternSummary += `\nColumn ${colLetter}: ${changes.length} changes detected`;
                
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

function normalizeSelectionRanges(selection) {
    if (!Array.isArray(selection)) return null;
    return selection.map(([r1, c1, r2, c2]) => ([
        Math.min(r1, r2), Math.min(c1, c2),
        Math.max(r1, r2), Math.max(c1, c2)
    ]));
}
function isColSelected(ranges, col) {
    if (typeof col !== 'number') return false;
    for (const [sr, sc, er, ec] of ranges) {
        if (col >= sc && col <= ec) return true;
    }
    return false;
}
function isRowSelected(ranges, row) {
    if (typeof row !== 'number') return false;
    for (const [sr, sc, er, ec] of ranges) {
        if (row >= sr && row <= er) return true;
    }
    return false;
}

/**
 * Highlight column and row headers for the selected cell range
 */
function highlightHeaders(hotInstance, selection) {
    if (!hotInstance || !selection || selection.length === 0) return;
    hotInstance.__currentSelectionRanges = normalizeSelectionRanges(selection);
    hotInstance.render();
}

function clearHeaderHighlights(hotInstance) {
    if (!hotInstance) return;
    hotInstance.__currentSelectionRanges = null;
    hotInstance.render();
}

export function highlightCells(cells) {
    if (!cells || !Array.isArray(cells) || cells.length === 0) return;
    
    const formattedCells = cells.map(cell => {
        if (Array.isArray(cell) && cell.length >= 2) {
            return [cell[0], cell[1]];
        } else if (typeof cell === 'object' && cell.row !== undefined && cell.col !== undefined) {
            return [cell.row, cell.col];
        }
        return null;
    }).filter(cell => cell !== null);
    
    if (formattedCells.length > 0) {
        const showScrollAnimation = window.isBatchCommandMode || false;
        console.log('🎬 Manual highlight - batch mode:', window.isBatchCommandMode, '| Show scroll animation:', showScrollAnimation);
        highlightModifiedCells(formattedCells, showScrollAnimation);
    }
}

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

/**
 * Debounced refresh of header highlights for current selection
 */
function refreshHeaderHighlights(hotInstance) {
    if (!hotInstance || hotInstance.isDestroyed) return;
    const selection = hotInstance.getSelected();
    if (selection && selection.length > 0) {
        highlightHeaders(hotInstance, selection);
    } else {
        clearHeaderHighlights(hotInstance);
    }
}

function scheduleHeaderRefresh(hotInstance) {
    if (!hotInstance || hotInstance.isDestroyed) return;
    if (hotInstance.__headerRaf) {
        cancelAnimationFrame(hotInstance.__headerRaf);
    }
    hotInstance.__headerRaf = requestAnimationFrame(() => {
        refreshHeaderHighlights(hotInstance);
        hotInstance.__headerRaf = null;
    });
}

export function isSplitViewEnabled() {
    return isSplitViewActive;
}

export function getEditableInstance() {
    return editableHotInstance;
}
