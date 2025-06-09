/**
 * Cell Tagger Module
 * Handles cell tagging with # symbol and popup suggestions
 */
import { getCurrentSelection, isSelectionActiveState } from './cell-selector.js';

let commandInput = null;
let popup = null;
let isPopupVisible = false;
let lastTagPosition = -1;
let currentFilter = '';
let cellSuggestions = [];
let pendingTagSelection = null; // Store the tag selection that's pending Enter confirmation

/**
 * Initialize the cell tagger functionality
 * @param {HTMLElement} inputElement - The command input text area 
 */
export function initCellTagger(inputElement) {
    commandInput = inputElement;
    
    if (!commandInput) {
        console.error('Command input element not found');
        return;
    }
    
    // Create popup element if it doesn't exist
    createPopup();
    
    // Add event listeners to command input
    commandInput.addEventListener('input', handleInputChange);
    commandInput.addEventListener('keydown', handleKeyDown);
    commandInput.addEventListener('blur', () => {
        // Small delay to allow for popup item clicks
        setTimeout(() => {
            hidePopup();
        }, 200);
    });
    
    // Close popup when clicking outside
    document.addEventListener('click', (e) => {
        if (popup && isPopupVisible && !popup.contains(e.target) && e.target !== commandInput) {
            hidePopup();
        }
    });
}

/**
 * Create the popup element for cell suggestions
 */
function createPopup() {
    popup = document.createElement('div');
    popup.id = 'cellTaggingPopup';
    popup.className = 'cell-tagging-popup';
    popup.style.display = 'none';
    document.body.appendChild(popup);
}

/**
 * Handle input changes in the command input
 */
function handleInputChange(e) {
    const text = commandInput.value;
    const cursorPosition = commandInput.selectionStart;
    
    // Find the position of # before cursor
    lastTagPosition = findTagPosition(text, cursorPosition);
    
    if (lastTagPosition >= 0) {
        // Extract the current filter text after #
        currentFilter = text.substring(lastTagPosition + 1, cursorPosition).trim();
        
        // Generate and show suggestions
        generateSuggestions();
        showPopup();
        
        // Store the current tag text for potential selection, but don't apply yet
        pendingTagSelection = currentFilter;
    } else {
        hidePopup();
        pendingTagSelection = null;
    }
}

/**
 * Find the position of the # tag before cursor
 */
function findTagPosition(text, cursorPosition) {
    // Find the last # before cursor that isn't inside a word
    let position = -1;
    for (let i = cursorPosition - 1; i >= 0; i--) {
        if (text[i] === '#') {
            // Check if # is at start of text or preceded by whitespace or delimiter
            if (i === 0 || /[\s,;:]/.test(text[i-1])) {
                position = i;
                break;
            }
        } else if (/[\s,;:]/.test(text[i])) {
            // Stop searching if we hit whitespace or delimiter
            break;
        }
    }
    return position;
}

/**
 * Generate cell suggestions based on current filter
 */
