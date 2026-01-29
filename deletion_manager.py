"""
Deletion management for the title generator.
Handles title deletion, undo functionality, and full record deletion.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Set, List, Optional
import json

import config_manager as cfg
from config_manager import FileOperationError, ValidationError


# ============================================================================
# Constants
# ============================================================================

TRASH_FILE = cfg.BASE_DIR / "deleted_titles_trash.json"
MAX_TRASH_SIZE = 100  # Maximum number of titles to keep in trash


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class DeletedTitle:
    """Represents a deleted title with metadata."""
    title: str
    deleted_at: str  # ISO format timestamp
    
    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "deleted_at": self.deleted_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "DeletedTitle":
        return cls(
            title=data["title"],
            deleted_at=data.get("deleted_at", datetime.now().isoformat())
        )


@dataclass
class TrashBin:
    """
    Container for deleted titles with undo capability.
    Maintains a stack of recently deleted titles.
    """
    items: List[DeletedTitle] = field(default_factory=list)
    max_size: int = MAX_TRASH_SIZE
    
    def add(self, title: str) -> None:
        """Add a deleted title to the trash."""
        deleted = DeletedTitle(
            title=title,
            deleted_at=datetime.now().isoformat()
        )
        self.items.append(deleted)
        
        # Trim if over max size (remove oldest)
        while len(self.items) > self.max_size:
            self.items.pop(0)
    
    def add_multiple(self, titles: List[str]) -> None:
        """Add multiple deleted titles to the trash."""
        timestamp = datetime.now().isoformat()
        for title in titles:
            deleted = DeletedTitle(title=title, deleted_at=timestamp)
            self.items.append(deleted)
        
        # Trim if over max size
        while len(self.items) > self.max_size:
            self.items.pop(0)
    
    def pop_last(self) -> Optional[DeletedTitle]:
        """Remove and return the most recently deleted title."""
        if self.items:
            return self.items.pop()
        return None
    
    def peek_last(self) -> Optional[DeletedTitle]:
        """View the most recently deleted title without removing it."""
        if self.items:
            return self.items[-1]
        return None
    
    def clear(self) -> int:
        """Clear all items from trash. Returns count of cleared items."""
        count = len(self.items)
        self.items.clear()
        return count
    
    def get_all(self) -> List[DeletedTitle]:
        """Get all items in trash (newest last)."""
        return list(self.items)
    
    def is_empty(self) -> bool:
        """Check if trash is empty."""
        return len(self.items) == 0
    
    def __len__(self) -> int:
        return len(self.items)
    
    def to_dict(self) -> dict:
        return {
            "items": [item.to_dict() for item in self.items],
            "max_size": self.max_size
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TrashBin":
        trash = cls(max_size=data.get("max_size", MAX_TRASH_SIZE))
        trash.items = [DeletedTitle.from_dict(item) for item in data.get("items", [])]
        return trash


# ============================================================================
# Trash Persistence
# ============================================================================

def load_trash() -> TrashBin:
    """
    Load the trash bin from file.
    
    Returns:
        TrashBin instance with loaded or empty state
    """
    if not TRASH_FILE.exists():
        return TrashBin()
    
    try:
        with open(TRASH_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return TrashBin.from_dict(data)
    except (json.JSONDecodeError, IOError, KeyError) as e:
        print(f"Warning: Could not load trash file. Starting fresh. Error: {e}")
        return TrashBin()


def save_trash(trash: TrashBin) -> None:
    """
    Save the trash bin to file.
    
    Args:
        trash: The TrashBin instance to save
        
    Raises:
        FileOperationError: If the file cannot be written
    """
    try:
        with open(TRASH_FILE, "w", encoding="utf-8") as f:
            json.dump(trash.to_dict(), f, indent=2)
    except IOError as e:
        raise FileOperationError(f"Could not save trash: {e}")


# ============================================================================
# Deletion Operations
# ============================================================================

def delete_single_title(
    title: str,
    generated_titles: Set[str],
    trash: TrashBin
) -> None:
    """
    Delete a single title and move it to trash.
    
    Args:
        title: The title to delete
        generated_titles: The set of all generated titles (modified in place)
        trash: The trash bin to store deleted title
        
    Raises:
        ValidationError: If the title doesn't exist
        FileOperationError: If saving fails
    """
    if title not in generated_titles:
        raise ValidationError(f"Title '{title}' not found")
    
    generated_titles.remove(title)
    trash.add(title)
    
    cfg.save_all_titles(generated_titles)
    save_trash(trash)


def delete_all_titles(
    generated_titles: Set[str],
    trash: TrashBin,
    save_to_trash: bool = True
) -> int:
    """
    Delete all titles from the record.
    
    Args:
        generated_titles: The set of all generated titles (modified in place)
        trash: The trash bin to store deleted titles
        save_to_trash: Whether to save deleted titles to trash (default True)
        
    Returns:
        Number of titles deleted
        
    Raises:
        FileOperationError: If saving fails
    """
    count = len(generated_titles)
    
    if count == 0:
        return 0
    
    if save_to_trash:
        # Add all to trash (sorted for consistency)
        trash.add_multiple(sorted(generated_titles))
        save_trash(trash)
    
    generated_titles.clear()
    cfg.save_all_titles(generated_titles)
    
    return count


def undo_last_delete(
    generated_titles: Set[str],
    trash: TrashBin
) -> Optional[str]:
    """
    Restore the most recently deleted title.
    
    Args:
        generated_titles: The set of all generated titles (modified in place)
        trash: The trash bin to restore from
        
    Returns:
        The restored title, or None if trash is empty
        
    Raises:
        ValidationError: If the title already exists (was re-generated)
        FileOperationError: If saving fails
    """
    deleted = trash.pop_last()
    
    if deleted is None:
        return None
    
    if deleted.title in generated_titles:
        # Title was re-generated, put it back in trash and raise error
        trash.items.append(deleted)
        raise ValidationError(f"Title '{deleted.title}' already exists (was re-generated)")
    
    generated_titles.add(deleted.title)
    
    cfg.save_all_titles(generated_titles)
    save_trash(trash)
    
    return deleted.title


def undo_multiple_deletes(
    generated_titles: Set[str],
    trash: TrashBin,
    count: int
) -> List[str]:
    """
    Restore multiple recently deleted titles.
    
    Args:
        generated_titles: The set of all generated titles (modified in place)
        trash: The trash bin to restore from
        count: Number of titles to restore
        
    Returns:
        List of restored titles
        
    Raises:
        FileOperationError: If saving fails
    """
    restored = []
    skipped = []
    
    for _ in range(count):
        deleted = trash.pop_last()
        if deleted is None:
            break
        
        if deleted.title in generated_titles:
            # Skip titles that were re-generated
            skipped.append(deleted)
            continue
        
        generated_titles.add(deleted.title)
        restored.append(deleted.title)
    
    # Put back skipped items
    for item in reversed(skipped):
        trash.items.append(item)
    
    if restored:
        cfg.save_all_titles(generated_titles)
        save_trash(trash)
    
    return restored


def clear_trash(trash: TrashBin) -> int:
    """
    Permanently clear all items from trash.
    
    Args:
        trash: The trash bin to clear
        
    Returns:
        Number of items cleared
        
    Raises:
        FileOperationError: If saving fails
    """
    count = trash.clear()
    save_trash(trash)
    return count


def view_trash(trash: TrashBin) -> List[DeletedTitle]:
    """
    Get all items in the trash bin.
    
    Args:
        trash: The trash bin to view
        
    Returns:
        List of DeletedTitle items (oldest first, newest last)
    """
    return trash.get_all()
