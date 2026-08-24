"""
menu_system.py

Reusable menu system for game configuration.
"""

from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class MenuItem:
    """Single menu item with label and options."""
    label: str
    options: List[Any]
    current_index: int = 0

    def get_current(self) -> Any:
        """Get currently selected option."""
        return self.options[self.current_index]

    def cycle(self, delta: int) -> None:
        """Cycle through options by delta (-1 or +1)."""
        self.current_index = (self.current_index + delta) % len(self.options)

    def set_value(self, value: Any) -> bool:
        """Set current value if it exists in options. Returns True if successful."""
        if value in self.options:
            self.current_index = self.options.index(value)
            return True
        return False


class MenuSystem:
    """Manages a collection of menu items."""

    def __init__(self, items: Optional[List[Tuple[str, List[Any], int]]] = None):
        """
        Initialize with list of (label, options, initial_index) tuples.
        """
        self.items: Dict[str, MenuItem] = {}
        if items:
            for label, options, initial_index in items:
                self.add_item(label, options, initial_index)

    def add_item(self, label: str, options: List[Any], initial_index: int = 0) -> None:
        """Add a menu item."""
        self.items[label] = MenuItem(label, options, initial_index)

    def get_item(self, label: str) -> Optional[MenuItem]:
        """Get menu item by label."""
        return self.items.get(label)

    def get_selection(self, label: str) -> Any:
        """Get current selection for a menu item."""
        item = self.items.get(label)
        return item.get_current() if item else None

    def get_all_selections(self) -> Dict[str, Any]:
        """Get all current selections as a dictionary."""
        return {label: item.get_current() for label, item in self.items.items()}

    def cycle_item(self, label: str, delta: int) -> None:
        """Cycle a menu item's selection."""
        item = self.items.get(label)
        if item:
            item.cycle(delta)

    def set_selection(self, label: str, value: Any) -> bool:
        """Set selection for a menu item. Returns True if successful."""
        item = self.items.get(label)
        if item:
            return item.set_value(value)
        return False

    def get_labels(self) -> List[str]:
        """Get all menu item labels in order."""
        return list(self.items.keys())

    def to_list(self) -> List[Tuple[str, List[Any], int]]:
        """Export as list of tuples for compatibility."""
        return [(item.label, item.options, item.current_index)
                for item in self.items.values()]