function generateSuggestions() {
    if (!window.hotInstance || window.hotInstance.isDestroyed) {
        cellSuggestions = [];
        return;
    }
    
    const hot = window.hotInstance;
    const maxRows = hot.countRows();
    const maxCols = hot.countCols();
    
    if (maxRows === 0 || maxCols === 0) {
        cellSuggestions = [];
        return;
    }
    
    // Create list of suggestions
    const suggestions = [];
    
    // Check if the current filter is a single column letter
    const isColumnFilter = /^[A-Z]$/i.test(currentFilter);
    const filterColumn = isColumnFilter ? parseColumnLetter(currentFilter.toUpperCase()) : -1;
    
    // If we have a column filter, prioritize cells from that column
    if (isColumnFilter && filterColumn >= 0 && filterColumn < maxCols) {
        const colLetter = getColumnLetter(filterColumn);
        
        // Add the column header itself
        suggestions.push({ 
            text: colLetter,
            type: 'column',
            description: `Column ${colLetter}`
        });
        
        // Add cells from this column (limit to first 20 cells for performance)
        const cellsToShow = Math.min(maxRows, 20);
        for (let row = 0; row < cellsToShow; row++) {
            const cellId = `${colLetter}${row + 1}`;
            const cellValue = hot.getDataAtCell(row, filterColumn);
            let cellPreview = cellValue ? String(cellValue).substring(0, 15) : '';
            if (cellValue && String(cellValue).length > 15) {
                cellPreview += '...';
            }
            
            suggestions.push({ 
                text: cellId,
                type: 'cell',
                description: cellPreview ? `Cell ${cellId}: ${cellPreview}` : `Cell ${cellId}`
            });
        }
        
        // Add a range suggestion for this column
        suggestions.push({ 
            text: `${colLetter}1:${colLetter}${maxRows}`,
            type: 'range',
            description: `All rows in column ${colLetter}`
        });
        
        // Also add just the first few cells from other columns
        const otherColumnsToShow = Math.min(3, maxCols);
        for (let col = 0; col < maxCols; col++) {
            if (col === filterColumn) continue; // Skip the filtered column
            
            const otherColLetter = getColumnLetter(col);
            suggestions.push({ 
                text: otherColLetter,
                type: 'column',
                description: `Column ${otherColLetter}`
            });
            
            // Add just the first cell from this column
            const cellId = `${otherColLetter}1`;
            const cellValue = hot.getDataAtCell(0, col);
            let cellPreview = cellValue ? String(cellValue).substring(0, 15) : '';
            if (cellValue && String(cellValue).length > 15) {
                cellPreview += '...';
            }
            
            suggestions.push({ 
                text: cellId,
                type: 'cell',
                description: cellPreview ? `Cell ${cellId}: ${cellPreview}` : `Cell ${cellId}`
            });
        }
    } else {
        // Default behavior - add all columns, rows, and cells
        
        // Add column headers (A, B, C, etc.)
        for (let col = 0; col < maxCols; col++) {
            const colLetter = getColumnLetter(col);
            suggestions.push({ 
                text: colLetter,
                type: 'column',
                description: `Column ${colLetter}`
            });
        }
        
        // Add row headers (1, 2, 3, etc.)
        for (let row = 0; row < maxRows; row++) {
            suggestions.push({ 
                text: (row + 1).toString(),
                type: 'row',
                description: `Row ${row + 1}`
            });
        }
        
        // Add cells (limit to first 1000 cells to avoid performance issues)
        const maxCells = 1000;
        let cellCount = 0;
        
        for (let col = 0; col < maxCols && cellCount < maxCells; col++) {
            const colLetter = getColumnLetter(col);
            for (let row = 0; row < maxRows && cellCount < maxCells; row++) {
                const cellId = `${colLetter}${row + 1}`;
                const cellValue = hot.getDataAtCell(row, col);
                let cellPreview = cellValue ? String(cellValue).substring(0, 15) : '';
                if (cellValue && String(cellValue).length > 15) {
                    cellPreview += '...';
                }
                
                suggestions.push({ 
                    text: cellId,
                    type: 'cell',
                    description: cellPreview ? `Cell ${cellId}: ${cellPreview}` : `Cell ${cellId}`
                });
                cellCount++;
            }
        }
        
        // Add common range patterns
        suggestions.push({ 
            text: 'A1:A10',
            type: 'range',
            description: 'Range example: A1 to A10'
        });
        
        suggestions.push({ 
            text: 'A:C',
            type: 'range',
            description: 'Column range: A to C'
        });
        
        suggestions.push({ 
            text: '1:5',
            type: 'range',
            description: 'Row range: 1 to 5'
        });
    }
    
    // Filter suggestions based on current filter
    if (currentFilter) {
        // If we have a column filter, we've already prioritized those cells
        // so don't filter further (allow partial matches on the row number)
        if (!isColumnFilter) {
            const filterLower = currentFilter.toLowerCase();
            cellSuggestions = suggestions.filter(s => 
                s.text.toLowerCase().includes(filterLower) ||
                s.description.toLowerCase().includes(filterLower)
            );
        } else {
            cellSuggestions = suggestions;
        }
    } else {
        cellSuggestions = suggestions;
    }
    
    // Limit to 10 results
    cellSuggestions = cellSuggestions.slice(0, 10);
}

