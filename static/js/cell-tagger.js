import { getCurrentSelection, isSelectionActiveState } from './cell-selector.js';

let commandInput = null;
let popup = null;
let isPopupVisible = false;
let lastTagPosition = -1;
let currentFilter = '';
let cellSuggestions = [];
let pendingTagSelection = null;

export function initCellTagger(inputElement) {
    commandInput = inputElement;
    
    if (!commandInput) {
        console.error('Command input element not found');
        return;
    }
    
    createPopup();
    
    commandInput.addEventListener('input', handleInputChange);
    commandInput.addEventListener('keydown', handleKeyDown);
    commandInput.addEventListener('blur', () => {
        setTimeout(() => {
            hidePopup();
        }, 200);
    });
    
    document.addEventListener('click', (e) => {
        if (popup && isPopupVisible && !popup.contains(e.target) && e.target !== commandInput) {
            hidePopup();
        }
    });
}

function createPopup() {
    popup = document.createElement('div');
    popup.id = 'cellTaggingPopup';
    popup.className = 'cell-tagging-popup';
    popup.style.display = 'none';
    document.body.appendChild(popup);
}

function handleInputChange(e) {
    const text = commandInput.value;
    const cursorPosition = commandInput.selectionStart;
    
    lastTagPosition = findTagPosition(text, cursorPosition);
    
    if (lastTagPosition >= 0) {
        currentFilter = text.substring(lastTagPosition + 1, cursorPosition).trim();
        
        generateSuggestions();
        showPopup();
        
        pendingTagSelection = currentFilter;
    } else {
        hidePopup();
        pendingTagSelection = null;
    }
}

function findTagPosition(text, cursorPosition) {
    let position = -1;
    for (let i = cursorPosition - 1; i >= 0; i--) {
        if (text[i] === '#') {
            if (i === 0 || /[\s,;:]/.test(text[i-1])) {
                position = i;
                break;
            }
        } else if (/[\s,;:]/.test(text[i])) {
            break;
        }
    }
    return position;
}

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
    
    const suggestions = [];
    
    const isColumnFilter = /^[A-Z]$/i.test(currentFilter);
    const filterColumn = isColumnFilter ? parseColumnLetter(currentFilter.toUpperCase()) : -1;
    
    if (isColumnFilter && filterColumn >= 0 && filterColumn < maxCols) {
        const colLetter = getColumnLetter(filterColumn);
        
        suggestions.push({ 
            text: colLetter,
            type: 'column',
            description: `Column ${colLetter}`
        });
        
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
        
        suggestions.push({ 
            text: `${colLetter}1:${colLetter}${maxRows}`,
            type: 'range',
            description: `All rows in column ${colLetter}`
        });
        
        const otherColumnsToShow = Math.min(3, maxCols);
        for (let col = 0; col < maxCols; col++) {
            if (col === filterColumn) continue;
            
            const otherColLetter = getColumnLetter(col);
            suggestions.push({ 
                text: otherColLetter,
                type: 'column',
                description: `Column ${otherColLetter}`
            });
            
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
        for (let col = 0; col < maxCols; col++) {
            const colLetter = getColumnLetter(col);
            suggestions.push({ 
                text: colLetter,
                type: 'column',
                description: `Column ${colLetter}`
            });
        }
        
        for (let row = 0; row < maxRows; row++) {
            suggestions.push({ 
                text: (row + 1).toString(),
                type: 'row',
                description: `Row ${row + 1}`
            });
        }
        
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
    if (currentFilter) {
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
    
    cellSuggestions = cellSuggestions.slice(0, 10);
}

function parseColumnLetter(columnName) {
    let col = 0;
    if (!columnName) return -1;
    columnName = columnName.toUpperCase();
    for (let i = 0; i < columnName.length; i++) {
        const charCode = columnName.charCodeAt(i);
        if (charCode < 65 || charCode > 90) return -1;
        col = col * 26 + (charCode - 64);
    }
    return col - 1;
}

function showPopup() {
    if (!popup || cellSuggestions.length === 0) {
        hidePopup();
        return;
    }
    
    const inputRect = commandInput.getBoundingClientRect();
    const cursorCoords = getCursorCoordinates(commandInput);
    
    popup.style.left = `${inputRect.left + cursorCoords.left}px`;
    popup.style.top = `${inputRect.top + cursorCoords.top + 20}px`;
    
    popup.innerHTML = '';
    const list = document.createElement('ul');
    list.className = 'suggestion-list';
    
    cellSuggestions.forEach((suggestion, index) => {
        const item = document.createElement('li');
        item.className = `suggestion-item suggestion-${suggestion.type}`;
        item.setAttribute('data-value', suggestion.text);
        item.setAttribute('data-index', index);
        
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
            applySuggestion(suggestion.text, true);
        });
        
        list.appendChild(item);
    });
    
    popup.appendChild(list);
    popup.style.display = 'block';
    isPopupVisible = true;
}

