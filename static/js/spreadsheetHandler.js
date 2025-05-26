import { showLoading, hideLoading, showError } from './uiInteractions.js';
import { updateUndoRedoButtons } from './uiInteractions.js';


const spreadsheetDataContainer = document.getElementById('spreadsheetData');

export function renderSpreadsheet(data) { // data is currentData from main.js
    if (!data || !data.data) return;
    
    if (window.hotInstance) {
        window.hotInstance.destroy();
    }
    
    const settings = {
        data: data.data,
        rowHeaders: true,
        colHeaders: data.headers,
        licenseKey: 'non-commercial-and-evaluation',
        stretchH: 'all',
        readOnly: true,
        contextMenu: false,
        manualColumnResize: true,
        manualRowResize: true,
        className: 'htDark',
        afterRender: function() {
            this.rootElement.classList.add('handsontable-dark');
        }
    };
    
    window.hotInstance = new Handsontable(spreadsheetDataContainer, settings);
    
    if (data.modified_cells && data.modified_cells.length > 0) {
        highlightModifiedCells(data.modified_cells);
    }
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