/**
 * Convert column letter to index (A=0, B=1, etc.)
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
 * Show the popup with suggestions
 */
function showPopup() {
    if (!popup || cellSuggestions.length === 0) {
        hidePopup();
        return;
    }
    
    // Position popup below the cursor position
    const inputRect = commandInput.getBoundingClientRect();
    const cursorCoords = getCursorCoordinates(commandInput);
    
    popup.style.left = `${inputRect.left + cursorCoords.left}px`;
    popup.style.top = `${inputRect.top + cursorCoords.top + 20}px`;
    
    // Populate popup with suggestions
    popup.innerHTML = '';
    const list = document.createElement('ul');
    list.className = 'suggestion-list';
    
    cellSuggestions.forEach((suggestion, index) => {
        const item = document.createElement('li');
        item.className = `suggestion-item suggestion-${suggestion.type}`;
        item.setAttribute('data-value', suggestion.text);
        item.setAttribute('data-index', index);
        
        // Add an icon based on suggestion type
        const icon = document.createElement('i');
        switch(suggestion.type) {
            case 'cell':
                icon.className = 'fas fa-square';
                break;
            case 'column':
                icon.className = 'fas fa-columns';
                break;
            case 'row':
                icon.className = 'fas fa-bars';
                break;
            case 'range':
                icon.className = 'fas fa-table';
                break;
        }
        
        const textSpan = document.createElement('span');
        textSpan.className = 'suggestion-text';
        textSpan.textContent = suggestion.text;
        
        const descSpan = document.createElement('span');
        descSpan.className = 'suggestion-description';
        descSpan.textContent = suggestion.description;
        
        item.appendChild(icon);
        item.appendChild(textSpan);
        item.appendChild(descSpan);
        
        item.addEventListener('click', () => {
            // Apply suggestion WITH selection highlighting when clicked
            applySuggestion(suggestion.text, true);
        });
        
        list.appendChild(item);
    });
    
    popup.appendChild(list);
    popup.style.display = 'block';
    isPopupVisible = true;
}

/**
 * Hide the popup
 */
function hidePopup() {
    if (popup) {
        popup.style.display = 'none';
        isPopupVisible = false;
    }
}

/**
 * Get cursor coordinates in text area
 */
function getCursorCoordinates(input) {
    // Create a mirror div to calculate position
    const div = document.createElement('div');
    const styles = window.getComputedStyle(input);
    
    // Copy styles from input to div
    const stylesToCopy = [
        'font-family', 'font-size', 'font-weight', 'letter-spacing',
        'line-height', 'text-transform', 'word-spacing', 'padding-left',
        'padding-top', 'padding-right', 'padding-bottom', 'width', 'height'
    ];
    
    stylesToCopy.forEach(style => {
        div.style[style] = styles[style];
    });
    
    // Set content up to cursor
    div.textContent = input.value.substring(0, input.selectionStart);
    
    // Create a span for cursor position
    const span = document.createElement('span');
    span.textContent = '.';
    div.appendChild(span);
    
    // Position div absolutely and make it invisible
    div.style.position = 'absolute';
    div.style.visibility = 'hidden';
    div.style.whiteSpace = 'pre-wrap';
    div.style.overflowWrap = 'break-word';
    
    document.body.appendChild(div);
    const coordinates = {
        left: span.offsetLeft,
        top: span.offsetTop
    };
    document.body.removeChild(div);
    
    return coordinates;
}

/**
 * Handle keyboard navigation in popup
 */