function hidePopup() {
    if (popup) {
        popup.style.display = 'none';
        isPopupVisible = false;
    }
}

function getCursorCoordinates(input) {
    const div = document.createElement('div');
    const styles = window.getComputedStyle(input);
    
    const stylesToCopy = [
        'font-family', 'font-size', 'font-weight', 'letter-spacing',
        'line-height', 'text-transform', 'word-spacing', 'padding-left',
        'padding-top', 'padding-right', 'padding-bottom', 'width', 'height'
    ];
    
    stylesToCopy.forEach(style => {
        div.style[style] = styles[style];
    });
    
    div.textContent = input.value.substring(0, input.selectionStart);
    
    const span = document.createElement('span');
    span.textContent = '.';
    div.appendChild(span);
    
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
                e.stopPropagation();
                const selected = popup.querySelector('.selected');
                if (selected) {
                    applySuggestion(selected.getAttribute('data-value'), true);
                } else if (pendingTagSelection) {
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
                    applySuggestion(selected.getAttribute('data-value'), true);
                }
            }
            break;
    }
}

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

function applySuggestion(value) {
    if (!commandInput || lastTagPosition < 0) return;
    
    const text = commandInput.value;
    const cursorPosition = commandInput.selectionStart;
    
    const before = text.substring(0, lastTagPosition);
    const after = text.substring(cursorPosition);
    const newText = before + '#' + value + after;
    
    commandInput.value = newText;
    commandInput.setSelectionRange(lastTagPosition + 1 + value.length, lastTagPosition + 1 + value.length);
    commandInput.focus();
    
    highlightTaggedCells(value, true);
    commandInput.focus();
    hidePopup();
}

function highlightTaggedCells(value, preventFocusShift = false) {
    if (!window.hotInstance || window.hotInstance.isDestroyed) return;
    
    try {
        const displayInput = document.getElementById('cellSelectorDisplay');
        if (displayInput) {
            const activeElement = document.activeElement;
            
            displayInput.value = value;
            
            const customEvent = new CustomEvent('cellTagChange', { 
                bubbles: true,
                detail: { preventFocusShift: true }
            });
            displayInput.dispatchEvent(customEvent);
            
            if (activeElement === commandInput) {
                setTimeout(() => {
                    commandInput.focus();
                    
                    const length = commandInput.value.length;
                    commandInput.setSelectionRange(length, length);
                }, 50);
            }
        }
    } catch (error) {
        console.error('Error highlighting tagged cells:', error);
    }
}

function getColumnLetter(colIndex) {
    let result = '';
    let index = colIndex;
    
    while (index >= 0) {
        result = String.fromCharCode(65 + (index % 26)) + result;
        index = Math.floor(index / 26) - 1;
    }
    
    return result;
}

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
        const cellRef = cellRefs.join(', ');
        highlightTaggedCells(cellRef);
    }
}
