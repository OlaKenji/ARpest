"""
File stack model for managing processing states.

Each file has a raw dataset plus a history of processed states.
Users can navigate through states (undo/redo) and add new processing operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .dataset import Dataset


@dataclass
class FileStack:
    """
    Manages a file with its processing history.
    
    The FileStack maintains:
    - Original raw data (never modified)
    - List of processed states
    - Current position in state history
    
    Attributes:
        filename: Original filename
        raw_data: Unmodified original data
        states: List of datasets (including raw)
        state_names: Human-readable names for each state
        current_index: Index of currently active state
    """

    filename: str
    raw_data: Dataset
    states: list[Dataset] = field(default_factory=list)
    state_names: list[str] = field(default_factory=list)
    current_index: int = 0

    def __post_init__(self) -> None:
        """Initialize with raw state if states list is empty."""
        if not self.states:
            self.states = [self.raw_data]
            self.state_names = ["raw"]
            self.current_index = 0

    @property
    def current_state(self) -> Dataset:
        """Get currently active dataset."""
        return self.states[self.current_index]

    @property
    def current_name(self) -> str:
        """Get name of current state."""
        return self.state_names[self.current_index]

    @property
    def num_states(self) -> int:
        """Total number of states."""
        return len(self.states)

    @property
    def can_undo(self) -> bool:
        """Check if undo is possible."""
        return self.current_index > 0

    @property
    def can_redo(self) -> bool:
        """Check if redo is possible."""
        return self.current_index < len(self.states) - 1

    def add_state(self, dataset: Dataset, name: str) -> None:
        """
        Add a new processed state.
        
        If we're not at the end of the history, this will remove
        all states after the current position (like a new branch).
        
        Args:
            dataset: Processed dataset to add
            name: Human-readable name for this state
        """
        # Remove any states after current position
        self.states = self.states[: self.current_index + 1]
        self.state_names = self.state_names[: self.current_index + 1]

        # Add new state
        self.states.append(dataset)
        self.state_names.append(name)
        self.current_index = len(self.states) - 1

    def delete_state(self, index: Optional[int] = None) -> bool:
        """
        Delete a state from history.
        
        Cannot delete the raw state (index 0).
        
        Args:
            index: Index to delete (default: current state)
            
        Returns:
            True if deleted, False if not allowed
        """
        if index is None:
            index = self.current_index

        # Protect raw state
        if index == 0:
            return False

        # Remove state
        del self.states[index]
        del self.state_names[index]

        # Adjust current index if needed
        if self.current_index >= index:
            self.current_index = max(0, self.current_index - 1)

        return True

    def goto_state(self, index: int) -> None:
        """
        Jump to a specific state.
        
        Args:
            index: State index to jump to
            
        Raises:
            IndexError: If index out of range
        """
        if not 0 <= index < len(self.states):
            raise IndexError(f"State index {index} out of range [0, {len(self.states)})")
        self.current_index = index

    def next_state(self) -> bool:
        """
        Move to next state (redo).
        
        Returns:
            True if moved, False if already at end
        """
        if self.can_redo:
            self.current_index += 1
            return True
        return False

    def previous_state(self) -> bool:
        """
        Move to previous state (undo).
        
        Returns:
            True if moved, False if already at beginning
        """
        if self.can_undo:
            self.current_index -= 1
            return True
        return False

    def reset_to_raw(self) -> None:
        """Reset to raw state (index 0)."""
        self.current_index = 0

    def get_state_info(self) -> list[tuple[int, str, bool]]:
        """
        Get information about all states.
        
        Returns:
            List of (index, name, is_current) tuples
        """
        return [
            (i, name, i == self.current_index)
            for i, name in enumerate(self.state_names)
        ]