function handleKeyDown(e) {
    if (!isPopupVisible) return;
    
    switch (e.key) {
        case 'ArrowDown':
            e.preventDefault();
            navigatePopup(1);
            break;
        case 'ArrowUp':
            e.preventDefault();
            navigatePopup(-1);
            break;
        case 'Enter':
            if (isPopupVisible) {
                e.preventDefault();
                e.stopPropagation(); // Prevent Enter from triggering the command
                const selected = popup.querySelector('.selected');
                if (selected) {
                    // Apply the suggestion WITH selection highlighting
                    applySuggestion(selected.getAttribute('data-value'), true);
                } else if (pendingTagSelection) {
                    // If nothing is selected but we have filtered text, use that
                    // This allows direct entry like #A1 followed by Enter
                    applySuggestion(pendingTagSelection, true);
                }
            }
            break;
        case 'Escape':
            e.preventDefault();
            hidePopup();
            pendingTagSelection = null;
            break;
        case 'Tab':
            if (isPopupVisible) {
                e.preventDefault();
                const selected = popup.querySelector('.selected') || 
                                 popup.querySelector('.suggestion-item');
                if (selected) {
                    // Apply the suggestion WITH selection highlighting
                    applySuggestion(selected.getAttribute('data-value'), true);
                }
            }
            break;
    }
}

/**
 * Navigate through popup items
 */
function navigatePopup(direction) {
    const items = popup.querySelectorAll('.suggestion-item');
    if (!items.length) return;
    
    const selected = popup.querySelector('.selected');
    let index = 0;
    
    if (selected) {
        index = parseInt(selected.getAttribute('data-index'));
        selected.classList.remove('selected');
        index = (index + direction + items.length) % items.length;
    } else if (direction < 0) {
        index = items.length - 1;
    }
    
    items[index].classList.add('selected');
    items[index].scrollIntoView({ block: 'nearest' });
}

/**
 * Apply the selected suggestion
 */
function applySuggestion(value) {
    if (!commandInput || lastTagPosition < 0) return;
    
    const text = commandInput.value;
    const cursorPosition = commandInput.selectionStart;
    
    // Replace the tag with the selected value
    const before = text.substring(0, lastTagPosition); // Position before the #
    const after = text.substring(cursorPosition);
    const newText = before + '#' + value + after; // Manually add the # to preserve spacing
    
    commandInput.value = newText;
    commandInput.setSelectionRange(lastTagPosition + 1 + value.length, lastTagPosition + 1 + value.length);
    commandInput.focus();
    
    // Trigger selection in spreadsheet if needed (preview only)
    highlightTaggedCells(value, true);
    commandInput.focus(); // Ensure we remain focused on the AI Command Interface
    hidePopup();
}

/**
 * Highlight cells tagged in the command
 */
function highlightTaggedCells(value, preventFocusShift = false) {
    // Ensure we have a valid Handsontable instance
    if (!window.hotInstance || window.hotInstance.isDestroyed) return;
    
    try {
        // Parse the cell reference and highlight it without shifting focus
        const displayInput = document.getElementById('cellSelectorDisplay');
        if (displayInput) {
            // Store the current active element to restore focus later
            const activeElement = document.activeElement;
            
            // Set the value in the cell selector
            displayInput.value = value; // Fix: use 'value' parameter instead of undefined 'cellRef'
            
            // Create a custom event instead of using the standard change event
            // This will allow us to add a flag to prevent focus shift
            const customEvent = new CustomEvent('cellTagChange', { 
                bubbles: true,
                detail: { preventFocusShift: true }
            });
            displayInput.dispatchEvent(customEvent);
            
            // Ensure focus returns to the command input
            if (activeElement === commandInput) {
                // Small delay to ensure focus is restored after any handlers run
                setTimeout(() => {
                    commandInput.focus();
                    
                    // Place cursor at the end of the text
                    const length = commandInput.value.length;
                    commandInput.setSelectionRange(length, length);
                }, 50);
            }
        }
    } catch (error) {
        console.error('Error highlighting tagged cells:', error);
    }
}

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
 * Analyze command input for tags and highlight all tagged cells
 * This is called on form submission or when explicitly requested
 */
export function scanAndHighlightTags() {
    if (!commandInput) return;
    
    const text = commandInput.value;
    const tagPattern = /\#([A-Z0-9\:]+)/gi;
    
    let match;
    let cellRefs = [];
    
    while ((match = tagPattern.exec(text)) !== null) {
        if (match[1]) {
            cellRefs.push(match[1]);
        }
    }
    
    if (cellRefs.length > 0) {
        // Join multiple references with commas
        const cellRef = cellRefs.join(', ');
        highlightTaggedCells(cellRef);
    }
}
