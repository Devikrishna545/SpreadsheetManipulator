"""Modification History module for tracking spreadsheet modifications with undo/redo functionality"""

from typing import List, Optional
from src.model.spreadsheet_manager import SpreadsheetManager

class ModificationHistory:
    """Tracks spreadsheet modifications and provides undo/redo functionality"""
    
    def __init__(self):
        """Initialize modification history"""
        self.states: List[SpreadsheetManager] = []
        self.current_position = -1
    
    def add_state(self, spreadsheet: SpreadsheetManager) -> None:
        """Add a new state to the history"""
        if self.current_position < len(self.states) - 1:
            self.states = self.states[:self.current_position + 1]
        
        self.states.append(spreadsheet)
        self.current_position += 1
    
    def can_undo(self) -> bool:
        """Check if undo is available"""
        return self.current_position > 0
    
    def can_redo(self) -> bool:
        """Check if redo is available"""
        return self.current_position < len(self.states) - 1
    
    def undo(self) -> Optional[SpreadsheetManager]:
        """Undo to previous state"""
        if not self.can_undo():
            return None
        
        self.current_position -= 1
        return self.states[self.current_position]
    
    def redo(self) -> Optional[SpreadsheetManager]:
        """Redo to next state"""
        if not self.can_redo():
            return None
        
        self.current_position += 1
        return self.states[self.current_position]
    
    def get_current_state(self) -> Optional[SpreadsheetManager]:
        """Get the current state"""
        if not self.states or self.current_position < 0:
            return None
        
        return self.states[self.current_position]
