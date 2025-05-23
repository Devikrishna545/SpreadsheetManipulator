"""
Modification History module
-------------------------
Tracks modifications to a spreadsheet with undo/redo functionality
"""

from typing import List, Optional
from src.model.spreadsheet import Spreadsheet


class ModificationHistory:
    """
    Tracks spreadsheet modifications and provides undo/redo functionality
    """
    
    def __init__(self):
        """Initialize modification history"""
        self.states: List[Spreadsheet] = []
        self.current_position = -1
    
    def add_state(self, spreadsheet: Spreadsheet) -> None:
        """
        Add a new state to the history

        Args:
            spreadsheet: The spreadsheet state to add
        """
        # If we're not at the end of the history, remove future states
        if self.current_position < len(self.states) - 1:
            self.states = self.states[:self.current_position + 1]
        
        # Add the new state
        self.states.append(spreadsheet)
        self.current_position += 1
    
    def can_undo(self) -> bool:
        """
        Check if undo is available

        Returns:
            bool: True if undo is available, False otherwise
        """
        return self.current_position > 0
    
    def can_redo(self) -> bool:
        """
        Check if redo is available

        Returns:
            bool: True if redo is available, False otherwise
        """
        return self.current_position < len(self.states) - 1
    
    def undo(self) -> Optional[Spreadsheet]:
        """
        Undo to previous state

        Returns:
            Optional[Spreadsheet]: Previous state if available, None otherwise
        """
        if not self.can_undo():
            return None
        
        self.current_position -= 1
        return self.states[self.current_position]
    
    def redo(self) -> Optional[Spreadsheet]:
        """
        Redo to next state

        Returns:
            Optional[Spreadsheet]: Next state if available, None otherwise
        """
        if not self.can_redo():
            return None
        
        self.current_position += 1
        return self.states[self.current_position]
    
    def get_current_state(self) -> Optional[Spreadsheet]:
        """
        Get the current state

        Returns:
            Optional[Spreadsheet]: Current state if available, None otherwise
        """
        if not self.states or self.current_position < 0:
            return None
        
        return self.states[self.current_position]
